"""Site-neutral Slurm array generation for cohorts."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any


def generate_cohort_array_script(
    plan: dict[str, Any],
    *,
    config_path: Path,
    manifest_path: Path,
    slurm_profile: dict[str, Any] | None,
    script_path: Path,
    max_concurrent: int,
    dry_run: bool = True,
) -> Path:
    if max_concurrent < 1:
        raise ValueError("max_concurrent must be at least 1")
    task_count = int(plan["task_count"])
    if task_count < 1:
        raise ValueError("cannot generate Slurm array for zero selected samples")
    profile = slurm_profile or {}
    script_path.parent.mkdir(parents=True, exist_ok=True)
    array_spec = f"1-{task_count}%{max_concurrent}"
    log_root = script_path.parent.parent / "logs" / "slurm" / "%A" / "%a"
    workflow = (
        f"{shlex.quote(sys.executable)} -m variant_analysis_harness.cli run "
        f"--config {shlex.quote(str(config_path.resolve()))} "
        '--manifest "${SAMPLE_MANIFEST}" '
        '--sample "${SAMPLE_ID}" '
        '--analysis "${SAMPLE_ANALYSIS}" '
        '--attempt-id "${SAMPLE_ATTEMPT_ID}"'
    )
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"#SBATCH --job-name={_sbatch_value(profile.get('job_name', 'vah_cohort'))}",
        f"#SBATCH --array={array_spec}",
        f"#SBATCH --output={log_root}.out",
        f"#SBATCH --error={log_root}.err",
    ]
    for key, directive in (("partition", "partition"), ("account", "account"), ("qos", "qos"), ("time", "time")):
        if profile.get(key):
            lines.append(f"#SBATCH --{directive}={_sbatch_value(profile[key])}")
    if profile.get("cpus_per_task"):
        lines.append(f"#SBATCH --cpus-per-task={int(profile['cpus_per_task'])}")
    if profile.get("memory_gb"):
        lines.append(f"#SBATCH --mem={int(profile['memory_gb'])}G")
    lines.extend(
        [
            "",
            'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'COHORT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"',
            'ARRAY_INDEX="${COHORT_DIR}/array_index.tsv"',
            'TASK_ROW="$(awk -F "\\t" -v idx="${SLURM_ARRAY_TASK_ID}" \'NR > 1 && $1 == idx {print; found=1} END {if (!found) exit 44}\' "${ARRAY_INDEX}")"',
            'IFS=$\'\\t\' read -r ARRAY_INDEX_VALUE SAMPLE_ID SAMPLE_ANALYSIS SAMPLE_INPUT_TYPE SAMPLE_ATTEMPT_ID MANIFEST_ROW_HASH <<< "${TASK_ROW}"',
            'SAMPLE_MANIFEST="${COHORT_DIR}/manifests/${SAMPLE_ID}.manifest.tsv"',
            'STATUS_DIR="${COHORT_DIR}/status/events/${SAMPLE_ID:0:2}/${SAMPLE_ID}"',
            'mkdir -p "${STATUS_DIR}" "$(dirname "${SAMPLE_MANIFEST}")"',
            'python -m variant_analysis_harness.cli cohort-rerun-manifest --cohort-dir "${COHORT_DIR}" --include-samples "${SAMPLE_ID}" --output "${SAMPLE_MANIFEST}" --allow-successful',
            'echo "Running sample ${SAMPLE_ID} from array task ${SLURM_ARRAY_TASK_ID}"',
            workflow,
        ]
    )
    if dry_run:
        lines.append("# Submission disabled by default; review this script before any manual scheduler use.")
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script_path


def write_dependency_graph(plan: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "implemented": "one full single-sample workflow per array task",
        "submit_enabled_by_default": False,
        "future_stage_array_policy": {
            "analytical_stages": "afterok",
            "qc_and_failure_reporting": "afterany where justified",
        },
        "arrays": plan.get("array_grouping", []),
    }
    (out_dir / "dependency_graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Cohort Dependency Graph",
        "",
        "Implemented Phase 2B design: one full single-sample workflow per array task.",
        "",
        "Future stage-array design should use `afterok` for analytical dependencies and `afterany` for failure-aware QC/reporting when justified.",
    ]
    (out_dir / "dependency_graph.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sbatch_value(value: Any) -> str:
    text = str(value)
    if any(ch in text for ch in "\n\r;&|`$"):
        raise ValueError(f"unsafe Slurm directive value: {value!r}")
    return text
