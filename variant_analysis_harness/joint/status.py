"""Joint shard status aggregation."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness.joint import JOINT_STATUS_VALUES


def write_shard_status(joint_dir: Path, event: dict[str, Any]) -> Path:
    status = event.get("status", "unknown")
    if status not in JOINT_STATUS_VALUES:
        event["status"] = "unknown"
    shard_id = str(event.get("shard_id", "unknown"))
    event.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
    path = joint_dir / "status" / "shards" / shard_id[:8] / f"{shard_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(event, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)
    return path


def seed_shard_statuses(joint_dir: Path, plan: dict[str, Any]) -> None:
    for row in plan.get("shard_definitions", []):
        write_shard_status(
            joint_dir,
            {
                "joint_id": plan["joint_id"],
                "joint_attempt_id": plan["joint_attempt_id"],
                "shard_id": row["shard_id"],
                "shard_index": row["shard_index"],
                "contig": row["contig"],
                "interval": f"{row['contig']}:{row['start']}-{row['end']}",
                "status": "pending",
                "backend": plan["backend"],
                "failure_category": None,
                "retry_count": 0,
                "warning_count": 0,
                "output_path": row["output_vcf"],
            },
        )


def aggregate_joint_status(joint_dir: Path) -> dict[str, Any]:
    records = []
    for path in sorted((joint_dir / "status" / "shards").glob("*/*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    counts = Counter(r.get("status", "unknown") for r in records)
    failures = Counter(r.get("failure_category", "unknown") for r in records if r.get("status") == "failed")
    result = {"total_shards": len(records), "status_counts": dict(sorted(counts.items())), "failure_category_counts": dict(sorted(failures.items())), "records": records}
    (joint_dir / "joint_status.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["shard_id\tshard_index\tcontig\tstatus\tfailure_category\toutput_path"]
    for r in records:
        lines.append(f"{r.get('shard_id')}\t{r.get('shard_index')}\t{r.get('contig')}\t{r.get('status')}\t{r.get('failure_category') or ''}\t{r.get('output_path') or ''}")
    (joint_dir / "joint_status.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Joint Shard Status", "", f"Total shards: {len(records)}", "", "## Status Counts"]
    md.extend([f"- {k}: {v}" for k, v in result["status_counts"].items()] or ["- none"])
    (joint_dir / "joint_status.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return result

