from __future__ import annotations

from variant_analysis_harness.somatic.integrated.qc import aggregate_qc, qc_domain, write_qc


def test_integrated_qc_domains(tmp_path):
    qc = aggregate_qc([qc_domain("identity QC", "PASS"), qc_domain("Severus BND validation", "WARN", reason_codes=["orphan_bnd"])])
    assert qc["overall_readiness"] == "WARN"
    assert qc["domain_counts"]["WARN"] == 1
    fail = aggregate_qc([qc_domain("reference QC", "FAIL")])
    assert fail["overall_readiness"] == "FAIL"
    write_qc(qc, tmp_path / "qc")
    assert (tmp_path / "qc" / "integrated_qc.json").exists()

