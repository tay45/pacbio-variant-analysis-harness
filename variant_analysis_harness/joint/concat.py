"""Final cohort VCF concatenation planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.joint.commands import build_concat_commands


def build_concat_plan(cfg: dict[str, Any], plan: dict[str, Any], attempt_dir: Path) -> dict[str, Any]:
    outputs = [Path(row["output_vcf"]) for row in plan["shard_definitions"] if str(row.get("enabled", "true")).lower() == "true"]
    final = Path(plan["expected_outputs"]["final_vcf"])
    commands = build_concat_commands(cfg, outputs, final)
    result = {
        "required_shards": [str(p) for p in outputs],
        "final_vcf": str(final),
        "final_index": str(final) + ".tbi",
        "commands": [{"stage": c.stage, "argv": c.argv, "inputs": [str(p) for p in c.inputs], "outputs": [str(p) for p in c.outputs]} for c in commands],
        "blocked_until_shards_success": True,
    }
    (attempt_dir / "concat_plan.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def validate_concat_inputs(shard_paths: list[Path]) -> dict[str, Any]:
    missing = [str(p) for p in shard_paths if not p.exists() or p.stat().st_size == 0]
    return {"status": "FAIL" if missing else "PASS", "missing_shards": missing}

