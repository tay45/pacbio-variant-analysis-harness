from __future__ import annotations

import json

from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.cli import main
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.severus.commands import build_severus_base_argv, build_severus_multi_target_base_argv, severus_output_paths
from variant_analysis_harness.somatic.severus.config import default_severus_config


def contract():
    return json.loads(open("contracts/severus/1.7/cli_contract.json", encoding="utf-8").read())


def pair_from_row(tmp_path, row_data, cfg=None):
    selected, _, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row_data]), somatic_config=cfg or default_somatic_config())
    assert validation.status in {"PASS", "WARN"}
    return selected[0]


def test_official_matched_command_flags_come_from_contract(tmp_path, tiny_reference):
    c = contract()
    pair = pair_from_row(tmp_path, row())
    cfg = default_severus_config()
    cfg["severus"]["parameters"].update({"threads": 8, "vntr_bed": str(tiny_reference["bed"]), "pon": str(tmp_path / "pon.vcf")})
    (tmp_path / "pon.vcf").write_text("pon\n", encoding="utf-8")
    paths = severus_output_paths(tmp_path / "attempt")
    argv = build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, output_paths=paths)
    flags = c["flags"]
    assert flags["target_bam"] in argv
    assert flags["control_bam"] in argv
    assert flags["out_dir"] in argv
    assert flags["threads"] in argv
    assert flags["vntr_bed"] in argv
    assert flags["pon"] in argv
    for bad in c["unavailable_flags"]:
        assert bad not in argv


def test_tumor_only_omits_control_and_multiple_target_order_is_stable(tmp_path, tiny_reference):
    somatic_cfg = default_somatic_config()
    somatic_cfg["tumor_only"]["allowed"] = True
    pair = pair_from_row(tmp_path, row(mode="tumor_only", normal="", tumor_only_acknowledgment="ack"), somatic_cfg)
    paths = severus_output_paths(tmp_path / "attempt")
    argv = build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=default_severus_config(), output_paths=paths)
    assert "--target-bam" in argv
    assert "--control-bam" not in argv
    multi = build_severus_multi_target_base_argv(
        target_bams=[tmp_path / "A.bam", tmp_path / "B.bam"],
        control_bam=tmp_path / "N.bam",
        analysis_mode="tumor_normal",
        sev_config=default_severus_config(),
        output_paths=paths,
    )
    idx = multi.index("--target-bam")
    assert multi[idx + 1: idx + 3] == [str(tmp_path / "A.bam"), str(tmp_path / "B.bam")]


def test_phasing_supplementary_and_protected_flag_contract(tmp_path, tiny_reference):
    phased = tmp_path / "phased.vcf.gz"
    phased.write_text("vcf\n", encoding="utf-8")
    idx = tmp_path / "phased.vcf.gz.tbi"
    idx.write_text("idx\n", encoding="utf-8")
    pair = pair_from_row(tmp_path, row())
    cfg = default_severus_config()
    cfg["severus"]["phasing"].update({"phased_vcf": str(phased), "phased_vcf_index": str(idx), "supplementary_hp_tags": "present", "haplotagging_method": "HiPhase"})
    argv = build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, output_paths=severus_output_paths(tmp_path / "attempt"))
    assert "--phasing-vcf" in argv
    assert "--use-supplementary-tag" in argv
    cfg["severus"]["parameters"]["extra_args"] = ["--reference", "bad.fa"]
    try:
        build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, output_paths=severus_output_paths(tmp_path / "attempt2"))
    except ValueError as exc:
        assert "protected" in str(exc)
    else:
        raise AssertionError("obsolete protected flag must be rejected")


def test_unknown_version_execution_rejected(tmp_path, tiny_reference):
    pair = pair_from_row(tmp_path, row())
    cfg = default_severus_config()
    cfg["severus"]["requested_version"] = "9.9"
    cfg["severus"]["unknown_version_policy"] = "warn"
    try:
        build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, output_paths=severus_output_paths(tmp_path / "attempt"))
    except ValueError as exc:
        assert "verified contract" in str(exc)
    else:
        raise AssertionError("unverified versions must not generate executable commands")


def test_contract_drift_check_with_mocked_help(tmp_path):
    help_file = tmp_path / "help.txt"
    help_file.write_text(open("contracts/severus/1.7/cli_help.txt", encoding="utf-8").read(), encoding="utf-8")
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.7\n", encoding="utf-8")
    assert main(["severus-contract-check", "--executable", "severus", "--expected-version", "1.7", "--mock-help", str(help_file), "--mock-version", str(version_file), "--output-dir", str(tmp_path / "drift")]) == 0
    assert (tmp_path / "drift" / "severus_contract_drift.json").exists()
