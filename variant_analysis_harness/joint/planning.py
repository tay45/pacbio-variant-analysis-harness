"""Joint-genotyping plan generation."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness import __version__
from variant_analysis_harness.common.signatures import file_signature, object_signature
from variant_analysis_harness.common.yaml_io import dump_yaml
from variant_analysis_harness.joint.commands import build_glnexus_command, command_signature
from variant_analysis_harness.joint.inputs import JointInput
from variant_analysis_harness.joint.sharding import JointShard, write_shards


def joint_attempt_dir(cfg: dict[str, Any], joint_id: str, attempt_id: str, output_root: Path | None = None) -> Path:
    root = output_root or Path(cfg["project"]["output_root"])
    return root / cfg["project"]["name"] / "joint_genotyping" / joint_id / attempt_id


def prepare_joint_attempt(attempt_dir: Path, *, config_path: Path, cfg: dict[str, Any]) -> None:
    for sub in ("inputs", "status", "shards", "logs", "slurm", "qc", "reports", "provenance", "outputs", "storage"):
        (attempt_dir / sub).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_path, attempt_dir / "config.original.yaml")
    dump_yaml(cfg, attempt_dir / "config.resolved.yaml")


def generate_joint_plan(
    cfg: dict[str, Any],
    *,
    config_path: Path,
    manifest_path: Path | None,
    joint_id: str,
    attempt_id: str,
    inputs: list[JointInput],
    excluded_samples: list[dict[str, Any]],
    shards: list[JointShard],
    attempt_dir: Path,
    max_concurrent: int,
    reference_result: dict[str, Any],
    identity_result: dict[str, Any],
    reuse_summary: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    command_entries = []
    for shard in shards:
        spec, input_list = build_glnexus_command(cfg, shard, inputs, attempt_dir)
        command_entries.append(
            {
                "shard_id": shard.shard_id,
                "shard_index": shard.shard_index,
                "command": spec.argv,
                "command_signature": command_signature(spec),
                "input_list": str(input_list),
                "output_vcf": str(shard.output_vcf),
            }
        )
    plan = {
        "joint_id": joint_id,
        "joint_attempt_id": attempt_id,
        "source_cohort_id": _first([i.source_cohort_id for i in inputs]),
        "selected_sample_count": len([i for i in inputs if i.enabled]),
        "excluded_sample_count": len(excluded_samples),
        "sample_list_checksum": object_signature([i.to_row() for i in inputs if i.enabled]),
        "backend": "glnexus",
        "backend_preset": (cfg.get("joint_genotyping", {}).get("glnexus", {}) or {}).get("config_name", "DeepVariantWGS"),
        "executable_container_identity": cfg.get("joint_genotyping", {}).get("glnexus", {}),
        "reference_id": _first([i.reference_id for i in inputs]),
        "reference_signature": _first([i.reference_signature for i in inputs]),
        "reference_compatibility": reference_result,
        "sample_identity": identity_result,
        "contig_policy": cfg.get("joint_genotyping", {}).get("sharding", {}),
        "shard_count": len(shards),
        "shard_definitions": [s.to_row() for s in shards],
        "array_grouping": [{"name": "joint_genotyping_shards", "task_count": len(shards), "max_concurrent": max_concurrent}],
        "max_concurrency": max_concurrent,
        "resource_profile": cfg.get("resources", {}).get("joint_genotyping_shard", {}),
        "reusable_prior_shards": [],
        "pending_shards": [s.shard_id for s in shards],
        "failed_shards": [],
        "blocked_shards": [],
        "final_concatenation_plan": {"method": "bcftools concat", "merge_semantics": "nonoverlapping shard concatenation"},
        "normalization_plan": cfg.get("joint_genotyping", {}).get("normalization", {"enabled": False}),
        "indexing_plan": {"tool": "tabix", "index_type": "tbi"},
        "qc_plan": {"technical_variant_qc": True},
        "expected_outputs": {"final_vcf": str(attempt_dir / "outputs" / cfg.get("joint_genotyping", {}).get("output", {}).get("cohort_vcf_name", "cohort.germline.vcf.gz"))},
        "commands": command_entries,
        "config_signature": file_signature(config_path),
        "manifest_signature": file_signature(manifest_path) if manifest_path else {},
        "package_version": __version__,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "research_use_only": True,
        "reuse_summary": reuse_summary or [],
    }
    return plan


def write_joint_plan(plan: dict[str, Any], attempt_dir: Path) -> None:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "joint_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_shards([_row_to_shard(row) for row in plan["shard_definitions"]], attempt_dir / "joint_genotyping_shards.tsv")
    lines = [
        "# Joint Genotyping Plan",
        "",
        "Research-use only. Technical validation does not establish biological or clinical validity.",
        "",
        f"Joint ID: {plan['joint_id']}",
        f"Attempt: {plan['joint_attempt_id']}",
        f"Backend: {plan['backend']}",
        f"Preset: {plan['backend_preset']}",
        f"Selected samples: {plan['selected_sample_count']}",
        f"Shards: {plan['shard_count']}",
        f"Max concurrency: {plan['max_concurrency']}",
    ]
    (attempt_dir / "joint_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_array_index(plan, attempt_dir / "array_index.tsv")


def _write_array_index(plan: dict[str, Any], path: Path) -> None:
    lines = ["array_index\tshard_id\tcontig\tstart\tend\tinput_list\toutput_vcf"]
    by_command = {c["shard_id"]: c for c in plan.get("commands", [])}
    for row in plan["shard_definitions"]:
        command = by_command.get(row["shard_id"], {})
        lines.append(f"{row['shard_index']}\t{row['shard_id']}\t{row['contig']}\t{row['start']}\t{row['end']}\t{command.get('input_list', '')}\t{row['output_vcf']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row_to_shard(row: dict[str, Any]) -> JointShard:
    return JointShard(int(row["shard_index"]), row["shard_id"], row["contig"], int(row["start"]), int(row["end"]), int(row["estimated_bases"]), str(row["enabled"]).lower() == "true", Path(row["output_vcf"]), Path(row["output_index"]))


def _first(values: list[str]) -> str:
    return next((v for v in values if v), "")

