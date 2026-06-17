from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import write_config, write_manifest
from variant_analysis_harness.common.paths import ensure_cleanup_target_is_safe
from variant_analysis_harness.exceptions import CleanupSafetyError
from variant_analysis_harness.execution.slurm import generate_sbatch_script
from variant_analysis_harness.models import CommandSpec


def test_cleanup_cannot_escape_attempt(tmp_path):
    attempt = tmp_path / "results" / "proj" / "sample" / "attempt"
    temp = attempt / "temp"
    temp.mkdir(parents=True)
    ensure_cleanup_target_is_safe(temp, attempt)
    with pytest.raises(CleanupSafetyError):
        ensure_cleanup_target_is_safe(tmp_path, attempt)


def test_slurm_script_generation_neutral(tmp_path):
    spec = CommandSpec("stage", "tool", ["echo", "hello"], cwd=tmp_path)
    script = generate_sbatch_script(
        spec,
        {"slurm": {"time": "01:00:00", "cpus_per_task": 2, "memory_gb": 4, "extra_sbatch_options": [], "environment_setup": []}},
        tmp_path / "job.sbatch",
        tmp_path / "job.out",
        tmp_path / "job.err",
    )
    text = script.read_text()
    assert "#SBATCH --time=01:00:00" in text
    assert "echo hello" in text


def test_no_prohibited_terms_outside_legacy():
    root = Path(__file__).resolve().parents[2]
    prohibited = [
        "Apo" + "llo",
        "City" + " of " + "Hope",
        "/" + "net" + "/" + "isi-dcnl",
        "/" + "opt" + "/" + "singularity-images",
    ]
    allowed_parts = {"legacy", "work", ".pytest_cache"}
    offenders = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in allowed_parts for part in path.parts) or path.name == "PORTABILITY_SCAN.txt":
            continue
        if path.suffix in {".pyc", ".simg", ".sif"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in prohibited:
            if term in text:
                offenders.append((str(path.relative_to(root)), term))
    assert offenders == []
