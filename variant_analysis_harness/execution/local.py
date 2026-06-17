"""Local execution orchestration."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.common.command import run_command
from variant_analysis_harness.common.stage_status import write_stage_status
from variant_analysis_harness.models import CommandSpec, StageResult


def execute_stage(spec: CommandSpec, stage_dir: Path, dry_run: bool = False) -> StageResult:
    stage_dir.mkdir(parents=True, exist_ok=True)
    result = run_command(spec, stage_dir, dry_run=dry_run)
    write_stage_status(result, stage_dir / "stage.status.json")
    return result
