from __future__ import annotations

import subprocess

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.cli import main
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.severus.config import default_severus_config
from variant_analysis_harness.somatic.severus.execution import can_resume_attempt, run_severus_command, supersede_attempt, write_execution_result
from variant_analysis_harness.somatic.severus.planning import generate_severus_plan, write_severus_plan
from variant_analysis_harness.somatic.severus.rerun import generate_severus_rerun_manifest
from variant_analysis_harness.somatic.severus.slurm import write_severus_slurm_array


def fake_runner(return_code=0, stdout="ok", stderr=""):
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, return_code, stdout=stdout, stderr=stderr)
    return runner


def build_plan(tmp_path, tiny_reference, row_data):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    somatic_cfg = default_somatic_config()
    somatic_cfg["structural_variants"] = default_severus_config()
    selected, _, _ = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row_data]), somatic_config=somatic_cfg)
    return generate_severus_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path / "somatic", selected=selected, reference=tiny_reference["fasta"], pair_attempt_id="attempt_001", max_concurrent=2)


def test_mocked_execution_success_failure_timeout_and_resume(tmp_path, tiny_reference):
    plan = build_plan(tmp_path, tiny_reference, row())
    argv = plan["commands"][0]["argv"]
    result = run_severus_command(argv, cwd=tmp_path, runner=fake_runner())
    assert result.status == "caller_success"
    failed = run_severus_command(argv, cwd=tmp_path, runner=fake_runner(2, stderr="boom"))
    assert failed.failure_category == "severus_execution_failed"

    def timeout_runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, timeout=1, output="partial", stderr="late")

    timed = run_severus_command(argv, cwd=tmp_path, timeout_seconds=1, runner=timeout_runner)
    assert timed.failure_category == "severus_timeout"
    status_path = tmp_path / "status.json"
    write_execution_result(result, status_path)
    assert not can_resume_attempt(status_path, expected_command_signature=result.command_signature)
    status_path.write_text('{"status":"complete","command_signature":"' + result.command_signature + '","output_validation_status":"PASS","bnd_validation_status":"PASS"}\n', encoding="utf-8")
    assert can_resume_attempt(status_path, expected_command_signature=result.command_signature)
    supersede_attempt(status_path, "attempt_002")
    assert "superseded" in status_path.read_text()


def test_cli_plan_slurm_rerun_report(tmp_path, tiny_reference):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(tumor_read_group_sample="WRONG")])
    assert main(["somatic-sv-plan", "--config", str(config), "--manifest", str(manifest), "--somatic-project-id", "SOMATIC_1", "--include-warning-pairs"]) == 0
    somatic_dir = tmp_path / "results" / "test_project" / "somatic" / "SOMATIC_1" / "somatic_attempt_001"
    assert (somatic_dir / "severus_plan.json").exists()
    assert main(["somatic-sv-status", "--somatic-dir", str(somatic_dir)]) == 0
    assert main(["somatic-sv-report", "--somatic-dir", str(somatic_dir)]) == 0
    assert main(["somatic-sv-rerun-manifest", "--somatic-dir", str(somatic_dir), "--output", str(tmp_path / "rerun.tsv")]) == 0
    assert main(["somatic-sv-slurm", "--config", str(config), "--manifest", str(manifest), "--somatic-project-id", "SOMATIC_1", "--include-warning-pairs"]) == 0


def test_slurm_array_script_and_rerun_manifest(tmp_path, tiny_reference):
    plan = build_plan(tmp_path, tiny_reference, row())
    write_severus_plan(plan, tmp_path)
    script = write_severus_slurm_array(plan, tmp_path / "array.sh", max_concurrent=4)
    assert "#SBATCH --array=1-1%4" in script.read_text()
    rows = generate_severus_rerun_manifest(tmp_path / "severus_plan.json", tmp_path / "blocked.tsv", status="BLOCKED")
    assert rows == []
