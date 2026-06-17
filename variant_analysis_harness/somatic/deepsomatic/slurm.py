"""DeepSomatic Slurm pair-array planning."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_deepsomatic_slurm_array(plan: dict[str, Any], path: Path, *, max_concurrent: int, submit: bool = False) -> Path:
    task_count = len(plan.get("pairs", []))
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "#!/usr/bin/env bash",
        "#SBATCH --job-name=deepsomatic_pairs",
        f"#SBATCH --array=1-{task_count}%{max_concurrent}" if task_count else "#SBATCH --array=1-1%1",
        "#SBATCH --output=slurm/deepsomatic_%A_%a.out",
        "#SBATCH --error=slurm/deepsomatic_%A_%a.err",
        "set -euo pipefail",
        "echo \"DeepSomatic pair-array script is planning-only unless submitted explicitly.\"",
        "PAIR_INDEX=${SLURM_ARRAY_TASK_ID}",
        "echo \"Would run pair index ${PAIR_INDEX}\"",
    ]
    if not submit:
        lines.append("echo \"Submission disabled by default.\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
