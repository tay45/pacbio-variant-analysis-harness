"""Small data models shared across the harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_ANALYSES = {"snv", "sv", "combined"}
VALID_STAGE_STATUSES = {
    "pending",
    "running",
    "success",
    "warning",
    "failed",
    "skipped",
    "blocked",
    "interrupted",
}
QC_STATES = {"PASS", "WARN", "FAIL", "NOT_EVALUATED"}


@dataclass(frozen=True)
class Sample:
    sample_id: str
    platform: str
    input_type: str
    input_path: Path
    additional_inputs: tuple[Path, ...] = ()
    aligned: bool = False
    reference_id: str = ""
    read_group_sample: str = ""
    output_prefix: str = ""


@dataclass
class ToolConfig:
    name: str
    backend: str = "native"
    executable: str | None = None
    version: str | None = None
    container: Path | None = None
    conda_environment: str | None = None
    model_type: str | None = None
    num_shards: int | None = None
    ccs_mode: bool = False
    extra_args: list[str] = field(default_factory=list)


@dataclass
class CommandSpec:
    stage: str
    tool_name: str
    argv: list[str]
    inputs: list[Path] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)
    cwd: Path | None = None
    timeout_seconds: int | None = None


@dataclass
class StageResult:
    stage: str
    status: str
    exit_code: int | None
    stdout_path: Path | None
    stderr_path: Path | None
    started_at: str
    ended_at: str
    runtime_seconds: float
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
