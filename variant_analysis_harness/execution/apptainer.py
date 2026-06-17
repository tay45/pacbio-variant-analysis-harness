"""Apptainer/Singularity validation helpers."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.exceptions import ValidationError
from variant_analysis_harness.models import ToolConfig


def validate_container_tool(tool: ToolConfig) -> None:
    if tool.backend not in {"apptainer", "singularity"}:
        return
    if tool.container is None:
        raise ValidationError(f"{tool.name} container is required")
    if not Path(tool.container).exists():
        raise ValidationError(f"{tool.name} container not found: {tool.container}")
