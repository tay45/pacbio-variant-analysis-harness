"""Technical validation for joint shard and final cohort VCF outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.joint.vcf import detect_vcf_index, quick_record_scan, read_vcf_header


def validate_joint_vcf(path: Path, *, expected_samples: list[str], shard: dict[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.exists() or path.stat().st_size == 0:
        return {"status": "FAIL", "errors": [f"missing or empty VCF: {path}"], "warnings": warnings}
    try:
        header = read_vcf_header(path)
    except Exception as exc:
        return {"status": "FAIL", "errors": [f"header read failed: {exc}"], "warnings": warnings}
    if header["samples"] != expected_samples:
        errors.append("sample header mismatch")
    if len(header["samples"]) != len(set(header["samples"])):
        errors.append("duplicate sample names")
    scan = quick_record_scan(path)
    errors.extend(scan["errors"])
    if shard:
        for contig in scan["contig_counts"]:
            if contig != shard.get("contig"):
                errors.append("record outside shard contig")
    if detect_vcf_index(path) is None:
        warnings.append("VCF index not present")
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "errors": errors, "warnings": warnings, "header": header, "scan": scan}


def write_validation(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

