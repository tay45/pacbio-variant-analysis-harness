"""Planning-only storage estimates for joint genotyping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.joint.inputs import JointInput
from variant_analysis_harness.joint.sharding import JointShard


def estimate_joint_storage(inputs: list[JointInput], shards: list[JointShard]) -> dict[str, Any]:
    total_gvcf = sum((i.gvcf_path.stat().st_size if i.gvcf_path.exists() else 1024) for i in inputs if i.enabled)
    total_gb = total_gvcf / (1024**3)
    result = {
        "assumptions": "Planning approximation only; GLnexus temporary storage depends on variant density, sample count, backend version, and retention policy.",
        "input_gvcf_gb": round(total_gb, 6),
        "input_index_gb": round(total_gb * 0.02, 6),
        "per_shard_temp_gb": round(max(0.001, total_gb * 2.0 / max(1, len(shards))), 6),
        "per_shard_vcf_gb": round(max(0.001, total_gb * 0.2 / max(1, len(shards))), 6),
        "final_vcf_gb": round(max(0.001, total_gb * 0.3), 6),
        "normalization_temp_gb": round(max(0.001, total_gb * 0.5), 6),
        "sorting_temp_gb": round(max(0.001, total_gb * 0.5), 6),
        "logs_qc_gb": 0.001,
        "peak_scratch_gb": round(max(0.001, total_gb * 2.5), 6),
        "sample_count": len([i for i in inputs if i.enabled]),
        "shard_count": len(shards),
    }
    return result


def write_joint_storage(estimate: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "joint_storage_estimate.json").write_text(json.dumps(estimate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "joint_storage_estimate.tsv").write_text("metric\tvalue\n" + "\n".join(f"{k}\t{v}" for k, v in estimate.items()) + "\n", encoding="utf-8")
    md = ["# Joint Storage Estimate", "", estimate["assumptions"], "", f"Input gVCF GB: {estimate['input_gvcf_gb']}", f"Peak scratch GB: {estimate['peak_scratch_gb']}"]
    (out_dir / "joint_storage_estimate.md").write_text("\n".join(md) + "\n", encoding="utf-8")

