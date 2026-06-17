from __future__ import annotations

from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.preflight import HeaderMetadata, validate_identity, validate_pair_preflight, validate_reference


def pair_from_row(tmp_path, row_data, cfg=None):
    selected, _, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row_data]), somatic_config=cfg or default_somatic_config())
    assert selected
    return selected[0], validation


def test_strict_identity_exact_match(tmp_path):
    pair, _ = pair_from_row(tmp_path, row())
    result = validate_pair_preflight(pair, default_somatic_config())
    assert result["identity"]["status"] == "PASS"
    assert result["readiness_status"] == "ready"


def test_tumor_header_mismatch_fails(tmp_path):
    pair, _ = pair_from_row(tmp_path, row(tumor_read_group_sample="WRONG"))
    result = validate_pair_preflight(pair, default_somatic_config())
    assert any(e["category"] == "tumor_header_mismatch" for e in result["errors"])


def test_identity_warn_policy_warns(tmp_path):
    cfg = default_somatic_config()
    cfg["identity_policy"] = "warn"
    pair, _ = pair_from_row(tmp_path, row(tumor_read_group_sample="WRONG"), cfg)
    result = validate_pair_preflight(pair, cfg)
    assert result["identity"]["status"] == "WARN"
    assert result["readiness_status"] == "warning"


def test_ambiguous_and_missing_sample_names(tmp_path):
    pair, _ = pair_from_row(tmp_path, row())
    result = validate_identity(
        pair,
        HeaderMetadata("BAM", sample_names=("A", "B"), read_groups=({"SM": "A"},)),
        HeaderMetadata("BAM", sample_names=(), read_groups=()),
        default_somatic_config(),
    )
    assert result["status"] == "FAIL"
    assert any(e["category"] in {"ambiguous_sample_identity", "missing_sample_tag"} for e in result["errors"])


def test_reference_mismatched_signature_order_length_and_chr_prefix(tmp_path):
    pair, _ = pair_from_row(tmp_path, row(tumor_reference_signature="a", normal_reference_signature="b"))
    result = validate_reference(
        pair,
        HeaderMetadata("BAM", contigs=(("chr1", 10), ("chr2", 20))),
        HeaderMetadata("BAM", contigs=(("chr2", 20), ("chr1", 10))),
        default_somatic_config(),
    )
    assert any(e["category"] == "tumor_normal_reference_mismatch" for e in result["errors"])
    assert any(e["category"] == "contig_order_mismatch" for e in result["errors"])
    result = validate_reference(
        pair,
        HeaderMetadata("BAM", contigs=(("chr1", 10),)),
        HeaderMetadata("BAM", contigs=(("chr1", 11),)),
        default_somatic_config(),
    )
    assert any(e["category"] == "contig_length_mismatch" for e in result["errors"])
    result = validate_reference(
        pair,
        HeaderMetadata("BAM", contigs=(("chr1", 10),)),
        HeaderMetadata("BAM", contigs=(("1", 10),)),
        default_somatic_config(),
    )
    assert result["status"] == "FAIL"


def test_coverage_thresholds_and_invalid_numbers(tmp_path):
    cfg = default_somatic_config()
    cfg["preflight"]["minimum_tumor_coverage"] = 30
    cfg["preflight"]["minimum_normal_coverage"] = 20
    cfg["preflight"]["maximum_tumor_normal_coverage_ratio"] = 2
    pair, _ = pair_from_row(tmp_path, row(tumor_coverage="10", normal_coverage="4"), cfg)
    result = validate_pair_preflight(pair, cfg)
    cats = {e["category"] for e in result["errors"]}
    assert "insufficient_tumor_coverage" in cats
    assert "insufficient_normal_coverage" in cats
    assert "extreme_coverage_imbalance" in cats
    pair, _ = pair_from_row(tmp_path, row(tumor_coverage="nan"), cfg)
    assert validate_pair_preflight(pair, cfg)["readiness_status"] == "failed"


def test_purity_contamination_ploidy_metadata(tmp_path):
    pair, _ = pair_from_row(tmp_path, row(tumor_purity="1.2", tumor_contamination="-0.1", normal_contamination="2", tumor_ploidy="0"))
    result = validate_pair_preflight(pair, default_somatic_config())
    cats = {e["category"] for e in result["errors"]}
    assert {"invalid_purity", "invalid_contamination", "invalid_ploidy"} <= cats


def test_required_metadata_and_source(tmp_path):
    cfg = default_somatic_config()
    cfg["metadata"]["require_purity"] = True
    cfg["metadata"]["require_source_for_values"] = True
    pair, _ = pair_from_row(tmp_path, row(tumor_purity="0.5"), cfg)
    result = validate_pair_preflight(pair, cfg)
    assert any(e["category"] == "missing_required_metadata" for e in result["errors"])
