"""Safe command rendering and execution."""

from __future__ import annotations

import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from variant_analysis_harness.exceptions import CommandError
from variant_analysis_harness.models import CommandSpec, StageResult


def render_command(argv: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in argv)


def write_command_json(spec: CommandSpec, path: Path) -> None:
    data = {
        "stage": spec.stage,
        "tool_name": spec.tool_name,
        "argv": spec.argv,
        "display_command": render_command(spec.argv),
        "inputs": [str(p) for p in spec.inputs],
        "outputs": [str(p) for p in spec.outputs],
        "cwd": str(spec.cwd) if spec.cwd else None,
        "timeout_seconds": spec.timeout_seconds,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(spec: CommandSpec, stage_dir: Path, dry_run: bool = False) -> StageResult:
    logs = stage_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stdout_path = logs / "stdout.log"
    stderr_path = logs / "stderr.log"
    command_path = stage_dir / "stage.command.json"
    write_command_json(spec, command_path)
    started = _now()
    start_time = time.monotonic()
    if dry_run:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return StageResult(spec.stage, "skipped", None, stdout_path, stderr_path, started, _now(), 0.0)
    try:
        completed = subprocess.run(
            [str(x) for x in spec.argv],
            cwd=str(spec.cwd) if spec.cwd else None,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            check=False,
        )
    except KeyboardInterrupt as exc:
        ended = _now()
        stderr_path.write_text("Interrupted by operator\n", encoding="utf-8")
        return StageResult(spec.stage, "interrupted", None, stdout_path, stderr_path, started, ended, time.monotonic() - start_time, error=str(exc))
    except subprocess.TimeoutExpired as exc:
        ended = _now()
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text((exc.stderr or "") + "\nCommand timed out\n", encoding="utf-8")
        return StageResult(spec.stage, "failed", None, stdout_path, stderr_path, started, ended, time.monotonic() - start_time, error="timeout")
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    ended = _now()
    status = "success" if completed.returncode == 0 else "failed"
    return StageResult(
        spec.stage,
        status,
        completed.returncode,
        stdout_path,
        stderr_path,
        started,
        ended,
        time.monotonic() - start_time,
        error=None if completed.returncode == 0 else "nonzero_exit",
    )


def raise_on_failed(result: StageResult) -> None:
    if result.status not in {"success", "warning", "skipped"}:
        raise CommandError(f"Stage {result.stage} failed with status {result.status}")


def environment_summary() -> dict[str, str]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "working_directory": os.getcwd(),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
