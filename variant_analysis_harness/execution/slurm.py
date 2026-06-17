"""Site-neutral Slurm script generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.common.command import render_command
from variant_analysis_harness.common.schema_validation import validate_execution_profile_schema
from variant_analysis_harness.exceptions import ConfigError
from variant_analysis_harness.models import CommandSpec

UNSAFE = {";", "&&", "||", "`", "$("}


def validate_slurm_profile(profile: dict[str, Any]) -> None:
    validate_execution_profile_schema(profile)
    slurm = profile.get("slurm", profile)
    if not isinstance(slurm, dict):
        raise ConfigError("slurm profile must be a mapping")
    for key, value in slurm.items():
        if isinstance(value, str) and any(token in value for token in UNSAFE):
            raise ConfigError(f"Unsafe Slurm profile value for {key}")
    extra = slurm.get("extra_sbatch_options", [])
    if not isinstance(extra, list):
        raise ConfigError("slurm.extra_sbatch_options must be a list")
    for option in extra:
        if not isinstance(option, str) or any(token in option for token in UNSAFE):
            raise ConfigError("Unsafe extra sbatch option")


def generate_sbatch_script(
    spec: CommandSpec,
    profile: dict[str, Any],
    script_path: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> Path:
    validate_slurm_profile(profile)
    slurm = profile.get("slurm", profile)
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "echo 'This workflow is for research use only. It is not a clinically validated, diagnostic, or treatment-decision system.'",
    ]
    option_map = {
        "partition": "--partition",
        "account": "--account",
        "qos": "--qos",
        "constraint": "--constraint",
        "time": "--time",
        "cpus_per_task": "--cpus-per-task",
        "memory_gb": "--mem",
        "gres": "--gres",
    }
    for key, flag in option_map.items():
        value = slurm.get(key)
        if value in (None, ""):
            continue
        if key == "memory_gb":
            value = f"{value}G"
        lines.insert(1, f"#SBATCH {flag}={value}")
    lines.insert(1, f"#SBATCH --output={stdout_path}")
    lines.insert(1, f"#SBATCH --error={stderr_path}")
    for option in slurm.get("extra_sbatch_options", []):
        lines.insert(1, f"#SBATCH {option}")
    for setup in slurm.get("environment_setup", []):
        lines.append(str(setup))
    lines.append(f"cd {spec.cwd or Path.cwd()}")
    lines.append(render_command(spec.argv))
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script_path
