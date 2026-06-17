"""Optional minimal test runner for restricted environments.

This is not pytest and is not used by standard development or CI testing.
Standard tests must be run with the official pytest package:

    python -m pytest -q

The runner sets the testing-only dependency fallback flag locally for its own
process because it is meant only for dependency-free smoke checks.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
import tempfile
import time
import traceback
from contextlib import ContextDecorator
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


_FIXTURES: dict[str, Callable[..., Any]] = {}


class MonkeyPatch:
    def __init__(self) -> None:
        self._env: list[tuple[str, str | None]] = []

    def setenv(self, key: str, value: str) -> None:
        self._env.append((key, os.environ.get(key)))
        os.environ[key] = value

    def undo(self) -> None:
        for key, old in reversed(self._env):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def fixture(func: Callable[..., Any]) -> Callable[..., Any]:
    _FIXTURES[func.__name__] = func
    return func


class raises(ContextDecorator):
    def __init__(self, exc_type: type[BaseException]) -> None:
        self.exc_type = exc_type

    def __enter__(self) -> "raises":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            raise AssertionError(f"Expected exception {self.exc_type.__name__}")
        if not issubclass(exc_type, self.exc_type):
            return False
        return True


def main() -> int:
    os.environ["VARIANT_ANALYSIS_HARNESS_TEST_ALLOW_DEP_FALLBACK"] = "1"
    sys.modules.setdefault("pytest", sys.modules[__name__])
    root = Path.cwd()
    conftest = root / "tests" / "conftest.py"
    if conftest.exists():
        _load_module(conftest)
    failures = 0
    total = 0
    timings: list[tuple[float, str]] = []
    suite_start = time.monotonic()
    for path in sorted((root / "tests").rglob("test_*.py")):
        module = _load_module(path)
        for name, func in sorted(vars(module).items()):
            if name.startswith("test_") and callable(func):
                total += 1
                start = time.monotonic()
                try:
                    _run_test(func)
                    elapsed = time.monotonic() - start
                    timings.append((elapsed, f"{path.relative_to(root)}::{name}"))
                    print(f"{path.relative_to(root)}::{name} PASSED ({elapsed:.3f}s)")
                except Exception:
                    elapsed = time.monotonic() - start
                    timings.append((elapsed, f"{path.relative_to(root)}::{name}"))
                    failures += 1
                    print(f"{path.relative_to(root)}::{name} FAILED ({elapsed:.3f}s)")
                    traceback.print_exc()
    total_elapsed = time.monotonic() - suite_start
    print("slowest tests:")
    for elapsed, test_name in sorted(timings, reverse=True)[:10]:
        print(f"{elapsed:.3f}s {test_name}")
    print(f"total duration: {total_elapsed:.3f}s")
    print(f"{total - failures} passed, {failures} failed")
    return 1 if failures else 0


def _load_module(path: Path) -> ModuleType:
    name = "local_" + "_".join(path.with_suffix("").parts[-4:])
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run_test(func: Callable[..., Any]) -> None:
    temp_dir = tempfile.TemporaryDirectory()
    tmp_path = Path(temp_dir.name)
    monkeypatch = MonkeyPatch()
    cache: dict[str, Any] = {"tmp_path": tmp_path, "monkeypatch": monkeypatch}
    try:
        kwargs = {name: _resolve_fixture(name, cache) for name in inspect.signature(func).parameters}
        func(**kwargs)
    finally:
        monkeypatch.undo()
        temp_dir.cleanup()


def _resolve_fixture(name: str, cache: dict[str, Any]) -> Any:
    if name in cache:
        return cache[name]
    if name not in _FIXTURES:
        raise RuntimeError(f"Unknown fixture: {name}")
    func = _FIXTURES[name]
    kwargs = {param: _resolve_fixture(param, cache) for param in inspect.signature(func).parameters}
    value = func(**kwargs)
    cache[name] = value
    return value


if __name__ == "__main__":
    raise SystemExit(main())
