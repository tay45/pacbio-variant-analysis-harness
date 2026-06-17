"""Slurm shard array generation for joint genotyping."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any


def write_joint_slurm_array(plan: dict[str, Any], script_path: Path, *, max_concurrent: int, profile: dict[str, Any] | None = None) -> Path:
    if max_concurrent < 1:
        raise ValueError("max_concurrent must be at least 1")
    count = int(plan["shard_count"])
    if count < 1:
        raise ValueError("no enabled shards")
    profile = profile or {}
    script_path.parent.mkdir(parents=True, exist_ok=True)
    log_root = script_path.parent.parent / "logs" / "slurm" / "%A" / "%a"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "#SBATCH --job-name=vah_joint",
        f"#SBATCH --array=1-{count}%{max_concurrent}",
        f"#SBATCH --output={log_root}.out",
        f"#SBATCH --error={log_root}.err",
    ]
    for key in ("partition", "account", "qos", "time"):
        if profile.get(key):
            lines.append(f"#SBATCH --{key}={_safe(profile[key])}")
    lines.extend(
        [
            "",
            'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'JOINT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"',
            'ARRAY_INDEX="${JOINT_DIR}/array_index.tsv"',
            'TASK_ROW="$(awk -F "\\t" -v idx="${SLURM_ARRAY_TASK_ID}" \'NR > 1 && $1 == idx {print; found=1} END {if (!found) exit 44}\' "${ARRAY_INDEX}")"',
            'IFS=$\'\\t\' read -r ARRAY_INDEX_VALUE SHARD_ID CONTIG START END INPUT_LIST OUTPUT_VCF <<< "${TASK_ROW}"',
            'echo "Planned shard ${SHARD_ID} ${CONTIG}:${START}-${END}"',
            "# Phase 2C generates reviewable shard arrays; no submission is performed by the harness.",
        ]
    )
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (script_path.parent / "dependency_graph.json").write_text(json.dumps({"shard_array": "afterok before concat", "qc_report": "afterany when needed"}, indent=2) + "\n", encoding="utf-8")
    return script_path


def _safe(value: Any) -> str:
    text = str(value)
    if any(ch in text for ch in "\n\r;&|`$"):
        raise ValueError(f"unsafe Slurm value: {value!r}")
    return shlex.quote(text)

