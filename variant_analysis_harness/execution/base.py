"""Backend command wrapping."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.models import ToolConfig


def wrap_tool_command(tool: ToolConfig, inner_argv: list[str], bind_paths: list[Path] | None = None) -> list[str]:
    if tool.backend == "native":
        executable = tool.executable or tool.name
        return [executable] + inner_argv
    if tool.backend in {"apptainer", "singularity"}:
        runtime = "apptainer" if tool.backend == "apptainer" else "singularity"
        if tool.executable:
            runtime = tool.executable
        argv = [runtime, "exec"]
        for path in sorted({p.resolve() for p in bind_paths or []}):
            argv.extend(["--bind", f"{path}:{path}"])
        argv.append(str(tool.container))
        return argv + inner_argv
    if tool.backend == "docker":
        image = str(tool.container)
        argv = ["docker", "run", "--rm"]
        for path in sorted({p.resolve() for p in bind_paths or []}):
            argv.extend(["-v", f"{path}:{path}"])
        argv.append(image)
        return argv + inner_argv
    if tool.backend == "conda":
        if not tool.conda_environment:
            raise ValueError("conda backend requires conda_environment")
        executable = tool.executable or tool.name
        return ["conda", "run", "-n", tool.conda_environment, executable] + inner_argv
    raise ValueError(f"Unsupported backend: {tool.backend}")
