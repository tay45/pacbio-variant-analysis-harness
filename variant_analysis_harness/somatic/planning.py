"""Somatic preflight planning and artifact writing."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER, __version__
from variant_analysis_harness.common.signatures import file_signature, object_signature
from variant_analysis_harness.common.yaml_io import dump_yaml
from variant_analysis_harness.somatic.manifest import SomaticPair, write_somatic_manifest_artifacts
from variant_analysis_harness.somatic.preflight import pair_input_paths, validate_pair_preflight


PAIR_STATUSES = {
    "pending",
    "validating",
    "ready",
    "warning",
    "failed",
    "blocked",
    "excluded",
    "interrupted",
    "cancelled",
    "superseded",
    "unknown",
}


def somatic_attempt_dir(
    cfg: dict[str, Any],
    somatic_project_id: str,
    attempt_id: str,
    output_root: Path | None = None,
) -> Path:
    root = output_root or Path(cfg["project"]["output_root"])
    return root / cfg["project"]["name"] / "somatic" / somatic_project_id / attempt_id


def pair_dir(attempt_dir: Path, pair: SomaticPair) -> Path:
    shard = pair.pair_id[:2] if len(pair.pair_id) >= 2 else "_"
    return attempt_dir / "pairs" / shard / pair.pair_id


def prepare_somatic_attempt(
    attempt_dir: Path,
    *,
    config_path: Path,
    manifest_path: Path,
    cfg: dict[str, Any],
    selected: list[SomaticPair],
    excluded: list[SomaticPair],
    validation: Any,
) -> None:
    for sub in ("status", "manifests", "reports", "provenance", "slurm", "logs"):
        (attempt_dir / sub).mkdir(parents=True, exist_ok=True)
    for pair in selected:
        for sub in ("preflight", "status", "logs", "provenance", "snv", "sv"):
            (pair_dir(attempt_dir, pair) / sub).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_path, attempt_dir / "config.original.yaml")
    dump_yaml(cfg, attempt_dir / "config.resolved.yaml")
    shutil.copyfile(manifest_path, attempt_dir / "somatic_manifest.original.tsv")
    write_somatic_manifest_artifacts(selected, excluded, validation, attempt_dir)


def generate_somatic_plan(
    cfg: dict[str, Any],
    somatic_config: dict[str, Any],
    *,
    config_path: Path,
    manifest_path: Path,
    selected: list[SomaticPair],
    excluded: list[SomaticPair],
    validation: Any,
    somatic_project_id: str,
    attempt_id: str,
    output_root: Path | None,
    max_concurrent_pairs: int,
) -> dict[str, Any]:
    attempt_dir = somatic_attempt_dir(cfg, somatic_project_id, attempt_id, output_root)
    pair_entries = []
    statuses = []
    for pair in selected:
        preflight = validate_pair_preflight(pair, somatic_config)
        status = build_pair_status(cfg, somatic_project_id, attempt_id, pair, preflight)
        statuses.append(status)
        if status["readiness_status"] in {"ready", "warning"} and (
            status["readiness_status"] == "ready" or somatic_config.get("warning_pairs_active", True)
        ):
            array_index = len(pair_entries) + 1
            pair_entries.append(
                {
                    "array_index": array_index,
                    "pair_id": pair.pair_id,
                    "subject_id": pair.subject_id,
                    "analysis_mode": pair.analysis_mode,
                    "tumor_sample_id": pair.tumor_sample_id,
                    "normal_sample_id": pair.normal_sample_id,
                    "tumor_input_type": pair.tumor_input_type.upper(),
                    "normal_input_type": pair.normal_input_type.upper() if pair.normal_input_type else "",
                    "manifest_row_hash": pair.row_hash,
                    "preflight_status": status["readiness_status"],
                    "expected_pair_dir": str(pair_dir(attempt_dir, pair)),
                }
            )
    excluded_entries = [{"pair_id": p.pair_id, "reason": "disabled_or_filtered", "manifest_row_hash": p.row_hash} for p in excluded]
    plan = {
        "somatic_project_id": somatic_project_id,
        "attempt_id": attempt_id,
        "selected_pair_count": len(selected),
        "excluded_pair_count": len(excluded),
        "tumor_normal_count": sum(1 for p in selected if p.analysis_mode == "tumor_normal"),
        "tumor_only_count": sum(1 for p in selected if p.analysis_mode == "tumor_only"),
        "pair_ids": [p.pair_id for p in selected],
        "subject_ids": sorted({p.subject_id for p in selected}),
        "pairs": pair_entries,
        "excluded_pairs": excluded_entries,
        "blocked_pairs": [s for s in statuses if s["readiness_status"] == "failed"],
        "warning_pairs": [s for s in statuses if s["readiness_status"] == "warning"],
        "identity_policy": somatic_config.get("identity_policy", "strict"),
        "normal_reuse_policy": somatic_config.get("normal_reuse", {}),
        "coverage_metadata_state": _metadata_state(selected, ["tumor_coverage", "normal_coverage"]),
        "purity_metadata_state": _metadata_state(selected, ["tumor_purity"]),
        "contamination_metadata_state": _metadata_state(selected, ["tumor_contamination", "normal_contamination"]),
        "ploidy_metadata_state": _metadata_state(selected, ["tumor_ploidy"]),
        "caller_stages_deferred": True,
        "expected_future_snv_stage": "deferred_deepsomatic_or_selected_somatic_small_variant_caller",
        "expected_future_sv_stage": "deferred_long_read_somatic_sv_caller_evaluation",
        "resource_profile_placeholders": {
            "somatic_preflight": {"cpus": 1, "memory_gb": 4, "time": "00:30:00"},
            "future_snv": {"status": "deferred"},
            "future_sv": {"status": "deferred"},
        },
        "slurm_grouping_placeholders": [
            {"name": "somatic_preflight_pairs", "task_count": len(pair_entries), "max_concurrent": max_concurrent_pairs}
        ],
        "validation_state": validation.to_dict() if hasattr(validation, "to_dict") else validation,
        "pair_statuses": statuses,
        "array_index_path": str(attempt_dir / "somatic_array_index.tsv"),
        "config_signature": file_signature(config_path),
        "config_object_signature": object_signature(cfg),
        "manifest_signature": file_signature(manifest_path),
        "reference_signature": object_signature(cfg.get("reference", {})),
        "package_version": __version__,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "research_use_only": True,
        "no_somatic_callers_executed": True,
    }
    return plan


def build_pair_status(
    cfg: dict[str, Any],
    somatic_project_id: str,
    attempt_id: str,
    pair: SomaticPair,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "somatic_project_id": somatic_project_id,
        "project_attempt": attempt_id,
        "pair_id": pair.pair_id,
        "subject_id": pair.subject_id,
        "tumor_sample_id": pair.tumor_sample_id,
        "normal_sample_id": pair.normal_sample_id,
        "analysis_mode": pair.analysis_mode,
        "preflight_status": preflight["readiness_status"],
        "identity_status": preflight["identity"]["status"],
        "reference_status": preflight["reference"]["status"],
        "coverage_status": preflight["coverage"]["status"],
        "metadata_status": preflight["metadata"]["status"],
        "readiness_status": preflight["readiness_status"],
        "failure_category": preflight["failure_category"],
        "warning_count": preflight["warning_count"],
        "start_time": now,
        "end_time": now,
        "prior_attempt": "",
        "config_signature": object_signature(cfg),
        "manifest_row_signature": pair.row_hash,
        "errors": preflight["errors"],
        "warnings": preflight["warnings"],
    }


def write_somatic_plan(plan: dict[str, Any], attempt_dir: Path) -> None:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    (attempt_dir / "somatic_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = [
        "# Somatic Preflight Plan",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        f"Somatic project ID: {plan['somatic_project_id']}",
        f"Attempt ID: {plan['attempt_id']}",
        f"Selected pairs: {plan['selected_pair_count']}",
        f"Excluded pairs: {plan['excluded_pair_count']}",
        f"Tumor-normal pairs: {plan['tumor_normal_count']}",
        f"Tumor-only pairs: {plan['tumor_only_count']}",
        "",
        "No somatic SNV, indel, SV, CNV, annotation, or clinical interpretation was executed in Phase 2D.",
    ]
    (attempt_dir / "somatic_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_array_index(plan, attempt_dir / "somatic_array_index.tsv")
    write_pair_statuses(plan, attempt_dir)
    write_provenance(plan, attempt_dir)


def write_array_index(plan: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["array_index", "pair_id", "subject_id", "analysis_mode", "tumor_sample_id", "normal_sample_id", "manifest_row_hash", "preflight_status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in plan["pairs"]:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_pair_statuses(plan: dict[str, Any], attempt_dir: Path) -> None:
    status_dir = attempt_dir / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "somatic_pair_status.json").write_text(
        json.dumps(plan["pair_statuses"], indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    counts = aggregate_status_counts(plan["pair_statuses"])
    (status_dir / "somatic_status_summary.json").write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def aggregate_status_counts(statuses: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for status in statuses:
        key = status.get("readiness_status", "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def write_provenance(plan: dict[str, Any], attempt_dir: Path) -> None:
    prov = {
        "somatic_project_id": plan["somatic_project_id"],
        "attempt_id": plan["attempt_id"],
        "config_signature": plan["config_signature"],
        "manifest_signature": plan["manifest_signature"],
        "pair_row_hashes": {status["pair_id"]: status["manifest_row_signature"] for status in plan["pair_statuses"]},
        "identity_policy": plan["identity_policy"],
        "normal_reuse_policy": plan["normal_reuse_policy"],
        "package_version": plan["package_version"],
        "schema_versions": {"somatic_manifest": "phase2d.v1", "somatic_plan": "phase2d.v1"},
        "no_credentials_recorded": True,
        "no_somatic_callers_executed": True,
    }
    out = attempt_dir / "provenance" / "somatic_provenance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(prov, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _metadata_state(pairs: list[SomaticPair], fields: list[str]) -> dict[str, int]:
    present = 0
    missing = 0
    for pair in pairs:
        if any(pair.optional.get(field) not in (None, "") for field in fields):
            present += 1
        else:
            missing += 1
    return {"present": present, "missing": missing}
