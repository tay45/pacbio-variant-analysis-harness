"""Path helpers and cleanup safety checks."""

from __future__ import annotations

import os
from pathlib import Path

from variant_analysis_harness.exceptions import CleanupSafetyError


def resolve_path(value: str | Path | None, base_dir: Path) -> Path | None:
    if value in (None, ""):
        return None
    expanded = os.path.expandvars(str(value))
    path = Path(expanded).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def safe_name(value: str, label: str) -> str:
    if not value:
        raise ValueError(f"{label} is required")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(ch not in allowed for ch in value):
        raise ValueError(f"{label} contains unsupported characters: {value!r}")
    if value in {".", ".."} or value.startswith("-"):
        raise ValueError(f"{label} is unsafe: {value!r}")
    return value


def ensure_cleanup_target_is_safe(path: Path, attempt_dir: Path) -> None:
    target = path.resolve()
    attempt = attempt_dir.resolve()
    if str(target) in {"", "/", str(Path.home().resolve())}:
        raise CleanupSafetyError(f"Refusing unsafe cleanup path: {target}")
    if target == attempt.parent or target == attempt.parent.parent:
        raise CleanupSafetyError(f"Refusing parent cleanup path: {target}")
    try:
        target.relative_to(attempt)
    except ValueError as exc:
        raise CleanupSafetyError(f"Cleanup path is outside attempt directory: {target}") from exc
