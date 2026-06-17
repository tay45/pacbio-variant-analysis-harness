from __future__ import annotations

import gzip
import os
import time
from pathlib import Path

from variant_analysis_harness.somatic.severus.validation import validate_severus_vcf, write_validation_artifacts


def write_vcf(path: Path, records: list[str], samples: str = "T1\tN1") -> Path:
    text = "\n".join(
        [
            "##fileformat=VCFv4.2",
            "##contig=<ID=chr1,length=1000>",
            "##contig=<ID=chr2,length=1000>",
            "##FILTER=<ID=LowSupport,Description=\"low support\">",
            f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{samples}",
            *records,
        ]
    ) + "\n"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)
    idx = Path(str(path) + ".tbi")
    idx.write_text("index\n", encoding="utf-8")
    return path


def test_valid_sv_vcf_with_bnd_and_complex(tmp_path):
    vcf = write_vcf(
        tmp_path / "sv.vcf.gz",
        [
            "chr1\t10\tdel1\tN\t<DEL>\t60\tPASS\tSVTYPE=DEL;END=20;SVLEN=-10;SUPPORT=8\tGT\t0/1\t0/0",
            "chr1\t30\tins1\tN\t<INS>\t60\tPASS\tSVTYPE=INS;SVLEN=5;SUPPORT=9\tGT\t0/1\t0/0",
            "chr1\t40\tbnd1\tN\tN]chr2:80]\t60\tPASS\tSVTYPE=BND;MATEID=bnd2;CHR2=chr2;SUPPORT=6\tGT\t0/1\t0/0",
            "chr2\t80\tbnd2\tN\tN]chr1:40]\t60\tPASS\tSVTYPE=BND;MATEID=bnd1;CHR2=chr1;SUPPORT=6\tGT\t0/1\t0/0",
            "chr2\t90\tcpx1\tN\t<CPX>\t60\tLowSupport\tSVTYPE=CPX;END=120;SVLEN=30\tGT\t0/1\t0/0",
        ],
    )
    result = validate_severus_vcf(vcf, index_path=Path(str(vcf) + ".tbi"), expected_samples=["T1", "N1"])
    assert result["status"] == "PASS"
    assert result["svtype_counts"]["BND"] == 2
    write_validation_artifacts(result, tmp_path / "validation")
    assert (tmp_path / "validation" / "severus_bnd_validation.tsv").exists()


def test_sample_sort_index_and_record_validation_failures(tmp_path):
    vcf = write_vcf(tmp_path / "bad.vcf.gz", ["chr2\t20\ta\tN\t<DEL>\t60\tPASS\tSVTYPE=DEL;END=10;SVLEN=x\tGT\t0/1\t0/0", "chr1\t10\tb\tN\t<FOO>\t60\tNope\tSVTYPE=FOO;END=bad\tGT\t0/1\t0/0"])
    result = validate_severus_vcf(vcf, index_path=Path(str(vcf) + ".tbi"), expected_samples=["X", "N1"], unknown_svtype_policy="fail", unknown_filter_policy="fail")
    assert result["status"] == "FAIL"
    assert any("samples" in error for error in result["errors"])
    assert any("not sorted" in error for error in result["errors"])
    missing_index = validate_severus_vcf(vcf, index_path=tmp_path / "no.tbi", expected_samples=["T1", "N1"])
    assert any("index is missing" in error for error in missing_index["errors"])
    stale = Path(str(vcf) + ".tbi")
    os.utime(stale, (time.time() - 100, time.time() - 100))
    assert any("stale" in error for error in validate_severus_vcf(vcf, index_path=stale, expected_samples=["T1", "N1"])["errors"])
