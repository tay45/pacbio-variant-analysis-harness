"""Provenance record writing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.command import environment_summary, render_command
from variant_analysis_harness.models import CommandSpec


def write_provenance(
    path: Path,
    *,
    project_id: str,
    sample_id: str,
    attempt_id: str,
    stage: str,
    command: CommandSpec | None,
    tool: dict[str, Any] | None,
    reference: dict[str, Any],
    outputs: list[Path],
    validation_status: str,
    warnings: list[str] | None = None,
) -> None:
    data = {
        "project_id": project_id,
        "sample_id": sample_id,
        "attempt_id": attempt_id,
        "stage": stage,
        "tool": tool or {},
        "backend_type": (tool or {}).get("backend"),
        "container_path": (tool or {}).get("container"),
        "command_argv": command.argv if command else None,
        "display_command": render_command(command.argv) if command else None,
        "input_paths": [str(p) for p in command.inputs] if command else [],
        "reference": reference,
        "environment": environment_summary(),
        "output_paths": [str(p) for p in outputs],
        "validation_status": validation_status,
        "warnings": warnings or [],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
