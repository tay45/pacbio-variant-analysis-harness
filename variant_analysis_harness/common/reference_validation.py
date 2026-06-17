"""Reference, FAI, dictionary, and BED validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_reference_bundle(reference: dict[str, str]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    fasta = Path(reference["fasta"])
    fai = Path(reference["fai"])
    dictionary = Path(reference["sequence_dictionary"]) if reference.get("sequence_dictionary") else None
    bed = Path(reference["tandem_repeats_bed"]) if reference.get("tandem_repeats_bed") else None
    bed_sort_policy = reference.get("tandem_repeats_sort_policy", "require_sorted")
    _check(checks, "fasta_exists", fasta.exists())
    _check(checks, "fasta_non_empty", fasta.exists() and fasta.stat().st_size > 0)
    _check(checks, "fai_exists", fai.exists())
    fai_result = parse_fai(fai) if fai.exists() else {"contigs": {}, "errors": ["missing fai"]}
    _check(checks, "fai_parses", not fai_result["errors"])
    _check(checks, "no_duplicate_contigs", not fai_result.get("duplicates"))
    dict_result = {"contigs": {}, "errors": ["not configured"]}
    dictionary_compatibility = {"status": "NOT_EVALUATED"}
    if dictionary:
        _check(checks, "dictionary_exists", dictionary.exists())
        dict_result = parse_sequence_dictionary(dictionary) if dictionary.exists() else dict_result
        _check(checks, "dictionary_parses", not dict_result["errors"])
        _check(checks, "dictionary_duplicate_contigs", not dict_result.get("duplicates"))
        dictionary_compatibility = compare_contig_sets(dict_result["contigs"], fai_result["contigs"], "dictionary", "fai")
        _check(checks, "dictionary_fai_names_compatible", dictionary_compatibility["status"] in {"exact_match", "compatible_subset"})
        _check(checks, "dictionary_fai_lengths_match", not dictionary_compatibility["length_mismatches"])
    else:
        checks.append({"name": "dictionary_exists", "status": "NOT_EVALUATED"})
    bed_result = {"rows": 0, "contigs": [], "errors": [], "sorted": None}
    if bed:
        _check(checks, "bed_exists", bed.exists())
        bed_result = parse_bed(bed, list(fai_result["contigs"])) if bed.exists() else {"rows": 0, "contigs": [], "errors": ["missing bed"], "sorted": None}
        _check(checks, "bed_non_empty", bed_result["rows"] > 0)
        _check(checks, "bed_parses", not bed_result["errors"])
        if bed_sort_policy == "do_not_evaluate":
            checks.append({"name": "bed_sorted", "status": "NOT_EVALUATED"})
        else:
            _check(checks, "bed_sorted", bool(bed_result["sorted"]), warn=bed_sort_policy == "warn_if_unsorted")
        _check(checks, "bed_reference_contigs_compatible", set(bed_result["contigs"]).issubset(set(fai_result["contigs"])))
    else:
        checks.append({"name": "bed_exists", "status": "NOT_EVALUATED"})
    style = chromosome_style(list(fai_result["contigs"]))
    status = _overall(checks)
    return {
        "status": status,
        "reference_id": reference.get("id"),
        "build": reference.get("build"),
        "chromosome_style": style,
        "fai": fai_result,
        "dictionary": dict_result,
        "dictionary_compatibility": dictionary_compatibility,
        "bed": bed_result,
        "checks": checks,
    }


def write_reference_validation(result: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [f"# Reference Validation", "", f"Status: **{result['status']}**", "", "## Checks"]
    lines.extend(f"- {c['name']}: {c['status']}" for c in result["checks"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_fai(path: Path) -> dict[str, Any]:
    contigs: dict[str, int] = {}
    duplicates: list[str] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        parts = line.split("\t")
        if len(parts) < 5:
            errors.append(f"line {number}: expected at least 5 columns")
            continue
        name = parts[0]
        try:
            length = int(parts[1])
        except ValueError:
            errors.append(f"line {number}: invalid length")
            continue
        if length <= 0:
            errors.append(f"line {number}: nonpositive length")
        if name in contigs:
            duplicates.append(name)
        contigs[name] = length
    return {"contigs": contigs, "duplicates": duplicates, "errors": errors}


def parse_sequence_dictionary(path: Path) -> dict[str, Any]:
    contigs: dict[str, int] = {}
    duplicates: list[str] = []
    errors: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("@SQ"):
            continue
        fields = dict(field.split(":", 1) for field in line.split("\t")[1:] if ":" in field)
        if "SN" not in fields or "LN" not in fields:
            errors.append("missing SN or LN")
            continue
        try:
            length = int(fields["LN"])
            if length <= 0:
                errors.append(f"nonpositive LN for {fields['SN']}")
            if fields["SN"] in contigs:
                duplicates.append(fields["SN"])
            contigs[fields["SN"]] = length
        except ValueError:
            errors.append(f"invalid LN for {fields['SN']}")
    if not contigs:
        errors.append("no @SQ records")
    return {"contigs": contigs, "duplicates": duplicates, "errors": errors}


def parse_bed(path: Path, reference_order: list[str] | None = None) -> dict[str, Any]:
    contigs: list[str] = []
    errors: list[str] = []
    overlaps: list[str] = []
    unknown_contigs: list[str] = []
    order_index = {name: i for i, name in enumerate(reference_order or [])}
    last: tuple[int, str, int, int] | None = None
    first_unsorted: dict[str, Any] | None = None
    sorted_ok = True
    rows = 0
    previous_by_contig: dict[str, tuple[int, int]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            errors.append(f"line {number}: expected at least 3 columns")
            continue
        chrom = parts[0]
        try:
            start = int(parts[1])
            end = int(parts[2])
        except ValueError:
            errors.append(f"line {number}: invalid coordinates")
            continue
        if start < 0 or end <= start:
            errors.append(f"line {number}: invalid interval")
        if reference_order is not None and chrom not in order_index:
            unknown_contigs.append(chrom)
        current = (order_index.get(chrom, 10**12), chrom, start, end)
        if last and (current[0] < last[0] or (current[0] == last[0] and start < last[2])):
            sorted_ok = False
            if first_unsorted is None:
                first_unsorted = {
                    "line": number,
                    "previous_record": {"contig": last[1], "start": last[2], "end": last[3]},
                    "current_record": {"contig": chrom, "start": start, "end": end},
                    "expected_reference_order": reference_order,
                }
        if chrom in previous_by_contig and start < previous_by_contig[chrom][1]:
            overlaps.append(f"line {number}: overlaps previous interval on {chrom}")
        previous_by_contig[chrom] = (start, end)
        last = current
        contigs.append(chrom)
        rows += 1
    errors.extend(f"unknown contig {c}" for c in sorted(set(unknown_contigs)))
    return {
        "rows": rows,
        "contigs": sorted(set(contigs)),
        "errors": errors,
        "sorted": sorted_ok,
        "first_unsorted": first_unsorted,
        "overlaps": overlaps,
    }


def compare_contig_sets(left: dict[str, int], right: dict[str, int], left_label: str, right_label: str) -> dict[str, Any]:
    missing_from_right = sorted(set(left) - set(right))
    missing_from_left = sorted(set(right) - set(left))
    length_mismatches = [
        {left_label: name, f"{left_label}_length": left[name], f"{right_label}_length": right[name]}
        for name in sorted(set(left) & set(right))
        if left[name] != right[name]
    ]
    if missing_from_right or length_mismatches:
        status = "incompatible_mismatch"
    elif missing_from_left:
        status = "compatible_subset"
    else:
        status = "exact_match"
    return {
        "status": status,
        f"missing_from_{right_label}": missing_from_right,
        f"missing_from_{left_label}": missing_from_left,
        "length_mismatches": length_mismatches,
    }


def chromosome_style(contigs: list[str]) -> str:
    if not contigs:
        return "unknown"
    prefixed = sum(1 for c in contigs if c.startswith("chr"))
    if prefixed == len(contigs):
        return "chr"
    if prefixed == 0:
        return "no_chr"
    return "mixed"


def _check(checks: list[dict[str, str]], name: str, ok: bool, warn: bool = False) -> None:
    checks.append({"name": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL")})


def _overall(checks: list[dict[str, str]]) -> str:
    states = {c["status"] for c in checks}
    if "FAIL" in states:
        return "FAIL"
    if "WARN" in states:
        return "WARN"
    return "PASS"
