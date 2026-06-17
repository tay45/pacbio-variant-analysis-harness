from __future__ import annotations

import json

from variant_analysis_harness.somatic.severus.compatibility import COMPATIBILITY_REGISTRY
from variant_analysis_harness.somatic.severus.outputs import discover_severus_outputs, validate_breakpoint_tables


def output_contract():
    return json.loads(open("contracts/severus/1.7/output_contract.json", encoding="utf-8").read())


def write_native(native):
    for rel in [
        "all_SVs/severus_all.vcf",
        "somatic_SVs/severus_somatic.vcf",
        "all_SVs/breakpoint_clusters.tsv",
        "all_SVs/breakpoint_clusters_list.tsv",
        "somatic_SVs/breakpoint_clusters.tsv",
        "somatic_SVs/breakpoint_clusters_list.tsv",
        "all_SVs/plots/severus_1.html",
        "somatic_SVs/plots/severus_2.html",
        "severus.log",
    ]:
        path = native / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html>plot</html>\n" if rel.endswith(".html") else "col1\tcol2\n1\t2\n", encoding="utf-8")


def test_official_output_names_and_no_invented_outputs(tmp_path):
    c = output_contract()
    assert c["required_outputs"]["all_vcf"] == "all_SVs/severus_all.vcf"
    assert c["conditional_required_outputs"]["somatic_vcf"]["path"] == "somatic_SVs/severus_somatic.vcf"
    assert "graph.gfa" in c["unavailable_outputs"]
    assert "breakpoints.tsv" in c["unavailable_outputs"]


def test_output_discovery_uses_contract_and_preserves_unknowns(tmp_path):
    native = tmp_path / "native"
    write_native(native)
    (native / "unknown.extra").write_text("x\n", encoding="utf-8")
    result = discover_severus_outputs(native, COMPATIBILITY_REGISTRY["1.7"], target_ids=["T1", "T2"])
    assert result["status"] == "WARN"
    assert any(item["category"] == "all_sv_vcf" for item in result["inventory"])
    assert any(item["category"] == "somatic_sv_vcf" for item in result["inventory"])
    assert any(item["category"] == "html_breakpoint_graph" for item in result["inventory"])
    assert any(item["category"] == "unknown_native" for item in result["inventory"])
    assert result["target_output_map"]["targets"]["T1"].endswith("somatic_SVs/severus_somatic.vcf")


def test_missing_required_output_and_breakpoint_tables(tmp_path):
    native = tmp_path / "native"
    native.mkdir()
    result = discover_severus_outputs(native, COMPATIBILITY_REGISTRY["1.7"])
    assert result["status"] == "FAIL"
    write_native(native)
    tables = validate_breakpoint_tables(native, COMPATIBILITY_REGISTRY["1.7"])
    assert tables["status"] == "PASS"


def test_tumor_only_without_somatic_output_requires_only_all_vcf(tmp_path):
    native = tmp_path / "native"
    (native / "all_SVs").mkdir(parents=True)
    (native / "all_SVs" / "severus_all.vcf").write_text("vcf\n", encoding="utf-8")
    result = discover_severus_outputs(native, COMPATIBILITY_REGISTRY["1.7"], require_somatic=False, target_ids=["T1"])
    assert result["status"] == "PASS"
    assert result["somatic_vcf"] == ""
