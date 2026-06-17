"""samtools-backed BAM validation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.reference_validation import parse_fai


def validate_bam_with_samtools(
    bam: Path,
    *,
    expected_sample: str,
    reference_fai: Path | None = None,
    require_pbi: bool = False,
    samtools: str = "samtools",
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    header_text = ""
    _check(checks, "exists", bam.exists())
    _check(checks, "non_empty", bam.exists() and bam.stat().st_size > 0)
    index_info = detect_bam_index(bam)
    index = index_info["selected"]
    checks.extend(index_info["checks"])
    if index and index.exists() and bam.exists():
        _check(checks, "index_not_stale", index.stat().st_mtime_ns >= bam.stat().st_mtime_ns, warn=True)
    quick = _run([samtools, "quickcheck", str(bam)])
    _check(checks, "samtools_quickcheck", quick["exit_code"] == 0)
    header = _run([samtools, "view", "-H", str(bam)])
    if header["exit_code"] == 0:
        header_text = header["stdout"]
    _check(checks, "bam_header_readable", header["exit_code"] == 0)
    parsed = parse_bam_header(header_text)
    _check(checks, "sq_contigs_exist", bool(parsed["contigs"]))
    _check(checks, "duplicate_bam_contigs", not parsed["duplicate_contigs"])
    _check(checks, "rg_records_exist", bool(parsed["read_groups"]))
    sample_names = sorted({rg.get("SM", "") for rg in parsed["read_groups"] if rg.get("SM")})
    _check(checks, "read_group_sample_matches", expected_sample in sample_names if sample_names else False)
    _check(checks, "duplicate_sample_names", len(sample_names) <= 1, warn=True)
    _check(checks, "coordinate_sort_order", parsed.get("sort_order") in {"coordinate", None}, warn=True)
    compatibility: dict[str, Any] = {"status": "NOT_EVALUATED"}
    if reference_fai and reference_fai.exists() and parsed["contigs"]:
        compatibility = compare_bam_reference_contigs(parsed["contigs"], parse_fai(reference_fai))
        _check(checks, "bam_reference_contigs_compatible", compatibility["status"] in {"exact_match", "compatible_subset"})
        _check(checks, "bam_reference_contig_lengths_match", not compatibility["length_mismatches"])
    else:
        checks.append({"name": "bam_reference_contigs_compatible", "status": "NOT_EVALUATED"})
    pbi = bam.with_suffix(bam.suffix + ".pbi")
    if require_pbi:
        _check(checks, "pacbio_pbi_exists", pbi.exists())
    else:
        checks.append({"name": "pacbio_pbi_exists", "status": "NOT_EVALUATED"})
    status = _overall(checks)
    return {
        "status": status,
        "bam": str(bam),
        "index": str(index) if index else None,
        "index_type": index_info["index_type"],
        "index_candidates": [str(p) for p in index_info["candidates"]],
        "sample_names": sample_names,
        "contigs": parsed["contigs"],
        "duplicate_contigs": parsed["duplicate_contigs"],
        "contig_compatibility": compatibility,
        "sort_order": parsed.get("sort_order"),
        "checks": checks,
        "raw": {"quickcheck": quick, "header_stderr": header["stderr"]},
    }


def write_bam_validation(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_bam_header(text: str) -> dict[str, Any]:
    contigs: dict[str, int] = {}
    duplicate_contigs: list[str] = []
    read_groups: list[dict[str, str]] = []
    sort_order: str | None = None
    for line in text.splitlines():
        fields = line.split("\t")
        if not fields:
            continue
        if fields[0] == "@HD":
            for field in fields[1:]:
                if field.startswith("SO:"):
                    sort_order = field[3:]
        if fields[0] == "@SQ":
            name = None
            length = None
            for field in fields[1:]:
                if field.startswith("SN:"):
                    name = field[3:]
                elif field.startswith("LN:"):
                    try:
                        length = int(field[3:])
                    except ValueError:
                        length = None
            if name and length:
                if name in contigs:
                    duplicate_contigs.append(name)
                contigs[name] = length
        if fields[0] == "@RG":
            rg: dict[str, str] = {}
            for field in fields[1:]:
                if ":" in field:
                    key, value = field.split(":", 1)
                    rg[key] = value
            read_groups.append(rg)
    return {"contigs": contigs, "duplicate_contigs": duplicate_contigs, "read_groups": read_groups, "sort_order": sort_order}


def detect_bam_index(bam: Path) -> dict[str, Any]:
    candidates = [
        (Path(str(bam) + ".bai"), "BAI"),
        (bam.with_suffix(".bai"), "BAI"),
        (Path(str(bam) + ".csi"), "CSI"),
        (bam.with_suffix(".csi"), "CSI"),
    ]
    existing: list[tuple[Path, str]] = []
    for path, index_type in candidates:
        if path.exists() and all(path != prior for prior, _ in existing):
            existing.append((path, index_type))
    checks: list[dict[str, Any]] = []
    _check(checks, "index_exists", bool(existing))
    if not existing:
        return {"selected": None, "index_type": None, "candidates": [], "checks": checks}
    types = {kind for _, kind in existing}
    _check(checks, "index_ambiguous", len(types) <= 1, warn=False)
    selected, index_type = existing[0]
    if len(types) > 1:
        # Prefer the deterministic first candidate but mark validation failed.
        selected, index_type = existing[0]
    _check(checks, "index_non_empty", selected.stat().st_size > 0)
    return {
        "selected": selected,
        "index_type": index_type,
        "candidates": [path for path, _ in existing],
        "checks": checks,
    }


def compare_bam_reference_contigs(bam_contigs: dict[str, int], fai_result: dict[str, Any]) -> dict[str, Any]:
    ref_contigs: dict[str, int] = fai_result.get("contigs", {})
    missing_from_reference = sorted(set(bam_contigs) - set(ref_contigs))
    missing_from_bam = sorted(set(ref_contigs) - set(bam_contigs))
    length_mismatches = [
        {"contig": name, "bam_length": bam_contigs[name], "reference_length": ref_contigs[name]}
        for name in sorted(set(bam_contigs) & set(ref_contigs))
        if bam_contigs[name] != ref_contigs[name]
    ]
    chr_mismatch = _chr_style(set(bam_contigs)) != _chr_style(set(ref_contigs))
    if missing_from_reference or length_mismatches:
        status = "incompatible_mismatch"
    elif not missing_from_bam:
        status = "exact_match"
    else:
        status = "compatible_subset"
    return {
        "status": status,
        "missing_from_reference": missing_from_reference,
        "missing_from_bam": missing_from_bam,
        "length_mismatches": length_mismatches,
        "chromosome_naming_mismatch": chr_mismatch,
    }


def _chr_style(contigs: set[str]) -> str:
    if not contigs:
        return "unknown"
    prefixed = sum(1 for c in contigs if c.startswith("chr"))
    if prefixed == len(contigs):
        return "chr"
    if prefixed == 0:
        return "no_chr"
    return "mixed"


def _run(argv: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
    except Exception as exc:
        return {"exit_code": None, "stdout": "", "stderr": str(exc)}
    return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _check(checks: list[dict[str, Any]], name: str, ok: bool, warn: bool = False) -> None:
    checks.append({"name": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL")})


def _overall(checks: list[dict[str, Any]]) -> str:
    states = {c["status"] for c in checks}
    if "FAIL" in states:
        return "FAIL"
    if "WARN" in states:
        return "WARN"
    return "PASS"
