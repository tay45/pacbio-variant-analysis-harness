"""Minimal technical variant normalization for integrated reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_small_variant(record: dict[str, Any], *, caller: str = "deepsomatic", source_file: str = "") -> dict[str, Any]:
    ref = record.get("ref", "")
    alt = record.get("alt", "")
    alts = str(alt).split(",") if alt else []
    variant_class = "snv" if len(ref) == 1 and alts and all(len(a) == 1 for a in alts) else "indel"
    return {
        "chromosome": record.get("chrom") or record.get("chromosome"),
        "position": int(record.get("pos") or record.get("position")),
        "ref": ref,
        "alt": alt,
        "variant_class": variant_class,
        "filter": record.get("filter", "PASS"),
        "tumor_genotype": record.get("tumor_genotype"),
        "normal_genotype": record.get("normal_genotype"),
        "tumor_depth": _int_or_none(record.get("tumor_depth")),
        "normal_depth": _int_or_none(record.get("normal_depth")),
        "tumor_alt_depth": _int_or_none(record.get("tumor_alt_depth")),
        "normal_alt_depth": _int_or_none(record.get("normal_alt_depth")),
        "vaf": _float_or_none(record.get("vaf")),
        "caller": caller,
        "source_file": source_file,
        "source_record_key": record.get("id") or f"{record.get('chrom')}:{record.get('pos')}:{ref}:{alt}",
        "raw": dict(record),
    }


def normalize_sv(record: dict[str, Any], *, caller: str = "severus", source_file: str = "") -> dict[str, Any]:
    svtype = record.get("svtype") or record.get("SVTYPE") or "UNKNOWN"
    start = int(record.get("start") or record.get("pos") or 0)
    end = _int_or_none(record.get("end") or record.get("END"))
    category = "TRA" if svtype == "BND" and record.get("remote_chrom") and record.get("remote_chrom") != record.get("chrom") else svtype
    return {
        "chromosome": record.get("chrom") or record.get("chromosome"),
        "start": start,
        "end": end,
        "remote_chromosome": record.get("remote_chrom") or record.get("CHR2"),
        "remote_position": _int_or_none(record.get("remote_pos") or record.get("POS2")),
        "raw_svtype": svtype,
        "category": category,
        "raw_alt": record.get("alt") or record.get("ALT"),
        "filter": record.get("filter", "PASS"),
        "tumor_support": _int_or_none(record.get("tumor_support") or record.get("support")),
        "normal_support": _int_or_none(record.get("normal_support")),
        "event_id": record.get("event") or record.get("EVENT") or record.get("id"),
        "cluster_id": record.get("cluster") or record.get("cluster_id"),
        "mate_id": record.get("mateid") or record.get("MATEID"),
        "caller": caller,
        "source_file": source_file,
        "source_record_key": record.get("id") or f"{record.get('chrom')}:{start}:{svtype}",
        "raw": dict(record),
    }


def parse_small_variant_tsv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return [normalize_small_variant(row, source_file=str(path)) for row in csv.DictReader(handle, delimiter="\t")]


def parse_sv_tsv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return [normalize_sv(row, source_file=str(path)) for row in csv.DictReader(handle, delimiter="\t")]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None

