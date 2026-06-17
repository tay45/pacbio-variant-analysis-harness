"""DeepSomatic local execution and attempt helpers."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from variant_analysis_harness.common.signatures import object_signature


@dataclass(frozen=True)
class DeepSomaticExecutionResult:
    status: str
    exit_code: int
    stdout: str
    stderr: str
    runtime_seconds: float
    command_signature: str
    failure_category: str = ""


def run_deepsomatic_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> DeepSomaticExecutionResult:
    start = time.monotonic()
    try:
        completed = runner(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired as exc:
        return DeepSomaticExecutionResult("caller_failed", 124, str(exc.stdout or ""), str(exc.stderr or ""), time.monotonic() - start, object_signature(argv), "deepsomatic_timeout")
    runtime = time.monotonic() - start
    status = "caller_success" if completed.returncode == 0 else "caller_failed"
    failure = "" if completed.returncode == 0 else "deepsomatic_execution_failed"
    return DeepSomaticExecutionResult(status, int(completed.returncode), completed.stdout or "", completed.stderr or "", runtime, object_signature(argv), failure)


def write_execution_result(result: DeepSomaticExecutionResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.__dict__, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def can_resume_attempt(status_path: Path, *, expected_command_signature: str) -> bool:
    if not status_path.exists():
        return False
    status = json.loads(status_path.read_text(encoding="utf-8"))
    return (
        status.get("status") == "complete"
        and status.get("command_signature") == expected_command_signature
        and status.get("output_validation_status") == "PASS"
    )


def supersede_attempt(prior_status: Path, new_attempt_id: str) -> None:
    if not prior_status.exists():
        return
    data = json.loads(prior_status.read_text(encoding="utf-8"))
    data["status"] = "superseded"
    data["superseded_by"] = new_attempt_id
    prior_status.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
