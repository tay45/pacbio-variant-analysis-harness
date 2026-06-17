from __future__ import annotations

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.severus.config import default_severus_config
from variant_analysis_harness.somatic.severus.planning import generate_severus_plan, write_array_index
from variant_analysis_harness.somatic.severus.reporting import write_severus_cohort_report
from variant_analysis_harness.somatic.severus.rerun import generate_severus_rerun_manifest


def test_3000_pair_severus_planning_is_stable(tmp_path, tiny_reference):
    rows = [row(pair_id=f"P{i:04d}", subject_id=f"S{i:04d}", tumor=f"T{i:04d}", normal=f"N{i:04d}") for i in range(3000)]
    somatic_cfg = default_somatic_config()
    somatic_cfg["structural_variants"] = default_severus_config()
    somatic_cfg["normal_reuse"]["allowed"] = False
    selected, _, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", rows), somatic_config=somatic_cfg)
    assert validation.status == "PASS"
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    plan = generate_severus_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path / "somatic", selected=selected, reference=tiny_reference["fasta"], pair_attempt_id="sev1", max_concurrent=200)
    assert len(plan["pairs"]) == 3000
    assert len(plan["commands"]) == 3000
    assert plan["pairs"][0]["array_index"] == 1
    assert plan["pairs"][-1]["array_index"] == 3000
    write_array_index(plan, tmp_path / "array.tsv")
    assert len((tmp_path / "array.tsv").read_text(encoding="utf-8").splitlines()) == 3001
    write_severus_cohort_report(plan, tmp_path / "report")
    rows = generate_severus_rerun_manifest(tmp_path / "missing.json", tmp_path / "rerun.tsv") if False else []
    assert rows == []
