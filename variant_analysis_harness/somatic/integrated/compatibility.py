"""Cross-caller identity and reference compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_pair_compatibility(pair: Any, small: dict[str, Any] | None, sv: dict[str, Any] | None, policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    small = small or {}
    sv = sv or {}
    for label, source in (("small", small), ("sv", sv)):
        if not source:
            continue
        if policy.get("require_matching_subject", True) and source.get("subject_id") and source.get("subject_id") != pair.subject_id:
            errors.append(f"{label} subject mismatch")
        if policy.get("require_matching_tumor_identity", True) and source.get("tumor_sample_id") and source.get("tumor_sample_id") != pair.tumor_sample_id:
            errors.append(f"{label} tumor identity mismatch")
        if pair.analysis_mode == "tumor_normal" and policy.get("require_matching_normal_identity", True) and source.get("normal_sample_id") and source.get("normal_sample_id") != pair.normal_sample_id:
            errors.append(f"{label} normal identity mismatch")
        if source.get("analysis_mode") and source.get("analysis_mode") != pair.analysis_mode:
            errors.append(f"{label} analysis mode mismatch")
        if policy.get("require_matching_reference", True) and source.get("reference_id") and source.get("reference_id") != pair.reference_id:
            errors.append(f"{label} reference mismatch")
        if source.get("manifest_row_hash") and source.get("manifest_row_hash") != pair.row_hash:
            warnings.append(f"{label} manifest row hash differs")
    if small and sv:
        for field, message in (("reference_signature", "reference signature mismatch"), ("contig_signature", "contig mismatch"), ("tumor_input_signature", "tumor input signature mismatch"), ("normal_input_signature", "normal input signature mismatch")):
            if small.get(field) and sv.get(field) and small.get(field) != sv.get(field):
                errors.append(message)
    return {"pair_id": pair.pair_id, "status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "errors": errors, "warnings": warnings}


def write_compatibility(rows: list[dict[str, Any]], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_compatibility.json").write_text(json.dumps(rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    fields = ["pair_id", "status", "errors", "warnings"]
    with (out_dir / "integrated_compatibility.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"pair_id": row.get("pair_id", ""), "status": row.get("status", ""), "errors": ";".join(row.get("errors", [])), "warnings": ";".join(row.get("warnings", []))})
    lines = ["# Integrated Compatibility", ""]
    lines.extend(f"- {row.get('pair_id')}: {row.get('status')}" for row in rows)
    (out_dir / "integrated_compatibility.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

