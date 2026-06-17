#!/usr/bin/env python3
"""Verify that hermetic pytest completes and exits cleanly."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


RECURSION_GUARD_ENV = "VARIANT_HARNESS_EXIT_VERIFIER_ACTIVE"
DEFAULT_TIMEOUT_SECONDS = 30.0
FULL_TIMEOUT_SECONDS = 180.0
SMOKE_TEST_PATH = "tests/smoke/test_exit_smoke_subset.py"


@dataclass(frozen=True)
class VerificationResult:
    command: list[str]
    return_code: int
    elapsed_seconds: float
    timeout_seconds: float
    timeout: bool
    process_exited: bool
    success_summary: str
    summary_printed: bool
    clean_exit: bool
    stdout: str
    stderr: str
    diagnostic: str = ""


def build_pytest_command(full: bool) -> list[str]:
    repo = Path(__file__).resolve().parents[1]
    command = [sys.executable, str(repo / "scripts" / "run_tests.py"), "-q"]
    if not full:
        command.append(SMOKE_TEST_PATH)
    return command


def build_hermetic_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env[RECURSION_GUARD_ENV] = "1"
    env.pop("PYTEST_PLUGINS", None)
    return env


def select_timeout(full: bool, timeout_seconds: float | None) -> float:
    if timeout_seconds is not None:
        return timeout_seconds
    return FULL_TIMEOUT_SECONDS if full else DEFAULT_TIMEOUT_SECONDS


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _find_summary(stdout: str) -> str:
    return next((line for line in reversed(stdout.splitlines()) if " passed" in line or " failed" in line), "")


def evaluate_completed_process(
    *,
    command: Sequence[str],
    completed: subprocess.CompletedProcess[str],
    elapsed_seconds: float,
    timeout_seconds: float,
) -> VerificationResult:
    stdout = _coerce_output(completed.stdout)
    stderr = _coerce_output(completed.stderr)
    summary = _find_summary(stdout)
    clean = completed.returncode == 0 and bool(summary)
    return VerificationResult(
        command=list(command),
        return_code=int(completed.returncode),
        elapsed_seconds=elapsed_seconds,
        timeout_seconds=timeout_seconds,
        timeout=False,
        process_exited=True,
        success_summary=summary,
        summary_printed=bool(summary),
        clean_exit=clean,
        stdout=stdout,
        stderr=stderr,
    )


def evaluate_timeout(
    *,
    command: Sequence[str],
    exc: subprocess.TimeoutExpired,
    timeout_seconds: float,
) -> VerificationResult:
    stdout = _coerce_output(exc.stdout)
    stderr = _coerce_output(exc.stderr)
    summary = _find_summary(stdout)
    return VerificationResult(
        command=list(command),
        return_code=124,
        elapsed_seconds=timeout_seconds,
        timeout_seconds=timeout_seconds,
        timeout=True,
        process_exited=False,
        success_summary=summary,
        summary_printed=bool(summary),
        clean_exit=False,
        stdout=stdout,
        stderr=stderr,
        diagnostic=f"pytest exit verification timed out after {timeout_seconds:.3f}s",
    )


def evaluate_runner_error(
    *,
    command: Sequence[str],
    exc: OSError,
    elapsed_seconds: float,
    timeout_seconds: float,
) -> VerificationResult:
    return VerificationResult(
        command=list(command),
        return_code=127,
        elapsed_seconds=elapsed_seconds,
        timeout_seconds=timeout_seconds,
        timeout=False,
        process_exited=False,
        success_summary="",
        summary_printed=False,
        clean_exit=False,
        stdout="",
        stderr="",
        diagnostic=f"failed to start pytest exit verification: {exc}",
    )


def run_exit_verification(
    *,
    full: bool,
    timeout_seconds: float | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    base_env: Mapping[str, str] | None = None,
) -> VerificationResult:
    command = build_pytest_command(full)
    timeout = select_timeout(full, timeout_seconds)
    env = build_hermetic_environment(base_env)
    start = time.monotonic()
    try:
        completed = runner(
            command,
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return evaluate_timeout(command=command, exc=exc, timeout_seconds=timeout)
    except OSError as exc:
        elapsed = time.monotonic() - start
        return evaluate_runner_error(command=command, exc=exc, elapsed_seconds=elapsed, timeout_seconds=timeout)
    elapsed = time.monotonic() - start
    return evaluate_completed_process(
        command=command,
        completed=completed,
        elapsed_seconds=elapsed,
        timeout_seconds=timeout,
    )


def format_verification_result(result: VerificationResult) -> str:
    lines = [
        f"command={' '.join(result.command)}",
        f"return_code={result.return_code}",
        f"elapsed_seconds={result.elapsed_seconds:.3f}",
        f"timeout_seconds={result.timeout_seconds:.3f}",
        f"timeout={result.timeout}",
        f"process_exited={result.process_exited}",
        f"summary_to_exit_seconds={0.0 if result.summary_printed and result.process_exited else 'unavailable'}",
        f"success_summary={result.success_summary}",
        f"summary_printed={result.summary_printed}",
        f"clean_exit={result.clean_exit}",
    ]
    if result.diagnostic:
        lines.append(f"diagnostic={result.diagnostic}")
    lines.extend(["--- stdout ---", result.stdout, "--- stderr ---", result.stderr])
    return "\n".join(lines)


def recursion_guard_result() -> VerificationResult:
    return VerificationResult(
        command=[sys.executable, str(Path(__file__).resolve())],
        return_code=2,
        elapsed_seconds=0.0,
        timeout_seconds=0.0,
        timeout=False,
        process_exited=True,
        success_summary="",
        summary_printed=False,
        clean_exit=False,
        stdout="",
        stderr="",
        diagnostic=(
            f"recursive pytest exit verification rejected because {RECURSION_GUARD_ENV} "
            "is already set"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify hermetic pytest process exit.")
    parser.add_argument("--full", action="store_true", help="Run the full standard suite.")
    parser.add_argument("--timeout", type=float, default=None, help="Override timeout seconds.")
    args = parser.parse_args(argv)
    if os.environ.get(RECURSION_GUARD_ENV):
        result = recursion_guard_result()
        print(format_verification_result(result))
        return result.return_code
    result = run_exit_verification(full=args.full, timeout_seconds=args.timeout)
    print(format_verification_result(result))
    return 0 if result.clean_exit else result.return_code or 1


if __name__ == "__main__":
    raise SystemExit(main())
