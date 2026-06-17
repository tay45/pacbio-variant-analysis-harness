"""Severus phasing and haplotagging validation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.somatic.severus.config import validate_phasing_config


def validate_severus_phasing(phasing: dict[str, Any]) -> dict[str, Any]:
    result = validate_phasing_config(phasing)
    result["mode"] = phasing.get("mode", "auto")
    result["phased_vcf"] = phasing.get("phased_vcf")
    result["phased_vcf_index"] = phasing.get("phased_vcf_index")
    result["hp_tags"] = phasing.get("hp_tags", "unknown")
    result["supplementary_hp_tags"] = phasing.get("supplementary_hp_tags", "unknown")
    result["haplotagging_method"] = phasing.get("haplotagging_method")
    result["source_tool"] = phasing.get("source_tool")
    result["source_version"] = phasing.get("source_version")
    return result


def write_phasing_validation(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "severus_phasing_validation.json").write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = [
        "# Severus Phasing Validation",
        "",
        f"Status: {result['status']}",
        f"Mode: {result.get('mode')}",
        f"Supplementary-tag decision: {result.get('supplementary_tag_decision', {}).get('reason')}",
        "",
        "This technical validation does not infer or fabricate HP-tag state.",
    ]
    lines.extend(f"- ERROR: {e}" for e in result.get("errors", []))
    lines.extend(f"- WARNING: {w}" for w in result.get("warnings", []))
    (out_dir / "severus_phasing_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
