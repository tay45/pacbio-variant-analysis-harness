from __future__ import annotations

import gzip
import importlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.conftest import write_config, write_manifest
from variant_analysis_harness.cli import main
from variant_analysis_harness.common.bam_validation import validate_bam_with_samtools
from variant_analysis_harness.common.bam_validation import compare_bam_reference_contigs, detect_bam_index
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.common.reference_validation import parse_bed, parse_sequence_dictionary, validate_reference_bundle
from variant_analysis_harness.common.tool_probe import probe_tool
from variant_analysis_harness.common.vcf_validation import validate_svsig_gzip, validate_variant_vcf
from variant_analysis_harness.common.yaml_io import load_yaml
from variant_analysis_harness.common.schema_validation import _validate
from variant_analysis_harness.common.atomic import incomplete_path, publish_atomically
from variant_analysis_harness.common.manifest import load_manifest
from variant_analysis_harness.common.stage_status import write_stage_status
from variant_analysis_harness.exceptions import ConfigError, ManifestError
from variant_analysis_harness.models import StageResult, ToolConfig


def test_yaml_duplicate_key_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("a: 1\na: 2\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml(path)


def test_official_pytest_not_repo_shadowed():
    import pytest as official_pytest

    assert "site-packages" in str(official_pytest.__file__)
    assert not str(official_pytest.__file__).endswith("/pytest.py")


def test_fallback_environment_not_set_by_default():
    assert os.environ.get("VARIANT_ANALYSIS_HARNESS_TEST_ALLOW_DEP_FALLBACK") is None


def test_manifest_unsafe_sample_id_contract(tmp_path, tiny_inputs):
    manifest = write_manifest(tmp_path, "BAD SAMPLE", "aligned_bam", tiny_inputs["bam"])
    with pytest.raises(ManifestError):
        load_manifest(manifest)


def test_missing_pyyaml_fails_production_cli(tmp_path):
    import variant_analysis_harness.common.yaml_io as yaml_io

    original_import = importlib.import_module

    def blocked(name, package=None):
        if name == "yaml":
            raise ModuleNotFoundError("No module named 'yaml'", name="yaml")
        return original_import(name, package)

    importlib.import_module = blocked
    try:
        with pytest.raises(ConfigError, match="PyYAML is required"):
            importlib.reload(yaml_io)
    finally:
        importlib.import_module = original_import
        importlib.reload(yaml_io)


def test_missing_jsonschema_fails_production_schema(tmp_path):
    import variant_analysis_harness.common.schema_validation as schema_validation

    original_import = importlib.import_module

    def blocked(name, package=None):
        if name == "jsonschema":
            raise ModuleNotFoundError("No module named 'jsonschema'", name="jsonschema")
        return original_import(name, package)

    importlib.import_module = blocked
    try:
        with pytest.raises(ConfigError, match="jsonschema is required"):
            importlib.reload(schema_validation)
    finally:
        importlib.import_module = original_import
        importlib.reload(schema_validation)


def test_schema_missing_version_rejected(tmp_path, tiny_reference):
    config = write_config(tmp_path, tiny_reference)
    config.write_text(config.read_text().replace("schema_version: phase2a1.v1\n", ""))
    with pytest.raises(ConfigError):
        load_run_config(config)


def test_schema_invalid_nested_key_rejected(tmp_path, tiny_reference):
    config = write_config(tmp_path, tiny_reference)
    config.write_text(config.read_text().replace("research_use_only: true", "research_use_only: true\n  bad_key: value"))
    with pytest.raises(ConfigError):
        load_run_config(config)


def test_local_schema_ref_resolution_and_remote_ref_rejected():
    schema = {
        "type": "object",
        "properties": {"child": {"$ref": "#/$defs/child"}},
        "required": ["child"],
        "$defs": {"child": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}, "additionalProperties": False}},
        "additionalProperties": False,
    }
    _validate({"child": {"name": "ok"}}, schema, "test schema")
    remote = {"$ref": "https://example.invalid/schema.json"}
    with pytest.raises(ConfigError):
        _validate({}, remote, "remote schema")


