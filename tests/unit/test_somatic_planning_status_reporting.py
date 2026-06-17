from __future__ import annotations

import json

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.cli import main
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.planning import (
    aggregate_status_counts,
    generate_somatic_plan,
    somatic_attempt_dir,
    write_somatic_plan,
)
from variant_analysis_harness.somatic.reporting import write_somatic_report
from variant_analysis_harness.somatic.rerun import generate_somatic_rerun_manifest


def build_plan(tmp_path, tiny_reference, rows, cfg_override=None):
    config_path = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config_path)
    somatic_config = default_somatic_config()
    if cfg_override:
        cfg_override(somatic_config)
    manifest = write_manifest(tmp_path / "somatic.tsv", rows)
    selected, excluded, validation = load_somatic_manifest(manifest, somatic_config=somatic_config)
    plan = generate_somatic_plan(
        cfg,
        somatic_config,
        config_path=config_path,
        manifest_path=manifest,
        selected=selected,
        excluded=excluded,
        validation=validation,
        somatic_project_id="SOMATIC_1",
        attempt_id="somatic_attempt_001",
        output_root=None,
        max_concurrent_pairs=2,
    )
    return cfg, somatic_config, manifest, selected, excluded, validation, plan


def test_somatic_plan_array_index_and_no_caller_commands(tmp_path, tiny_reference):
    _, _, _, _, _, _, plan = build_plan(tmp_path, tiny_reference, [row(pair_id="P2", tumor="T2", normal="N2"), row(pair_id="P1", tumor="T1", normal="N1")])
    assert [p["pair_id"] for p in plan["pairs"]] == ["P1", "P2"]
    assert [p["array_index"] for p in plan["pairs"]] == [1, 2]
    assert plan["caller_stages_deferred"] is True
    assert plan["no_somatic_callers_executed"] is True
    text = json.dumps(plan)
    assert "DeepSomatic" not in text
    assert "Severus" not in text


def test_failed_pair_excluded_from_array_index(tmp_path, tiny_reference):
    _, _, _, _, _, _, plan = build_plan(tmp_path, tiny_reference, [row(pair_id="P1", tumor_read_group_sample="WRONG")])
    assert plan["pairs"] == []
    assert plan["blocked_pairs"][0]["failure_category"] == "tumor_header_mismatch"


def test_write_plan_status_report_and_rerun(tmp_path, tiny_reference):
    cfg, _, _, _, _, _, plan = build_plan(tmp_path, tiny_reference, [row(pair_id="P1", tumor_read_group_sample="WRONG")])
    attempt_dir = somatic_attempt_dir(cfg, "SOMATIC_1", "somatic_attempt_001")
    write_somatic_plan(plan, attempt_dir)
    report = write_somatic_report(plan, attempt_dir)
    assert (attempt_dir / "somatic_plan.json").exists()
    assert (attempt_dir / "somatic_array_index.tsv").exists()
    assert "No somatic variants were called" in report.read_text()
    counts = aggregate_status_counts(plan["pair_statuses"])
    assert counts["failed"] == 1
    rerun = generate_somatic_rerun_manifest(attempt_dir, tmp_path / "failed_pairs.tsv", status="failed", failure_category="tumor_header_mismatch")
    assert [r["pair_id"] for r in rerun] == ["P1"]
    assert (tmp_path / "failed_pairs.tsv.criteria.json").exists()


def test_somatic_cli_plan_status_rerun_report(tmp_path, tiny_reference):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(pair_id="P1")])
    rc = main(["somatic-plan", "--config", str(config), "--manifest", str(manifest), "--somatic-project-id", "SOMATIC_1"])
    assert rc == 0
    attempt_dir = tmp_path / "results" / "test_project" / "somatic" / "SOMATIC_1" / "somatic_attempt_001"
    assert (attempt_dir / "somatic_plan.json").exists()
    assert main(["somatic-status", "--somatic-dir", str(attempt_dir)]) == 0
    assert main(["somatic-rerun-manifest", "--somatic-dir", str(attempt_dir), "--status", "failed", "--output", str(tmp_path / "rerun.tsv")]) == 0
    assert main(["somatic-report", "--somatic-dir", str(attempt_dir)]) == 0


def test_somatic_validate_returns_nonzero_on_validation_error(tmp_path, tiny_reference):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(normal="")])
    rc = main(["somatic-validate", "--config", str(config), "--manifest", str(manifest), "--somatic-project-id", "SOMATIC_1"])
    assert rc == 1
