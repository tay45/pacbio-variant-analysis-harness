from __future__ import annotations

from variant_analysis_harness.somatic.integrated.relationships import build_relationships, summarize_event_context, write_relationship_outputs
from variant_analysis_harness.somatic.integrated.variants import normalize_small_variant, normalize_sv


def test_relationships_interval_breakpoint_bnd_and_filtered(tmp_path):
    small = [
        normalize_small_variant({"chrom": "chr1", "pos": 100, "ref": "A", "alt": "G", "filter": "PASS", "vaf": "0.2", "id": "s1"}),
        normalize_small_variant({"chrom": "chr1", "pos": 1000, "ref": "A", "alt": "AT", "filter": "Low", "id": "s2"}),
        normalize_small_variant({"chrom": "chr2", "pos": 500, "ref": "C", "alt": "T", "filter": "PASS", "id": "s3"}),
    ]
    svs = [
        normalize_sv({"chrom": "chr1", "start": 50, "end": 150, "svtype": "DEL", "filter": "PASS", "id": "sv1"}),
        normalize_sv({"chrom": "chr1", "start": 900, "svtype": "BND", "remote_chrom": "chr2", "remote_pos": 505, "filter": "PASS", "id": "sv2"}),
    ]
    rel = build_relationships(small, svs, window_bp=20, large_window_bp=100)
    assert any(r["relationship_type"] == "inside_sv_interval" for r in rel)
    assert any(r["relationship_type"] == "near_bnd_remote_breakpoint" for r in rel)
    assert not any(r.get("small_variant_key") == "s2" for r in rel)
    summaries = summarize_event_context(rel, svs)
    assert summaries[0]["small_variant_relationship_count"] >= 1
    write_relationship_outputs(rel, tmp_path / "rel")
    assert (tmp_path / "rel" / "integrated_variant_relationships.tsv").exists()

