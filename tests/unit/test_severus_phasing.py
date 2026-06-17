from __future__ import annotations

from variant_analysis_harness.somatic.severus.phasing import validate_severus_phasing, write_phasing_validation


def test_phased_vcf_and_supplementary_haplotagging(tmp_path):
    vcf = tmp_path / "phase.vcf.gz"
    vcf.write_text("vcf\n", encoding="utf-8")
    idx = tmp_path / "phase.vcf.gz.tbi"
    idx.write_text("idx\n", encoding="utf-8")
    result = validate_severus_phasing({"mode": "phased", "phased_vcf": str(vcf), "phased_vcf_index": str(idx), "hp_tags": "present", "supplementary_hp_tags": "present", "haplotagging_method": "HiPhase"})
    assert result["status"] == "PASS"
    assert result["supplementary_tag_decision"]["emit"] is True
    write_phasing_validation(result, tmp_path / "out")
    assert (tmp_path / "out" / "severus_phasing_validation.json").exists()


def test_phasing_missing_vcf_index_and_unknown_supplementary_state(tmp_path):
    vcf = tmp_path / "phase.vcf.gz"
    vcf.write_text("vcf\n", encoding="utf-8")
    result = validate_severus_phasing({"mode": "phased", "phased_vcf": str(vcf), "hp_tags": "unknown", "supplementary_hp_tags": "unknown"})
    assert result["status"] == "FAIL"
    assert any("index" in error for error in result["errors"])
    unphased = validate_severus_phasing({"mode": "unphased"})
    assert unphased["status"] == "WARN"


def test_haplotagged_inputs_require_phased_vcf_by_policy():
    result = validate_severus_phasing({"mode": "auto", "hp_tags": "present", "require_phased_vcf_for_haplotagged_inputs": True})
    assert result["status"] == "FAIL"
    relaxed = validate_severus_phasing({"mode": "auto", "hp_tags": "present", "require_phased_vcf_for_haplotagged_inputs": False, "supplementary_hp_tags": "present"})
    assert relaxed["status"] == "WARN"
