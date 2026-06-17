from __future__ import annotations

import gzip

from variant_analysis_harness.somatic.severus.qc import run_somatic_sv_qc, write_qc_artifacts


def test_somatic_sv_qc_counts_and_artifacts(tmp_path):
    vcf = tmp_path / "sv.vcf.gz"
    text = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tT1\tN1
chr1\t10\tdel\tN\t<DEL>\t60\tPASS\tSVTYPE=DEL;END=20;SVLEN=-10;SUPPORT=8\tGT\t0/1\t0/0
chr1\t30\tdup\tN\t<DUP>\t60\tPASS\tSVTYPE=DUP;END=60;SVLEN=30\tGT\t0/1\t0/0
chr1\t40\tbnd\tN\tN]chr2:80]\t60\tPASS\tSVTYPE=BND;CHR2=chr2\tGT\t0/1\t0/0
chr2\t80\tcpx\tN\t<COMPLEX>\t60\tLowSupport\tSVTYPE=COMPLEX;END=120;SVLEN=40\tGT\t0/1\t0/0
"""
    with gzip.open(vcf, "wt", encoding="utf-8") as handle:
        handle.write(text)
    qc = run_somatic_sv_qc(vcf, caller_version="1.0.0")
    assert qc["total_sv_records"] == 4
    assert qc["svtype_counts"]["DEL"] == 1
    assert qc["svtype_counts"]["DUP"] == 1
    assert qc["interchromosomal_count"] == 1
    assert qc["complex_event_count"] == 1
    assert qc["missing_support_field_count"] == 3
    write_qc_artifacts(qc, tmp_path / "qc")
    assert (tmp_path / "qc" / "somatic_sv_qc.tsv").exists()
