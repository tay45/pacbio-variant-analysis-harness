from __future__ import annotations

from variant_analysis_harness.somatic.integrated.status import derive_pair_status, status_counts


GOOD = {"status": "complete", "validation_status": "PASS", "qc_status": "PASS"}
WARN = {"status": "complete", "validation_status": "WARN", "qc_status": "PASS"}
FAIL = {"status": "failed", "validation_status": "FAIL", "qc_status": "FAIL"}
NOT = {"status": "not_started", "validation_status": "UNKNOWN", "qc_status": "UNKNOWN"}


def test_status_derivation_core_cases():
    assert derive_pair_status(GOOD, GOOD) == "complete"
    assert derive_pair_status(WARN, GOOD, include_warning_results=True) == "complete_with_warnings"
    assert derive_pair_status(GOOD, FAIL) == "partial_success"
    assert derive_pair_status(GOOD, FAIL, allow_partial_success=False) == "failed"
    assert derive_pair_status(GOOD, NOT, sv_policy="disabled") == "small_variants_only"
    assert derive_pair_status(NOT, GOOD, small_policy="disabled") == "structural_variants_only"
    assert derive_pair_status(NOT, NOT) == "not_started"
    assert derive_pair_status(GOOD, GOOD, compatibility_status="FAIL") == "inconsistent"
    assert derive_pair_status({"superseded": True}, GOOD) == "superseded"


def test_status_counts():
    assert status_counts([{"integrated_status": "complete"}, {"integrated_status": "complete"}, {"integrated_status": "failed"}]) == {"complete": 2, "failed": 1}

