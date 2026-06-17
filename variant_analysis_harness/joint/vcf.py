"""Small VCF/gVCF helpers for joint-genotyping planning tests."""

from __future__ import annotations

import gzip
import re
from pathlib import Path
from typing import Any

CONTIG_RE = re.compile(r"##contig=<([^>]+)>")


def read_vcf_header(path: Path, *, max_lines: int = 10000) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    lines: list[str] = []
    samples: list[str] = []
    contigs: list[dict[str, Any]] = []
    has_fileformat = False
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if line.startswith("##fileformat="):
                has_fileformat = True
            if line.startswith("##contig="):
                parsed = _parse_contig_line(line)
                if parsed:
                    contigs.append(parsed)
            if line.startswith("#CHROM"):
                fields = line.split("\t")
                samples = fields[9:]
                lines.append(line)
                break
            lines.append(line)
            if line_number >= max_lines:
                break
    return {
        "has_fileformat": has_fileformat,
        "samples": samples,
        "sample_count": len(samples),
        "contigs": contigs,
        "header_lines": lines,
    }


def quick_record_scan(path: Path, *, limit: int = 1000) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    last: tuple[str, int] | None = None
    count = 0
    errors: list[str] = []
    contig_counts: dict[str, int] = {}
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 8:
                errors.append("record has fewer than 8 columns")
                continue
            try:
                pos = int(fields[1])
            except ValueError:
                errors.append("record POS is not an integer")
                continue
            key = (fields[0], pos)
            if last and key[0] == last[0] and key[1] < last[1]:
                errors.append("records are not sorted within contig")
            last = key
            contig_counts[fields[0]] = contig_counts.get(fields[0], 0) + 1
            count += 1
            if count >= limit:
                break
    return {"records_scanned": count, "errors": errors, "contig_counts": contig_counts}


def detect_vcf_index(path: Path) -> Path | None:
    candidates = [Path(str(path) + ".tbi"), Path(str(path) + ".csi")]
    for candidate in candidates:
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def _parse_contig_line(line: str) -> dict[str, Any] | None:
    match = CONTIG_RE.match(line)
    if not match:
        return None
    values: dict[str, Any] = {}
    for part in match.group(1).split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key] = int(value) if key == "length" and value.isdigit() else value
    if "ID" not in values:
        return None
    return {"id": values["ID"], "length": values.get("length")}

