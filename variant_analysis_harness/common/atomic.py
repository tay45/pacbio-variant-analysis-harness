"""Atomic output publication helpers."""

from __future__ import annotations

import os
from pathlib import Path

from variant_analysis_harness.exceptions import ValidationError


def incomplete_path(final_path: Path) -> Path:
    return final_path.with_name(final_path.name + ".incomplete")


def publish_atomically(temp_path: Path, final_path: Path, *, overwrite: bool = False) -> None:
    if not temp_path.exists() or temp_path.stat().st_size == 0:
        raise ValidationError(f"Cannot publish missing or empty temporary output: {temp_path}")
    if final_path.exists() and not overwrite:
        raise ValidationError(f"Refusing to overwrite existing output: {final_path}")
    if temp_path.resolve().parent != final_path.resolve().parent:
        raise ValidationError("Atomic publish requires temp and final outputs on the same filesystem directory")
    os.replace(temp_path, final_path)
