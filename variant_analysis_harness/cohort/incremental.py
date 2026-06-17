"""Incremental cohort comparison and conservative reuse decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.cohort.manifest import CohortSample
from variant_analysis_harness.common.signatures import object_signature


def compare_incremental(
    *,
    current_samples: list[CohortSample],
    current_config: dict[str, Any],
    previous_cohort_dir: Path | None,
    out_dir: Path,
) -> list[dict[str, Any]]:
    previous_rows = _load_previous_plan(previous_cohort_dir)
    previous_by_sample = {row.get("sample_id"): row for row in previous_rows}
    config_sig = object_signature(current_config)
    comparisons = []
    for sample in current_samples:
        prior = previous_by_sample.get(sample.sample_id)
        if prior is None:
            decision = "new"
            reason = "sample not present in previous cohort"
        elif prior.get("manifest_row_hash") != sample.row_hash:
            decision = "rerun"
            reason = "manifest row signature changed"
        elif prior.get("config_object_signature") and prior.get("config_object_signature") != config_sig:
            decision = "rerun"
            reason = "configuration signature changed"
        else:
            decision = "reuse_candidate"
            reason = "sample and available signatures are compatible"
        comparisons.append(
            {
                "sample_id": sample.sample_id,
                "decision": decision,
                "reason": reason,
                "manifest_row_hash": sample.row_hash,
            }
        )
    current_ids = {sample.sample_id for sample in current_samples}
    for sample_id in sorted(set(previous_by_sample) - current_ids):
        comparisons.append({"sample_id": sample_id, "decision": "removed", "reason": "not present in current manifest"})
    write_incremental_outputs(comparisons, out_dir)
    return comparisons


def write_incremental_outputs(comparisons: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "incremental_comparison.json").write_text(json.dumps(comparisons, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    headers = ["sample_id", "decision", "reason", "manifest_row_hash"]
    lines = ["\t".join(headers)]
    for row in sorted(comparisons, key=lambda r: str(r.get("sample_id", ""))):
        lines.append("\t".join(str(row.get(h, "")) for h in headers))
    (out_dir / "incremental_comparison.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Incremental Cohort Comparison", ""]
    for row in sorted(comparisons, key=lambda r: str(r.get("sample_id", ""))):
        md.append(f"- {row['sample_id']}: {row['decision']} - {row['reason']}")
    (out_dir / "incremental_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _load_previous_plan(previous_cohort_dir: Path | None) -> list[dict[str, Any]]:
    if previous_cohort_dir is None:
        return []
    path = previous_cohort_dir / "cohort_plan.json"
    if not path.exists():
        return []
    plan = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for row in plan.get("selected_samples", []):
        item = dict(row)
        item["config_object_signature"] = plan.get("config_object_signature")
        rows.append(item)
    return rows

