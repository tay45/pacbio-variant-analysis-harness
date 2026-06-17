"""DeepSomatic rerun manifest selection."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def generate_deepsomatic_rerun_manifest(
    plan_path: Path,
    output: Path,
    *,
    status: str | None = "BLOCKED",
    failure_category: str | None = None,
    analysis_mode: str | None = None,
    include_pairs: set[str] | None = None,
) -> list[dict[str, Any]]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    rows = []
    for item in plan.get("pair_statuses", []):
        if include_pairs and item["pair_id"] not in include_pairs:
            continue
        if status and item.get("caller_preflight_status") != status:
            continue
        if failure_category and item.get("failure_category") != failure_category:
            continue
        if analysis_mode and item.get("analysis_mode") != analysis_mode:
            continue
        rows.append({k: item.get(k, "") for k in ("pair_id", "subject_id", "analysis_mode", "tumor_sample_id", "normal_sample_id", "failure_category")})
    rows = sorted(rows, key=lambda row: row["pair_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=["pair_id", "subject_id", "analysis_mode", "tumor_sample_id", "normal_sample_id", "failure_category"])
        writer.writeheader()
        writer.writerows(rows)
    (output.with_suffix(output.suffix + ".recommendations.json")).write_text(json.dumps({"selected": len(rows), "recommendation": "review failure category before rerun; no automatic submission performed"}, indent=2) + "\n", encoding="utf-8")
    return rows
