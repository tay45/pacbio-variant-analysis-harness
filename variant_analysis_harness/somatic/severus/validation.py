"""Severus somatic SV VCF and BND validation."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any

KNOWN_SVTYPES = {"DEL", "INS", "DUP", "INV", "BND", "TRA", "CPX", "COMPLEX"}
BND_RE = re.compile(r"^[ACGTN.]*[\[\]][A-Za-z0-9_.-]+:[0-9]+[\[\]][ACGTN.]*$")


def validate_severus_vcf(path: Path, *, index_path: Path | None, expected_samples: list[str], unknown_svtype_policy: str = "warn", unknown_filter_policy: str = "warn") -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not path.exists():
        return _result("FAIL", path, index_path, ["SV VCF is missing"], warnings)
    if path.stat().st_size == 0:
        return _result("FAIL", path, index_path, ["SV VCF is empty"], warnings)
    if index_path is None or not index_path.exists():
        errors.append("SV VCF index is missing")
    elif index_path.stat().st_mtime_ns < path.stat().st_mtime_ns:
        errors.append("SV VCF index is stale")
    lines = _read_lines(path)
    header = [line for line in lines if line.startswith("#")]
    records = [line for line in lines if line and not line.startswith("#")]
    if not any(line.startswith("##fileformat=") for line in header):
        errors.append("missing fileformat header")
    contig_order = _contig_order([line for line in header if line.startswith("##contig=")])
    if not contig_order:
        errors.append("missing contig headers")
    filters = _declared_filters(header)
    sample_line = next((line for line in header if line.startswith("#CHROM")), "")
    samples = sample_line.split("\t")[9:] if sample_line else []
    if samples != expected_samples:
        errors.append(f"samples {samples} do not match expected {expected_samples}")
    last_key = None
    svtype_counts: dict[str, int] = {}
    bnd_records: list[dict[str, Any]] = []
    malformed = 0
    for line in records:
        parts = line.split("\t")
        if len(parts) < 8:
            malformed += 1
            continue
        chrom, pos_text, rid, ref, alt, _qual, filt, info = parts[:8]
        try:
            pos = int(pos_text)
        except ValueError:
            malformed += 1
            continue
        key = (contig_order.get(chrom, 10**9), pos)
        if last_key and key < last_key:
            errors.append("SV VCF records are not sorted")
            break
        last_key = key
        info_map = _parse_info(info)
        svtype = info_map.get("SVTYPE", _svtype_from_alt(alt))
        svtype_counts[svtype] = svtype_counts.get(svtype, 0) + 1
        if svtype not in KNOWN_SVTYPES:
            msg = f"unknown SVTYPE {svtype}"
            (errors if unknown_svtype_policy == "fail" else warnings).append(msg)
        if svtype == "BND":
            bnd_records.append({"id": rid, "chrom": chrom, "pos": pos, "alt": alt, "filter": filt, "mateid": info_map.get("MATEID"), "event": info_map.get("EVENT")})
            if not BND_RE.match(alt):
                errors.append(f"malformed BND ALT for {rid}")
        if "END" in info_map:
            try:
                if int(info_map["END"]) < pos:
                    errors.append(f"END precedes POS for {rid}")
            except ValueError:
                errors.append(f"invalid END for {rid}")
        if "SVLEN" in info_map:
            try:
                int(str(info_map["SVLEN"]).split(",")[0])
            except ValueError:
                errors.append(f"invalid SVLEN for {rid}")
        for value in filt.split(";"):
            if value not in {"PASS", "."} and value not in filters:
                msg = f"filter {value} is not declared"
                (errors if unknown_filter_policy == "fail" else warnings).append(msg)
    if malformed:
        errors.append(f"malformed record count: {malformed}")
    bnd = validate_bnd_records(bnd_records)
    errors.extend(bnd["errors"])
    warnings.extend(bnd["warnings"])
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return _result(status, path, index_path, errors, warnings, records=len(records), svtype_counts=svtype_counts, bnd_validation=bnd)


def validate_bnd_records(records: list[dict[str, Any]], *, orphan_policy: str = "fail") -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    by_id = {}
    for record in records:
        rid = record.get("id")
        if not rid or rid == ".":
            warnings.append("BND record lacks stable ID")
            continue
        if rid in by_id:
            errors.append(f"duplicate BND ID {rid}")
        by_id[rid] = record
    for rid, record in by_id.items():
        mate = record.get("mateid")
        if not mate:
            msg = f"BND {rid} lacks MATEID"
            (errors if orphan_policy == "fail" else warnings if orphan_policy == "warn" else []).append(msg)
            continue
        if mate == rid:
            errors.append(f"BND {rid} is self-referential")
            continue
        mate_record = by_id.get(mate)
        if mate_record is None:
            msg = f"BND {rid} mate {mate} is missing"
            (errors if orphan_policy == "fail" else warnings if orphan_policy == "warn" else []).append(msg)
        elif mate_record.get("mateid") != rid:
            errors.append(f"BND {rid} and {mate} are not reciprocal")
        elif mate_record.get("filter") != record.get("filter"):
            warnings.append(f"BND {rid} and {mate} have inconsistent FILTER values")
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "records": len(records), "orphan_count": len([e for e in errors + warnings if "mate" in e or "MATEID" in e]), "errors": errors, "warnings": warnings}


def write_validation_artifacts(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "severus_vcf_validation.json").write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out_dir / "severus_vcf_validation.md").write_text("# Severus VCF Validation\n\nStatus: " + result["status"] + "\n", encoding="utf-8")
    if result.get("checksum"):
        (out_dir / "severus_vcf_checksum.txt").write_text(f"{result['checksum']}  {result['path']}\n", encoding="utf-8")
    bnd = result.get("bnd_validation", {})
    (out_dir / "severus_bnd_validation.json").write_text(json.dumps(bnd, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "severus_bnd_validation.md").write_text("# Severus BND Validation\n\nStatus: " + bnd.get("status", "NOT_EVALUATED") + "\n", encoding="utf-8")
    (out_dir / "severus_bnd_validation.tsv").write_text("metric\tvalue\nrecords\t" + str(bnd.get("records", 0)) + "\n", encoding="utf-8")


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


def _parse_info(info: str) -> dict[str, str]:
    result = {}
    for item in info.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


def _svtype_from_alt(alt: str) -> str:
    if alt.startswith("<") and alt.endswith(">"):
        return alt.strip("<>")
    if "[" in alt or "]" in alt:
        return "BND"
    return "UNKNOWN"


def _result(status: str, path: Path, index_path: Path | None, errors: list[str], warnings: list[str], **extra: Any) -> dict[str, Any]:
    checksum = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() and path.stat().st_size else None
    return {"status": status, "path": str(path), "index_path": str(index_path) if index_path else None, "checksum": checksum, "errors": errors, "warnings": warnings, **extra}
