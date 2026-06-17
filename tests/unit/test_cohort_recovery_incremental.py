from __future__ import annotations

from tests.unit.test_cohort_manifest import row, write_cohort_manifest
from variant_analysis_harness.cohort.planning import write_array_index
from variant_analysis_harness.cohort.rerun import generate_rerun_manifest
from variant_analysis_harness.cohort.status import write_status_event


def test_failed_sample_rerun_manifest(tmp_path, tiny_inputs):
    cohort_dir = tmp_path / "cohort"
    manifest = write_cohort_manifest(
        cohort_dir / "cohort_manifest.resolved.tsv",
        [row("SAMPLE_A", tiny_inputs["bam"]), row("SAMPLE_B", tiny_inputs["bam"])],
    )
    assert manifest.exists()
    write_status_event(cohort_dir, {"sample_id": "SAMPLE_A", "stage": "alignment", "status": "failed", "failure_category": "alignment_failure"})
    write_status_event(cohort_dir, {"sample_id": "SAMPLE_B", "stage": "workflow", "status": "success"})
    output = tmp_path / "rerun_failed.tsv"
    rows = generate_rerun_manifest(cohort_dir, output, status="failed")
    assert [r["sample_id"] for r in rows] == ["SAMPLE_A"]
    assert "rerun_failure_category" in output.read_text()


def test_failed_stage_and_category_selection(tmp_path, tiny_inputs):
    cohort_dir = tmp_path / "cohort"
    write_cohort_manifest(
        cohort_dir / "cohort_manifest.resolved.tsv",
        [row("SAMPLE_A", tiny_inputs["bam"]), row("SAMPLE_B", tiny_inputs["bam"])],
    )
    write_status_event(cohort_dir, {"sample_id": "SAMPLE_A", "stage": "germline_snv", "status": "failed", "failure_category": "snv_calling_failure"})
    write_status_event(cohort_dir, {"sample_id": "SAMPLE_B", "stage": "germline_sv_call", "status": "failed", "failure_category": "sv_calling_failure"})
    rows = generate_rerun_manifest(cohort_dir, tmp_path / "rerun_snv.tsv", status="failed", stage="germline_snv", failure_category="snv_calling_failure")
    assert [r["sample_id"] for r in rows] == ["SAMPLE_A"]


def test_allow_successful_include_sample_for_array_task_manifest(tmp_path, tiny_inputs):
    cohort_dir = tmp_path / "cohort"
    write_cohort_manifest(
        cohort_dir / "cohort_manifest.resolved.tsv",
        [row("SAMPLE_A", tiny_inputs["bam"]), row("SAMPLE_B", tiny_inputs["bam"])],
    )
    rows = generate_rerun_manifest(cohort_dir, tmp_path / "sample_manifest.tsv", include_samples={"SAMPLE_B"}, allow_successful=True)
    assert [r["sample_id"] for r in rows] == ["SAMPLE_B"]

