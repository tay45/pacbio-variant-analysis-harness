from __future__ import annotations

from pathlib import Path

from tests.conftest import write_config, write_manifest
from variant_analysis_harness.cli import main


def test_combined_mock_run(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    code = main(["run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "combined"])
    assert code == 0
    attempt = tmp_path / "results" / "test_project" / "SAMPLE_001" / "attempt_001"
    assert (attempt / "snv" / "SAMPLE_001.snv.vcf").exists()
    assert (attempt / "sv" / "SAMPLE_001.sv.vcf").exists()
    assert (attempt / "reports" / "sample_report.md").exists()


def test_dry_run_modes(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    for analysis in ("snv", "sv", "combined"):
        code = main(["dry-run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", analysis, "--attempt-id", f"attempt_{analysis}"])
        assert code == 0
        assert (tmp_path / "results" / "test_project" / "SAMPLE_001" / f"attempt_{analysis}" / "command_plan.json").exists()


def test_mock_failure_blocks_downstream(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    failing = tmp_path / "bin" / "deepvariant"
    failing.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(7)\n")
    failing.chmod(0o755)
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    code = main(["run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"])
    assert code == 1
    attempt = tmp_path / "results" / "test_project" / "SAMPLE_001" / "attempt_001"
    assert (attempt / "status" / "germline_snv" / "stage.status.json").exists()


def test_resume_skips_successful_stage(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    assert main(["run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "sv"]) == 0
    assert main(["resume", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "sv"]) == 0