def test_bundled_cross_file_ref_resolution():
    schema = {"type": "object", "properties": {"reference": {"$ref": "reference.schema.json"}}, "required": ["reference"], "additionalProperties": False}
    _validate(
        {
            "reference": {
                "id": "ref",
                "build": "GRCh38",
                "fasta": "/tmp/ref.fa",
                "fai": "/tmp/ref.fa.fai",
                "checksum_policy": "metadata",
            }
        },
        schema,
        "cross file ref",
    )


def test_remote_ref_rejected_without_socket(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network should not be attempted")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    with pytest.raises(ConfigError, match="Remote schema references"):
        _validate({}, {"$ref": "https://example.invalid/schema.json"}, "remote")
    with pytest.raises(ConfigError, match="Remote schema references"):
        _validate({}, {"$ref": "http://example.invalid/schema.json"}, "remote")
    with pytest.raises(ConfigError, match="Remote schema references"):
        _validate({}, {"$ref": "ftp://example.invalid/schema.json"}, "remote")
    with pytest.raises(ConfigError, match="Remote schema references"):
        _validate({}, {"$ref": "//example.invalid/schema.json"}, "remote")


def test_unresolved_local_schema_ref_raises_config_error():
    with pytest.raises(ConfigError, match="Unresolved bundled local schema reference"):
        _validate({}, {"$ref": "missing.schema.json"}, "missing local")


def test_tool_probe_missing_executable():
    result = probe_tool(ToolConfig(name="samtools", backend="native", executable="definitely_missing_tool"))
    assert result["status"] == "FAIL"


def test_bam_index_bam_bai(tmp_path, tiny_inputs):
    info = detect_bam_index(tiny_inputs["bam"])
    assert info["index_type"] == "BAI"
    assert info["selected"].name.endswith(".bam.bai")


def test_bam_index_plain_bai(tmp_path):
    bam = tmp_path / "x.bam"
    bam.write_bytes(b"bam")
    (tmp_path / "x.bai").write_text("idx")
    info = detect_bam_index(bam)
    assert info["index_type"] == "BAI"
    assert info["selected"].name == "x.bai"


def test_bam_index_bam_csi(tmp_path):
    bam = tmp_path / "x.bam"
    bam.write_bytes(b"bam")
    Path(str(bam) + ".csi").write_text("idx")
    info = detect_bam_index(bam)
    assert info["index_type"] == "CSI"


def test_bam_index_plain_csi(tmp_path):
    bam = tmp_path / "x.bam"
    bam.write_bytes(b"bam")
    (tmp_path / "x.csi").write_text("idx")
    info = detect_bam_index(bam)
    assert info["index_type"] == "CSI"


def test_bam_index_zero_byte(tmp_path):
    bam = tmp_path / "x.bam"
    bam.write_bytes(b"bam")
    Path(str(bam) + ".bai").write_text("")
    info = detect_bam_index(bam)
    assert any(c["name"] == "index_non_empty" and c["status"] == "FAIL" for c in info["checks"])


def test_bam_index_bai_csi_ambiguous(tmp_path):
    bam = tmp_path / "x.bam"
    bam.write_bytes(b"bam")
    Path(str(bam) + ".bai").write_text("idx")
    Path(str(bam) + ".csi").write_text("idx")
    info = detect_bam_index(bam)
    assert any(c["name"] == "index_ambiguous" and c["status"] == "FAIL" for c in info["checks"])


def test_bam_index_stale_warning(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    index = Path(str(tiny_inputs["bam"]) + ".bai")
    old = time.time() - 100
    os.utime(index, (old, old))
    result = validate_bam_with_samtools(tiny_inputs["bam"], expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])
    assert any(c["name"] == "index_not_stale" and c["status"] == "WARN" for c in result["checks"])


def test_pbi_independent_of_bai(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    pbi = Path(str(tiny_inputs["bam"]) + ".pbi")
    pbi.write_text("pbi")
    result = validate_bam_with_samtools(tiny_inputs["bam"], expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"], require_pbi=True)
    assert any(c["name"] == "pacbio_pbi_exists" and c["status"] == "PASS" for c in result["checks"])


def test_bam_reference_exact_and_subset_and_mismatch():
    fai = {"contigs": {"chr1": 12, "chr2": 20}, "duplicates": [], "errors": []}
    assert compare_bam_reference_contigs({"chr1": 12, "chr2": 20}, fai)["status"] == "exact_match"
    assert compare_bam_reference_contigs({"chr1": 12}, fai)["status"] == "compatible_subset"
    mismatch = compare_bam_reference_contigs({"chr1": 13}, fai)
    assert mismatch["status"] == "incompatible_mismatch"
    assert mismatch["length_mismatches"]


def test_reference_validation_malformed_fai(tmp_path, tiny_reference):
    tiny_reference["fai"].write_text("chr1\tbad\n", encoding="utf-8")
    result = validate_reference_bundle(
        {
            "id": "ref",
            "build": "test",
            "fasta": str(tiny_reference["fasta"]),
            "fai": str(tiny_reference["fai"]),
            "sequence_dictionary": str(tiny_reference["dict"]),
            "tandem_repeats_bed": str(tiny_reference["bed"]),
        }
    )
    assert result["status"] == "FAIL"


def test_dictionary_length_mismatch(tmp_path, tiny_reference):
    tiny_reference["dict"].write_text("@SQ\tSN:chr1\tLN:99\n")
    result = validate_reference_bundle({"id": "ref", "build": "test", "fasta": str(tiny_reference["fasta"]), "fai": str(tiny_reference["fai"]), "sequence_dictionary": str(tiny_reference["dict"]), "tandem_repeats_bed": str(tiny_reference["bed"])})
    assert result["status"] == "FAIL"
    assert result["dictionary_compatibility"]["length_mismatches"]


def test_dictionary_duplicate_contig(tmp_path):
    path = tmp_path / "dup.dict"
    path.write_text("@SQ\tSN:chr1\tLN:1\n@SQ\tSN:chr1\tLN:1\n")
    result = parse_sequence_dictionary(path)
    assert result["duplicates"] == ["chr1"]


def test_dictionary_missing_and_malformed_ln(tmp_path):
    path = tmp_path / "bad.dict"
    path.write_text("@SQ\tSN:chr1\n@SQ\tSN:chr2\tLN:bad\n")
    result = parse_sequence_dictionary(path)
    assert result["errors"]


def test_bed_reference_order_chr10_ok(tmp_path):
    bed = tmp_path / "ok.bed"
    bed.write_text("chr1\t0\t1\nchr2\t0\t1\nchr10\t0\t1\n")
    result = parse_bed(bed, ["chr1", "chr2", "chr10"])
    assert result["sorted"] is True


def test_bed_wrong_contig_order(tmp_path):
    bed = tmp_path / "bad.bed"
    bed.write_text("chr2\t0\t1\nchr1\t0\t1\n")
    result = parse_bed(bed, ["chr1", "chr2"])
    assert result["sorted"] is False
    assert result["first_unsorted"]


def test_bed_descending_same_contig(tmp_path):
    bed = tmp_path / "bad.bed"
    bed.write_text("chr1\t10\t12\nchr1\t5\t6\n")
    assert parse_bed(bed, ["chr1"])["sorted"] is False


def test_bed_unknown_malformed_zero_and_empty(tmp_path):
    bad = tmp_path / "bad.bed"
    bad.write_text("chrX\t0\t1\nchr1\ta\t2\nchr1\t1\t1\n")
    result = parse_bed(bad, ["chr1"])
    assert result["errors"]
    empty = tmp_path / "empty.bed"
    empty.write_text("")
    assert parse_bed(empty, ["chr1"])["rows"] == 0


def test_bed_overlap_warn_summary(tmp_path):
    bed = tmp_path / "overlap.bed"
    bed.write_text("chr1\t0\t10\nchr1\t5\t12\n")
    assert parse_bed(bed, ["chr1"])["overlaps"]


def test_bam_validation_with_mock_samtools(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    result = validate_bam_with_samtools(
        tiny_inputs["bam"],
        expected_sample="SAMPLE_001",
        reference_fai=tiny_reference["fai"],
        samtools="samtools",
    )
    assert result["status"] == "PASS"


def test_bam_validation_missing_index(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    Path(str(tiny_inputs["bam"]) + ".bai").unlink()
    result = validate_bam_with_samtools(
        tiny_inputs["bam"],
        expected_sample="SAMPLE_001",
        reference_fai=tiny_reference["fai"],
        samtools="samtools",
    )
    assert result["status"] == "FAIL"


def test_vcf_validation_wrong_sample(tmp_path, tiny_reference):
    vcf = tmp_path / "wrong.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tOTHER\nchr1\t1\t.\tA\tG\t50\tPASS\t.\tGT\t0/1\n",
        encoding="utf-8",
    )
    result = validate_variant_vcf(vcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])
    assert result["status"] == "FAIL"


def test_vcf_multiallelic_and_symbolic(tmp_path, tiny_reference):
    vcf = tmp_path / "multi.vcf"
    vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tA\tG,<DEL>\t50\tPASS\tSVTYPE=DEL;END=3;SVLEN=-2\tGT\t0/1\n")
    result = validate_variant_vcf(vcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])
    assert result["metrics"]["multi_allelic_count"] == 1
    assert result["metrics"]["symbolic_allele_count"] == 0


def test_vcf_malformed_format_and_info(tmp_path, tiny_reference):
    vcf = tmp_path / "bad.vcf"
    vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tA\tG\t50\tPASS\tBAD=;X\tGT:DP\t0/1\n")
    result = validate_variant_vcf(vcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])
    assert result["status"] == "FAIL"


def test_vcf_unexpected_contig(tmp_path, tiny_reference):
    vcf = tmp_path / "badcontig.vcf"
    vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchrZ\t1\t.\tA\tG\t50\tPASS\t.\tGT\t0/1\n")
    assert validate_variant_vcf(vcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])["status"] == "FAIL"


