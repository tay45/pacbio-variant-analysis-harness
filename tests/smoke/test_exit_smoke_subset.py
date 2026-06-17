from __future__ import annotations

import pytest

from tests.conftest import write_config
from tests.unit.test_cohort_manifest import row, write_cohort_manifest
from tests.unit.test_joint_genotyping import write_gvcf, write_joint_manifest
from variant_analysis_harness import RESEARCH_USE_DISCLAIMER, __version__
from variant_analysis_harness.cohort.manifest import load_cohort_manifest
from variant_analysis_harness.cohort.planning import generate_cohort_plan
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.joint.inputs import build_joint_inputs, load_joint_seed_manifest
from variant_analysis_harness.joint.planning import generate_joint_plan
from variant_analysis_harness.joint.sharding import shards_from_contigs


pytestmark = pytest.mark.exit_smoke


def test_exit_smoke_core_metadata():
    assert __version__
    assert "research use only" in RESEARCH_USE_DISCLAIMER.lower()


def test_exit_smoke_cohort_planning(tmp_path, tiny_reference, tiny_inputs):
    config = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config)
    manifest = write_cohort_manifest(tmp_path / "cohort.tsv", [row("SAMPLE_A", tiny_inputs["bam"])])
    selected, excluded, _ = load_cohort_manifest(manifest)
    plan = generate_cohort_plan(
        cfg,
        config_path=config,
        manifest_path=manifest,
        selected=selected,
        excluded=excluded,
        cohort_id="EXIT_SMOKE",
        cohort_attempt_id="cohort_attempt_001",
        sample_attempt_id="attempt_001",
        output_root=None,
        max_concurrent=1,
    )
    assert plan["task_count"] == 1
    assert plan["selected_samples"][0]["sample_id"] == "SAMPLE_A"


def test_exit_smoke_joint_planning(tmp_path, tiny_reference):
    config = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config)
    cfg["joint_genotyping"]["enabled"] = True
    gvcf = write_gvcf(tmp_path / "A.g.vcf.gz", "A", contigs=[("chr1", 12)])
    manifest = write_joint_manifest(tmp_path / "joint.tsv", [("A", gvcf, "ref")])
    rows = load_joint_seed_manifest(manifest)
    inputs, errors, warnings = build_joint_inputs(rows, base_dir=tmp_path)
    shards = shards_from_contigs([{"id": "chr1", "length": 12}], out_dir=tmp_path)
    plan = generate_joint_plan(
        cfg,
        config_path=config,
        manifest_path=manifest,
        shards=shards,
        inputs=inputs,
        excluded_samples=[],
        joint_id="EXIT_SMOKE_JOINT",
        attempt_id="joint_attempt_001",
        attempt_dir=tmp_path / "joint_attempt",
        max_concurrent=1,
        reference_result={"status": "PASS", "errors": [], "warnings": []},
        identity_result={"status": "PASS", "errors": [], "warnings": []},
    )
    assert not errors
    assert not warnings
    assert plan["selected_sample_count"] == 1
    assert plan["shard_count"] == 1
