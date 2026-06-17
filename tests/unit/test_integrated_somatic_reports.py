from __future__ import annotations

from variant_analysis_harness.somatic.integrated.reporting import PORTFOLIO_WORDING, write_machine_summary, write_reports


def test_integrated_reports_include_boundaries_and_portfolio_wording(tmp_path):
    project = {"somatic_project_id": "SOM", "integrated_attempt_id": "int1"}
    rows = [{"pair_id": "P1", "subject_id": "S1", "analysis_mode": "tumor_normal", "integrated_status": "partial_success", "identity_compatibility": "PASS", "reference_compatibility": "PASS"}]
    paths = write_reports(project, rows, [], {"overall_readiness": "WARN"}, [{"pair_id": "P1", "recommendation": "rerun Severus only"}], tmp_path)
    report = (tmp_path / "reports" / "integrated_somatic_report.md").read_text()
    assert "not for clinical use" in report
    assert "partial" in report.lower() or "Pair counts" in report
    assert PORTFOLIO_WORDING in (tmp_path / "reports" / "integrated_portfolio_report.md").read_text()
    assert "clinical readiness" not in (tmp_path / "reports" / "integrated_portfolio_report.md").read_text().lower()
    write_machine_summary(project, rows, tmp_path / "exports")
    assert (tmp_path / "exports" / "integrated_somatic_summary.json").exists()

