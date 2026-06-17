"""Tool and container preflight probing."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from variant_analysis_harness.models import ToolConfig

REQUIRED_TOOL_NAMES = ("dataset", "pbmm2", "samtools", "deepvariant", "pbsv", "bgzip", "tabix")

VERSION_ARGS = {
    "dataset": ["--version"],
    "pbmm2": ["--version"],
    "samtools": ["--version"],
    "deepvariant": ["run_deepvariant", "--version"],
    "pbsv": ["--version"],
    "bgzip": ["--version"],
    "tabix": ["--version"],
}


def probe_tool(tool: ToolConfig, expected_version: str | None = None, checksum: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "tool": tool.name,
        "backend": tool.backend,
        "expected_version": expected_version or tool.version,
        "detected_version": None,
        "status": "PASS",
        "checks": [],
        "warnings": [],
    }
    if tool.backend == "native":
        executable = tool.executable or tool.name
        resolved = shutil.which(executable) if not Path(executable).is_absolute() else executable
        result["executable"] = str(resolved) if resolved else executable
        if resolved is None:
            result["status"] = "FAIL"
            result["checks"].append({"name": "executable_resolution", "status": "FAIL"})
            return result
        result["checks"].append({"name": "executable_resolution", "status": "PASS"})
        version = _run_version([str(resolved)] + VERSION_ARGS.get(tool.name, ["--version"]))
        result["detected_version"] = version["stdout_first_line"] or version["stderr_first_line"]
        result["version_command_exit_code"] = version["exit_code"]
        if version["exit_code"] != 0:
            result["warnings"].append("version command returned nonzero")
            result["checks"].append({"name": "version_probe", "status": "WARN"})
        else:
            result["checks"].append({"name": "version_probe", "status": "PASS"})
        _compare_version(result)
        return result
    if tool.backend in {"apptainer", "singularity"}:
        runtime = tool.executable or tool.backend
        runtime_path = shutil.which(runtime)
        result["container_runtime"] = runtime
        result["container_runtime_path"] = runtime_path
        if runtime_path is None:
            result["status"] = "FAIL"
            result["checks"].append({"name": "container_runtime_resolution", "status": "FAIL"})
            return result
        result["checks"].append({"name": "container_runtime_resolution", "status": "PASS"})
        if tool.container is None or not Path(tool.container).exists():
            result["status"] = "FAIL"
            result["checks"].append({"name": "container_exists", "status": "FAIL"})
            return result
        container = Path(tool.container)
        result["container"] = str(container)
        result["container_size"] = container.stat().st_size
        result["checks"].append({"name": "container_exists", "status": "PASS"})
        if checksum:
            result["container_sha256"] = _sha256(container)
        runtime_version = _run_version([runtime_path, "--version"])
        result["runtime_version"] = runtime_version["stdout_first_line"] or runtime_version["stderr_first_line"]
        inner = VERSION_ARGS.get(tool.name, ["--version"])
        version = _run_version([runtime_path, "exec", str(container)] + inner)
        result["detected_version"] = version["stdout_first_line"] or version["stderr_first_line"]
        result["version_command_exit_code"] = version["exit_code"]
        if version["exit_code"] != 0:
            result["status"] = "FAIL"
            result["checks"].append({"name": "container_tool_probe", "status": "FAIL"})
        else:
            result["checks"].append({"name": "container_tool_probe", "status": "PASS"})
        _compare_version(result)
        return result
    result["status"] = "NOT_EVALUATED"
    result["warnings"].append(f"Backend {tool.backend} probing is scaffolded")
    return result


def write_probe_results(results: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tools": results}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_version(argv: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    except Exception as exc:
        return {"exit_code": None, "stdout_first_line": "", "stderr_first_line": str(exc)}
    return {
        "exit_code": completed.returncode,
        "stdout_first_line": (completed.stdout or "").splitlines()[0] if completed.stdout else "",
        "stderr_first_line": (completed.stderr or "").splitlines()[0] if completed.stderr else "",
    }


def _compare_version(result: dict[str, Any]) -> None:
    expected = result.get("expected_version")
    detected = result.get("detected_version") or ""
    if not expected:
        return
    if expected not in detected:
        result["warnings"].append(f"configured version {expected!r} not found in detected version")
        if result["status"] == "PASS":
            result["status"] = "WARN"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
