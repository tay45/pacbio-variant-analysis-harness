"""Stage status JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.models import StageResult


def write_stage_status(result: StageResult, path: Path, extra: dict[str, Any] | None = None) -> None:
    data = {
        "stage": result.stage,
        "status": result.status,
        "exit_code": result.exit_code,
        "stdout_path": str(result.stdout_path) if result.stdout_path else None,
        "stderr_path": str(result.stderr_path) if result.stderr_path else None,
        "start_time": result.started_at,
        "end_time": result.ended_at,
        "runtime_seconds": result.runtime_seconds,
        "validation_result": extra.get("validation_result") if extra else None,
        "warnings": result.warnings,
        "failure_category": result.error,
        "downstream_blocking_status": "blocked" if result.status == "failed" else None,
    }
    if extra:
        data.update(extra)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_stage_status(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
