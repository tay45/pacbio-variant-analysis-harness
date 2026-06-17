from __future__ import annotations

from variant_analysis_harness.somatic.integrated.model import build_project_model
from variant_analysis_harness.somatic.integrated.planning import write_integrated_outputs
from variant_analysis_harness.somatic.integrated.status import derive_pair_status, status_counts
from variant_analysis_harness.somatic.manifest import SomaticPair, default_somatic_config


def _pair(idx: int) -> SomaticPair:
    return SomaticPair(
        row_number=idx + 2,
        pair_id=f"P{idx:04d}",
        subject_id=f"S{idx:04d}",
        tumor_sample_id=f"T{idx:04d}",
        tumor_specimen_id=f"T{idx:04d}_SPEC",
        tumor_input_type="BAM",
        tumor_input_path=f"T{idx:04d}.bam",
        tumor_index_path=f"T{idx:04d}.bam.bai",
        normal_sample_id=f"N{idx:04d}",
        normal_specimen_id=f"N{idx:04d}_SPEC",
        normal_input_type="BAM",
        normal_input_path=f"N{idx:04d}.bam",
        normal_index_path=f"N{idx:04d}.bam.bai",
        reference_id="ref_001",
        analysis_mode="tumor_normal",
        enabled=True,
        row_hash=f"hash{idx:04d}",
    )


def test_3000_pair_integrated_reporting_is_deterministic_and_isolates_failures(tmp_path, tiny_reference):
    cfg = {"project": {"name": "scale_project", "output_root": str(tmp_path / "results")}, "reference": {"id": "ref_001", "fasta": str(tiny_reference["fasta"])}}
    somatic_cfg = default_somatic_config()
    somatic_cfg["integrated"]["enabled"] = True
    pairs = [_pair(idx) for idx in range(3000)]
    project = build_project_model(
        cfg=cfg,
        somatic_project_id="SCALE",
        integrated_attempt_id="integrated_attempt_001",
        selected_pairs=pairs,
        excluded_pairs=[],
        integrated_config=somatic_cfg["integrated"],
    )
    rows = []
    sources = []
    compatibility = []
    for idx, pair in enumerate(pairs):
        ds = {"caller": "deepsomatic", "pair_id": pair.pair_id, "attempt_id": "ds1", "status": "complete", "validation_status": "PASS", "qc_status": "PASS", "subject_id": pair.subject_id, "tumor_sample_id": pair.tumor_sample_id, "normal_sample_id": pair.normal_sample_id, "analysis_mode": pair.analysis_mode, "reference_id": pair.reference_id}
        sv_status = "failed" if idx % 10 == 0 else "complete"
        sv_validation = "FAIL" if idx % 10 == 0 else "PASS"
        sv = {"caller": "severus", "pair_id": pair.pair_id, "attempt_id": "sv1", "status": sv_status, "validation_status": sv_validation, "qc_status": "PASS", "subject_id": pair.subject_id, "tumor_sample_id": pair.tumor_sample_id, "normal_sample_id": pair.normal_sample_id, "analysis_mode": pair.analysis_mode, "reference_id": pair.reference_id}
        status = derive_pair_status(ds, sv, small_policy="optional", sv_policy="optional", allow_partial_success=True, include_warning_results=False, compatibility_status="PASS")
        rows.append({"pair_id": pair.pair_id, "subject_id": pair.subject_id, "analysis_mode": pair.analysis_mode, "integrated_status": status, "identity_compatibility": "PASS", "reference_compatibility": "PASS", "failure_categories": ["integrated_partial_result", "integrated_unvalidated_sv_output"] if status == "partial_success" else [], "deepsomatic": ds, "severus": sv})
        sources.extend([ds, sv])
        compatibility.append({"pair_id": pair.pair_id, "status": "PASS", "errors": [], "warnings": []})
    plan = {"project": project, "integrated_config": {"relationship_analysis": {"enabled": True, "window_bp": 10000, "large_window_bp": 100000, "include_filtered_small_variants": False, "include_filtered_structural_variants": False}}, "pair_rows": rows, "source_attempts": sources, "compatibility": compatibility}

    result = write_integrated_outputs(plan, tmp_path / "integrated")
    counts = status_counts(rows)

    assert counts["complete"] == 2700
    assert counts["partial_success"] == 300
    actionable = [row for row in result["recommendations"] if row["recommendation"] != "no rerun required"]
    assert len(actionable) == 300
    assert {row["recommendation"] for row in actionable} == {"rerun Severus only"}
    assert (tmp_path / "integrated" / "reports" / "integrated_recruiter_summary.md").exists()
