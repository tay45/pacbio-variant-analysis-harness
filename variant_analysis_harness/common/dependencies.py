"""Runtime dependency loading with actionable errors."""

from __future__ import annotations

import importlib
from typing import Any

from variant_analysis_harness.exceptions import ConfigError


def load_required_dependency(module_name: str, package_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        raise ConfigError(
            f"{package_name} is required. Install the project dependencies before running this command."
        ) from exc
