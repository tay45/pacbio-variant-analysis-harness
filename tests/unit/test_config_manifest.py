from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import write_config, write_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.common.manifest import load_manifest
from variant_analysis_harness.exceptions import ConfigError, ManifestError


def test_valid_config(tiny_reference, tmp_path):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    assert cfg["project"]["name"] == "test_project"
    assert cfg["tools"]["deepvariant"]["model_type"] == "PACBIO"


def test_invalid_enum_rejected(tiny_reference, tmp_path):
    config = write_config(tmp_path, tiny_reference)
    text = config.read_text().replace("model_type: PACBIO", "model_type: SOMATIC")
    config.write_text(text)
    with pytest.raises(ConfigError):
        load_run_config(config)


def test_shell_fragment_rejected(tiny_reference, tmp_path):
    config = write_config(tmp_path, tiny_reference)
    text = config.read_text().replace("executable: pbmm2", "executable: 'pbmm2; rm x'")
    config.write_text(text)
    with pytest.raises(ConfigError):
        load_run_config(config)


def test_manifest_valid_aligned_bam(tmp_path, tiny_inputs):
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    samples = load_manifest(manifest)
    assert samples[0].sample_id == "SAMPLE_001"


def test_manifest_multiple_xml(tmp_path, tiny_inputs):
    manifest = write_manifest(
        tmp_path,
        "SAMPLE_001",
        "pacbio_dataset_xml_list",
        tiny_inputs["xml1"],
        additional=str(tiny_inputs["xml2"]),
        aligned="false",
    )
    sample = load_manifest(manifest)[0]
    assert sample.additional_inputs == (tiny_inputs["xml2"].resolve(),)


def test_manifest_duplicate_sample(tmp_path, tiny_inputs):
    manifest = tmp_path / "dup.tsv"
    row = f"SAMPLE_001\tpacbio_hifi\taligned_bam\t{tiny_inputs['bam']}\t\ttrue\tref\tSAMPLE_001\tSAMPLE_001\n"
    manifest.write_text(
        "sample_id\tplatform\tinput_type\tinput_path\tadditional_inputs\taligned\treference_id\tread_group_sample\toutput_prefix\n"
        + row
        + row
    )
    with pytest.raises(ManifestError):
        load_manifest(manifest)


def test_manifest_unsafe_sample_id(tmp_path, tiny_inputs):
    manifest = write_manifest(tmp_path, "BAD SAMPLE", "aligned_bam", tiny_inputs["bam"])
    with pytest.raises(ManifestError):
        load_manifest(manifest)
