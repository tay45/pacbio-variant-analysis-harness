"""Technical Severus somatic SV QC."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from variant_analysis_harness.somatic.severus.validation import _parse_info, _read_lines, _svtype_from_alt


def run_somatic_sv_qc(vcf: Path, *, validation_status: str = "PASS", caller_version: str | None = None) -> dict[str, Any]:
    records = [line for line in _read_lines(vcf) if line and not line.startswith("#")]
    svtype_counts: dict[str, int] = {}
    filter_counts: dict[str, int] = {}
    contig_counts: dict[str, int] = {}
    svlens: list[int] = []
    orphan_bnd = complex_count = interchromosomal = intrachromosomal = missing_support = missing_gt = 0
    for line in records:
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        chrom, _pos, _id, _ref, alt, _qual, filt, info = parts[:8]
        info_map = _parse_info(info)
        svtype = info_map.get("SVTYPE", _svtype_from_alt(alt))
        category = "TRA" if svtype == "BND" and "CHR2" in info_map and info_map["CHR2"] != chrom else svtype
        if category in {"CPX", "COMPLEX"}:
            complex_count += 1
        if category == "TRA":
            interchromosomal += 1
        else:
            intrachromosomal += 1
        svtype_counts[category] = svtype_counts.get(category, 0) + 1
        contig_counts[chrom] = contig_counts.get(chrom, 0) + 1
        for value in filt.split(";"):
            filter_counts[value] = filter_counts.get(value, 0) + 1
        if "SVLEN" in info_map:
            try:
                svlens.append(abs(int(info_map["SVLEN"].split(",")[0])))
            except ValueError:
                pass
        if svtype == "BND" and "MATEID=" not in info:
            orphan_bnd += 1
        if "SUPPORT" not in info and "RE" not in info:
            missing_support += 1
        if len(parts) < 10:
            missing_gt += 1
    total = len(records)
    warnings = []
    if total and svtype_counts.get("BND", 0) / total > 0.8:
        warnings.append("high BND fraction")
    if total and missing_support / total > 0.5:
        warnings.append("many records lack support annotations")
    qc = {
        "status": "WARN" if warnings else "PASS",
        "validation_status": validation_status,
        "total_sv_records": total,
        "pass_records": filter_counts.get("PASS", 0),
        "filtered_records": total - filter_counts.get("PASS", 0),
        "svtype_counts": dict(sorted(svtype_counts.items())),
        "filter_counts": dict(sorted(filter_counts.items())),
        "per_contig_counts": dict(sorted(contig_counts.items())),
        "orphan_bnd_count": orphan_bnd,
        "complex_event_count": complex_count,
        "interchromosomal_count": interchromosomal,
        "intrachromosomal_count": intrachromosomal,
        "svlen_mean": mean(svlens) if svlens else None,
        "missing_support_field_count": missing_support,
        "missing_genotype_count": missing_gt,
        "caller_version": caller_version,
        "output_size": vcf.stat().st_size if vcf.exists() else 0,
        "warnings": warnings,
    }
    return qc


def write_qc_artifacts(qc: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "somatic_sv_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out_dir / "somatic_sv_qc.tsv").write_text("metric\tvalue\n" + "\n".join(f"{k}\t{json.dumps(v, default=str)}" for k, v in sorted(qc.items())) + "\n", encoding="utf-8")
    (out_dir / "somatic_sv_qc.md").write_text("# Somatic SV Technical QC\n\nStatus: " + qc["status"] + "\n\nTechnical QC does not establish biological or clinical validity.\n", encoding="utf-8")
