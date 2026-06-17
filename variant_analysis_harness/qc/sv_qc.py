"""Dependency-free germline SV VCF QC."""

from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.validation import require_readable_file


def run_sv_qc(vcf: Path, expected_sample: str | None, minimum_records: int = 1) -> dict[str, Any]:
    require_readable_file(vcf, "SV VCF")
    metrics = _parse_sv_vcf(vcf)
    checks = {
        "vcf_header_integrity": "PASS" if metrics["has_fileformat"] and metrics["has_chrom_header"] else "FAIL",
        "expected_sample": _sample_check(metrics["samples"], expected_sample),
        "minimum_records": "PASS" if metrics["total_sv_count"] >= minimum_records else "WARN",
        "malformed_records": "PASS" if metrics["malformed_record_count"] == 0 else "FAIL",
    }
    status = "FAIL" if "FAIL" in checks.values() else ("WARN" if "WARN" in checks.values() else "PASS")
    return {"status": status, "checks": checks, "metrics": metrics}


def write_sv_qc_outputs(qc: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sv_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = ["metric\tvalue", *[f"{k}\t{v}" for k, v in qc["metrics"].items() if not isinstance(v, (dict, list))]]
    (out_dir / "sv_qc.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (out_dir / "sv_qc.md").write_text(_qc_markdown("Germline SV QC", qc), encoding="utf-8")
    counts = qc["metrics"].get("counts_by_svtype", {})
    (out_dir / "svtype_counts.tsv").write_text(
        "svtype\tcount\n" + "".join(f"{k}\t{v}\n" for k, v in sorted(counts.items())),
        encoding="utf-8",
    )
    sizes = qc["metrics"].get("size_distribution_by_svtype", {})
    lines = ["svtype\tcount\tmin\tmax"]
    for svtype, values in sorted(sizes.items()):
        lines.append(f"{svtype}\t{values['count']}\t{values['min']}\t{values['max']}")
    (out_dir / "sv_size_distribution.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_sv_vcf(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    metrics: dict[str, Any] = {
        "has_fileformat": False,
        "has_chrom_header": False,
        "samples": [],
        "total_sv_count": 0,
        "pass_count": 0,
        "filtered_count": 0,
        "counts_by_svtype": {},
        "size_distribution_by_svtype": {},
        "chromosome_distribution": {},
        "genotype_distribution": {},
        "supporting_read_metrics": "NOT_EVALUATED",
        "support_fraction": "NOT_EVALUATED",
        "breakpoint_precision_confidence": "NOT_EVALUATED",
        "repeat_region_overlap_summary": "NOT_EVALUATED",
        "missing_field_counts": {},
        "malformed_record_count": 0,
        "unexpected_contig_count": "NOT_EVALUATED",
        "indexed_vcf_available": path.with_suffix(path.suffix + ".tbi").exists(),
    }
    svtypes: Counter[str] = Counter()
    chroms: Counter[str] = Counter()
    genotypes: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    sizes: dict[str, list[int]] = defaultdict(list)
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("##fileformat=VCF"):
                metrics["has_fileformat"] = True
            elif line.startswith("#CHROM"):
                metrics["has_chrom_header"] = True
                parts = line.split("\t")
                metrics["samples"] = parts[9:] if len(parts) > 9 else []
            elif line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) < 8:
                    metrics["malformed_record_count"] += 1
                    continue
                chrom, pos, _, _, _, flt, info = parts[0], parts[1], parts[2], parts[3], parts[4], parts[6], parts[7]
                metrics["total_sv_count"] += 1
                chroms[chrom] += 1
                if flt == "PASS":
                    metrics["pass_count"] += 1
                else:
                    metrics["filtered_count"] += 1
                info_map = _parse_info(info)
                svtype = info_map.get("SVTYPE", "MISSING")
                if svtype == "MISSING":
                    missing["SVTYPE"] += 1
                svtypes[svtype] += 1
                size = _sv_size(pos, info_map)
                if size is not None:
                    sizes[svtype].append(abs(size))
                else:
                    missing["SVLEN_OR_END"] += 1
                if len(parts) > 9:
                    fmt = parts[8].split(":")
                    values = parts[9].split(":")
                    gt = dict(zip(fmt, values)).get("GT", "./.")
                    genotypes[gt] += 1
    metrics["counts_by_svtype"] = dict(svtypes)
    metrics["chromosome_distribution"] = dict(chroms)
    metrics["genotype_distribution"] = dict(genotypes)
    metrics["missing_field_counts"] = dict(missing)
    metrics["size_distribution_by_svtype"] = {
        key: {"count": len(vals), "min": min(vals), "max": max(vals)}
        for key, vals in sizes.items()
        if vals
    }
    return metrics


def _parse_info(info: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in info.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


def _sv_size(pos: str, info: dict[str, str]) -> int | None:
    if "SVLEN" in info:
        try:
            return int(info["SVLEN"].split(",", 1)[0])
        except ValueError:
            return None
    if "END" in info:
        try:
            return int(info["END"]) - int(pos)
        except ValueError:
            return None
    return None


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
