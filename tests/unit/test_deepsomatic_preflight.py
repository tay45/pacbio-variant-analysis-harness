from __future__ import annotations

from tests.conftest import write_config
from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.somatic.deepsomatic.config import default_deepsomatic_config
from variant_analysis_harness.somatic.deepsomatic.planning import generate_deepsomatic_plan
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest


def selected_pair(tmp_path, row_data, cfg=None):
    selected, _, _ = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row_data]), somatic_config=cfg or default_somatic_config())
    return selected


def test_ready_blocked_and_model_mismatch(tmp_path, tiny_reference):
    config_path = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config_path)
    somatic_cfg = default_somatic_config()
    somatic_cfg["small_variants"] = default_deepsomatic_config()
    plan = generate_deepsomatic_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path, selected=selected_pair(tmp_path, row()), reference=tiny_reference["fasta"], pair_attempt_id="a1", max_concurrent=1)
    assert len(plan["pairs"]) == 1
    somatic_cfg["small_variants"]["deepsomatic"]["model_type"]["tumor_normal"] = "PACBIO_TUMOR_ONLY"
    plan = generate_deepsomatic_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path, selected=selected_pair(tmp_path, row()), reference=tiny_reference["fasta"], pair_attempt_id="a1", max_concurrent=1)
    assert plan["blocked_pairs"][0]["failure_category"] == "deepsomatic_config_error"


def test_warning_pair_policy(tmp_path, tiny_reference):
    config_path = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config_path)
    somatic_cfg = default_somatic_config()
    somatic_cfg["identity_policy"] = "warn"
    somatic_cfg["small_variants"] = default_deepsomatic_config()
    pairs = selected_pair(tmp_path, row(tumor_read_group_sample="WRONG"), somatic_cfg)
    plan = generate_deepsomatic_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path, selected=pairs, reference=tiny_reference["fasta"], pair_attempt_id="a1", max_concurrent=1, include_warning_pairs=False)
    assert not plan["pairs"]
    plan = generate_deepsomatic_plan(cfg, somatic_cfg, project_attempt_dir=tmp_path, selected=pairs, reference=tiny_reference["fasta"], pair_attempt_id="a1", max_concurrent=1, include_warning_pairs=True)
    assert plan["pairs"][0]["caller_preflight_status"] == "READY_WITH_WARNINGS"
