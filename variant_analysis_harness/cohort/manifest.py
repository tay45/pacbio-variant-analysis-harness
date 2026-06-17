"""Multi-sample cohort manifest parsing and validation."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.paths import resolve_path, safe_name
from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.exceptions import ManifestError
from variant_analysis_harness.models import VALID_ANALYSES

SUPPORTED_PLATFORMS = {"pacbio_hifi"}
SUPPORTED_INPUT_TYPES = {
    "aligned_bam",
    "unaligned_bam",
    "pacbio_dataset_xml",
    "pacbio_dataset_xml_list",
}
REQUIRED_COLUMNS = {
    "sample_id",
    "platform",
    "input_type",
    "input_path",
    "additional_inputs",
    "aligned",
    "reference_id",
    "read_group_sample",
    "output_prefix",
    "analysis",
    "enabled",
    "cohort_group",
    "priority",
}
OPTIONAL_COLUMNS = {"family_id", "population_group", "batch_id", "library_id", "sex", "notes"}
RERUN_METADATA_COLUMNS = {
    "rerun_source_cohort",
    "rerun_source_attempt",
    "rerun_reason",
    "rerun_stage",
    "rerun_failure_category",
}


@dataclass(frozen=True)
class CohortSample:
    row_number: int
    sample_id: str
    platform: str
    input_type: str
    input_path: Path
    additional_inputs: tuple[Path, ...]
    aligned: bool
    reference_id: str
    read_group_sample: str
    output_prefix: str
    analysis: str
    enabled: bool
    cohort_group: str = ""
    priority: int = 0
    optional: dict[str, str] = field(default_factory=dict)
    original_row: dict[str, str] = field(default_factory=dict)
    row_hash: str = ""


@dataclass
class CohortValidationResult:
    status: str
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    samples: list[CohortSample]
    excluded_samples: list[CohortSample]
    stage_counts: dict[str, int]
    tool_requirements: dict[str, list[str]]
    expected_array_tasks: int
    max_concurrent: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "selected_samples": len(self.samples),
            "excluded_samples": len(self.excluded_samples),
            "stage_counts": self.stage_counts,
            "tool_requirements": self.tool_requirements,
            "expected_array_tasks": self.expected_array_tasks,
            "max_concurrent": self.max_concurrent,
        }


def load_cohort_manifest(
    path: Path,
    *,
    require_existing: bool = False,
    max_rows: int | None = None,
    include_samples: set[str] | None = None,
    exclude_samples: set[str] | None = None,
) -> tuple[list[CohortSample], list[CohortSample], CohortValidationResult]:
    base_dir = path.parent.resolve()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ManifestError("Cohort manifest is missing a header")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ManifestError(f"Cohort manifest missing required columns: {sorted(missing)}")
        raw_rows = list(reader)
    if max_rows is not None and len(raw_rows) > max_rows:
        raise ManifestError(f"Cohort manifest has {len(raw_rows)} rows; configured maximum is {max_rows}")
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    selected: list[CohortSample] = []
    excluded: list[CohortSample] = []
    for offset, row in enumerate(raw_rows, start=2):
        try:
            sample = _row_to_cohort_sample(row, offset, base_dir, require_existing=require_existing)
        except ManifestError as exc:
            errors.append({"row": offset, "message": str(exc)})
            continue
        filter_excluded = False
        if include_samples is not None and sample.sample_id not in include_samples:
            filter_excluded = True
        if exclude_samples is not None and sample.sample_id in exclude_samples:
            filter_excluded = True
        if sample.enabled and not filter_excluded:
            selected.append(sample)
        else:
            excluded.append(sample)
    _cross_validate(selected, excluded, errors, warnings)
    selected = sorted(selected, key=lambda s: (s.priority, s.sample_id))
    excluded = sorted(excluded, key=lambda s: (s.priority, s.sample_id))
    result = build_validation_result(selected, excluded, errors, warnings)
    return selected, excluded, result


def build_validation_result(
    selected: list[CohortSample],
    excluded: list[CohortSample],
    errors: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    max_concurrent: int = 1,
) -> CohortValidationResult:
    errors = errors or []
    warnings = warnings or []
    stage_counts: dict[str, int] = {}
    tool_requirements: dict[str, set[str]] = {}
    for sample in selected:
        for stage in required_stages(sample):
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            for tool in tools_for_stage(stage):
                tool_requirements.setdefault(tool, set()).add(stage)
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return CohortValidationResult(
        status=status,
        errors=errors,
        warnings=warnings,
        samples=selected,
        excluded_samples=excluded,
        stage_counts=stage_counts,
        tool_requirements={k: sorted(v) for k, v in sorted(tool_requirements.items())},
        expected_array_tasks=len(selected),
        max_concurrent=max_concurrent,
    )


def required_stages(sample: CohortSample) -> list[str]:
    stages = ["preflight"]
    if sample.input_type == "pacbio_dataset_xml_list":
        stages.append("dataset_merge")
    if sample.input_type != "aligned_bam":
        stages.append("alignment")
    else:
        stages.append("alignment_reuse")
    stages.append("alignment_qc")
    if sample.analysis in {"snv", "combined"}:
        stages.extend(["germline_snv", "germline_snv_qc"])
    if sample.analysis in {"sv", "combined"}:
        stages.extend(["germline_sv_discover", "germline_sv_call", "germline_sv_qc"])
    stages.append("sample_report")
    return stages


def tools_for_stage(stage: str) -> list[str]:
    return {
        "dataset_merge": ["dataset"],
        "alignment": ["pbmm2", "samtools"],
        "alignment_reuse": ["samtools"],
        "alignment_qc": ["samtools"],
        "germline_snv": ["deepvariant"],
        "germline_snv_qc": ["bcftools", "tabix"],
        "germline_sv_discover": ["pbsv"],
        "germline_sv_call": ["pbsv"],
        "germline_sv_qc": ["bcftools", "tabix"],
    }.get(stage, [])


def write_resolved_manifest(samples: list[CohortSample], excluded: list[CohortSample], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "platform",
        "input_type",
        "input_path",
        "additional_inputs",
        "aligned",
        "reference_id",
        "read_group_sample",
        "output_prefix",
        "analysis",
        "enabled",
        "cohort_group",
        "priority",
        "manifest_row_hash",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for sample in samples + excluded:
            writer.writerow(_sample_to_row(sample))


def write_validation_artifacts(result: CohortValidationResult, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cohort_manifest.validation.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Cohort Manifest Validation",
        "",
        f"Status: {result.status}",
        f"Selected samples: {len(result.samples)}",
        f"Excluded samples: {len(result.excluded_samples)}",
        f"Expected array tasks: {result.expected_array_tasks}",
        "",
        "## Errors",
    ]
    lines.extend(_issue_lines(result.errors))
    lines.append("")
    lines.append("## Warnings")
    lines.extend(_issue_lines(result.warnings))
    lines.append("")
    lines.append("## Stage Counts")
    for stage, count in sorted(result.stage_counts.items()):
        lines.append(f"- {stage}: {count}")
    (out_dir / "cohort_manifest.validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def manifest_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        return next(reader)


def _row_to_cohort_sample(row: dict[str, str], row_number: int, base_dir: Path, *, require_existing: bool) -> CohortSample:
    try:
        sample_id = safe_name(row.get("sample_id", ""), "sample_id")
        output_prefix = safe_name(row.get("output_prefix") or sample_id, "output_prefix")
        read_group_sample = safe_name(row.get("read_group_sample") or sample_id, "read_group_sample")
    except ValueError as exc:
        raise ManifestError(f"row {row_number}: {exc}") from exc
    platform = row.get("platform", "")
    if platform not in SUPPORTED_PLATFORMS:
        raise ManifestError(f"row {row_number} {sample_id}: unsupported platform {platform!r}")
    input_type = row.get("input_type", "")
    if input_type not in SUPPORTED_INPUT_TYPES:
        raise ManifestError(f"row {row_number} {sample_id}: unsupported input_type {input_type!r}")
    analysis = row.get("analysis", "combined")
    if analysis not in VALID_ANALYSES:
        raise ManifestError(f"row {row_number} {sample_id}: analysis must be one of {sorted(VALID_ANALYSES)}")
    aligned = _parse_bool(row.get("aligned", ""), "aligned", row_number)
    enabled = _parse_bool(row.get("enabled", "true"), "enabled", row_number)
    if input_type == "aligned_bam" and not aligned:
        raise ManifestError(f"row {row_number} {sample_id}: input_type aligned_bam requires aligned=true")
    if input_type != "aligned_bam" and aligned:
        raise ManifestError(f"row {row_number} {sample_id}: only aligned_bam may set aligned=true")
    input_path = resolve_path(row.get("input_path", ""), base_dir)
    if input_path is None:
        raise ManifestError(f"row {row_number} {sample_id}: input_path is required")
    additional_inputs = tuple(
        p
        for p in (
            resolve_path(value.strip(), base_dir)
            for value in row.get("additional_inputs", "").split(",")
            if value.strip()
        )
        if p is not None
    )
    if input_type == "pacbio_dataset_xml_list" and not additional_inputs:
        raise ManifestError(f"row {row_number} {sample_id}: pacbio_dataset_xml_list requires additional_inputs")
    paths = (input_path,) + additional_inputs
    if len(set(paths)) != len(paths):
        raise ManifestError(f"row {row_number} {sample_id}: duplicate input path detected within row")
    if require_existing:
        for item in paths:
            if not item.exists() or not item.is_file():
                raise ManifestError(f"row {row_number} {sample_id}: input does not exist: {item}")
    priority = _parse_priority(row.get("priority", "0"), row_number, sample_id)
    optional = {key: row.get(key, "") for key in OPTIONAL_COLUMNS if key in row}
    normalized = {
        "sample_id": sample_id,
        "platform": platform,
        "input_type": input_type,
        "input_path": str(input_path),
        "additional_inputs": [str(p) for p in additional_inputs],
        "aligned": aligned,
        "reference_id": row.get("reference_id", ""),
        "read_group_sample": read_group_sample,
        "output_prefix": output_prefix,
        "analysis": analysis,
        "enabled": enabled,
        "cohort_group": row.get("cohort_group", ""),
        "priority": priority,
        "optional": optional,
    }
    return CohortSample(
        row_number=row_number,
        sample_id=sample_id,
        platform=platform,
        input_type=input_type,
        input_path=input_path,
        additional_inputs=additional_inputs,
        aligned=aligned,
        reference_id=row.get("reference_id", ""),
        read_group_sample=read_group_sample,
        output_prefix=output_prefix,
        analysis=analysis,
        enabled=enabled,
        cohort_group=row.get("cohort_group", ""),
        priority=priority,
        optional=optional,
        original_row=dict(row),
        row_hash=object_signature(normalized),
    )


def _cross_validate(
    selected: list[CohortSample],
    excluded: list[CohortSample],
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    all_samples = selected + excluded
    _duplicate_error(all_samples, "sample_id", [s.sample_id for s in all_samples], errors)
    _duplicate_error(all_samples, "output_prefix", [s.output_prefix for s in all_samples], errors)
    _duplicate_warning(selected, "input_path", [str(s.input_path) for s in selected], warnings)
    _duplicate_warning(selected, "read_group_sample", [s.read_group_sample for s in selected], warnings)
    references = {s.reference_id for s in selected if s.reference_id}
    if len(references) > 1:
        errors.append({"scope": "cohort", "message": f"Selected samples use multiple reference_id values: {sorted(references)}"})


def _duplicate_error(samples: list[CohortSample], label: str, values: list[str], errors: list[dict[str, Any]]) -> None:
    seen: dict[str, int] = {}
    for sample, value in zip(samples, values):
        if value in seen:
            errors.append({"row": sample.row_number, "message": f"duplicate {label}: {value}"})
        seen[value] = sample.row_number


def _duplicate_warning(samples: list[CohortSample], label: str, values: list[str], warnings: list[dict[str, Any]]) -> None:
    seen: dict[str, int] = {}
    for sample, value in zip(samples, values):
        if value and value in seen:
            warnings.append({"row": sample.row_number, "message": f"duplicate {label}: {value}"})
        seen[value] = sample.row_number


def _parse_bool(value: str, label: str, row_number: int) -> bool:
    lower = str(value).strip().lower()
    if lower in {"true", "1", "yes", "y"}:
        return True
    if lower in {"false", "0", "no", "n"}:
        return False
    raise ManifestError(f"row {row_number}: malformed boolean for {label}: {value!r}")


def _parse_priority(value: str, row_number: int, sample_id: str) -> int:
    if str(value).strip() == "":
        return 0
    try:
        return int(value)
    except ValueError as exc:
        raise ManifestError(f"row {row_number} {sample_id}: priority must be an integer") from exc


def _sample_to_row(sample: CohortSample) -> dict[str, Any]:
    return {
        "sample_id": sample.sample_id,
        "platform": sample.platform,
        "input_type": sample.input_type,
        "input_path": str(sample.input_path),
        "additional_inputs": ",".join(str(p) for p in sample.additional_inputs),
        "aligned": str(sample.aligned).lower(),
        "reference_id": sample.reference_id,
        "read_group_sample": sample.read_group_sample,
        "output_prefix": sample.output_prefix,
        "analysis": sample.analysis,
        "enabled": str(sample.enabled).lower(),
        "cohort_group": sample.cohort_group,
        "priority": sample.priority,
        "manifest_row_hash": sample.row_hash,
    }


def _issue_lines(issues: list[dict[str, Any]]) -> list[str]:
    if not issues:
        return ["- none"]
    return [f"- {issue}" for issue in issues]

