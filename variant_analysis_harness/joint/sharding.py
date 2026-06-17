"""Deterministic genome sharding for joint genotyping."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JointShard:
    shard_index: int
    shard_id: str
    contig: str
    start: int
    end: int
    estimated_bases: int
    enabled: bool
    output_vcf: Path
    output_index: Path

    def to_row(self) -> dict[str, Any]:
        return {
            "shard_index": self.shard_index,
            "shard_id": self.shard_id,
            "contig": self.contig,
            "start": self.start,
            "end": self.end,
            "estimated_bases": self.estimated_bases,
            "enabled": str(self.enabled).lower(),
            "output_vcf": str(self.output_vcf),
            "output_index": str(self.output_index),
        }


def shards_from_contigs(
    contigs: list[dict[str, Any]],
    *,
    out_dir: Path,
    include_contigs: set[str] | None = None,
    exclude_contigs: set[str] | None = None,
    max_shards: int | None = None,
) -> list[JointShard]:
    selected = []
    for contig in contigs:
        name = str(contig["id"])
        if include_contigs and name not in include_contigs:
            continue
        if exclude_contigs and name in exclude_contigs:
            continue
        selected.append(contig)
    if max_shards is not None:
        selected = selected[:max_shards]
    shards: list[JointShard] = []
    for index, contig in enumerate(selected, start=1):
        name = str(contig["id"])
        length = int(contig.get("length") or 0)
        if length <= 0:
            continue
        shard_id = f"shard_{index:05d}_{_safe_contig(name)}"
        shard_dir = out_dir / "shards" / shard_id[:8] / shard_id
        output = shard_dir / f"{shard_id}.germline.vcf.gz"
        shards.append(JointShard(index, shard_id, name, 1, length, length, True, output, Path(str(output) + ".tbi")))
    return shards


def shards_from_interval_file(path: Path, *, out_dir: Path, reference_contigs: dict[str, int]) -> tuple[list[JointShard], list[str]]:
    errors: list[str] = []
    shards: list[JointShard] = []
    last: tuple[str, int] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 3:
                errors.append(f"line {index}: expected at least 3 BED columns")
                continue
            contig, start_text, end_text = fields[:3]
            try:
                start0 = int(start_text)
                end = int(end_text)
            except ValueError:
                errors.append(f"line {index}: coordinates must be integers")
                continue
            start = start0 + 1
            if contig not in reference_contigs:
                errors.append(f"line {index}: unknown contig {contig}")
            if start > end:
                errors.append(f"line {index}: interval is zero-length or negative")
            if end > reference_contigs.get(contig, end):
                errors.append(f"line {index}: interval exceeds reference length")
            if last and contig == last[0] and start <= last[1]:
                errors.append(f"line {index}: intervals overlap or are unsorted")
            last = (contig, end)
            shard_id = f"shard_{len(shards)+1:05d}_{_safe_contig(contig)}_{start}_{end}"
            output = out_dir / "shards" / shard_id[:8] / shard_id / f"{shard_id}.germline.vcf.gz"
            shards.append(JointShard(len(shards) + 1, shard_id, contig, start, end, end - start + 1, True, output, Path(str(output) + ".tbi")))
    return shards, errors


def write_shards(shards: list[JointShard], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["shard_index", "shard_id", "contig", "start", "end", "estimated_bases", "enabled", "output_vcf", "output_index"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames)
        writer.writeheader()
        for shard in shards:
            writer.writerow(shard.to_row())


def _safe_contig(contig: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in contig)

