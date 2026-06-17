"""Cohort status event writing and aggregation."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness.cohort import COHORT_STATUS_VALUES


def status_shard(sample_id: str) -> str:
    return sample_id[:2] if len(sample_id) >= 2 else "_"


def write_status_event(cohort_dir: Path, event: dict[str, Any]) -> Path:
    status = event.get("status", "unknown")
    if status not in COHORT_STATUS_VALUES:
        status = "unknown"
        event["status"] = status
    sample_id = str(event.get("sample_id", "unknown"))
    stage = str(event.get("stage", "workflow"))
    timestamp = event.get("end_time") or datetime.now(timezone.utc).isoformat()
    event.setdefault("recorded_at", timestamp)
    event_dir = cohort_dir / "status" / "events" / status_shard(sample_id) / sample_id
    event_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = timestamp.replace(":", "").replace("+", "Z")
    final = event_dir / f"{stage}.{safe_ts}.json"
    _atomic_json(final, event)
    current = cohort_dir / "status" / "current" / status_shard(sample_id) / f"{sample_id}.json"
    _atomic_json(current, event)
    return final


def aggregate_status(cohort_dir: Path) -> dict[str, Any]:
    records = []
    current_root = cohort_dir / "status" / "current"
    for path in sorted(current_root.glob("*/*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            records.append({"sample_id": path.stem, "status": "unknown", "failure_category": "unknown"})
    counts = Counter(record.get("status", "unknown") for record in records)
    failure_counts = Counter(record.get("failure_category", "unknown") for record in records if record.get("status") == "failed")
    summary = {
        "cohort_dir": str(cohort_dir),
        "total_records": len(records),
        "status_counts": dict(sorted(counts.items())),
        "failure_category_counts": dict(sorted(failure_counts.items())),
        "records": sorted(records, key=lambda r: str(r.get("sample_id", ""))),
    }
    _write_status_outputs(cohort_dir, summary)
    return summary


def seed_pending_statuses(cohort_dir: Path, plan: dict[str, Any]) -> None:
    for sample in plan.get("selected_samples", []):
        _write_current_status(
            cohort_dir,
            {
                "cohort_id": plan["cohort_id"],
                "cohort_attempt": plan["cohort_attempt_id"],
                "sample_id": sample["sample_id"],
                "sample_attempt": sample["attempt_id"],
                "stage": "workflow",
                "status": "pending",
                "validation_status": "NOT_EVALUATED",
                "failure_category": None,
                "warning_count": 0,
                "output_manifest_path": None,
                "report_path": None,
                "retry_count": 0,
                "signatures": {"manifest_row_hash": sample["manifest_row_hash"]},
            },
        )
    for sample in plan.get("excluded_samples", []):
        _write_current_status(
            cohort_dir,
            {
                "cohort_id": plan["cohort_id"],
                "cohort_attempt": plan["cohort_attempt_id"],
                "sample_id": sample["sample_id"],
                "stage": "workflow",
                "status": "excluded",
                "validation_status": "NOT_EVALUATED",
                "failure_category": None,
                "warning_count": 0,
                "retry_count": 0,
                "signatures": {"manifest_row_hash": sample["manifest_row_hash"]},
            },
        )


def _write_status_outputs(cohort_dir: Path, summary: dict[str, Any]) -> None:
    (cohort_dir / "cohort_status.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    headers = ["sample_id", "stage", "status", "failure_category", "warning_count", "exit_code", "report_path"]
    lines = ["\t".join(headers)]
    for record in summary["records"]:
        lines.append("\t".join(str(record.get(h, "") or "") for h in headers))
    (cohort_dir / "cohort_status.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Cohort Status", "", f"Total records: {summary['total_records']}", "", "## Status Counts"]
    for status, count in summary["status_counts"].items():
        md.append(f"- {status}: {count}")
    md.append("")
    md.append("## Failure Categories")
    if summary["failure_category_counts"]:
        for category, count in summary["failure_category_counts"].items():
            md.append(f"- {category}: {count}")
    else:
        md.append("- none")
    (cohort_dir / "cohort_status.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _write_current_status(cohort_dir: Path, event: dict[str, Any]) -> None:
    sample_id = str(event.get("sample_id", "unknown"))
    status = event.get("status", "unknown")
    if status not in COHORT_STATUS_VALUES:
        event["status"] = "unknown"
    event.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
    current = cohort_dir / "status" / "current" / status_shard(sample_id) / f"{sample_id}.json"
    _atomic_json(current, event)
