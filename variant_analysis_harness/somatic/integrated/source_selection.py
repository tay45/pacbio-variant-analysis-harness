"""Safe source-attempt selection for integrated reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.exceptions import ValidationError


def discover_attempt_records(plan_path: Path, *, caller: str) -> list[dict[str, Any]]:
    if not plan_path.exists():
        return []
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    rows = []
    for item in plan.get("pair_statuses", []):
        rows.append(
            {
                "caller": caller,
                "pair_id": item.get("pair_id", ""),
                "attempt_id": plan.get("pair_attempt_id", ""),
                "path": str(plan_path.parent),
                "status": "complete" if item.get("caller_preflight_status") in {"READY", "READY_WITH_WARNINGS"} else "failed",
                "validation_status": "WARN" if item.get("caller_preflight_status") == "READY_WITH_WARNINGS" else ("PASS" if item.get("caller_preflight_status") == "READY" else "FAIL"),
                "qc_status": "PASS",
                "failure_category": item.get("failure_category", ""),
                "command_signature": item.get("command_signature", ""),
                "superseded": bool(item.get("superseded", False)),
                "reference_signature": item.get("reference_signature", ""),
                "reference_id": item.get("reference_id", ""),
                "manifest_row_hash": item.get("manifest_row_hash", ""),
                "subject_id": item.get("subject_id", ""),
                "tumor_sample_id": item.get("tumor_sample_id", ""),
                "normal_sample_id": item.get("normal_sample_id", ""),
                "analysis_mode": item.get("analysis_mode", ""),
                "output_checksum": item.get("output_checksum", ""),
                "bnd_validation_status": item.get("bnd_validation_status", ""),
            }
        )
    return rows


def select_source_attempt(
    records: list[dict[str, Any]],
    *,
    pair_id: str,
    explicit_attempt: str | None = None,
    policy: str = "latest_validated_compatible",
    include_superseded: bool = False,
) -> dict[str, Any] | None:
    candidates = [r for r in records if r.get("pair_id") == pair_id]
    if not include_superseded:
        candidates = [r for r in candidates if not r.get("superseded")]
    if explicit_attempt:
        matches = [r for r in candidates if r.get("attempt_id") == explicit_attempt]
        if len(matches) > 1:
            raise ValidationError(f"ambiguous explicit source attempt for {pair_id}: {explicit_attempt}")
        return matches[0] if matches else None
    if policy == "latest_validated_compatible":
        candidates = [r for r in candidates if r.get("status") == "complete" and r.get("validation_status") in {"PASS", "WARN"}]
    elif policy == "latest_complete":
        candidates = [r for r in candidates if r.get("status") == "complete"]
    elif policy != "pinned_manifest":
        raise ValidationError(f"unsupported source attempt selection policy: {policy}")
    if not candidates:
        return None
    # Attempt IDs are the deterministic ordering key; directory mtime is not used.
    candidates = sorted(candidates, key=lambda r: (str(r.get("attempt_id", "")), str(r.get("path", ""))))
    if len(candidates) >= 2 and candidates[-1].get("attempt_id") == candidates[-2].get("attempt_id"):
        raise ValidationError(f"ambiguous source attempt for {pair_id}: {candidates[-1].get('attempt_id')}")
    return candidates[-1]


def write_source_attempts(rows: list[dict[str, Any]], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_source_attempts.json").write_text(json.dumps(rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    fields = ["pair_id", "caller", "attempt_id", "status", "validation_status", "qc_status", "path", "failure_category"]
    with (out_dir / "integrated_source_attempts.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
