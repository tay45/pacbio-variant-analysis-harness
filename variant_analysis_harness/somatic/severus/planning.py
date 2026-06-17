"""Severus pair planning, status, and provenance."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER, __version__
from variant_analysis_harness.somatic.severus.compatibility import SEVERUS_CONTRACT_VERSION
from variant_analysis_harness.somatic.manifest import SomaticPair
from variant_analysis_harness.somatic.preflight import validate_pair_preflight
from variant_analysis_harness.somatic.severus.commands import (
    build_severus_command_spec,
    command_signature,
    sanitized_command,
)
from variant_analysis_harness.somatic.severus.config import resolve_severus_config, validate_severus_config

SEVERUS_FAILURE_CATEGORIES = {
    "severus_config_error",
    "severus_version_mismatch",
    "severus_mode_unsupported",
    "severus_container_missing",
    "severus_container_digest_mismatch",
    "severus_executable_missing",
    "severus_version_probe_failed",
    "severus_preflight_failed",
    "severus_command_conflict",
    "severus_execution_failed",
    "severus_timeout",
    "severus_resource_exhaustion",
    "severus_disk_space_error",
    "severus_output_missing",
    "severus_vcf_invalid",
    "severus_bnd_invalid",
    "severus_index_missing",
    "severus_index_invalid",
    "severus_unknown_filter",
    "severus_qc_failed",
    "tumor_only_unsupported",
    "normal_background_missing",
    "interrupted",
    "cancelled",
    "unknown",
}


def generate_severus_plan(
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
    sev_config = resolve_severus_config(somatic_config)
    pair_entries: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    for pair in selected:
        phase2d = validate_pair_preflight(pair, somatic_config)
        try:
            config_validation = validate_severus_config(sev_config, mode=pair.analysis_mode)
        except Exception as exc:
            config_validation = {"status": "FAIL", "errors": [str(exc)], "warnings": []}
        status = "READY" if phase2d["readiness_status"] == "ready" and config_validation["status"] != "FAIL" else "BLOCKED"
        if phase2d["readiness_status"] == "warning" and include_warning_pairs and config_validation["status"] != "FAIL":
            status = "READY_WITH_WARNINGS"
        failure = ""
        if status == "BLOCKED":
            failure = "severus_preflight_failed" if phase2d["readiness_status"] != "ready" else "severus_config_error"
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
                spec, paths = build_severus_command_spec(
                    pair=pair,
                    reference=reference,
                    sev_config=sev_config,
                    project_attempt_dir=project_attempt_dir,
                    pair_attempt_id=pair_attempt_id,
                )
            except ValueError as exc:
                entry["caller_preflight_status"] = "BLOCKED"
                entry["failure_category"] = "severus_command_conflict"
                entry["diagnostic"] = str(exc)
                continue
            array_index = len(pair_entries) + 1
            sig = command_signature(spec.argv)
            pair_entries.append(
                {
                    **entry,
                    "array_index": array_index,
                    "attempt_id": pair_attempt_id,
                    "command_signature": sig,
                    "resource_class": _resource_class(sev_config),
                    "output_dir": str(paths["native_outputs"]),
                }
            )
            commands.append(
                {
                    "pair_id": pair.pair_id,
                    "argv": spec.argv,
                    "sanitized_argv": sanitized_command(spec.argv),
                    "command_signature": sig,
                    "outputs": [str(path) for path in spec.outputs],
                }
            )
    return {
        "backend": "severus",
        "package_version": __version__,
        "research_use_only": True,
        "pair_attempt_id": pair_attempt_id,
        "severus_contract_version": SEVERUS_CONTRACT_VERSION,
        "migration_warning": "Phase 2F Severus command signatures used unverified flags and are not resumable under Phase 2F.1.",
        "array_group": {"name": "severus_pairs", "task_count": len(pair_entries), "max_concurrent": max_concurrent},
        "pairs": pair_entries,
        "blocked_pairs": [s for s in statuses if s["caller_preflight_status"] == "BLOCKED"],
        "pair_statuses": statuses,
        "commands": commands,
        "severus_config": sev_config,
        "reference": str(reference),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "non_goals": ["CNV calling", "clinical interpretation", "automatic cloud execution", "tumor-only Severus fallback"],
    }


def write_severus_plan(plan: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "severus_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_array_index(plan, out_dir / "severus_array_index.tsv")
    write_execution_environment(plan, out_dir)
    lines = [
        "# Severus Somatic SV Pair Plan",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        f"Ready pairs: {len(plan['pairs'])}",
        f"Blocked pairs: {len(plan['blocked_pairs'])}",
        "",
        "Tumor-only Severus planning is blocked unless a future compatibility policy explicitly supports it.",
        "No CNV, annotation, clinical interpretation, cloud execution, or automatic submission is implemented.",
    ]
    (out_dir / "severus_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_array_index(plan: dict[str, Any], path: Path) -> None:
    fieldnames = [
        "array_index",
        "pair_id",
        "subject_id",
        "analysis_mode",
        "tumor_sample_id",
        "normal_sample_id",
        "attempt_id",
        "manifest_row_hash",
        "command_signature",
        "resource_class",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for row in plan["pairs"]:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_execution_environment(plan: dict[str, Any], out_dir: Path) -> None:
    sev = plan["severus_config"]["severus"]
    env = {"execution": sev.get("execution", {}), "container": sev.get("container", {}), "executable": sev.get("executable", {}), "parameters": sev.get("parameters", {})}
    (out_dir / "severus_execution_environment.json").write_text(json.dumps(env, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = ["# Severus Execution Environment", "", f"Mode: {env['execution'].get('mode')}", f"Container: {env['container']}", f"Executable: {env['executable']}"]
    (out_dir / "severus_execution_environment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_command_files(plan: dict[str, Any], out_dir: Path) -> None:
    command_dir = out_dir / "commands"
    command_dir.mkdir(parents=True, exist_ok=True)
    for command in plan["commands"]:
        pair_dir = command_dir / command["pair_id"]
        pair_dir.mkdir(parents=True, exist_ok=True)
        (pair_dir / "command.json").write_text(json.dumps(command, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (pair_dir / "command.sh").write_text("#!/usr/bin/env bash\n# Review-only command; generated as an argument list in provenance.\n" + " ".join(command["sanitized_argv"]) + "\n", encoding="utf-8")


def _resource_class(sev_config: dict[str, Any]) -> str:
    threads = sev_config.get("severus", {}).get("parameters", {}).get("threads")
    if threads and int(threads) >= 32:
        return "somatic_sv_high_cpu"
    return "somatic_sv_standard"
