"""Technical DeepSomatic SNV/indel QC without clinical interpretation."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from variant_analysis_harness.somatic.deepsomatic.validation import _read_lines


def run_somatic_snv_qc(vcf: Path, *, validation_status: str = "PASS", caller_version: str | None = None, model_type: str | None = None) -> dict[str, Any]:
    lines = _read_lines(vcf)
    records = [line for line in lines if line and not line.startswith("#")]
    filter_counts: dict[str, int] = {}
    contig_counts: dict[str, int] = {}
    snv_count = indel_count = multiallelic_count = malformed = missing_gt = 0
    vafs: list[float] = []
    dps: list[int] = []
    ads: list[int] = []
    gqs: list[int] = []
    transitions = transversions = 0
    for line in records:
        parts = line.split("\t")
        if len(parts) < 8:
            malformed += 1
            continue
        chrom, _pos, _id, ref, alt, _qual, filt = parts[:7]
        contig_counts[chrom] = contig_counts.get(chrom, 0) + 1
        for value in filt.split(";"):
            filter_counts[value] = filter_counts.get(value, 0) + 1
        alts = alt.split(",")
        if len(alts) > 1:
            multiallelic_count += 1
        if len(ref) == 1 and all(len(a) == 1 for a in alts):
            snv_count += 1
            for a in alts:
                if (ref, a) in {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}:
                    transitions += 1
                else:
                    transversions += 1
        else:
            indel_count += 1
        if len(parts) >= 10:
            _collect_format(parts[8], parts[9], vafs, dps, ads, gqs)
        else:
            missing_gt += 1
    total = len(records)
    pass_records = filter_counts.get("PASS", 0)
    warnings = []
    if total and pass_records / total < 0.1:
        warnings.append("very low PASS fraction")
    return {
        "status": "WARN" if warnings else "PASS",
        "validation_status": validation_status,
        "total_records": total,
        "pass_records": pass_records,
        "filter_counts": dict(sorted(filter_counts.items())),
        "snv_count": snv_count,
        "indel_count": indel_count,
        "multiallelic_count": multiallelic_count,
        "titv": (transitions / transversions) if transversions else None,
        "vaf_mean": mean(vafs) if vafs else None,
        "depth_mean": mean(dps) if dps else None,
        "alt_depth_mean": mean(ads) if ads else None,
        "gq_mean": mean(gqs) if gqs else None,
        "per_contig_counts": dict(sorted(contig_counts.items())),
        "missing_genotype_count": missing_gt,
        "malformed_record_count": malformed,
        "caller_version": caller_version,
        "model_type": model_type,
        "output_size": vcf.stat().st_size if vcf.exists() else 0,
        "warnings": warnings,
    }


def write_qc_artifacts(qc: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "somatic_snv_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out_dir / "somatic_snv_qc.tsv").write_text("metric\tvalue\n" + "\n".join(f"{k}\t{json.dumps(v, default=str)}" for k, v in sorted(qc.items())) + "\n", encoding="utf-8")
    lines = ["# Somatic SNV/Indel Technical QC", "", f"Status: {qc['status']}", f"Total records: {qc['total_records']}", f"PASS records: {qc['pass_records']}", "", "Technical QC does not establish biological or clinical validity."]
    (out_dir / "somatic_snv_qc.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _collect_format(fmt: str, sample: str, vafs: list[float], dps: list[int], ads: list[int], gqs: list[int]) -> None:
    keys = fmt.split(":")
    values = sample.split(":")
    data = dict(zip(keys, values))
    if "VAF" in data:
        try:
            vafs.append(float(data["VAF"].split(",")[0]))
        except ValueError:
            pass
    if "DP" in data:
        try:
            dps.append(int(data["DP"]))
        except ValueError:
            pass
    if "AD" in data:
        try:
            ads.append(int(data["AD"].split(",")[-1]))
        except ValueError:
            pass
    if "GQ" in data:
        try:
            gqs.append(int(data["GQ"]))
        except ValueError:
            pass
