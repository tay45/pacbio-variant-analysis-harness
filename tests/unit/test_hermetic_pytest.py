from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_tests as run_tests
import scripts.verify_pytest_exit as verifier


def fake_pytest(tmp_path: Path, exit_code: int = 0):
    calls: list[list[str]] = []

    def main(args):
        calls.append(list(args))
        return exit_code

    module = SimpleNamespace(__file__=str(tmp_path / "site-packages" / "pytest" / "__init__.py"), main=main)
    return module, calls


def test_launcher_builds_hermetic_environment_without_mutating_parent(monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "parent")
    monkeypatch.setenv("PYTEST_PLUGINS", "external_plugin")
    env = run_tests.build_hermetic_environment({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0", "PYTEST_PLUGINS": "plugin", "KEEP": "yes"})
    assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert "PYTEST_PLUGINS" not in env
    assert env["KEEP"] == "yes"
    assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "parent"
    assert os.environ["PYTEST_PLUGINS"] == "external_plugin"


def test_launcher_applies_and_restores_parent_environment(monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "parent")
    monkeypatch.setenv("PYTEST_PLUGINS", "external_plugin")
    previous = run_tests.apply_hermetic_environment({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"})
    assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert "PYTEST_PLUGINS" not in os.environ
    run_tests.restore_environment(previous)
    assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "parent"
    assert os.environ["PYTEST_PLUGINS"] == "external_plugin"


def test_launcher_forwards_arguments_and_exit_code(tmp_path, capsys):
    module, calls = fake_pytest(tmp_path, exit_code=5)
    rc = run_tests.run_pytest(["-q", "tests/unit"], pytest_module=module)
    assert rc == 5
    assert calls == [["-q", "tests/unit"]]
    assert "Hermetic pytest" in capsys.readouterr().err


def test_launcher_rejects_repository_local_pytest(capsys):
    module = SimpleNamespace(__file__=str(Path.cwd() / "pytest.py"), main=lambda args: 0)
    assert run_tests.run_pytest(["-q"], pytest_module=module) == 2
    assert "pytest resolved inside repository" in capsys.readouterr().err


def test_verifier_builds_default_smoke_command():
    command = verifier.build_pytest_command(full=False)
    assert command[:3] == [sys.executable, str(Path.cwd() / "scripts" / "run_tests.py"), "-q"]
    assert command[-1] == "tests/smoke/test_exit_smoke_subset.py"
    assert "test_hermetic_pytest.py" not in command
    assert "verify_pytest_exit.py" not in command


def test_verifier_builds_full_suite_command():
    command = verifier.build_pytest_command(full=True)
    assert command == [sys.executable, str(Path.cwd() / "scripts" / "run_tests.py"), "-q"]


def test_verifier_builds_hermetic_environment_without_mutating_parent(monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "parent")
    monkeypatch.setenv("PYTEST_PLUGINS", "external_plugin")
    env = verifier.build_hermetic_environment({"PYTEST_PLUGINS": "plugin", "KEEP": "yes"})
    assert env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert env[verifier.RECURSION_GUARD_ENV] == "1"
    assert "PYTEST_PLUGINS" not in env
    assert env["KEEP"] == "yes"
    assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "parent"
    assert os.environ["PYTEST_PLUGINS"] == "external_plugin"


def test_verifier_reports_success_for_zero_return_code():
    result = verifier.evaluate_completed_process(
        command=["python", "scripts/run_tests.py", "-q"],
        completed=subprocess.CompletedProcess(["cmd"], 0, stdout="...\\n3 passed in 0.10s\\n", stderr="stderr\\n"),
        elapsed_seconds=0.2,
        timeout_seconds=30.0,
    )
    assert result.clean_exit is True
    assert result.summary_printed is True
    assert result.process_exited is True
    assert result.return_code == 0
    formatted = verifier.format_verification_result(result)
    assert "--- stdout ---" in formatted
    assert "--- stderr ---" in formatted
    assert "3 passed in 0.10s" in formatted


def test_verifier_reports_failure_for_nonzero_return_code():
    result = verifier.evaluate_completed_process(
        command=["python", "scripts/run_tests.py", "-q"],
        completed=subprocess.CompletedProcess(["cmd"], 1, stdout="1 failed in 0.10s\\n", stderr="boom\\n"),
        elapsed_seconds=0.2,
        timeout_seconds=30.0,
    )
    assert result.clean_exit is False
    assert result.summary_printed is True
    assert result.return_code == 1


def test_verifier_reports_timeout_cleanly():
    exc = subprocess.TimeoutExpired(["cmd"], timeout=1.0, output="partial stdout", stderr="partial stderr")
    result = verifier.evaluate_timeout(command=["cmd"], exc=exc, timeout_seconds=1.0)
    assert result.timeout is True
    assert result.process_exited is False
    assert result.clean_exit is False
    assert result.return_code == 124
    assert "timed out" in result.diagnostic
    assert "partial stdout" in verifier.format_verification_result(result)
    assert "partial stderr" in verifier.format_verification_result(result)


def test_verifier_reports_runner_os_error():
    result = verifier.evaluate_runner_error(
        command=["cmd"],
        exc=FileNotFoundError("missing"),
        elapsed_seconds=0.01,
        timeout_seconds=30.0,
    )
    assert result.return_code == 127
    assert result.clean_exit is False
    assert "failed to start" in result.diagnostic


def test_verifier_run_uses_injected_runner_without_shell(monkeypatch):
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="1 passed in 0.01s\\n", stderr="err\\n")

    monkeypatch.delenv(verifier.RECURSION_GUARD_ENV, raising=False)
    result = verifier.run_exit_verification(full=False, timeout_seconds=7.0, runner=runner, base_env={"KEEP": "yes"})
    assert result.clean_exit is True
    command, kwargs = calls[0]
    assert command[-1] == "tests/smoke/test_exit_smoke_subset.py"
    assert kwargs["timeout"] == 7.0
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert "shell" not in kwargs
    assert kwargs["env"]["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert kwargs["env"][verifier.RECURSION_GUARD_ENV] == "1"
    assert kwargs["env"]["KEEP"] == "yes"
    assert verifier.RECURSION_GUARD_ENV not in os.environ


def test_verifier_run_selects_full_suite_with_injected_runner():
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="2 passed in 0.01s\\n", stderr="")

    result = verifier.run_exit_verification(full=True, timeout_seconds=8.0, runner=runner, base_env={})
    assert result.clean_exit is True
    assert calls == [[sys.executable, str(Path.cwd() / "scripts" / "run_tests.py"), "-q"]]


def test_verifier_run_handles_timeout_from_injected_runner():
    def runner(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"], output="partial", stderr="late")

    result = verifier.run_exit_verification(full=False, timeout_seconds=0.5, runner=runner, base_env={})
    assert result.timeout is True
    assert result.return_code == 124
    assert result.stdout == "partial"
    assert result.stderr == "late"


def test_verifier_run_handles_executable_not_found_from_injected_runner():
    def runner(command, **kwargs):
        raise FileNotFoundError("missing executable")

    result = verifier.run_exit_verification(full=False, timeout_seconds=0.5, runner=runner, base_env={})
    assert result.return_code == 127
    assert "missing executable" in result.diagnostic


def test_verifier_main_rejects_recursive_invocation(monkeypatch, capsys):
    monkeypatch.setenv(verifier.RECURSION_GUARD_ENV, "1")
    rc = verifier.main([])
    captured = capsys.readouterr()
    assert rc == 2
    assert "recursive pytest exit verification rejected" in captured.out
    assert verifier.RECURSION_GUARD_ENV in captured.out


def test_verifier_recursion_guard_result_is_clear():
    result = verifier.recursion_guard_result()
    assert result.return_code != 0
    assert result.clean_exit is False
    assert verifier.RECURSION_GUARD_ENV in result.diagnostic


def test_timeout_selection_defaults():
    assert verifier.select_timeout(full=False, timeout_seconds=None) == verifier.DEFAULT_TIMEOUT_SECONDS
    assert verifier.select_timeout(full=True, timeout_seconds=None) == verifier.FULL_TIMEOUT_SECONDS
    assert verifier.select_timeout(full=True, timeout_seconds=3.5) == 3.5


def test_hermetic_unit_tests_do_not_reintroduce_recursive_pytest_calls():
    source = Path(__file__).read_text(encoding="utf-8")
    prohibited = [
        "subprocess." + "run(",
        "scripts/" + "verify_pytest_exit.py",
        "python -m " + "pytest",
        "scripts/" + "run_tests.py\", \"-q\", \"tests/",
    ]
    for pattern in prohibited:
        assert pattern not in source
