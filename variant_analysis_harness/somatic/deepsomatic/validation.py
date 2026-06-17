"""DeepSomatic VCF/gVCF validation using lightweight text fixtures."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
from typing import Any


def validate_deepsomatic_vcf(
    path: Path,
    *,
    index_path: Path | None,
    expected_samples: list[str],
    allowed_contigs: list[str] | None = None,
    unknown_filter_policy: str = "warn",
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.exists():
        return _result("FAIL", path, index_path, ["VCF output is missing"], warnings)
    if path.stat().st_size == 0:
        return _result("FAIL", path, index_path, ["VCF output is empty"], warnings)
    if index_path is None or not index_path.exists():
        errors.append("VCF index is missing")
    elif index_path.stat().st_mtime_ns < path.stat().st_mtime_ns:
        errors.append("VCF index is stale")
    try:
        lines = _read_lines(path)
    except OSError as exc:
        return _result("FAIL", path, index_path, [f"VCF is not readable: {exc}"], warnings)
    header = [line for line in lines if line.startswith("#")]
    records = [line for line in lines if line and not line.startswith("#")]
    if not any(line.startswith("##fileformat=") for line in header):
        errors.append("VCF header lacks fileformat")
    contigs = [line for line in header if line.startswith("##contig=")]
    if not contigs:
        errors.append("VCF header lacks contig declarations")
    filter_ids = _declared_filters(header)
    sample_line = next((line for line in header if line.startswith("#CHROM")), "")
    observed_samples = sample_line.split("\t")[9:] if sample_line else []
    if observed_samples != expected_samples:
        errors.append(f"VCF samples {observed_samples} do not match expected {expected_samples}")
    last_key: tuple[int, int] | None = None
    contig_order = _contig_order(contigs)
    filter_counts: dict[str, int] = {}
    malformed = 0
    for line in records:
        parts = line.split("\t")
        if len(parts) < 8:
            malformed += 1
            continue
        chrom, pos_text, _id, ref, alt, _qual, filt = parts[:7]
        if allowed_contigs is not None and chrom not in allowed_contigs:
            errors.append(f"record outside allowed contigs: {chrom}")
        if not ref or not alt:
            malformed += 1
        try:
            pos = int(pos_text)
        except ValueError:
            malformed += 1
            continue
        key = (contig_order.get(chrom, 10**9), pos)
        if last_key and key < last_key:
            errors.append("VCF records are not sorted")
            break
        last_key = key
        for value in filt.split(";"):
            filter_counts[value] = filter_counts.get(value, 0) + 1
            if value not in {"PASS", "."} and value not in filter_ids:
                msg = f"filter {value} is not declared in header"
                if unknown_filter_policy == "fail":
                    errors.append(msg)
                else:
                    warnings.append(msg)
    if malformed:
        errors.append(f"VCF contains {malformed} malformed records")
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return _result(status, path, index_path, errors, warnings, records=len(records), filter_counts=filter_counts)


def validate_deepsomatic_gvcf(path: Path | None, *, index_path: Path | None, expected_samples: list[str], enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "NOT_EVALUATED", "enabled": False, "errors": [], "warnings": []}
    if path is None:
        return {"status": "FAIL", "enabled": True, "errors": ["gVCF path is missing"], "warnings": []}
    result = validate_deepsomatic_vcf(path, index_path=index_path, expected_samples=expected_samples)
    result["enabled"] = True
    return result


def write_validation_artifacts(result: dict[str, Any], json_path: Path, md_path: Path, checksum_path: Path | None = None) -> None:
    import json

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = ["# DeepSomatic VCF Validation", "", f"Status: {result['status']}"]
    lines.extend(f"- ERROR: {e}" for e in result.get("errors", []))
    lines.extend(f"- WARNING: {w}" for w in result.get("warnings", []))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if checksum_path and result.get("checksum"):
        checksum_path.write_text(f"{result['checksum']}  {result.get('path')}\n", encoding="utf-8")


def _read_lines(path: Path) -> list[str]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return [line.rstrip("\n") for line in handle]
    return path.read_text(encoding="utf-8").splitlines()


def _declared_filters(header: list[str]) -> set[str]:
    filters = set()
    for line in header:
        if line.startswith("##FILTER=<ID="):
            filters.add(line.split("ID=", 1)[1].split(",", 1)[0].split(">", 1)[0])
    return filters


def _contig_order(contigs: list[str]) -> dict[str, int]:
    order = {}
    for idx, line in enumerate(contigs):
        if "ID=" in line:
            order[line.split("ID=", 1)[1].split(",", 1)[0].split(">", 1)[0]] = idx
    return order


def _result(status: str, path: Path, index_path: Path | None, errors: list[str], warnings: list[str], **extra: Any) -> dict[str, Any]:
    checksum = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() and path.stat().st_size else None
    return {"status": status, "path": str(path), "index_path": str(index_path) if index_path else None, "checksum": checksum, "errors": errors, "warnings": warnings, **extra}
