"""Failed-shard rerun manifest generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def generate_joint_rerun_manifest(
    joint_dir: Path,
    output: Path,
    *,
    status: str = "failed",
    failure_category: str | None = None,
    shards: set[str] | None = None,
    contig: str | None = None,
) -> list[dict[str, Any]]:
    records = []
    for path in sorted((joint_dir / "status" / "shards").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if shards and record.get("shard_id") not in shards:
            continue
        if status and record.get("status") != status:
            continue
        if failure_category and record.get("failure_category") != failure_category:
            continue
        if contig and record.get("contig") != contig:
            continue
        records.append(record)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["shard_id", "shard_index", "contig", "interval", "status", "failure_category", "source_joint_dir"]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for record in sorted(records, key=lambda r: int(r.get("shard_index", 0))):
            row = {k: record.get(k, "") for k in fields}
            row["source_joint_dir"] = str(joint_dir)
            writer.writerow(row)
    output.with_suffix(".recommendations.md").write_text(f"# Joint Rerun Recommendations\n\nSelected shards: {len(records)}\n\nNo jobs were submitted automatically.\n", encoding="utf-8")
    return records

