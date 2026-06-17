"""Technical cohort SNV/indel QC for joint VCFs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from variant_analysis_harness.joint.vcf import read_vcf_header


def run_joint_variant_qc(vcf: Path, *, expected_samples: list[str] | None = None) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "total_samples": 0,
        "total_variants": 0,
        "snv_count": 0,
        "indel_count": 0,
        "multiallelic_count": 0,
        "pass_count": 0,
        "filtered_count": 0,
        "titv": None,
        "heterozygous_count": 0,
        "homozygous_alt_count": 0,
        "missing_genotype_count": 0,
        "singleton_count": 0,
        "doubleton_count": 0,
        "per_contig_counts": {},
        "per_sample_genotype_counts": {},
        "warnings": [],
    }
    if not vcf.exists():
        metrics["status"] = "FAIL"
        metrics["warnings"].append("VCF does not exist")
        return metrics
    header = read_vcf_header(vcf)
    samples = header["samples"]
    metrics["total_samples"] = len(samples)
    if expected_samples and samples != expected_samples:
        metrics["warnings"].append("unexpected sample order or identities")
    for sample in samples:
        metrics["per_sample_genotype_counts"][sample] = {"het": 0, "hom_alt": 0, "missing": 0}
    transitions = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}
    ti = tv = 0
    with _open_text(vcf) as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10:
                continue
            ref, alt, filt = fields[3], fields[4], fields[6]
            alts = alt.split(",")
            metrics["total_variants"] += 1
            metrics["per_contig_counts"][fields[0]] = metrics["per_contig_counts"].get(fields[0], 0) + 1
            if len(alts) > 1:
                metrics["multiallelic_count"] += 1
            if filt == "PASS":
                metrics["pass_count"] += 1
            else:
                metrics["filtered_count"] += 1
            if len(ref) == 1 and all(len(a) == 1 and not a.startswith("<") for a in alts):
                metrics["snv_count"] += 1
                for a in alts:
                    if (ref, a) in transitions:
                        ti += 1
                    else:
                        tv += 1
            else:
                metrics["indel_count"] += 1
            alt_allele_count = 0
            for sample, value in zip(samples, fields[9:]):
                gt = value.split(":", 1)[0]
                if gt in {"./.", "."}:
                    metrics["missing_genotype_count"] += 1
                    metrics["per_sample_genotype_counts"][sample]["missing"] += 1
                elif gt in {"0/1", "1/0", "0|1", "1|0"}:
                    alt_allele_count += 1
                    metrics["heterozygous_count"] += 1
                    metrics["per_sample_genotype_counts"][sample]["het"] += 1
                elif gt in {"1/1", "1|1"}:
                    alt_allele_count += 2
                    metrics["homozygous_alt_count"] += 1
                    metrics["per_sample_genotype_counts"][sample]["hom_alt"] += 1
            if alt_allele_count == 1:
                metrics["singleton_count"] += 1
            if alt_allele_count == 2:
                metrics["doubleton_count"] += 1
    metrics["titv"] = round(ti / tv, 3) if tv else None
    metrics["variant_call_rate"] = _rate(metrics["heterozygous_count"] + metrics["homozygous_alt_count"], max(1, metrics["total_variants"] * max(1, metrics["total_samples"])))
    metrics["status"] = "PASS"
    return metrics


def write_joint_qc(metrics: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cohort_variant_qc.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "cohort_variant_qc.tsv").write_text("metric\tvalue\n" + "\n".join(f"{k}\t{v}" for k, v in metrics.items() if not isinstance(v, dict)) + "\n", encoding="utf-8")
    sample_lines = ["sample_id\thet\thom_alt\tmissing"]
    for sample, counts in metrics.get("per_sample_genotype_counts", {}).items():
        sample_lines.append(f"{sample}\t{counts['het']}\t{counts['hom_alt']}\t{counts['missing']}")
    (out_dir / "cohort_sample_qc.tsv").write_text("\n".join(sample_lines) + "\n", encoding="utf-8")
    md = ["# Cohort Variant QC", "", "Technical QC only; not biological or clinical validation.", "", f"Total samples: {metrics.get('total_samples')}", f"Total variants: {metrics.get('total_variants')}"]
    (out_dir / "cohort_variant_qc.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _open_text(path: Path):
    import gzip

    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz" else path.open("r", encoding="utf-8")


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4)

