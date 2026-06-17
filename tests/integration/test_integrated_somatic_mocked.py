from __future__ import annotations

import json

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.cli import main
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.integrated.planning import generate_integrated_project, write_integrated_outputs


def _write_source_plans(somatic_dir, *, deepsomatic_status="READY", severus_status="READY"):
    somatic_dir.mkdir(parents=True, exist_ok=True)
    base_row = {
        "pair_id": "P1",
        "subject_id": "S1",
        "tumor_sample_id": "T1",
        "normal_sample_id": "N1",
        "analysis_mode": "tumor_normal",
        "reference_id": "ref_001",
        "reference_signature": "refsig",
        "manifest_row_hash": "rowhash",
    }
    (somatic_dir / "deepsomatic_plan.json").write_text(
        json.dumps({"pair_attempt_id": "deepsomatic_attempt_001", "pair_statuses": [dict(base_row, caller_preflight_status=deepsomatic_status, output_checksum="sha256:small")]}),
        encoding="utf-8",
    )
    (somatic_dir / "severus_plan.json").write_text(
        json.dumps({"pair_attempt_id": "severus_attempt_001", "pair_statuses": [dict(base_row, caller_preflight_status=severus_status, output_checksum="sha256:sv", bnd_validation_status="PASS")]}),
        encoding="utf-8",
    )


def test_integrated_planning_and_outputs_from_mocked_source_attempts(tmp_path, tiny_reference):
    cfg_path = write_config(tmp_path, tiny_reference)
    from variant_analysis_harness.common.config import load_run_config

    cfg = load_run_config(cfg_path)
    somatic_cfg = default_somatic_config()
    manifest = write_manifest(tmp_path / "somatic.tsv", [row()])
    selected, excluded, validation = load_somatic_manifest(manifest, somatic_config=somatic_cfg)
    assert validation.status == "PASS"
    somatic_dir = tmp_path / "somatic_attempt"
    _write_source_plans(somatic_dir)

    plan = generate_integrated_project(
        cfg,
        somatic_cfg,
        somatic_project_id="SOMATIC_1",
        integrated_attempt_id="integrated_attempt_001",
        selected_pairs=selected,
        excluded_pairs=excluded,
        somatic_dir=somatic_dir,
        manifest_path=manifest,
        config_path=cfg_path,
    )
    assert plan["pair_rows"][0]["integrated_status"] == "complete"

    out = tmp_path / "integrated"
    result = write_integrated_outputs(
        plan,
        out,
        small_variants=[{"source_record_key": "small1", "chromosome": "chr1", "position": 100, "filter": "PASS", "vaf": 0.25}],
        svs=[{"source_record_key": "sv1", "chromosome": "chr1", "start": 90, "end": 120, "filter": "PASS", "raw_svtype": "DEL"}],
    )
    assert result["relationships"]
    assert (out / "reports" / "integrated_somatic_report.md").exists()
    assert (out / "inventory" / "integrated_output_inventory.json").exists()


def test_integrated_cli_generates_status_report_and_rerun_outputs(tmp_path, tiny_reference):
    cfg_path = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path / "somatic.tsv", [row()])
    somatic_dir = tmp_path / "somatic_attempt"
    _write_source_plans(somatic_dir, severus_status="FAILED")

    assert main(["somatic-integrated-plan", "--config", str(cfg_path), "--manifest", str(manifest), "--somatic-project-id", "SOMATIC_1", "--somatic-dir", str(somatic_dir), "--allow-partial"]) == 0
    integrated_dir = tmp_path / "results" / "test_project" / "somatic" / "SOMATIC_1" / "integrated" / "integrated_attempt_001"
    assert (integrated_dir / "exports" / "integrated_pair_status.json").exists()
    assert main(["somatic-integrated-status", "--integrated-dir", str(integrated_dir)]) == 0
    assert main(["somatic-integrated-report", "--integrated-dir", str(integrated_dir)]) == 0
    assert main(["somatic-integrated-rerun-recommendations", "--integrated-dir", str(integrated_dir)]) == 0
    assert main(["somatic-portfolio-report", "--integrated-dir", str(integrated_dir)]) == 0
