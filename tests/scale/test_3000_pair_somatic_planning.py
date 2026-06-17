from __future__ import annotations

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.planning import aggregate_status_counts, generate_somatic_plan, somatic_attempt_dir, write_somatic_plan
from variant_analysis_harness.somatic.reporting import write_somatic_report
from variant_analysis_harness.somatic.rerun import generate_somatic_rerun_manifest


def test_3000_pair_somatic_planning(tmp_path, tiny_reference):
    rows = [
        row(
            pair_id=f"P{i:04d}",
            subject_id=f"S{i:04d}",
            tumor=f"T{i:04d}",
            normal=f"N{i:04d}",
            tumor_coverage="45",
            normal_coverage="35",
        )
        for i in range(3000, 0, -1)
    ]
    config_path = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config_path)
    somatic_config = default_somatic_config()
    somatic_config["execution"]["max_concurrent_pairs"] = 200
    manifest = write_manifest(tmp_path / "somatic_3000.tsv", rows)
    selected, excluded, validation = load_somatic_manifest(manifest, somatic_config=somatic_config)
    assert validation.status == "PASS"
    assert len(selected) == 3000
    assert not excluded
    assert selected[0].pair_id == "P0001"
    plan = generate_somatic_plan(
        cfg,
        somatic_config,
        config_path=config_path,
        manifest_path=manifest,
        selected=selected,
        excluded=excluded,
        validation=validation,
        somatic_project_id="SOMATIC_SCALE",
        attempt_id="somatic_attempt_001",
        output_root=None,
        max_concurrent_pairs=200,
    )
    assert plan["selected_pair_count"] == 3000
    assert plan["pairs"][0]["array_index"] == 1
    assert plan["pairs"][0]["pair_id"] == "P0001"
    assert plan["pairs"][-1]["pair_id"] == "P3000"
    assert aggregate_status_counts(plan["pair_statuses"]) == {"ready": 3000}
    attempt_dir = somatic_attempt_dir(cfg, "SOMATIC_SCALE", "somatic_attempt_001")
    write_somatic_plan(plan, attempt_dir)
    report = write_somatic_report(plan, attempt_dir)
    rerun = generate_somatic_rerun_manifest(attempt_dir, tmp_path / "failed.tsv", status="failed")
    assert rerun == []
    assert "No somatic variants were called" in report.read_text(encoding="utf-8")
