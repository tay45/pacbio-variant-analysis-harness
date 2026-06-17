"""Somatic failed-pair rerun manifest generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_pair_statuses(somatic_dir: Path) -> list[dict[str, Any]]:
    path = somatic_dir / "status" / "somatic_pair_status.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def generate_somatic_rerun_manifest(
    somatic_dir: Path,
    output: Path,
    *,
    status: str = "failed",
    failure_category: str | None = None,
    subject_id: str | None = None,
    analysis_mode: str | None = None,
    include_pairs: set[str] | None = None,
    allow_successful: bool = False,
) -> list[dict[str, Any]]:
    rows = []
    for item in load_pair_statuses(somatic_dir):
        if include_pairs is not None and item["pair_id"] not in include_pairs:
            continue
        if status and item.get("readiness_status") != status:
            continue
        if failure_category and item.get("failure_category") != failure_category:
            continue
        if subject_id and item.get("subject_id") != subject_id:
            continue
        if analysis_mode and item.get("analysis_mode") != analysis_mode:
            continue
        if not allow_successful and item.get("readiness_status") == "ready":
            continue
        rows.append(
            {
                "pair_id": item["pair_id"],
                "subject_id": item["subject_id"],
                "tumor_sample_id": item["tumor_sample_id"],
                "normal_sample_id": item["normal_sample_id"],
                "analysis_mode": item["analysis_mode"],
                "source_attempt": item["project_attempt"],
                "rerun_status": item["readiness_status"],
                "rerun_failure_category": item.get("failure_category", ""),
            }
        )
    rows = sorted(rows, key=lambda row: row["pair_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "pair_id",
        "subject_id",
        "tumor_sample_id",
        "normal_sample_id",
        "analysis_mode",
        "source_attempt",
        "rerun_status",
        "rerun_failure_category",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    criteria = {
        "status": status,
        "failure_category": failure_category,
        "subject_id": subject_id,
        "analysis_mode": analysis_mode,
        "include_pairs": sorted(include_pairs) if include_pairs else [],
        "allow_successful": allow_successful,
    }
    output.with_suffix(output.suffix + ".criteria.json").write_text(json.dumps(criteria, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rows
