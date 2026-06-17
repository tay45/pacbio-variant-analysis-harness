from __future__ import annotations

import json

from tests.conftest import write_config
from tests.unit.test_cohort_manifest import row, write_cohort_manifest
from variant_analysis_harness.cohort.incremental import compare_incremental
from variant_analysis_harness.cohort.manifest import load_cohort_manifest
from variant_analysis_harness.cohort.planning import (
    cohort_attempt_dir,
    generate_cohort_plan,
    prepare_cohort_attempt,
    write_array_index,
    write_cohort_plan,
)
from variant_analysis_harness.common.config import load_run_config


def test_cohort_plan_and_array_index_are_stable(tmp_path, tiny_reference, tiny_inputs):
    config = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config)
    manifest = write_cohort_manifest(tmp_path / "cohort.tsv", [row("SAMPLE_B", tiny_inputs["bam"]), row("SAMPLE_A", tiny_inputs["bam"])])
    selected, excluded, _ = load_cohort_manifest(manifest)
    plan = generate_cohort_plan(
        cfg,
        config_path=config,
        manifest_path=manifest,
        selected=selected,
        excluded=excluded,
        cohort_id="COHORT_1",
        cohort_attempt_id="cohort_attempt_001",
        sample_attempt_id="attempt_001",
        output_root=None,
        max_concurrent=2,
    )
    assert [s["array_index"] for s in plan["selected_samples"]] == [1, 2]
    assert [s["sample_id"] for s in plan["selected_samples"]] == ["SAMPLE_A", "SAMPLE_B"]
    out = tmp_path / "array_index.tsv"
    write_array_index(plan, out)
    assert out.read_text().splitlines()[1].startswith("1\tSAMPLE_A\t")


def test_incremental_reuse_and_changed_sample(tmp_path, tiny_reference, tiny_inputs):
    config = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config)
    manifest = write_cohort_manifest(tmp_path / "cohort.tsv", [row("SAMPLE_A", tiny_inputs["bam"])])
    selected, excluded, _ = load_cohort_manifest(manifest)
    attempt_dir = cohort_attempt_dir(cfg, "COHORT_1", "cohort_attempt_001")
    prepare_cohort_attempt(attempt_dir, config_path=config, manifest_path=manifest, cfg=cfg, selected=selected, excluded=excluded)
    plan = generate_cohort_plan(
        cfg,
        config_path=config,
        manifest_path=manifest,
        selected=selected,
        excluded=excluded,
        cohort_id="COHORT_1",
        cohort_attempt_id="cohort_attempt_001",
        sample_attempt_id="attempt_001",
        output_root=None,
        max_concurrent=1,
    )
    write_cohort_plan(plan, attempt_dir)
    comparisons = compare_incremental(current_samples=selected, current_config=cfg, previous_cohort_dir=attempt_dir, out_dir=tmp_path)
    assert comparisons[0]["decision"] == "reuse_candidate"
    changed = write_cohort_manifest(tmp_path / "changed.tsv", [row("SAMPLE_A", tiny_inputs["bam"], analysis="snv")])
    changed_selected, _, _ = load_cohort_manifest(changed)
    comparisons = compare_incremental(current_samples=changed_selected, current_config=cfg, previous_cohort_dir=attempt_dir, out_dir=tmp_path / "changed")
    assert comparisons[0]["decision"] == "rerun"


def test_cohort_plan_cli_creates_artifacts(tmp_path, tiny_reference, tiny_inputs):
    from variant_analysis_harness.cli import main

    config = write_config(tmp_path, tiny_reference)
    manifest = write_cohort_manifest(tmp_path / "cohort.tsv", [row("SAMPLE_A", tiny_inputs["bam"])])
    rc = main(["cohort-plan", "--config", str(config), "--manifest", str(manifest), "--cohort-id", "COHORT_1", "--max-concurrent", "1"])
    assert rc == 0
    plan_path = tmp_path / "results" / "test_project" / "cohorts" / "COHORT_1" / "cohort_attempt_001" / "cohort_plan.json"
    assert json.loads(plan_path.read_text())["task_count"] == 1

