"""Planning-only cohort storage estimation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.cohort.manifest import CohortSample

DEFAULT_FACTORS = {
    "aligned_bam": 1.2,
    "bam_index": 0.02,
    "deepvariant_intermediates": 2.0,
    "vcf_gvcf": 0.05,
    "pbsv_signatures": 0.15,
    "sv_vcf": 0.01,
    "logs_qc_reports": 0.01,
    "temporary_scratch": 2.5,
}


def estimate_storage(samples: list[CohortSample], factors: dict[str, float] | None = None) -> dict[str, Any]:
    factors = {**DEFAULT_FACTORS, **(factors or {})}
    rows = []
    totals = {key: 0.0 for key in factors}
    for sample in samples:
        input_gb = _file_size_gb(sample.input_path)
        if input_gb == 0:
            input_gb = 1.0
        categories = {
            "aligned_bam": input_gb if sample.input_type == "aligned_bam" else input_gb * factors["aligned_bam"],
            "bam_index": input_gb * factors["bam_index"],
            "deepvariant_intermediates": input_gb * factors["deepvariant_intermediates"] if sample.analysis in {"snv", "combined"} else 0.0,
            "vcf_gvcf": input_gb * factors["vcf_gvcf"] if sample.analysis in {"snv", "combined"} else 0.0,
            "pbsv_signatures": input_gb * factors["pbsv_signatures"] if sample.analysis in {"sv", "combined"} else 0.0,
            "sv_vcf": input_gb * factors["sv_vcf"] if sample.analysis in {"sv", "combined"} else 0.0,
            "logs_qc_reports": input_gb * factors["logs_qc_reports"],
            "temporary_scratch": input_gb * factors["temporary_scratch"],
        }
        for key, value in categories.items():
            totals[key] += value
        rows.append({"sample_id": sample.sample_id, **{k: round(v, 3) for k, v in categories.items()}})
    return {
        "assumptions": "Planning approximation only; real usage depends on coverage, chemistry, tool versions, and retention policy.",
        "per_sample": rows,
        "cohort_totals_gb": {k: round(v, 3) for k, v in totals.items()},
        "temporary_peak_gb": round(totals["temporary_scratch"], 3),
        "final_retained_gb": round(sum(v for k, v in totals.items() if k != "temporary_scratch"), 3),
    }


def write_storage_estimate(estimate: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "storage_estimate.json").write_text(json.dumps(estimate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    headers = ["sample_id", "aligned_bam", "bam_index", "deepvariant_intermediates", "vcf_gvcf", "pbsv_signatures", "sv_vcf", "logs_qc_reports", "temporary_scratch"]
    lines = ["\t".join(headers)]
    for row in estimate["per_sample"]:
        lines.append("\t".join(str(row.get(h, "")) for h in headers))
    (out_dir / "storage_estimate.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Storage Estimate", "", estimate["assumptions"], "", "## Cohort Totals GB"]
    for key, value in estimate["cohort_totals_gb"].items():
        md.append(f"- {key}: {value}")
    (out_dir / "storage_estimate.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _file_size_gb(path: Path) -> float:
    try:
        return path.stat().st_size / (1024**3)
    except OSError:
        return 0.0

