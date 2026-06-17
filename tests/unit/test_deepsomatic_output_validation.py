from __future__ import annotations

import gzip
import os

from variant_analysis_harness.somatic.deepsomatic.validation import validate_deepsomatic_gvcf, validate_deepsomatic_vcf, write_validation_artifacts


def write_vcf(path, sample="T1", filters=("PASS", "GERMLINE"), records=None):
    records = records or ["chr1\t1\t.\tA\tG\t.\tPASS\t.\tGT:DP:AD:VAF:GQ\t0/1:20:10,10:0.5:50"]
    text = "\n".join([
        "##fileformat=VCFv4.2",
        "##contig=<ID=chr1,length=10>",
        *[f"##FILTER=<ID={f},Description=\"{f}\">" for f in filters],
        f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{sample}",
        *records,
    ]) + "\n"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)
    index = path.with_suffix(path.suffix + ".tbi")
    index.write_text("index\n", encoding="utf-8")
    os.utime(index, None)
    return index


def test_valid_vcf_and_gvcf(tmp_path):
    vcf = tmp_path / "somatic.vcf.gz"
    index = write_vcf(vcf)
    result = validate_deepsomatic_vcf(vcf, index_path=index, expected_samples=["T1"])
    assert result["status"] == "PASS"
    assert result["checksum"]
    assert validate_deepsomatic_gvcf(vcf, index_path=index, expected_samples=["T1"], enabled=True)["status"] == "PASS"
    assert validate_deepsomatic_gvcf(None, index_path=None, expected_samples=["T1"], enabled=False)["status"] == "NOT_EVALUATED"


def test_invalid_outputs(tmp_path):
    missing = validate_deepsomatic_vcf(tmp_path / "missing.vcf.gz", index_path=None, expected_samples=["T1"])
    assert missing["status"] == "FAIL"
    empty = tmp_path / "empty.vcf.gz"
    empty.write_bytes(b"")
    assert validate_deepsomatic_vcf(empty, index_path=None, expected_samples=["T1"])["status"] == "FAIL"
    wrong = tmp_path / "wrong.vcf.gz"
    index = write_vcf(wrong, sample="OTHER")
    assert validate_deepsomatic_vcf(wrong, index_path=index, expected_samples=["T1"])["status"] == "FAIL"
    unknown = tmp_path / "unknown.vcf.gz"
    index = write_vcf(unknown, filters=("PASS",), records=["chr1\t1\t.\tA\tG\t.\tNovel\t.\tGT\t0/1"])
    assert validate_deepsomatic_vcf(unknown, index_path=index, expected_samples=["T1"])["status"] == "WARN"
    assert validate_deepsomatic_vcf(unknown, index_path=index, expected_samples=["T1"], unknown_filter_policy="fail")["status"] == "FAIL"


def test_validation_artifacts(tmp_path):
    vcf = tmp_path / "somatic.vcf.gz"
    index = write_vcf(vcf)
    result = validate_deepsomatic_vcf(vcf, index_path=index, expected_samples=["T1"])
    write_validation_artifacts(result, tmp_path / "validation.json", tmp_path / "validation.md", tmp_path / "checksum.txt")
    assert (tmp_path / "validation.json").exists()
    assert (tmp_path / "checksum.txt").exists()
