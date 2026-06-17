from __future__ import annotations

from variant_analysis_harness.somatic.severus.compatibility import COMPATIBILITY_REGISTRY
from variant_analysis_harness.somatic.severus.outputs import discover_severus_outputs, write_output_inventory


def test_output_discovery_inventories_native_files(tmp_path):
    native = tmp_path / "native"
    native.mkdir()
    for rel in ["all_SVs/severus_all.vcf", "somatic_SVs/severus_somatic.vcf", "all_SVs/breakpoint_clusters.tsv", "all_SVs/breakpoint_clusters_list.tsv", "somatic_SVs/breakpoint_clusters.tsv", "somatic_SVs/breakpoint_clusters_list.tsv", "somatic_SVs/plots/severus_1.html", "extra.txt"]:
        path = native / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html>x</html>\n" if rel.endswith(".html") else "a\tb\n1\t2\n", encoding="utf-8")
    result = discover_severus_outputs(native, COMPATIBILITY_REGISTRY["1.7"])
    assert result["status"] == "PASS"
    assert any(item["category"] == "breakpoint_clusters" for item in result["inventory"])
    assert any(item["category"] == "html_breakpoint_graph" for item in result["inventory"])
    assert any(item["category"] == "unknown_native" for item in result["inventory"])
    write_output_inventory(result, tmp_path / "out")
    assert (tmp_path / "out" / "severus_native_output_inventory.json").exists()


def test_missing_or_empty_required_output_fails(tmp_path):
    result = discover_severus_outputs(tmp_path / "missing", COMPATIBILITY_REGISTRY["1.7"])
    assert result["status"] == "FAIL"
    native = tmp_path / "native"
    native.mkdir()
    (native / "all_SVs").mkdir()
    (native / "all_SVs" / "severus_all.vcf").write_text("", encoding="utf-8")
    assert discover_severus_outputs(native, COMPATIBILITY_REGISTRY["1.7"])["status"] == "FAIL"
