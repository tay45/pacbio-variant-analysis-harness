from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.test_somatic_manifest_pairing import row, write_manifest
from variant_analysis_harness.somatic.deepsomatic.commands import build_deepsomatic_command_spec, build_run_deepsomatic_argv, deepsomatic_output_paths, wrap_deepsomatic_command
from variant_analysis_harness.somatic.deepsomatic.config import default_deepsomatic_config
from variant_analysis_harness.somatic.manifest import default_somatic_config, load_somatic_manifest


def pair_from(tmp_path, row_data, somatic_cfg=None):
    selected, _, _ = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row_data]), somatic_config=somatic_cfg or default_somatic_config())
    return selected[0]


def test_matched_and_tumor_only_commands(tmp_path, tiny_reference):
    cfg = default_deepsomatic_config()
    pair = pair_from(tmp_path, row())
    paths = deepsomatic_output_paths(tmp_path / "attempt")
    argv = build_run_deepsomatic_argv(pair=pair, reference=tiny_reference["fasta"], ds_config=cfg, output_paths=paths)
    assert "--model_type=PACBIO" in argv
    assert any(a.startswith("--reads_normal=") for a in argv)
    assert any(a == "--sample_name_normal=N1" for a in argv)
    som_cfg = default_somatic_config()
    som_cfg["tumor_only"]["allowed"] = True
    pair = pair_from(tmp_path, row(mode="tumor_only", normal="", tumor_only_acknowledgment="ack"), som_cfg)
    argv = build_run_deepsomatic_argv(pair=pair, reference=tiny_reference["fasta"], ds_config=cfg, output_paths=paths)
    assert "--model_type=PACBIO_TUMOR_ONLY" in argv
    assert not any("reads_normal" in a for a in argv)


def test_regions_pon_num_shards_and_extra_args(tmp_path, tiny_reference):
    cfg = default_deepsomatic_config()
    ds = cfg["deepsomatic"]
    ds["resources"]["num_shards"] = 8
    ds["regions"] = {"mode": "regions", "values": ["chr1:1-10"], "file": None}
    ds["pon"] = {"enabled": True, "path": str(tmp_path / "pon.vcf.gz"), "index_path": None, "signature": None, "use_default_filtering": False}
    ds["advanced"]["extra_args"] = ["--dry_run=true"]
    argv = build_run_deepsomatic_argv(pair=pair_from(tmp_path, row()), reference=tiny_reference["fasta"], ds_config=cfg, output_paths=deepsomatic_output_paths(tmp_path / "attempt"))
    assert "--num_shards=8" in argv
    assert "--regions=chr1:1-10" in argv
    assert any(a.startswith("--pon=") for a in argv)
    assert "--dry_run=true" in argv


def test_wrappers_and_protected_conflict(tmp_path, tiny_reference):
    cfg = default_deepsomatic_config()
    base = ["run_deepsomatic", "--model_type=PACBIO"]
    docker = wrap_deepsomatic_command(base, cfg, bind_paths=[tmp_path, tiny_reference["fasta"].parent])
    assert docker[:3] == ["docker", "run", "--rm"]
    cfg["deepsomatic"]["container"]["engine"] = "apptainer"
    assert wrap_deepsomatic_command(base, cfg, bind_paths=[tmp_path])[0:2] == ["apptainer", "exec"]
    cfg["deepsomatic"]["execution"]["mode"] = "executable"
    cfg["deepsomatic"]["executable"]["path"] = "/usr/bin/run_deepsomatic"
    assert wrap_deepsomatic_command(base, cfg, bind_paths=[])[0] == "/usr/bin/run_deepsomatic"
    cfg = default_deepsomatic_config()
    cfg["deepsomatic"]["advanced"]["extra_args"] = ["--output_vcf=bad.vcf.gz"]
    with pytest.raises(ValueError):
        build_run_deepsomatic_argv(pair=pair_from(tmp_path, row()), reference=tiny_reference["fasta"], ds_config=cfg, output_paths=deepsomatic_output_paths(tmp_path / "attempt"))


def test_command_spec_contains_outputs_and_signature(tmp_path, tiny_reference):
    spec, paths = build_deepsomatic_command_spec(pair=pair_from(tmp_path, row()), reference=tiny_reference["fasta"], ds_config=default_deepsomatic_config(), project_attempt_dir=tmp_path / "project", pair_attempt_id="attempt_001")
    assert spec.stage == "somatic_snv_deepsomatic"
    assert paths["vcf"] in spec.outputs
    assert isinstance(spec.argv, list)
