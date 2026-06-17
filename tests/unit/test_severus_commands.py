from __future__ import annotations

from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest
from variant_analysis_harness.somatic.severus.commands import build_severus_base_argv, build_severus_command_spec, build_severus_multi_target_base_argv, severus_output_paths, wrap_severus_command
from variant_analysis_harness.somatic.severus.config import default_severus_config


def pair_from_row(tmp_path, row_data):
    selected, _, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row_data]), somatic_config=default_somatic_config())
    assert validation.status == "PASS"
    return selected[0]


def test_matched_tumor_normal_command_contains_roles_and_options(tmp_path, tiny_reference):
    pair = pair_from_row(tmp_path, row())
    cfg = default_severus_config()
    cfg["severus"]["parameters"].update({"threads": 12, "vntr_bed": str(tiny_reference["bed"]), "pon": str(tmp_path / "pon.vcf.gz"), "regions": ["chr1"]})
    paths = severus_output_paths(tmp_path / "attempt")
    argv = build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, output_paths=paths)
    assert argv[0] == "severus"
    assert "--target-bam" in argv
    assert str(pair.tumor_input_path) in argv
    assert "--control-bam" in argv
    assert str(pair.normal_input_path) in argv
    assert "--reference" not in argv
    assert "--tumor-sample" not in argv
    assert "--normal-sample" not in argv
    assert "--threads" in argv
    assert "12" in argv
    assert "--PON" in argv
    assert "--vntr-bed" in argv


def test_wrappers_and_command_spec_outputs(tmp_path, tiny_reference):
    pair = pair_from_row(tmp_path, row())
    cfg = default_severus_config()
    spec, paths = build_severus_command_spec(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, project_attempt_dir=tmp_path / "somatic", pair_attempt_id="sev1")
    assert spec.stage == "somatic_sv_severus"
    assert paths["standard_vcf"] in spec.outputs
    assert spec.argv[:3] == ["docker", "run", "--rm"]
    cfg["severus"]["container"]["engine"] = "apptainer"
    assert wrap_severus_command(["severus"], cfg, bind_paths=[tmp_path])[:2] == ["apptainer", "exec"]
    cfg["severus"]["container"]["engine"] = "singularity"
    assert wrap_severus_command(["severus"], cfg, bind_paths=[tmp_path])[:2] == ["singularity", "exec"]
    cfg["severus"]["execution"]["mode"] = "executable"
    cfg["severus"]["executable"]["path"] = "/bin/severus"
    assert wrap_severus_command(["severus", "--help"], cfg, bind_paths=[])[0] == "/bin/severus"


def test_protected_extra_args_and_tumor_only_supported_when_authorized(tmp_path, tiny_reference):
    pair = pair_from_row(tmp_path, row())
    cfg = default_severus_config()
    cfg["severus"]["parameters"]["extra_args"] = ["--normal-bam=wrong.bam"]
    paths = severus_output_paths(tmp_path / "attempt")
    try:
        build_severus_base_argv(pair=pair, reference=tiny_reference["fasta"], sev_config=cfg, output_paths=paths)
    except ValueError as exc:
        assert "protected" in str(exc)
    else:
        raise AssertionError("protected extra args must fail")
    somatic_cfg = default_somatic_config()
    somatic_cfg["tumor_only"]["allowed"] = True
    selected, _, _ = load_somatic_manifest(write_manifest(tmp_path / "tumor_only.tsv", [row(mode="tumor_only", normal="", tumor_only_acknowledgment="ack")]), somatic_config=somatic_cfg)
    argv = build_severus_base_argv(pair=selected[0], reference=tiny_reference["fasta"], sev_config=default_severus_config(), output_paths=paths)
    assert "--target-bam" in argv
    assert "--control-bam" not in argv


def test_multi_target_command_uses_repeated_target_values(tmp_path):
    cfg = default_severus_config()
    paths = severus_output_paths(tmp_path / "attempt")
    argv = build_severus_multi_target_base_argv(
        target_bams=[tmp_path / "T1.bam", tmp_path / "T2.bam"],
        control_bam=tmp_path / "N1.bam",
        analysis_mode="tumor_normal",
        sev_config=cfg,
        output_paths=paths,
    )
    idx = argv.index("--target-bam")
    assert argv[idx + 1: idx + 3] == [str(tmp_path / "T1.bam"), str(tmp_path / "T2.bam")]
    assert "--control-bam" in argv