def test_gvcf_block_required(tmp_path, tiny_reference):
    gvcf = tmp_path / "x.g.vcf"
    gvcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tA\t<NON_REF>\t.\tPASS\tEND=10\tGT\t0/0\n")
    assert validate_variant_vcf(gvcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"], expect_gvcf_blocks=True)["status"] == "PASS"
    normal = tmp_path / "normal.g.vcf"
    normal.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tA\tG\t50\tPASS\t.\tGT\t0/1\n")
    assert validate_variant_vcf(normal, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"], expect_gvcf_blocks=True)["status"] == "FAIL"


def test_gvcf_malformed_end(tmp_path, tiny_reference):
    gvcf = tmp_path / "bad.g.vcf"
    gvcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tA\t<NON_REF>\t.\tPASS\t.\tGT\t0/0\n")
    assert validate_variant_vcf(gvcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"], expect_gvcf_blocks=True)["status"] == "FAIL"


def test_sv_bnd_and_svtype_validation(tmp_path, tiny_reference):
    valid = tmp_path / "bnd.vcf"
    valid.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tN\tN]chr1:5]\t50\tPASS\tSVTYPE=BND\tGT\t0/1\n")
    assert validate_variant_vcf(valid, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])["status"] == "PASS"
    bad = tmp_path / "badbnd.vcf"
    bad.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tN\tN]chr1:5\t50\tPASS\tSVTYPE=BND\tGT\t0/1\n")
    assert validate_variant_vcf(bad, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])["status"] == "FAIL"


