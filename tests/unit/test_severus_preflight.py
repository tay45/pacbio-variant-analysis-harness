from __future__ import annotations

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.severus.config import default_severus_config
from variant_analysis_harness.somatic.severus.planning import generate_severus_plan, write_severus_plan


def build_selected(tmp_path, rows, cfg):
    selected, _, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", rows), somatic_config=cfg)
    assert validation.status in {"PASS", "WARN"}
    return selected


def test_ready_warning_blocked_and_written_plan(tmp_path, tiny_reference):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    somatic_cfg = default_somatic_config()
    somatic_cfg["identity_policy"] = "warn"
    somatic_cfg["structural_variants"] = default_severus_config()
    selected = build_selected(tmp_path, [row(), row(pair_id="P2", tumor="T2", normal="N2", tumor_read_group_sample="WRONG")], somatic_cfg)
    plan = generate_severus_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path / "somatic", selected=selected, reference=tiny_reference["fasta"], pair_attempt_id="sev1", max_concurrent=2, include_warning_pairs=True)
    assert len(plan["pairs"]) == 2
    assert any(p["caller_preflight_status"] == "READY_WITH_WARNINGS" for p in plan["pairs"])
    write_severus_plan(plan, tmp_path / "out")
    assert (tmp_path / "out" / "severus_array_index.tsv").read_text().startswith("array_index\tpair_id")


def test_config_error_and_tumor_only_authorized_pairs(tmp_path, tiny_reference):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    somatic_cfg = default_somatic_config()
    bad = default_severus_config()
    bad["severus"]["requested_version"] = "9.9.9"
    somatic_cfg["structural_variants"] = bad
    selected = build_selected(tmp_path, [row()], somatic_cfg)
    plan = generate_severus_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path / "somatic", selected=selected, reference=tiny_reference["fasta"], pair_attempt_id="sev1", max_concurrent=1)
    assert plan["blocked_pairs"][0]["failure_category"] == "severus_config_error"
    tumor_only_cfg = default_somatic_config()
    tumor_only_cfg["tumor_only"]["allowed"] = True
    tumor_only_cfg["structural_variants"] = default_severus_config()
    selected, _, _ = load_somatic_manifest(write_manifest(tmp_path / "to.tsv", [row(mode="tumor_only", normal="", tumor_only_acknowledgment="ack")]), somatic_config=tumor_only_cfg)
    plan = generate_severus_plan(cfg, tumor_only_cfg, project_attempt_dir=tmp_path / "somatic", selected=selected, reference=tiny_reference["fasta"], pair_attempt_id="sev1", max_concurrent=1)
    assert not plan["blocked_pairs"]
    assert plan["pairs"][0]["analysis_mode"] == "tumor_only"
