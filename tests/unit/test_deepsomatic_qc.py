from __future__ import annotations

from tests.unit.test_deepsomatic_output_validation import write_vcf
from variant_analysis_harness.somatic.deepsomatic.qc import run_somatic_snv_qc, write_qc_artifacts


def test_qc_counts_filters_snv_indel_and_format_values(tmp_path):
    vcf = tmp_path / "somatic.vcf.gz"
    write_vcf(
        vcf,
        filters=("PASS", "GERMLINE", "LowQual", "NoCall"),
        records=[
            "chr1\t1\t.\tA\tG\t.\tPASS\t.\tGT:DP:AD:VAF:GQ\t0/1:20:10,10:0.5:50",
            "chr1\t2\t.\tA\tAT\t.\tLowQual\t.\tGT:DP:AD\t0/1:12:8,4",
            "chr1\t3\t.\tC\tT,G\t.\tGERMLINE\t.\tGT\t0/1",
        ],
    )
    qc = run_somatic_snv_qc(vcf, caller_version="1.10.0", model_type="PACBIO")
    assert qc["total_records"] == 3
    assert qc["pass_records"] == 1
    assert qc["snv_count"] == 2
    assert qc["indel_count"] == 1
    assert qc["multiallelic_count"] == 1
    assert qc["vaf_mean"] == 0.5
    write_qc_artifacts(qc, tmp_path / "qc")
    assert (tmp_path / "qc" / "somatic_snv_qc.json").exists()
