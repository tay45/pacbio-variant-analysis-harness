"""Native executable backend helpers."""

from __future__ import annotations

from shutil import which

from variant_analysis_harness.exceptions import ValidationError
from variant_analysis_harness.models import ToolConfig


def validate_native_tool(tool: ToolConfig) -> None:
    executable = tool.executable or tool.name
    if which(executable) is None:
        raise ValidationError(f"Tool not found on PATH: {executable}")
