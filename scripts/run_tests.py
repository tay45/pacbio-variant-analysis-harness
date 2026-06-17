#!/usr/bin/env python3
"""Run pytest with third-party plugin autoload disabled."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


HERMITIC_ENV = "PYTEST_DISABLE_PLUGIN_AUTOLOAD"
EXPLICIT_PLUGIN_ENV = "PYTEST_PLUGINS"
HERMITIC_MESSAGE = "Hermetic pytest: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"


def build_hermetic_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    env[HERMITIC_ENV] = "1"
    env.pop(EXPLICIT_PLUGIN_ENV, None)
    return env


def apply_hermetic_environment(env: Mapping[str, str]) -> dict[str, str | None]:
    previous = {HERMITIC_ENV: os.environ.get(HERMITIC_ENV), EXPLICIT_PLUGIN_ENV: os.environ.get(EXPLICIT_PLUGIN_ENV)}
    os.environ[HERMITIC_ENV] = env[HERMITIC_ENV]
    os.environ.pop(EXPLICIT_PLUGIN_ENV, None)
    return previous


def restore_environment(previous: Mapping[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def resolve_official_pytest(pytest_module: Any | None = None) -> Any:
    if pytest_module is None:
        try:
            import pytest as pytest_module
        except ModuleNotFoundError:
            print("ERROR: official pytest is required. Install test dependencies first.", file=sys.stderr)
            return None
    repo = Path(__file__).resolve().parents[1]
    pytest_file = getattr(pytest_module, "__file__", "")
    pytest_path = Path(pytest_file).resolve()
    if repo in pytest_path.parents or pytest_path == repo / "pytest.py":
        print(f"ERROR: pytest resolved inside repository: {pytest_path}", file=sys.stderr)
        return None
    return pytest_module


def run_pytest(args: list[str], pytest_module: ModuleType | Any | None = None) -> int:
    pytest_impl = resolve_official_pytest(pytest_module)
    if pytest_impl is None:
        return 2
    print(HERMITIC_MESSAGE, file=sys.stderr)
    return int(pytest_impl.main(args))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    env = build_hermetic_environment()
    previous = apply_hermetic_environment(env)
    try:
        return run_pytest(args)
    finally:
        restore_environment(previous)


if __name__ == "__main__":
    raise SystemExit(main())
