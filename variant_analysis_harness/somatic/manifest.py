"""Somatic manifest parsing, validation, and resolved manifest writing."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.exceptions import ManifestError
from variant_analysis_harness.somatic.failures import SOMATIC_FAILURE_CATEGORIES

REQUIRED_COLUMNS = {
    "pair_id",
    "subject_id",
    "tumor_sample_id",
    "tumor_specimen_id",
    "tumor_input_type",
    "tumor_input_path",
    "tumor_index_path",
    "normal_sample_id",
    "normal_specimen_id",
    "normal_input_type",
    "normal_input_path",
    "normal_index_path",
    "reference_id",
    "analysis_mode",
    "enabled",
}

OPTIONAL_COLUMNS = {
    "tumor_library_id",
    "normal_library_id",
    "tumor_read_group_sample",
    "normal_read_group_sample",
    "tumor_coverage",
    "normal_coverage",
    "tumor_purity",
    "normal_contamination",
    "tumor_contamination",
    "tumor_ploidy",
    "sex",
    "disease_label",
    "collection_site",
    "tumor_stage",
    "batch_id",
    "notes",
    "tumor_only_acknowledgment",
    "reference_signature",
    "tumor_reference_signature",
    "normal_reference_signature",
    "tumor_contigs",
    "normal_contigs",
    "tumor_sort_order",
    "normal_sort_order",
    "metadata_source_method",
    "metadata_source_file",
    "metadata_confidence",
    "metadata_timestamp",
}

SUPPORTED_INPUT_TYPES = {"BAM", "CRAM", "bam", "cram"}
SUPPORTED_MODES = {"tumor_normal", "tumor_only"}
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class SomaticPair:
    row_number: int
    pair_id: str
    subject_id: str
    tumor_sample_id: str
    tumor_specimen_id: str
    tumor_input_type: str
    tumor_input_path: Path
    tumor_index_path: Path | None
    normal_sample_id: str
    normal_specimen_id: str
    normal_input_type: str
    normal_input_path: Path | None
    normal_index_path: Path | None
    reference_id: str
    analysis_mode: str
    enabled: bool
    optional: dict[str, str] = field(default_factory=dict)
    original_row: dict[str, str] = field(default_factory=dict)
    row_hash: str = ""

    @property
    def is_tumor_only(self) -> bool:
        return self.analysis_mode == "tumor_only"


@dataclass
class SomaticManifestValidationResult:
    status: str
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    selected_pairs: list[SomaticPair]
    excluded_pairs: list[SomaticPair]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "selected_pair_count": len(self.selected_pairs),
            "excluded_pair_count": len(self.excluded_pairs),
        }


def default_somatic_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "mode": "tumor_normal",
        "identity_policy": "strict",
        "tumor_only": {"allowed": False, "acknowledgment_required": True, "acknowledgment_text": None},
        "normal_reuse": {"allowed": False, "maximum_pairs_per_normal": 1},
        "preflight": {
            "require_aligned_inputs": True,
            "require_indexes": True,
            "require_matching_reference": True,
            "require_matching_contig_order": True,
            "require_read_groups": True,
            "require_sample_names": True,
            "minimum_tumor_coverage": None,
            "minimum_normal_coverage": None,
            "maximum_tumor_normal_coverage_ratio": None,
            "minimum_tumor_normal_coverage_ratio": None,
        },
        "metadata": {
            "require_purity": False,
            "require_ploidy": False,
            "require_contamination_estimate": False,
            "require_sex": False,
            "require_source_for_values": False,
        },
        "execution": {"backend": "local", "max_concurrent_pairs": 1},
        "outputs": {"root": None},
        "small_variants": {
            "enabled": False,
            "backend": "deepsomatic",
        },
        "structural_variants": {
            "enabled": False,
            "backend": "severus",
        },
        "integrated": {
            "enabled": False,
        },
        "warning_pairs_active": True,
    }


def resolve_somatic_config(cfg: dict[str, Any]) -> dict[str, Any]:
    resolved = default_somatic_config()
    supplied = cfg.get("somatic", {}) or {}
    _merge_dict(resolved, supplied)
    return resolved


def _merge_dict(target: dict[str, Any], supplied: dict[str, Any]) -> None:
    for key, value in supplied.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value


def load_somatic_manifest(
    path: Path,
    *,
    somatic_config: dict[str, Any] | None = None,
    require_existing: bool = False,
    include_pairs: set[str] | None = None,
    exclude_pairs: set[str] | None = None,
    include_subjects: set[str] | None = None,
    exclude_subjects: set[str] | None = None,
) -> tuple[list[SomaticPair], list[SomaticPair], SomaticManifestValidationResult]:
    config = somatic_config or default_somatic_config()
    base_dir = path.parent.resolve()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ManifestError("Somatic manifest is missing a header")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ManifestError(f"Somatic manifest missing required columns: {sorted(missing)}")
        raw_rows = list(reader)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    selected: list[SomaticPair] = []
    excluded: list[SomaticPair] = []
    for row_number, row in enumerate(raw_rows, start=2):
        try:
            pair = _row_to_pair(row, row_number, base_dir)
        except ManifestError as exc:
            errors.append({"row": row_number, "pair_id": row.get("pair_id", ""), "category": "somatic_manifest_error", "message": str(exc)})
            continue
        row_errors, row_warnings = validate_pair_row(pair, config, require_existing=require_existing)
        errors.extend(row_errors)
        warnings.extend(row_warnings)
        filter_excluded = False
        if include_pairs is not None and pair.pair_id not in include_pairs:
            filter_excluded = True
        if exclude_pairs is not None and pair.pair_id in exclude_pairs:
            filter_excluded = True
        if include_subjects is not None and pair.subject_id not in include_subjects:
            filter_excluded = True
        if exclude_subjects is not None and pair.subject_id in exclude_subjects:
            filter_excluded = True
        if pair.enabled and not filter_excluded:
            selected.append(pair)
        else:
            excluded.append(pair)
    cross_errors, cross_warnings = cross_validate_pairs(selected, config)
    errors.extend(cross_errors)
    warnings.extend(cross_warnings)
    selected = sorted(selected, key=lambda pair: pair.pair_id)
    excluded = sorted(excluded, key=lambda pair: pair.pair_id)
    result = build_manifest_validation_result(selected, excluded, errors, warnings)
    return selected, excluded, result


def _row_to_pair(row: dict[str, str], row_number: int, base_dir: Path) -> SomaticPair:
    normalized = {key: (value or "").strip() for key, value in row.items()}
    analysis_mode = normalized["analysis_mode"] or "tumor_normal"
    enabled = _parse_bool(normalized["enabled"])
    tumor_input = _resolve_manifest_path(normalized["tumor_input_path"], base_dir)
    tumor_index = _resolve_optional_path(normalized["tumor_index_path"], base_dir)
    normal_input = _resolve_optional_path(normalized["normal_input_path"], base_dir)
    normal_index = _resolve_optional_path(normalized["normal_index_path"], base_dir)
    optional = {key: normalized.get(key, "") for key in OPTIONAL_COLUMNS if key in normalized}
    row_hash = object_signature({k: normalized.get(k, "") for k in sorted(normalized)})
    return SomaticPair(
        row_number=row_number,
        pair_id=normalized["pair_id"],
        subject_id=normalized["subject_id"],
        tumor_sample_id=normalized["tumor_sample_id"],
        tumor_specimen_id=normalized["tumor_specimen_id"],
        tumor_input_type=normalized["tumor_input_type"],
        tumor_input_path=tumor_input,
        tumor_index_path=tumor_index,
        normal_sample_id=normalized["normal_sample_id"],
        normal_specimen_id=normalized["normal_specimen_id"],
        normal_input_type=normalized["normal_input_type"],
        normal_input_path=normal_input,
        normal_index_path=normal_index,
        reference_id=normalized["reference_id"],
        analysis_mode=analysis_mode,
        enabled=enabled,
        optional=optional,
        original_row=normalized,
        row_hash=row_hash,
    )


def validate_pair_row(pair: SomaticPair, config: dict[str, Any], *, require_existing: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for field, value in {
        "pair_id": pair.pair_id,
        "subject_id": pair.subject_id,
        "tumor_sample_id": pair.tumor_sample_id,
        "tumor_specimen_id": pair.tumor_specimen_id,
        "reference_id": pair.reference_id,
    }.items():
        if not value:
            errors.append(_issue(pair, "somatic_manifest_error", f"{field} is required"))
        elif not SAFE_ID_RE.match(value):
            errors.append(_issue(pair, "somatic_manifest_error", f"{field} contains unsafe characters"))
    if pair.analysis_mode not in SUPPORTED_MODES:
        errors.append(_issue(pair, "somatic_manifest_error", f"unsupported analysis_mode {pair.analysis_mode!r}"))
    project_mode = config.get("mode", "tumor_normal")
    if project_mode != pair.analysis_mode and project_mode != "tumor_normal":
        errors.append(_issue(pair, "somatic_manifest_error", "analysis mode does not match project policy"))
    _validate_input_type(pair, "tumor", pair.tumor_input_type, errors)
    if pair.analysis_mode == "tumor_normal":
        if not pair.normal_sample_id or not pair.normal_specimen_id or pair.normal_input_path is None:
            errors.append(_issue(pair, "missing_normal_input", "tumor-normal mode requires normal sample, specimen, and input"))
        _validate_input_type(pair, "normal", pair.normal_input_type, errors)
    else:
        tumor_only = config.get("tumor_only", {})
        if not tumor_only.get("allowed", False):
            errors.append(_issue(pair, "tumor_only_not_allowed", "tumor-only analysis is disabled by project policy"))
        if tumor_only.get("acknowledgment_required", True) and not pair.optional.get("tumor_only_acknowledgment"):
            errors.append(_issue(pair, "tumor_only_acknowledgment_missing", "tumor-only acknowledgment is required"))
        warnings.append(_issue(pair, "unknown", "tumor-only analysis has reduced somatic specificity and requires study-specific review"))
    if pair.normal_input_path is not None and pair.tumor_input_path == pair.normal_input_path:
        errors.append(_issue(pair, "tumor_normal_identity_collision", "tumor and normal input paths must differ"))
    if pair.analysis_mode == "tumor_normal" and pair.tumor_sample_id == pair.normal_sample_id:
        errors.append(_issue(pair, "tumor_normal_identity_collision", "tumor and normal sample IDs must differ under strict policy"))
    if pair.analysis_mode == "tumor_normal" and pair.tumor_specimen_id == pair.normal_specimen_id:
        errors.append(_issue(pair, "tumor_normal_identity_collision", "tumor and normal specimen IDs must differ"))
    if config.get("preflight", {}).get("require_indexes", True):
        if pair.tumor_index_path is None:
            errors.append(_issue(pair, "missing_tumor_index", "tumor index path is required"))
        if pair.analysis_mode == "tumor_normal" and pair.normal_index_path is None:
            errors.append(_issue(pair, "missing_normal_index", "normal index path is required"))
    if require_existing:
        _validate_existing_input(pair, "tumor", pair.tumor_input_path, pair.tumor_index_path, errors)
        if pair.analysis_mode == "tumor_normal" and pair.normal_input_path is not None:
            _validate_existing_input(pair, "normal", pair.normal_input_path, pair.normal_index_path, errors)
    errors.extend(validate_numeric_metadata(pair, config))
    return errors, warnings


def cross_validate_pairs(pairs: list[SomaticPair], config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen_pairs: dict[str, SomaticPair] = {}
    seen_tumors: dict[str, SomaticPair] = {}
    normal_counts: dict[tuple[str, str], list[SomaticPair]] = {}
    for pair in pairs:
        if pair.pair_id in seen_pairs:
            errors.append(_issue(pair, "duplicate_pair_id", f"duplicate pair_id {pair.pair_id}"))
        seen_pairs[pair.pair_id] = pair
        if pair.tumor_sample_id in seen_tumors:
            errors.append(_issue(pair, "duplicate_tumor_sample", f"duplicate tumor_sample_id {pair.tumor_sample_id}"))
        seen_tumors[pair.tumor_sample_id] = pair
        if pair.analysis_mode == "tumor_normal":
            key = (pair.normal_sample_id, str(pair.normal_input_path))
            normal_counts.setdefault(key, []).append(pair)
    reuse = config.get("normal_reuse", {})
    reuse_allowed = reuse.get("allowed", False)
    max_reuse = int(reuse.get("maximum_pairs_per_normal", 1) or 1)
    for normal_key, normal_pairs in normal_counts.items():
        if len(normal_pairs) <= 1:
            continue
        subjects = {p.subject_id for p in normal_pairs}
        if not reuse_allowed:
            for pair in normal_pairs:
                errors.append(_issue(pair, "invalid_normal_reuse", f"normal {normal_key[0]} is reused but normal reuse is disabled"))
        elif len(normal_pairs) > max_reuse:
            for pair in normal_pairs:
                errors.append(_issue(pair, "invalid_normal_reuse", f"normal {normal_key[0]} exceeds maximum reuse {max_reuse}"))
        else:
            for pair in normal_pairs:
                warnings.append(_issue(pair, "invalid_normal_reuse", f"normal {normal_key[0]} is reused across {len(normal_pairs)} pairs"))
        if len(subjects) > 1:
            for pair in normal_pairs:
                errors.append(_issue(pair, "subject_mismatch", f"normal {normal_key[0]} is shared across different subjects"))
    return errors, warnings


def validate_numeric_metadata(pair: SomaticPair, config: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for field in ("tumor_coverage", "normal_coverage"):
        value = _optional_float(pair.optional.get(field))
        if value is not None and (value < 0 or not math.isfinite(value)):
            errors.append(_issue(pair, "insufficient_tumor_coverage" if field.startswith("tumor") else "insufficient_normal_coverage", f"{field} must be finite and nonnegative"))
    for field in ("tumor_purity", "normal_contamination", "tumor_contamination"):
        value = _optional_float(pair.optional.get(field))
        if value is not None and (value < 0 or value > 1 or not math.isfinite(value)):
            errors.append(_issue(pair, "invalid_purity" if field == "tumor_purity" else "invalid_contamination", f"{field} must be between 0 and 1"))
    ploidy = _optional_float(pair.optional.get("tumor_ploidy"))
    if ploidy is not None and (ploidy <= 0 or not math.isfinite(ploidy)):
        errors.append(_issue(pair, "invalid_ploidy", "tumor_ploidy must be greater than zero"))
    metadata_cfg = config.get("metadata", {})
    if metadata_cfg.get("require_purity") and _optional_float(pair.optional.get("tumor_purity")) is None:
        errors.append(_issue(pair, "missing_required_metadata", "tumor_purity is required by project policy"))
    if metadata_cfg.get("require_ploidy") and ploidy is None:
        errors.append(_issue(pair, "missing_required_metadata", "tumor_ploidy is required by project policy"))
    if metadata_cfg.get("require_contamination_estimate") and _optional_float(pair.optional.get("tumor_contamination")) is None:
        errors.append(_issue(pair, "missing_required_metadata", "tumor_contamination is required by project policy"))
    if metadata_cfg.get("require_sex") and not pair.optional.get("sex"):
        errors.append(_issue(pair, "missing_required_metadata", "sex is required by project policy"))
    if metadata_cfg.get("require_source_for_values"):
        has_value = any(pair.optional.get(field) for field in ("tumor_purity", "normal_contamination", "tumor_contamination", "tumor_ploidy"))
        if has_value and not pair.optional.get("metadata_source_method"):
            errors.append(_issue(pair, "missing_required_metadata", "metadata_source_method is required when values are supplied"))
    preflight = config.get("preflight", {})
    tumor_cov = _optional_float(pair.optional.get("tumor_coverage"))
    normal_cov = _optional_float(pair.optional.get("normal_coverage"))
    if tumor_cov is not None and preflight.get("minimum_tumor_coverage") is not None and tumor_cov < float(preflight["minimum_tumor_coverage"]):
        errors.append(_issue(pair, "insufficient_tumor_coverage", "tumor coverage is below configured threshold"))
    if normal_cov is not None and preflight.get("minimum_normal_coverage") is not None and normal_cov < float(preflight["minimum_normal_coverage"]):
        errors.append(_issue(pair, "insufficient_normal_coverage", "normal coverage is below configured threshold"))
    if tumor_cov is not None and normal_cov not in (None, 0):
        ratio = tumor_cov / normal_cov
        min_ratio = preflight.get("minimum_tumor_normal_coverage_ratio")
        max_ratio = preflight.get("maximum_tumor_normal_coverage_ratio")
        if min_ratio is not None and ratio < float(min_ratio):
            errors.append(_issue(pair, "extreme_coverage_imbalance", "tumor/normal coverage ratio is below configured threshold"))
        if max_ratio is not None and ratio > float(max_ratio):
            errors.append(_issue(pair, "extreme_coverage_imbalance", "tumor/normal coverage ratio is above configured threshold"))
    return errors


def build_manifest_validation_result(
    selected: list[SomaticPair],
    excluded: list[SomaticPair],
    errors: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> SomaticManifestValidationResult:
    errors = errors or []
    warnings = warnings or []
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return SomaticManifestValidationResult(status, errors, warnings, selected, excluded)


def write_somatic_manifest_artifacts(
    selected: list[SomaticPair],
    excluded: list[SomaticPair],
    validation: SomaticManifestValidationResult,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_resolved_manifest(selected, excluded, out_dir / "somatic_manifest.resolved.tsv")
    (out_dir / "somatic_manifest.validation.json").write_text(_json(validation.to_dict()), encoding="utf-8")
    lines = ["# Somatic Manifest Validation", "", f"Status: {validation.status}", f"Selected pairs: {len(selected)}", f"Excluded pairs: {len(excluded)}", ""]
    if validation.errors:
        lines.append("## Errors")
        lines.extend(f"- row {e.get('row')}: {e.get('category')}: {e.get('message')}" for e in validation.errors)
    if validation.warnings:
        lines.append("## Warnings")
        lines.extend(f"- row {w.get('row')}: {w.get('category')}: {w.get('message')}" for w in validation.warnings)
    (out_dir / "somatic_manifest.validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_resolved_manifest(selected: list[SomaticPair], excluded: list[SomaticPair], path: Path) -> None:
    fieldnames = sorted(REQUIRED_COLUMNS | OPTIONAL_COLUMNS | {"manifest_row_hash", "selected"})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for pair, selected_flag in [(p, "true") for p in selected] + [(p, "false") for p in excluded]:
            row = dict(pair.original_row)
            row["manifest_row_hash"] = pair.row_hash
            row["selected"] = selected_flag
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _validate_input_type(pair: SomaticPair, label: str, value: str, errors: list[dict[str, Any]]) -> None:
    if value not in SUPPORTED_INPUT_TYPES:
        errors.append(_issue(pair, "unsupported_input_type", f"{label} input type must be BAM or CRAM"))


def _validate_existing_input(pair: SomaticPair, label: str, input_path: Path, index_path: Path | None, errors: list[dict[str, Any]]) -> None:
    if not input_path.exists():
        errors.append(_issue(pair, f"missing_{label}_input", f"{label} input does not exist: {input_path}"))
    if index_path is None or not index_path.exists():
        errors.append(_issue(pair, f"missing_{label}_index", f"{label} index does not exist"))
    elif input_path.exists() and index_path.stat().st_mtime_ns < input_path.stat().st_mtime_ns:
        errors.append(_issue(pair, f"stale_{label}_index", f"{label} index is older than input"))


def _issue(pair: SomaticPair, category: str, message: str) -> dict[str, Any]:
    if category not in SOMATIC_FAILURE_CATEGORIES:
        category = "unknown"
    return {"row": pair.row_number, "pair_id": pair.pair_id, "category": category, "message": message}


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y"}


def _resolve_manifest_path(value: str, base_dir: Path) -> Path:
    if not value:
        raise ManifestError("required path field is empty")
    return _resolve_optional_path(value, base_dir) or base_dir


def _resolve_optional_path(value: str, base_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if ".." in path.parts:
        raise ManifestError(f"path traversal is not allowed: {value}")
    return path if path.is_absolute() else base_dir / path


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return math.nan
    return parsed


def _json(data: Any) -> str:
    import json

    return json.dumps(data, indent=2, sort_keys=True, default=str) + "\n"
