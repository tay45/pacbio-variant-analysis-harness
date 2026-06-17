"""Joint-genotyping input discovery and manifest writing."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.paths import safe_name
from variant_analysis_harness.common.signatures import file_signature, object_signature
from variant_analysis_harness.exceptions import ValidationError
from variant_analysis_harness.joint.vcf import detect_vcf_index, read_vcf_header


@dataclass(frozen=True)
class JointInput:
    cohort_sample_index: int
    sample_id: str
    gvcf_path: Path
    gvcf_index_path: Path | None
    source_cohort_id: str
    source_cohort_attempt_id: str
    source_sample_attempt_id: str
    reference_id: str
    reference_signature: str
    gvcf_signature: dict[str, Any]
    sample_name_in_header: str
    validation_status: str
    enabled: bool = True

    def to_row(self) -> dict[str, Any]:
        return {
            "cohort_sample_index": self.cohort_sample_index,
            "sample_id": self.sample_id,
            "gvcf_path": str(self.gvcf_path),
            "gvcf_index_path": str(self.gvcf_index_path) if self.gvcf_index_path else "",
            "source_cohort_id": self.source_cohort_id,
            "source_cohort_attempt_id": self.source_cohort_attempt_id,
            "source_sample_attempt_id": self.source_sample_attempt_id,
            "reference_id": self.reference_id,
            "reference_signature": self.reference_signature,
            "gvcf_signature": object_signature(self.gvcf_signature),
            "sample_name_in_header": self.sample_name_in_header,
            "validation_status": self.validation_status,
            "enabled": str(self.enabled).lower(),
        }


def load_joint_seed_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"sample_id", "gvcf_path", "reference_id"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValidationError(f"Joint manifest must include columns: {sorted(required)}")
        return list(reader)


def build_joint_inputs(
    rows: list[dict[str, str]],
    *,
    base_dir: Path,
    source_cohort_id: str = "",
    source_cohort_attempt_id: str = "",
    default_sample_attempt_id: str = "",
    require_existing: bool = True,
) -> tuple[list[JointInput], list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    built: list[JointInput] = []
    seen_samples: set[str] = set()
    seen_paths: set[Path] = set()
    seen_header_samples: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        try:
            sample_id = safe_name(row.get("sample_id", ""), "sample_id")
        except ValueError as exc:
            errors.append({"row": row_number, "message": str(exc)})
            continue
        gvcf_path = Path(row.get("gvcf_path", ""))
        if not gvcf_path.is_absolute():
            gvcf_path = (base_dir / gvcf_path).resolve()
        enabled = str(row.get("enabled", "true")).lower() not in {"false", "0", "no"}
        if sample_id in seen_samples:
            errors.append({"row": row_number, "message": f"duplicate sample_id: {sample_id}"})
        seen_samples.add(sample_id)
        if gvcf_path in seen_paths:
            errors.append({"row": row_number, "message": f"duplicate gVCF path: {gvcf_path}"})
        seen_paths.add(gvcf_path)
        if require_existing and (not gvcf_path.exists() or gvcf_path.stat().st_size == 0):
            errors.append({"row": row_number, "message": f"missing or empty gVCF: {gvcf_path}"})
            continue
        header_sample = row.get("sample_name_in_header", "")
        validation_status = "PASS"
        index_path = detect_vcf_index(gvcf_path) if gvcf_path.exists() else None
        if require_existing and index_path is None:
            errors.append({"row": row_number, "message": f"missing gVCF index: {gvcf_path}"})
            validation_status = "FAIL"
        if gvcf_path.exists():
            try:
                header = read_vcf_header(gvcf_path)
                if header["sample_count"] != 1:
                    errors.append({"row": row_number, "message": f"expected one sample in gVCF header, found {header['sample_count']}"})
                    validation_status = "FAIL"
                elif not header_sample:
                    header_sample = header["samples"][0]
            except Exception as exc:
                errors.append({"row": row_number, "message": f"failed to read gVCF header: {exc}"})
                validation_status = "FAIL"
        if header_sample:
            try:
                safe_name(header_sample, "sample_name_in_header")
            except ValueError as exc:
                errors.append({"row": row_number, "message": str(exc)})
            if header_sample in seen_header_samples:
                errors.append({"row": row_number, "message": f"duplicate VCF header sample: {header_sample}"})
            seen_header_samples.add(header_sample)
        else:
            errors.append({"row": row_number, "message": "empty VCF header sample name"})
        built.append(
            JointInput(
                cohort_sample_index=0,
                sample_id=sample_id,
                gvcf_path=gvcf_path,
                gvcf_index_path=index_path,
                source_cohort_id=row.get("source_cohort_id", source_cohort_id),
                source_cohort_attempt_id=row.get("source_cohort_attempt_id", source_cohort_attempt_id),
                source_sample_attempt_id=row.get("source_sample_attempt_id", default_sample_attempt_id),
                reference_id=row.get("reference_id", ""),
                reference_signature=row.get("reference_signature", ""),
                gvcf_signature=file_signature(gvcf_path),
                sample_name_in_header=header_sample,
                validation_status=validation_status,
                enabled=enabled,
            )
        )
    ordered = []
    for index, item in enumerate(sorted(built, key=lambda x: x.sample_id), start=1):
        ordered.append(
            JointInput(
                index,
                item.sample_id,
                item.gvcf_path,
                item.gvcf_index_path,
                item.source_cohort_id,
                item.source_cohort_attempt_id,
                item.source_sample_attempt_id,
                item.reference_id,
                item.reference_signature,
                item.gvcf_signature,
                item.sample_name_in_header,
                item.validation_status,
                item.enabled,
            )
        )
    return ordered, errors, warnings


def write_joint_inputs(inputs: list[JointInput], errors: list[dict[str, Any]], warnings: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(inputs[0].to_row().keys()) if inputs else [
        "cohort_sample_index", "sample_id", "gvcf_path", "gvcf_index_path", "source_cohort_id",
        "source_cohort_attempt_id", "source_sample_attempt_id", "reference_id", "reference_signature",
        "gvcf_signature", "sample_name_in_header", "validation_status", "enabled",
    ]
    with (out_dir / "joint_genotyping_inputs.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for item in inputs:
            writer.writerow(item.to_row())
    payload = {"inputs": [item.to_row() for item in inputs], "errors": errors, "warnings": warnings, "status": "FAIL" if errors else ("WARN" if warnings else "PASS")}
    (out_dir / "joint_genotyping_inputs.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Joint Genotyping Input Validation", "", f"Status: {payload['status']}", f"Inputs: {len(inputs)}", "", "## Errors"]
    lines.extend([f"- {e}" for e in errors] or ["- none"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {w}" for w in warnings] or ["- none"])
    (out_dir / "joint_genotyping_inputs.validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
