"""Cohort execution plan generation."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness import __version__
from variant_analysis_harness.cohort.manifest import CohortSample, required_stages, write_resolved_manifest
from variant_analysis_harness.common.signatures import file_signature, object_signature
from variant_analysis_harness.common.yaml_io import dump_yaml

DEFAULT_STAGE_RESOURCES = {
    "preflight": {"cpus": 1, "memory_gb": 4, "time": "00:30:00", "scratch_gb": None},
    "dataset_merge": {"cpus": 2, "memory_gb": 8, "time": "02:00:00", "scratch_gb": None},
    "alignment": {"cpus": 16, "memory_gb": 64, "time": "24:00:00", "scratch_gb": 500},
    "alignment_reuse": {"cpus": 1, "memory_gb": 4, "time": "01:00:00", "scratch_gb": None},
    "alignment_qc": {"cpus": 2, "memory_gb": 8, "time": "04:00:00", "scratch_gb": None},
    "germline_snv": {"cpus": 32, "memory_gb": 128, "time": "48:00:00", "scratch_gb": 500},
    "germline_snv_qc": {"cpus": 2, "memory_gb": 8, "time": "04:00:00", "scratch_gb": None},
    "germline_sv_discover": {"cpus": 8, "memory_gb": 32, "time": "12:00:00", "scratch_gb": None},
    "germline_sv_call": {"cpus": 8, "memory_gb": 32, "time": "12:00:00", "scratch_gb": None},
    "germline_sv_qc": {"cpus": 2, "memory_gb": 8, "time": "04:00:00", "scratch_gb": None},
    "sample_report": {"cpus": 1, "memory_gb": 4, "time": "01:00:00", "scratch_gb": None},
}


def cohort_attempt_dir(cfg: dict[str, Any], cohort_id: str, cohort_attempt_id: str, output_root: Path | None = None) -> Path:
    root = output_root or Path(cfg["project"]["output_root"])
    return root / cfg["project"]["name"] / "cohorts" / cohort_id / cohort_attempt_id


def sample_attempt_dir(cfg: dict[str, Any], sample: CohortSample, attempt_id: str, output_root: Path | None = None) -> Path:
    root = output_root or Path(cfg["project"]["output_root"])
    shard = sample.sample_id[:2] if len(sample.sample_id) >= 2 else "_"
    return root / cfg["project"]["name"] / "samples" / shard / sample.sample_id / attempt_id


def prepare_cohort_attempt(
    attempt_dir: Path,
    *,
    config_path: Path,
    manifest_path: Path,
    cfg: dict[str, Any],
    selected: list[CohortSample],
    excluded: list[CohortSample],
) -> None:
    for sub in ("status", "slurm", "logs", "manifests", "qc", "reports", "provenance", "scratch", "storage"):
        (attempt_dir / sub).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_path, attempt_dir / "config.original.yaml")
    dump_yaml(cfg, attempt_dir / "config.resolved.yaml")
    shutil.copyfile(manifest_path, attempt_dir / "cohort_manifest.original.tsv")
    write_resolved_manifest(selected, excluded, attempt_dir / "cohort_manifest.resolved.tsv")


def generate_cohort_plan(
    cfg: dict[str, Any],
    *,
    config_path: Path,
    manifest_path: Path,
    selected: list[CohortSample],
    excluded: list[CohortSample],
    cohort_id: str,
    cohort_attempt_id: str,
    sample_attempt_id: str,
    output_root: Path | None,
    max_concurrent: int,
    include_samples: set[str] | None = None,
    exclude_samples: set[str] | None = None,
    reuse_summary: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    attempt_dir = cohort_attempt_dir(cfg, cohort_id, cohort_attempt_id, output_root)
    resources = resolve_resource_profiles(cfg)
    sample_entries = []
    for index, sample in enumerate(selected, start=1):
        stages = required_stages(sample)
        sample_dir = sample_attempt_dir(cfg, sample, sample_attempt_id, output_root)
        sample_entries.append(
            {
                "array_index": index,
                "sample_id": sample.sample_id,
                "analysis": sample.analysis,
                "input_type": sample.input_type,
                "attempt_id": sample_attempt_id,
                "manifest_row_hash": sample.row_hash,
                "required_stages": stages,
                "reusable_validated_stages": [],
                "pending_stages": stages,
                "blocked_stages": [],
                "resource_profile": {stage: resources.get(stage, {}) for stage in stages},
                "expected_output_dir": str(sample_dir),
            }
        )
    plan = {
        "cohort_id": cohort_id,
        "cohort_attempt_id": cohort_attempt_id,
        "sample_attempt_id": sample_attempt_id,
        "selected_samples": sample_entries,
        "excluded_samples": [
            {"sample_id": s.sample_id, "reason": "disabled_or_filtered", "manifest_row_hash": s.row_hash}
            for s in excluded
        ],
        "array_grouping": [{"name": "full_sample_workflow", "task_count": len(sample_entries), "max_concurrent": max_concurrent}],
        "task_count": len(sample_entries),
        "maximum_concurrency": max_concurrent,
        "dependencies": {"implemented_design": "one_full_single_sample_workflow_per_array_task", "future_stage_arrays": []},
        "expected_output_locations": {"cohort_attempt_dir": str(attempt_dir)},
        "config_signature": file_signature(config_path),
        "config_object_signature": object_signature(cfg),
        "manifest_signature": file_signature(manifest_path),
        "reference_signature": object_signature(cfg.get("reference", {})),
        "tool_container_signatures": object_signature(cfg.get("tools", {})),
        "workflow_package_version": __version__,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "include_samples": sorted(include_samples) if include_samples else [],
        "exclude_samples": sorted(exclude_samples) if exclude_samples else [],
        "reuse_summary": reuse_summary or [],
        "research_use_only": True,
    }
    return plan


def resolve_resource_profiles(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configured = cfg.get("resources", {}) or {}
    resolved: dict[str, dict[str, Any]] = {}
    for stage, defaults in DEFAULT_STAGE_RESOURCES.items():
        merged = dict(defaults)
        if isinstance(configured.get(stage), dict):
            merged.update(configured[stage])
        resolved[stage] = merged
    return resolved


def write_cohort_plan(plan: dict[str, Any], attempt_dir: Path) -> None:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "cohort_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Cohort Execution Plan",
        "",
        "Research-use only. Technical planning does not establish biological or clinical validity.",
        "",
        f"Cohort ID: {plan['cohort_id']}",
        f"Cohort attempt: {plan['cohort_attempt_id']}",
        f"Package version: {plan['workflow_package_version']}",
        f"Selected samples: {len(plan['selected_samples'])}",
        f"Excluded samples: {len(plan['excluded_samples'])}",
        f"Array task count: {plan['task_count']}",
        f"Maximum concurrency: {plan['maximum_concurrency']}",
        "",
        "## Array Groups",
    ]
    for group in plan["array_grouping"]:
        lines.append(f"- {group['name']}: {group['task_count']} tasks, max concurrency {group['max_concurrent']}")
    lines.append("")
    lines.append("## Samples")
    for sample in plan["selected_samples"][:200]:
        lines.append(f"- {sample['array_index']}: {sample['sample_id']} ({sample['analysis']}, {sample['input_type']})")
    if len(plan["selected_samples"]) > 200:
        lines.append(f"- ... {len(plan['selected_samples']) - 200} additional samples omitted from preview")
    (attempt_dir / "cohort_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_array_index(plan: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["array_index\tsample_id\tanalysis\tinput_type\tattempt_id\tmanifest_row_hash"]
    for sample in plan["selected_samples"]:
        lines.append(
            "\t".join(
                [
                    str(sample["array_index"]),
                    sample["sample_id"],
                    sample["analysis"],
                    sample["input_type"],
                    sample["attempt_id"],
                    sample["manifest_row_hash"],
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
