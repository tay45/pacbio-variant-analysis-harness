"""Docker backend scaffold.

Phase 2A supports safe command construction for Docker but does not require
Docker for standard tests or local operation.
"""

from __future__ import annotations

from variant_analysis_harness.models import ToolConfig


def docker_image(tool: ToolConfig) -> str:
    if tool.container is None:
        raise ValueError(f"{tool.name} docker image is required")
    return str(tool.container)
