"""Safe scratch configuration helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from variant_analysis_harness.exceptions import ConfigError


def resolve_scratch_config(cfg: dict[str, Any]) -> dict[str, Any]:
    scratch = (cfg.get("execution", {}) or {}).get("scratch", {}) or {}
    resolved = {
        "enabled": bool(scratch.get("enabled", False)),
        "root": scratch.get("root"),
        "copy_inputs": bool(scratch.get("copy_inputs", False)),
        "stage_outputs_locally": bool(scratch.get("stage_outputs_locally", True)),
        "copy_back_on_success": bool(scratch.get("copy_back_on_success", True)),
        "preserve_on_failure": bool(scratch.get("preserve_on_failure", True)),
        "allow_symlinks": bool(scratch.get("allow_symlinks", False)),
    }
    if resolved["enabled"] and not resolved["root"]:
        raise ConfigError("execution.scratch.root is required when scratch is enabled")
    return resolved


def task_scratch_dir(root: Path, cohort_id: str, sample_id: str, stage: str) -> Path:
    if ".." in {cohort_id, sample_id, stage}:
        raise ConfigError("scratch identifiers may not contain path traversal")
    return root / cohort_id / sample_id[:2] / sample_id / stage


def validate_scratch_space(path: Path, required_gb: float | None) -> dict[str, Any]:
    if required_gb is None:
        return {"status": "NOT_EVALUATED", "required_gb": None, "available_gb": None, "warnings": []}
    if required_gb < 0:
        raise ConfigError("required scratch space must be zero or greater")
    target = path if path.exists() else path.parent
    try:
        usage = shutil.disk_usage(target)
    except OSError as exc:
        return {
            "status": "FAIL",
            "required_gb": required_gb,
            "available_gb": None,
            "warnings": [],
            "error": str(exc),
            "checked_path": str(target),
        }
    available_gb = usage.free / (1024**3)
    status = "PASS" if available_gb >= required_gb else "WARN"
    warnings = [] if status == "PASS" else [f"available scratch {available_gb:.2f} GB is below requested {required_gb:.2f} GB"]
    return {"status": status, "required_gb": required_gb, "available_gb": round(available_gb, 3), "warnings": warnings, "checked_path": str(target)}
