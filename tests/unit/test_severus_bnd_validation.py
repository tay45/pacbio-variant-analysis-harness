from __future__ import annotations

from variant_analysis_harness.somatic.severus.validation import validate_bnd_records


def bnd(rid, mate, filt="PASS"):
    return {"id": rid, "mateid": mate, "filter": filt, "alt": "N]chr2:200]"}


def test_reciprocal_bnd_passes_and_orphans_are_policy_controlled():
    assert validate_bnd_records([bnd("a", "b"), bnd("b", "a")])["status"] == "PASS"
    assert validate_bnd_records([bnd("a", "missing")])["status"] == "FAIL"
    assert validate_bnd_records([bnd("a", None)], orphan_policy="warn")["status"] == "WARN"
    assert validate_bnd_records([bnd("a", None)], orphan_policy="allow")["status"] == "PASS"


def test_bnd_duplicate_self_nonreciprocal_and_filter_warnings():
    assert validate_bnd_records([bnd("a", "a")])["status"] == "FAIL"
    assert validate_bnd_records([bnd("a", "b"), bnd("a", "b")])["status"] == "FAIL"
    assert validate_bnd_records([bnd("a", "b"), bnd("b", "c")])["status"] == "FAIL"
    result = validate_bnd_records([bnd("a", "b", "PASS"), bnd("b", "a", "LowSupport")])
    assert result["status"] == "WARN"
