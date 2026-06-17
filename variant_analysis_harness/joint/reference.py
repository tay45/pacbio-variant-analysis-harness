"""Reference and contig compatibility validation for joint genotyping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.joint.inputs import JointInput
from variant_analysis_harness.joint.vcf import read_vcf_header


def validate_reference_compatibility(inputs: list[JointInput], out_dir: Path | None = None) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    reference_ids = {item.reference_id for item in inputs if item.enabled}
    reference_signatures = {item.reference_signature for item in inputs if item.enabled and item.reference_signature}
    if len(reference_ids) > 1:
        errors.append({"scope": "reference", "message": f"mixed reference_id values: {sorted(reference_ids)}"})
    if len(reference_signatures) > 1:
        errors.append({"scope": "reference", "message": "mixed reference signatures"})
    expected_contigs: list[dict[str, Any]] | None = None
    for item in inputs:
        if not item.enabled or not item.gvcf_path.exists():
            continue
        header = read_vcf_header(item.gvcf_path)
        contigs = header["contigs"]
        rows.append({"sample_id": item.sample_id, "reference_id": item.reference_id, "contigs": contigs})
        if expected_contigs is None:
            expected_contigs = contigs
            continue
        if [c["id"] for c in contigs] != [c["id"] for c in expected_contigs]:
            errors.append({"sample_id": item.sample_id, "message": "contig order/name mismatch"})
        if [c.get("length") for c in contigs] != [c.get("length") for c in expected_contigs]:
            errors.append({"sample_id": item.sample_id, "message": "contig length mismatch"})
        if _chr_prefix_state(contigs) != _chr_prefix_state(expected_contigs):
            errors.append({"sample_id": item.sample_id, "message": "chr-prefix convention mismatch"})
    result = {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "errors": errors, "warnings": warnings, "rows": rows}
    if out_dir:
        write_reference_compatibility(result, out_dir)
    return result


def write_reference_compatibility(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reference_compatibility.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["sample_id\treference_id\tcontig_count"]
    for row in result["rows"]:
        lines.append(f"{row['sample_id']}\t{row['reference_id']}\t{len(row['contigs'])}")
    (out_dir / "reference_compatibility.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Reference Compatibility", "", f"Status: {result['status']}", "", "## Errors"]
    md.extend([f"- {e}" for e in result["errors"]] or ["- none"])
    (out_dir / "reference_compatibility.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _chr_prefix_state(contigs: list[dict[str, Any]]) -> str:
    ids = [str(c.get("id", "")) for c in contigs]
    if all(i.startswith("chr") for i in ids):
        return "all_chr"
    if all(not i.startswith("chr") for i in ids):
        return "none_chr"
    return "mixed"

