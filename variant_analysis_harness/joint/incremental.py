"""Incremental joint-genotyping safeguards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.joint.inputs import JointInput


def compare_joint_incremental(inputs: list[JointInput], plan: dict[str, Any], previous_joint_dir: Path | None, out_dir: Path) -> list[dict[str, Any]]:
    prior = _load_prior(previous_joint_dir)
    current_checksum = object_signature([i.to_row() for i in inputs if i.enabled])
    rows: list[dict[str, Any]] = []
    if not prior:
        for item in inputs:
            rows.append({"sample_id": item.sample_id, "decision": "new", "reason": "no previous joint attempt"})
    elif prior.get("sample_list_checksum") != current_checksum:
        prior_samples = {row.get("sample_id") for row in prior.get("inputs", [])}
        current_samples = {item.sample_id for item in inputs if item.enabled}
        for sample_id in sorted(current_samples | prior_samples):
            if sample_id not in prior_samples:
                decision, reason = "added_sample_invalidates_joint_shards", "adding samples requires joint genotyping rerun"
            elif sample_id not in current_samples:
                decision, reason = "removed_sample_invalidates_joint_shards", "removing samples requires joint genotyping rerun"
            else:
                decision, reason = "joint_shards_invalidated", "cohort sample-list checksum changed"
            rows.append({"sample_id": sample_id, "decision": decision, "reason": reason})
    else:
        for item in inputs:
            rows.append({"sample_id": item.sample_id, "decision": "per_sample_gvcf_reusable", "reason": "sample list unchanged; per-sample gVCF remains reusable"})
    write_joint_incremental(rows, out_dir)
    return rows


def write_joint_incremental(rows: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "joint_incremental_comparison.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    headers = ["sample_id", "decision", "reason"]
    lines = ["\t".join(headers)]
    lines.extend("\t".join(str(row.get(h, "")) for h in headers) for row in rows)
    (out_dir / "joint_incremental_comparison.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Joint Incremental Comparison", "", "Adding or removing samples invalidates prior joint-called shards by default."]
    md.extend(f"- {r['sample_id']}: {r['decision']} - {r['reason']}" for r in rows)
    (out_dir / "joint_incremental_comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _load_prior(previous_joint_dir: Path | None) -> dict[str, Any] | None:
    if previous_joint_dir is None:
        return None
    plan_path = previous_joint_dir / "joint_plan.json"
    inputs_path = previous_joint_dir / "joint_genotyping_inputs.json"
    if not plan_path.exists():
        return None
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if inputs_path.exists():
        plan["inputs"] = json.loads(inputs_path.read_text(encoding="utf-8")).get("inputs", [])
    return plan

