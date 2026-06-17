"""Stable signatures for restart safety."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def file_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    return {"path": str(path), "exists": True, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def object_signature(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stage_signature(config: dict[str, Any], sample: Any, inputs: list[Path], tool: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "config_signature": object_signature(config),
        "sample_signature": object_signature(sample.__dict__ if hasattr(sample, "__dict__") else sample),
        "input_signatures": [file_signature(path) for path in inputs],
        "tool_signature": object_signature(tool or {}),
    }