def test_sv_missing_svtype_and_inconsistent_svlen(tmp_path, tiny_reference):
    vcf = tmp_path / "badsv.vcf"
    vcf.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t1\t.\tN\t<DEL>\t50\tPASS\tEND=10;SVLEN=-2\tGT\t0/1\n")
    assert validate_variant_vcf(vcf, expected_sample="SAMPLE_001", reference_fai=tiny_reference["fai"])["status"] == "FAIL"


def test_svsig_gzip_validation(tmp_path):
    svsig = tmp_path / "x.svsig.gz"
    with gzip.open(svsig, "wt") as handle:
        handle.write("record\n")
    assert validate_svsig_gzip(svsig)["status"] == "PASS"
    bad = tmp_path / "bad.svsig.gz"
    bad.write_text("not gzip", encoding="utf-8")
    assert validate_svsig_gzip(bad)["status"] == "FAIL"


def test_svsig_zero_empty_and_concatenated(tmp_path):
    zero = tmp_path / "zero.svsig.gz"
    zero.write_bytes(b"")
    assert validate_svsig_gzip(zero)["status"] == "FAIL"
    empty = tmp_path / "empty.svsig.gz"
    with gzip.open(empty, "wt"):
        pass
    assert validate_svsig_gzip(empty)["status"] == "WARN"
    concat = tmp_path / "concat.svsig.gz"
    with gzip.open(concat, "wb") as h:
        h.write(b"a\n")
    first = concat.read_bytes()
    with gzip.open(concat, "wb") as h:
        h.write(b"b\n")
    concat.write_bytes(first + concat.read_bytes())
    assert validate_svsig_gzip(concat)["status"] == "PASS"


