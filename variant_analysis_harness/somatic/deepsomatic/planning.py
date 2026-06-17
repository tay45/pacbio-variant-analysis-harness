"""DeepSomatic pair planning, status, and provenance."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER, __version__
from variant_analysis_harness.common.signatures import file_signature, object_signature
from variant_analysis_harness.somatic.deepsomatic.commands import (
    build_deepsomatic_command_spec,
    command_signature,
    sanitized_command,
)
from variant_analysis_harness.somatic.deepsomatic.config import resolve_deepsomatic_config, validate_deepsomatic_config
from variant_analysis_harness.somatic.manifest import SomaticPair
from variant_analysis_harness.somatic.preflight import validate_pair_preflight

DEEPSOMATIC_FAILURE_CATEGORIES = {
    "deepsomatic_config_error",
    "deepsomatic_version_mismatch",
    "deepsomatic_model_type_mismatch",
    "deepsomatic_model_metadata_missing",
    "deepsomatic_model_metadata_invalid",
    "deepsomatic_model_file_missing",
    "deepsomatic_container_missing",
    "deepsomatic_container_digest_mismatch",
    "deepsomatic_executable_missing",
    "deepsomatic_version_probe_failed",
    "deepsomatic_preflight_failed",
    "deepsomatic_command_conflict",
    "deepsomatic_execution_failed",
    "deepsomatic_timeout",
    "deepsomatic_resource_exhaustion",
    "deepsomatic_disk_space_error",
    "deepsomatic_output_missing",
    "deepsomatic_vcf_invalid",
    "deepsomatic_gvcf_invalid",
    "deepsomatic_index_missing",
    "deepsomatic_index_invalid",
    "deepsomatic_unknown_filter",
    "deepsomatic_qc_failed",
    "pon_missing",
    "pon_incompatible",
    "tumor_only_model_mismatch",
    "interrupted",
    "cancelled",
    "unknown",
}


def generate_deepsomatic_plan(
    cfg: dict[str, Any],
    somatic_config: dict[str, Any],
    *,
    project_attempt_dir: Path,
    selected: list[SomaticPair],
    reference: Path,
    pair_attempt_id: str,
    max_concurrent: int,
    include_warning_pairs: bool = False,
) -> dict[str, Any]:
    ds_config = resolve_deepsomatic_config(somatic_config)
    pair_entries = []
    statuses = []
    commands = []
    for pair in selected:
        phase2d = validate_pair_preflight(pair, somatic_config)
        config_validation = validate_deepsomatic_config(ds_config, mode=pair.analysis_mode)
        status = "READY" if phase2d["readiness_status"] == "ready" and config_validation["status"] != "FAIL" else "BLOCKED"
        if phase2d["readiness_status"] == "warning" and include_warning_pairs and config_validation["status"] != "FAIL":
            status = "READY_WITH_WARNINGS"
        failure = ""
        if status == "BLOCKED":
            failure = "deepsomatic_preflight_failed" if phase2d["readiness_status"] != "ready" else "deepsomatic_config_error"
        entry = {
            "pair_id": pair.pair_id,
            "subject_id": pair.subject_id,
            "analysis_mode": pair.analysis_mode,
            "tumor_sample_id": pair.tumor_sample_id,
            "normal_sample_id": pair.normal_sample_id,
            "manifest_row_hash": pair.row_hash,
            "caller_preflight_status": status,
            "failure_category": failure,
            "phase2d_readiness": phase2d["readiness_status"],
            "config_validation": config_validation,
        }
        statuses.append(entry)
        if status in {"READY", "READY_WITH_WARNINGS"}:
            try:
                spec, paths = build_deepsomatic_command_spec(pair=pair, reference=reference, ds_config=ds_config, project_attempt_dir=project_attempt_dir, pair_attempt_id=pair_attempt_id)
            except ValueError as exc:
                entry["caller_preflight_status"] = "BLOCKED"
                entry["failure_category"] = "deepsomatic_command_conflict"
                entry["diagnostic"] = str(exc)
                continue
            array_index = len(pair_entries) + 1
            sig = command_signature(spec.argv)
            pair_entries.append({**entry, "array_index": array_index, "attempt_id": pair_attempt_id, "command_signature": sig, "output_dir": str(paths["output"])})
            commands.append({"pair_id": pair.pair_id, "argv": spec.argv, "sanitized_argv": sanitized_command(spec.argv), "command_signature": sig, "outputs": [str(p) for p in spec.outputs]})
    return {
        "backend": "deepsomatic",
        "package_version": __version__,
        "research_use_only": True,
        "pair_attempt_id": pair_attempt_id,
        "array_group": {"name": "deepsomatic_pairs", "task_count": len(pair_entries), "max_concurrent": max_concurrent},
        "pairs": pair_entries,
        "blocked_pairs": [s for s in statuses if s["caller_preflight_status"] == "BLOCKED"],
        "pair_statuses": statuses,
        "commands": commands,
        "deepsomatic_config": ds_config,
        "reference": str(reference),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_deepsomatic_plan(plan: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "deepsomatic_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_array_index(plan, out_dir / "deepsomatic_array_index.tsv")
    write_execution_environment(plan, out_dir)
    lines = ["# DeepSomatic Pair Plan", "", RESEARCH_USE_DISCLAIMER, "", f"Ready pairs: {len(plan['pairs'])}", f"Blocked pairs: {len(plan['blocked_pairs'])}", "", "No somatic SV, CNV, annotation, or clinical interpretation is implemented."]
    (out_dir / "deepsomatic_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_array_index(plan: dict[str, Any], path: Path) -> None:
    fieldnames = ["array_index", "pair_id", "subject_id", "analysis_mode", "tumor_sample_id", "normal_sample_id", "attempt_id", "manifest_row_hash", "command_signature"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in plan["pairs"]:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_execution_environment(plan: dict[str, Any], out_dir: Path) -> None:
    ds = plan["deepsomatic_config"]["deepsomatic"]
    env = {"execution": ds.get("execution", {}), "container": ds.get("container", {}), "executable": ds.get("executable", {}), "model": ds.get("model", {})}
    (out_dir / "deepsomatic_execution_environment.json").write_text(json.dumps(env, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = ["# DeepSomatic Execution Environment", "", f"Mode: {env['execution'].get('mode')}", f"Container: {env['container']}", f"Executable: {env['executable']}"]
    (out_dir / "deepsomatic_execution_environment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_command_files(plan: dict[str, Any], out_dir: Path) -> None:
    command_dir = out_dir / "commands"
    command_dir.mkdir(parents=True, exist_ok=True)
    for command in plan["commands"]:
        pair_dir = command_dir / command["pair_id"]
        pair_dir.mkdir(parents=True, exist_ok=True)
        (pair_dir / "command.json").write_text(json.dumps(command, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (pair_dir / "command.sh").write_text("#!/usr/bin/env bash\n# Review-only command; generated as an argument list in provenance.\n" + " ".join(command["sanitized_argv"]) + "\n", encoding="utf-8")
