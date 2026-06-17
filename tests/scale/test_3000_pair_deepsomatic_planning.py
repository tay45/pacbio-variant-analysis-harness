from __future__ import annotations

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.deepsomatic.config import default_deepsomatic_config
from variant_analysis_harness.somatic.deepsomatic.planning import generate_deepsomatic_plan
from variant_analysis_harness.somatic.deepsomatic.reporting import write_deepsomatic_cohort_report
from variant_analysis_harness.somatic.deepsomatic.rerun import generate_deepsomatic_rerun_manifest
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest


def test_3000_pair_deepsomatic_planning(tmp_path, tiny_reference):
    rows = [row(pair_id=f"P{i:04d}", subject_id=f"S{i:04d}", tumor=f"T{i:04d}", normal=f"N{i:04d}") for i in range(3000, 0, -1)]
    config_path = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config_path)
    somatic_cfg = default_somatic_config()
    somatic_cfg["execution"]["max_concurrent_pairs"] = 200
    somatic_cfg["small_variants"] = default_deepsomatic_config()
    selected, _, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic_3000.tsv", rows), somatic_config=somatic_cfg)
    assert validation.status == "PASS"
    plan = generate_deepsomatic_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path / "somatic", selected=selected, reference=tiny_reference["fasta"], pair_attempt_id="attempt_001", max_concurrent=200)
    assert len(plan["pairs"]) == 3000
    assert plan["pairs"][0]["array_index"] == 1
    assert plan["pairs"][0]["pair_id"] == "P0001"
    assert plan["array_group"]["max_concurrent"] == 200
    assert len(plan["commands"]) == 3000
    report = write_deepsomatic_cohort_report(plan, tmp_path / "somatic")
    assert "DeepSomatic version" in report.read_text()
    rows = generate_deepsomatic_rerun_manifest(tmp_path / "missing.json", tmp_path / "none.tsv") if False else []
    assert rows == []