def test_svsig_truncated(tmp_path):
    svsig = tmp_path / "trunc.svsig.gz"
    with gzip.open(svsig, "wb") as h:
        h.write(b"record\n")
    svsig.write_bytes(svsig.read_bytes()[:5])
    assert validate_svsig_gzip(svsig)["status"] == "FAIL"


def test_attempt_collision_rejected(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    assert main(["dry-run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"]) == 0
    assert main(["run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"]) == 1


def test_resume_missing_attempt_fails(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    assert main(["resume", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"]) == 1


def test_force_preserves_prior_attempt(tmp_path, tiny_reference, tiny_inputs, mock_tools, monkeypatch):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    assert main(["dry-run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"]) == 0

    def fake_run_stage(stage, cfg, sample, attempt_dir, *, resume, force):
        result = StageResult(stage["name"], "success", 0, None, None, "", "", 0.0)
        stage_dir = attempt_dir / "status" / stage["name"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        write_stage_status(result, stage_dir / "stage.status.json")
        return result, [], None

    monkeypatch.setattr("variant_analysis_harness.cli._run_stage", fake_run_stage)
    assert main(["run", "--force", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"]) == 0
    base = tmp_path / "results" / "test_project" / "SAMPLE_001"
    attempts = sorted(p.name for p in base.iterdir() if p.is_dir())
    assert "attempt_001" in attempts
    forced = [p for p in base.iterdir() if p.name.startswith("attempt_001_forced_")]
    assert forced and (forced[0] / "supersession.json").exists()


def test_concurrent_attempt_collision_message(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    attempt = tmp_path / "results" / "test_project" / "SAMPLE_001" / "attempt_001"
    attempt.mkdir(parents=True)
    assert main(["run", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "snv"]) == 1


def test_slurm_generates_full_workflow(tmp_path, tiny_reference, tiny_inputs, mock_tools):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", tiny_inputs["bam"])
    profile = tmp_path / "slurm.yaml"
    profile.write_text(
        "slurm:\n  time: \"01:00:00\"\n  cpus_per_task: 2\n  memory_gb: 4\n  extra_sbatch_options: []\n  environment_setup: []\n",
        encoding="utf-8",
    )
    assert main(["slurm-script", "--config", str(config), "--manifest", str(manifest), "--sample", "SAMPLE_001", "--analysis", "combined", "--slurm-profile", str(profile)]) == 0
    script = tmp_path / "results" / "test_project" / "SAMPLE_001" / "attempt_001" / "logs" / "slurm" / "SAMPLE_001.combined.sbatch"
    text = script.read_text(encoding="utf-8")
    assert "variant_analysis_harness.cli run" in text
    assert "--analysis combined" in text


def test_atomic_publish_requires_nonempty_temp(tmp_path):
    final = tmp_path / "out.vcf"
    temp = incomplete_path(final)
    temp.write_text("", encoding="utf-8")
    with pytest.raises(Exception):
        publish_atomically(temp, final)
    assert not final.exists()


def test_atomic_publish_success(tmp_path):
    final = tmp_path / "out.vcf"
    temp = incomplete_path(final)
    temp.write_text("data\n", encoding="utf-8")
    publish_atomically(temp, final)
    assert final.read_text(encoding="utf-8") == "data\n"
    assert not temp.exists()
