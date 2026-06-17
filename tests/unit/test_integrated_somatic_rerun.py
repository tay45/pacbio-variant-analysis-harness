from __future__ import annotations

from variant_analysis_harness.somatic.integrated.rerun import failure_summary, recommend_reruns, write_rerun_outputs


def test_integrated_rerun_recommendations(tmp_path):
    rows = [
        {"pair_id": "P1", "integrated_status": "complete", "failure_categories": [], "deepsomatic": {}, "severus": {}},
        {"pair_id": "P2", "integrated_status": "partial_success", "failure_categories": ["integrated_unvalidated_sv_output"], "deepsomatic": {"attempt_id": "d1"}, "severus": {"attempt_id": "s1"}},
        {"pair_id": "P3", "integrated_status": "inconsistent", "failure_categories": ["integrated_reference_mismatch"], "deepsomatic": {}, "severus": {}},
    ]
    recs = recommend_reruns(rows)
    assert recs[0]["recommendation"] == "no rerun required"
    assert recs[1]["recommendation"] == "rerun Severus only"
    assert recs[2]["recommendation"] == "correct reference mismatch"
    failures = failure_summary(rows)
    assert len(failures) == 2
    write_rerun_outputs(recs, failures, tmp_path / "status")
    assert (tmp_path / "status" / "integrated_rerun_recommendations.md").exists()

