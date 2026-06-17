from __future__ import annotations

from pathlib import Path

from tests.conftest import write_config, write_manifest
from variant_analysis_harness.common.config import load_run_config, tool_config
from variant_analysis_harness.common.manifest import load_manifest
from variant_analysis_harness.germline.alignment import build_pbmm2_align_command
from variant_analysis_harness.germline.deepvariant import build_deepvariant_command
from variant_analysis_harness.germline.pbsv import build_pbsv_call_command, build_pbsv_discover_command
from variant_analysis_harness.qc.snv_qc import run_snv_qc
from variant_analysis_harness.qc.sv_qc import run_sv_qc


def test_command_argv_paths_with_spaces(tmp_path, tiny_reference, tiny_inputs):
    spaced = tmp_path / "space dir"
    spaced.mkdir()
    bam = spaced / "sample aligned.bam"
    bam.write_bytes(b"BAM\1mock")
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    sample = load_manifest(write_manifest(tmp_path, "SAMPLE_001", "aligned_bam", bam))[0]
    cmd = build_pbmm2_align_command(sample, tool_config(cfg, "pbmm2"), Path(cfg["reference"]["fasta"]), bam, tmp_path / "out.bam", 2)
    assert "pbmm2" in cmd.argv[0]
    assert str(bam) in cmd.argv


def test_deepvariant_argv_no_hp_flag(tmp_path, tiny_reference, tiny_inputs):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    cmd = build_deepvariant_command(tool_config(cfg, "deepvariant"), Path(cfg["reference"]["fasta"]), tiny_inputs["bam"], tmp_path / "out.vcf", tmp_path / "out.g.vcf", tmp_path / "log")
    rendered = " ".join(cmd.argv)
    assert "--use_hp_information=true" not in rendered
    assert "--model_type=PACBIO" in cmd.argv


def test_pbsv_commands_include_ccs(tmp_path, tiny_reference, tiny_inputs):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    discover = build_pbsv_discover_command(tool_config(cfg, "pbsv"), tiny_inputs["bam"], tmp_path / "out.svsig.gz", tiny_reference["bed"])
    call = build_pbsv_call_command(tool_config(cfg, "pbsv"), tiny_reference["fasta"], tmp_path / "out.svsig.gz", tmp_path / "out.vcf")
    assert "--ccs" in discover.argv
    assert call.argv[1] == "call"


def test_snv_qc_counts(tmp_path):
    vcf = tmp_path / "snv.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t2\t.\tA\tG\t50\tPASS\t.\tGT:GQ:DP:AD\t0/1:60:20:10,10\n"
    )
    qc = run_snv_qc(vcf, "SAMPLE_001")
    assert qc["status"] == "PASS"
    assert qc["metrics"]["snv_count"] == 1


def test_sv_qc_counts(tmp_path):
    vcf = tmp_path / "sv.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE_001\nchr1\t3\t.\tN\t<DEL>\t50\tPASS\tSVTYPE=DEL;END=8;SVLEN=-5\tGT\t0/1\n"
    )
    qc = run_sv_qc(vcf, "SAMPLE_001")
    assert qc["status"] == "PASS"
    assert qc["metrics"]["counts_by_svtype"]["DEL"] == 1
