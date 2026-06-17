"""Rerun-manifest generation from cohort status records."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_current_statuses(cohort_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted((cohort_dir / "status" / "current").glob("*/*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            records.append({"sample_id": path.stem, "status": "unknown", "failure_category": "unknown"})
    return sorted(records, key=lambda r: str(r.get("sample_id", "")))


def generate_rerun_manifest(
    cohort_dir: Path,
    output: Path,
    *,
    status: str | None = "failed",
    stage: str | None = None,
    failure_category: str | None = None,
    warning_only: bool = False,
    include_samples: set[str] | None = None,
    allow_successful: bool = False,
) -> list[dict[str, str]]:
    original_manifest = cohort_dir / "cohort_manifest.resolved.tsv"
    if not original_manifest.exists():
        original_manifest = cohort_dir / "cohort_manifest.original.tsv"
    rows = _read_manifest_rows(original_manifest)
    statuses = {record.get("sample_id"): record for record in load_current_statuses(cohort_dir)}
    selected: list[dict[str, str]] = []
    for row in rows:
        sample_id = row.get("sample_id", "")
        record = statuses.get(sample_id, {})
        if include_samples is not None and sample_id not in include_samples:
            continue
        if not allow_successful:
            if status and record.get("status") != status:
                continue
            if stage and record.get("stage") != stage:
                continue
            if failure_category and record.get("failure_category") != failure_category:
                continue
            if warning_only and record.get("status") != "warning":
                continue
        row = dict(row)
        row["rerun_source_cohort"] = str(cohort_dir)
        row["rerun_source_attempt"] = cohort_dir.name
        row["rerun_reason"] = str(record.get("status", "selected"))
        row["rerun_stage"] = str(record.get("stage", stage or "workflow"))
        row["rerun_failure_category"] = str(record.get("failure_category", failure_category or ""))
        selected.append(row)
    _write_manifest(output, selected)
    _write_recommendations(output.with_suffix(".recommendations.md"), selected)
    return selected


def _read_manifest_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys())
    else:
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
            "rerun_source_cohort",
            "rerun_source_attempt",
            "rerun_reason",
            "rerun_stage",
            "rerun_failure_category",
        ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r.get("sample_id", "")):
            writer.writerow(row)


def _write_recommendations(path: Path, rows: list[dict[str, str]]) -> None:
    lines = ["# Rerun Recommendations", "", f"Selected samples: {len(rows)}", ""]
    if rows:
        lines.append("Review original logs and validation artifacts before resubmission. No jobs were submitted automatically.")
    else:
        lines.append("No matching samples were selected.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

