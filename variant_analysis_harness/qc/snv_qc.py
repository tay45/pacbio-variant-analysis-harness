"""Dependency-free germline SNV/indel VCF QC."""

from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from variant_analysis_harness.common.validation import require_readable_file


TRANSITIONS = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}


def run_snv_qc(vcf: Path, expected_sample: str | None, minimum_records: int = 1) -> dict[str, Any]:
    require_readable_file(vcf, "SNV VCF")
    metrics = _parse_small_vcf(vcf, expected_sample)
    checks = {
        "vcf_header_integrity": "PASS" if metrics["has_fileformat"] and metrics["has_chrom_header"] else "FAIL",
        "expected_sample": _sample_check(metrics["samples"], expected_sample),
        "minimum_records": "PASS" if metrics["total_records"] >= minimum_records else "WARN",
        "malformed_records": "PASS" if metrics["malformed_record_count"] == 0 else "FAIL",
    }
    status = "FAIL" if "FAIL" in checks.values() else ("WARN" if "WARN" in checks.values() else "PASS")
    return {"status": status, "checks": checks, "metrics": metrics}


def write_qc_outputs(qc: dict[str, Any], out_prefix: Path) -> None:
    out_prefix.with_suffix(".json").write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = [f"metric\tvalue", *[f"{k}\t{v}" for k, v in qc["metrics"].items() if not isinstance(v, (dict, list))]]
    out_prefix.with_suffix(".tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    out_prefix.with_suffix(".md").write_text(_qc_markdown("Germline SNV/indel QC", qc), encoding="utf-8")


def _parse_small_vcf(path: Path, expected_sample: str | None) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    metrics: dict[str, Any] = {
        "has_fileformat": False,
        "has_chrom_header": False,
        "samples": [],
        "total_records": 0,
        "pass_count": 0,
        "filtered_count": 0,
        "snv_count": 0,
        "indel_count": 0,
        "multi_allelic_count": 0,
        "transition_count": 0,
        "transversion_count": 0,
        "genotype_counts": {},
        "gq_summary": "NOT_EVALUATED",
        "depth_summary": "NOT_EVALUATED",
        "heterozygous_allele_balance_summary": "NOT_EVALUATED",
        "chromosome_distribution": {},
        "missing_genotype_count": 0,
        "indexed_vcf_available": path.with_suffix(path.suffix + ".tbi").exists(),
        "malformed_record_count": 0,
        "unexpected_contig_count": "NOT_EVALUATED",
    }
    genotype_counts: Counter[str] = Counter()
    chrom_counts: Counter[str] = Counter()
    gqs: list[int] = []
    dps: list[int] = []
    abs_: list[float] = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("##fileformat=VCF"):
                metrics["has_fileformat"] = True
                continue
            if line.startswith("#CHROM"):
                metrics["has_chrom_header"] = True
                parts = line.split("\t")
                metrics["samples"] = parts[9:] if len(parts) > 9 else []
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 8:
                metrics["malformed_record_count"] += 1
                continue
            chrom, _, _, ref, alt, _, flt = parts[:7]
            alts = alt.split(",")
            metrics["total_records"] += 1
            chrom_counts[chrom] += 1
            if flt == "PASS":
                metrics["pass_count"] += 1
            else:
                metrics["filtered_count"] += 1
            if len(alts) > 1:
                metrics["multi_allelic_count"] += 1
            for allele in alts:
                if len(ref) == 1 and len(allele) == 1:
                    metrics["snv_count"] += 1
                    if (ref.upper(), allele.upper()) in TRANSITIONS:
                        metrics["transition_count"] += 1
                    else:
                        metrics["transversion_count"] += 1
                else:
                    metrics["indel_count"] += 1
            if len(parts) > 9:
                fmt = parts[8].split(":")
                sample_index = 0
                if expected_sample and expected_sample in metrics["samples"]:
                    sample_index = metrics["samples"].index(expected_sample)
                sample_values = parts[9 + sample_index].split(":")
                values = dict(zip(fmt, sample_values))
                gt = values.get("GT", "./.")
                genotype_counts[gt] += 1
                if gt in {"./.", "."}:
                    metrics["missing_genotype_count"] += 1
                _append_int(values.get("GQ"), gqs)
                _append_int(values.get("DP"), dps)
                if "AD" in values and gt.startswith("0/1"):
                    depths = [int(x) for x in values["AD"].split(",") if x.isdigit()]
                    if len(depths) >= 2 and sum(depths) > 0:
                        abs_.append(depths[1] / sum(depths))
    metrics["genotype_counts"] = dict(genotype_counts)
    metrics["chromosome_distribution"] = dict(chrom_counts)
    metrics["titv_ratio"] = (
        metrics["transition_count"] / metrics["transversion_count"]
        if metrics["transversion_count"]
        else "NOT_EVALUATED"
    )
    metrics["gq_summary"] = _summary(gqs)
    metrics["depth_summary"] = _summary(dps)
    metrics["heterozygous_allele_balance_summary"] = _summary(abs_)
    return metrics


def _append_int(value: str | None, target: list[int]) -> None:
    if value and value.isdigit():
        target.append(int(value))


def _summary(values: list[float]) -> dict[str, float] | str:
    if not values:
        return "NOT_EVALUATED"
    return {"count": len(values), "mean": mean(values), "min": min(values), "max": max(values)}


def _sample_check(samples: list[str], expected: str | None) -> str:
    if not expected:
        return "NOT_EVALUATED"
    if not samples:
        return "WARN"
    return "PASS" if expected in samples else "FAIL"


def _qc_markdown(title: str, qc: dict[str, Any]) -> str:
    lines = [f"# {title}", "", f"Overall status: **{qc['status']}**", "", "## Checks"]
    lines.extend(f"- {k}: {v}" for k, v in qc["checks"].items())
    lines.append("")
    lines.append("## Metrics")
    lines.extend(f"- {k}: {v}" for k, v in qc["metrics"].items())
    return "\n".join(lines) + "\n"
