from __future__ import annotations

from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.somatic.integrated.compatibility import validate_pair_compatibility, write_compatibility
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest


def pair(tmp_path):
    selected, _, _ = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row()]), somatic_config=default_somatic_config())
    return selected[0]


def test_integrated_compatibility_matching_and_mismatches(tmp_path):
    p = pair(tmp_path)
    source = {"subject_id": p.subject_id, "tumor_sample_id": p.tumor_sample_id, "normal_sample_id": p.normal_sample_id, "analysis_mode": p.analysis_mode, "reference_id": p.reference_id, "manifest_row_hash": p.row_hash}
    assert validate_pair_compatibility(p, source, source, {})["status"] == "PASS"
    bad = dict(source, tumor_sample_id="WRONG")
    assert validate_pair_compatibility(p, bad, source, {})["status"] == "FAIL"
    bad_ref = dict(source, reference_id="other")
    result = validate_pair_compatibility(p, source, bad_ref, {})
    assert any("reference" in e for e in result["errors"])
    write_compatibility([result], tmp_path / "out")
    assert (tmp_path / "out" / "integrated_compatibility.tsv").exists()

