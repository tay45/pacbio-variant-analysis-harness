"""Technical regional relationships between small variants and SVs."""

from __future__ import annotations

import json
import bisect
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


def build_relationships(
    small_variants: list[dict[str, Any]],
    svs: list[dict[str, Any]],
    *,
    window_bp: int = 10000,
    large_window_bp: int = 100000,
    include_filtered_small_variants: bool = False,
    include_filtered_structural_variants: bool = False,
) -> list[dict[str, Any]]:
    small_by_contig: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for small in small_variants:
        if not include_filtered_small_variants and small.get("filter") not in {"PASS", "."}:
            continue
        small_by_contig[small["chromosome"]].append(small)
    for values in small_by_contig.values():
        values.sort(key=lambda row: row["position"])
    small_index = {contig: ([row["position"] for row in values], values) for contig, values in small_by_contig.items()}
    relationships: list[dict[str, Any]] = []
    for sv in svs:
        if not include_filtered_structural_variants and sv.get("filter") not in {"PASS", "."}:
            continue
        chrom = sv.get("chromosome")
        local = _nearby_index(small_index.get(chrom), sv["start"], window_bp)
        for small in local:
            relationships.append(_relationship(small, sv, "near_sv_start", abs(small["position"] - sv["start"])))
        if sv.get("end") is not None:
            inside = _inside_index(small_index.get(chrom), sv["start"], sv["end"])
            for small in inside:
                relationships.append(_relationship(small, sv, "inside_sv_interval", 0))
            end_near = _nearby_index(small_index.get(chrom), sv["end"], window_bp)
            for small in end_near:
                relationships.append(_relationship(small, sv, "near_sv_end", abs(small["position"] - sv["end"])))
        if sv.get("remote_chromosome") and sv.get("remote_position") is not None:
            remote = _nearby_index(small_index.get(sv["remote_chromosome"]), sv["remote_position"], window_bp)
            for small in remote:
                relationships.append(_relationship(small, sv, "near_bnd_remote_breakpoint", abs(small["position"] - sv["remote_position"])))
        large = _nearby_index(small_index.get(chrom), sv["start"], large_window_bp)
        if large:
            relationships.append({"relationship_type": "small_variant_density_context", "sv_event_key": sv["source_record_key"], "small_variant_count": len(large), "contig": chrom, "window_bp": large_window_bp})
    return _dedupe(relationships)


def summarize_event_context(relationships: list[dict[str, Any]], svs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sv: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in relationships:
        if row.get("sv_event_key"):
            by_sv[row["sv_event_key"]].append(row)
    summaries = []
    for sv in svs:
        rows = by_sv.get(sv["source_record_key"], [])
        vafs = [r.get("small_variant_vaf") for r in rows if isinstance(r.get("small_variant_vaf"), float)]
        summaries.append(
            {
                "sv_event_key": sv["source_record_key"],
                "raw_svtype": sv.get("raw_svtype"),
                "normalized_category": sv.get("category"),
                "cluster_id": sv.get("cluster_id"),
                "local_breakpoint": f"{sv.get('chromosome')}:{sv.get('start')}",
                "remote_breakpoint": f"{sv.get('remote_chromosome')}:{sv.get('remote_position')}" if sv.get("remote_chromosome") else "",
                "small_variant_relationship_count": len(rows),
                "small_variant_median_vaf": median(vafs) if vafs else None,
                "missing_vaf_count": len([r for r in rows if r.get("small_variant_vaf") is None]),
                "sv_filter": sv.get("filter"),
                "tumor_support": sv.get("tumor_support"),
                "normal_support": sv.get("normal_support"),
            }
        )
    return summaries


def write_relationship_outputs(relationships: list[dict[str, Any]], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_variant_relationships.json").write_text(json.dumps(relationships, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    fields = ["relationship_type", "small_variant_key", "sv_event_key", "contig", "position", "distance_bp", "small_variant_vaf"]
    with (out_dir / "integrated_variant_relationships.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in relationships:
            writer.writerow({field: row.get(field, "") for field in fields})
    lines = ["# Integrated Variant Relationships", "", "Technical regional context only; no causality or biological confirmation is implied.", "", f"Relationship rows: {len(relationships)}"]
    (out_dir / "integrated_variant_relationships.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _inside(rows: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    lo, hi = sorted((start, end))
    return [row for row in rows if lo <= row["position"] <= hi]


def _nearby(rows: list[dict[str, Any]], pos: int, window: int) -> list[dict[str, Any]]:
    return [row for row in rows if abs(row["position"] - pos) <= window]


def _inside_index(index: tuple[list[int], list[dict[str, Any]]] | None, start: int, end: int) -> list[dict[str, Any]]:
    if index is None:
        return []
    positions, rows = index
    lo, hi = sorted((start, end))
    left = bisect.bisect_left(positions, lo)
    right = bisect.bisect_right(positions, hi)
    return rows[left:right]


def _nearby_index(index: tuple[list[int], list[dict[str, Any]]] | None, pos: int, window: int) -> list[dict[str, Any]]:
    if index is None:
        return []
    positions, rows = index
    left = bisect.bisect_left(positions, pos - window)
    right = bisect.bisect_right(positions, pos + window)
    return rows[left:right]


def _relationship(small: dict[str, Any], sv: dict[str, Any], rel_type: str, distance: int) -> dict[str, Any]:
    return {"relationship_type": rel_type, "small_variant_key": small["source_record_key"], "sv_event_key": sv["source_record_key"], "contig": small["chromosome"], "position": small["position"], "distance_bp": distance, "small_variant_vaf": small.get("vaf")}


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for row in rows:
        key = (row.get("relationship_type"), row.get("small_variant_key"), row.get("sv_event_key"), row.get("contig"), row.get("position"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out
