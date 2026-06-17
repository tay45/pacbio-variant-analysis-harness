"""Reference metadata helpers."""

from __future__ import annotations

from pathlib import Path


def read_fai_contigs(fai: Path) -> list[str]:
    contigs: list[str] = []
    with fai.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            contigs.append(line.split("\t", 1)[0])
    return contigs


def duplicate_contigs(contigs: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for contig in contigs:
        if contig in seen:
            duplicates.add(contig)
        seen.add(contig)
    return duplicates


def chromosome_style(contigs: list[str]) -> str:
    if not contigs:
        return "unknown"
    prefixed = sum(1 for c in contigs if c.startswith("chr"))
    if prefixed == len(contigs):
        return "chr"
    if prefixed == 0:
        return "no_chr"
    return "mixed"
