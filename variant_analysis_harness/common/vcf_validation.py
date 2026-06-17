"""VCF, gVCF, and svsig integrity validation."""

from __future__ import annotations

import gzip
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.reference_validation import parse_fai


def validate_variant_vcf(
    vcf: Path,
    *,
    expected_sample: str | None,
    reference_fai: Path | None = None,
    require_index: bool = False,
    expect_gvcf_blocks: bool = False,
    bcftools: str | None = None,
    tabix: str | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    _check(checks, "exists", vcf.exists())
    _check(checks, "non_empty", vcf.exists() and vcf.stat().st_size > 0)
    result = _parse_vcf(vcf) if vcf.exists() and vcf.stat().st_size > 0 else {"errors": ["missing"], "samples": [], "contigs": [], "records": 0, "reference_blocks": 0}
    _check(checks, "valid_header", result.get("has_fileformat", False) and result.get("has_chrom_header", False))
    _check(checks, "records_parse", not result["errors"])
    if expected_sample:
        _check(checks, "expected_sample", expected_sample in result["samples"])
    if reference_fai and reference_fai.exists():
        ref_contigs = set(parse_fai(reference_fai)["contigs"])
        _check(checks, "reference_contigs_compatible", set(result["contigs"]).issubset(ref_contigs))
    else:
        checks.append({"name": "reference_contigs_compatible", "status": "NOT_EVALUATED"})
    index = _vcf_index(vcf)
    if require_index:
        _check(checks, "index_exists", index is not None and index.exists())
        _check(checks, "index_non_empty", index is not None and index.exists() and index.stat().st_size > 0)
    else:
        checks.append({"name": "index_exists", "status": "NOT_EVALUATED"})
    if expect_gvcf_blocks:
        _check(checks, "gvcf_reference_blocks", result.get("reference_blocks", 0) > 0)
        _check(checks, "gvcf_end_fields", not result.get("gvcf_end_errors"))
    external = _external_vcf_checks(vcf, bcftools=bcftools, tabix=tabix, index=_vcf_index(vcf))
    checks.extend(external["checks"])
    status = _overall(checks)
    return {"status": status, "vcf": str(vcf), "checks": checks, "metrics": result, "external_validation": external}


def validate_svsig_gzip(path: Path) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    _check(checks, "exists", path.exists())
    _check(checks, "non_empty", path.exists() and path.stat().st_size > 0)
    readable = False
    lines = 0
    uncompressed_bytes = 0
    error = None
    if path.exists() and path.stat().st_size > 0:
        try:
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    lines += 1
                    uncompressed_bytes += len(line.encode("utf-8"))
            readable = True
        except Exception as exc:
            readable = False
            error = str(exc)
    _check(checks, "gzip_integrity", readable)
    _check(checks, "non_empty_payload", uncompressed_bytes > 0, warn=True)
    return {
        "status": _overall(checks),
        "svsig": str(path),
        "checks": checks,
        "record_count": lines,
        "uncompressed_byte_count": uncompressed_bytes,
        "decompression_error": error,
    }


def write_validation_result(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_vcf(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    errors: list[str] = []
    samples: list[str] = []
    contigs: list[str] = []
    records = 0
    pass_count = 0
    filtered_count = 0
    reference_blocks = 0
    variant_records = 0
    symbolic_allele_count = 0
    multiallelic_count = 0
    svtype_counts: dict[str, int] = {}
    bnd_records = 0
    malformed_bnd_records = 0
    gvcf_end_errors: list[str] = []
    has_fileformat = False
    has_chrom_header = False
    try:
        with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                line = line.rstrip("\n")
                if line.startswith("##fileformat=VCF"):
                    has_fileformat = True
                elif line.startswith("#CHROM"):
                    has_chrom_header = True
                    parts = line.split("\t")
                    samples = parts[9:] if len(parts) > 9 else []
                elif line and not line.startswith("#"):
                    parts = line.split("\t")
                    if len(parts) < 8:
                        errors.append(f"line {number}: fewer than 8 columns")
                        continue
                    records += 1
                    contigs.append(parts[0])
                    if parts[6] == "PASS":
                        pass_count += 1
                    else:
                        filtered_count += 1
                    info_map = _parse_info(parts[7], errors, number)
                    if parts[4] in {"<*>", "<NON_REF>"} or "<NON_REF>" in parts[4]:
                        reference_blocks += 1
                        if "END" not in info_map:
                            gvcf_end_errors.append(f"line {number}: gVCF block missing END")
                    else:
                        variant_records += 1
                    if "," in parts[4]:
                        multiallelic_count += 1
                    if parts[4].startswith("<") and parts[4].endswith(">"):
                        symbolic_allele_count += 1
                    svtype = info_map.get("SVTYPE")
                    if svtype:
                        svtype_counts[svtype] = svtype_counts.get(svtype, 0) + 1
                    if _looks_like_bnd(parts[4]):
                        bnd_records += 1
                        if not _valid_bnd(parts[4]):
                            malformed_bnd_records += 1
                            errors.append(f"line {number}: malformed BND ALT")
                    _validate_sv_fields(parts, info_map, errors, number)
                    if len(parts) > 9 and len(parts[8].split(":")) != len(parts[9].split(":")):
                        errors.append(f"line {number}: malformed FORMAT/sample columns")
    except Exception as exc:
        errors.append(str(exc))
    return {
        "has_fileformat": has_fileformat,
        "has_chrom_header": has_chrom_header,
        "samples": samples,
        "contigs": sorted(set(contigs)),
        "records": records,
        "pass_count": pass_count,
        "filtered_count": filtered_count,
        "reference_blocks": reference_blocks,
        "variant_records": variant_records,
        "symbolic_allele_count": symbolic_allele_count,
        "multi_allelic_count": multiallelic_count,
        "svtype_counts": svtype_counts,
        "bnd_records": bnd_records,
        "malformed_bnd_records": malformed_bnd_records,
        "gvcf_end_errors": gvcf_end_errors,
        "errors": errors,
    }


def _parse_info(info: str, errors: list[str], number: int) -> dict[str, str]:
    result: dict[str, str] = {}
    if info == ".":
        return result
    for item in info.split(";"):
        if not item:
            errors.append(f"line {number}: malformed INFO empty field")
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            if not key or value == "":
                errors.append(f"line {number}: malformed INFO field {item!r}")
            result[key] = value
        else:
            result[item] = "true"
    return result


def _validate_sv_fields(parts: list[str], info: dict[str, str], errors: list[str], number: int) -> None:
    alt = parts[4]
    svtype = info.get("SVTYPE")
    symbolic = alt.startswith("<") and alt.endswith(">")
    if symbolic and alt not in {"<NON_REF>", "<*>"} and not svtype:
        errors.append(f"line {number}: symbolic SV allele missing SVTYPE")
    if svtype in {"DEL", "DUP", "INV"} and "END" not in info:
        errors.append(f"line {number}: {svtype} missing END")
    if "END" in info:
        try:
            end = int(info["END"])
            pos = int(parts[1])
            if end < pos and svtype not in {"BND", "INS"}:
                errors.append(f"line {number}: END before POS")
        except ValueError:
            errors.append(f"line {number}: malformed END")
    if "SVLEN" in info and "END" in info and svtype in {"DEL", "DUP", "INV"}:
        try:
            svlen = int(info["SVLEN"].split(",", 1)[0])
            span = int(info["END"]) - int(parts[1])
            if abs(abs(svlen) - abs(span)) > 1:
                errors.append(f"line {number}: inconsistent END/SVLEN")
        except ValueError:
            errors.append(f"line {number}: malformed SVLEN")


def _looks_like_bnd(alt: str) -> bool:
    return "[" in alt or "]" in alt


def _valid_bnd(alt: str) -> bool:
    # VCF breakend forms include N]chr:pos], N[chr:pos[, ]chr:pos]N, [chr:pos[N.
    return bool(re.match(r"^([ACGTN.]*[\[\]][^\[\]]+:\d+[\[\]][ACGTN.]*|[ACGTN.]+)$", alt))


def _external_vcf_checks(vcf: Path, *, bcftools: str | None, tabix: str | None, index: Path | None) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    raw: dict[str, Any] = {}
    if bcftools:
        header = _run([bcftools, "view", "-h", str(vcf)])
        parse = _run([bcftools, "view", str(vcf)])
        raw["bcftools_view_h"] = header
        raw["bcftools_view"] = parse
        _check(checks, "bcftools_header_validation", header["exit_code"] == 0)
        _check(checks, "bcftools_parse_validation", parse["exit_code"] == 0)
    else:
        checks.append({"name": "bcftools_header_validation", "status": "NOT_EVALUATED"})
        checks.append({"name": "bcftools_parse_validation", "status": "NOT_EVALUATED"})
    if tabix and index:
        idx = _run([tabix, "-l", str(vcf)])
        raw["tabix_index_validation"] = idx
        _check(checks, "tabix_index_validation", idx["exit_code"] == 0)
    elif index:
        _check(checks, "index_non_empty", index.stat().st_size > 0)
    else:
        checks.append({"name": "tabix_index_validation", "status": "NOT_EVALUATED"})
    return {"checks": checks, "raw": raw}


def _run(argv: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
    except Exception as exc:
        return {"exit_code": None, "stdout": "", "stderr": str(exc)}
    return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _vcf_index(path: Path) -> Path | None:
    for suffix in (".tbi", ".csi"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            return candidate
    return None


def _check(checks: list[dict[str, str]], name: str, ok: bool, warn: bool = False) -> None:
    checks.append({"name": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL")})


def _overall(checks: list[dict[str, str]]) -> str:
    states = {c["status"] for c in checks}
    if "FAIL" in states:
        return "FAIL"
    if "WARN" in states:
        return "WARN"
    return "PASS"
