"""Somatic pair preflight validation without caller execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from variant_analysis_harness.somatic.manifest import SomaticPair


@dataclass(frozen=True)
class HeaderMetadata:
    input_format: str
    sort_order: str = "coordinate"
    sample_names: tuple[str, ...] = ()
    read_groups: tuple[dict[str, str], ...] = ()
    platform: str = ""
    contigs: tuple[tuple[str, int], ...] = ()
    program_records: tuple[str, ...] = ()


def header_from_pair(pair: SomaticPair, label: str) -> HeaderMetadata:
    prefix = "tumor" if label == "tumor" else "normal"
    sample = pair.tumor_read_group_sample if False else ""
    optional_sample = pair.optional.get(f"{prefix}_read_group_sample") or (
        pair.tumor_sample_id if prefix == "tumor" else pair.normal_sample_id
    )
    contigs = parse_contigs(pair.optional.get(f"{prefix}_contigs", ""))
    return HeaderMetadata(
        input_format=(pair.tumor_input_type if prefix == "tumor" else pair.normal_input_type).upper(),
        sort_order=pair.optional.get(f"{prefix}_sort_order", "coordinate") or "coordinate",
        sample_names=(optional_sample,) if optional_sample else (),
        read_groups=({"ID": f"{prefix}_rg1", "SM": optional_sample},) if optional_sample else (),
        contigs=tuple(contigs),
    )


def validate_pair_preflight(pair: SomaticPair, config: dict[str, Any]) -> dict[str, Any]:
    tumor_header = header_from_pair(pair, "tumor")
    normal_header = header_from_pair(pair, "normal") if pair.analysis_mode == "tumor_normal" else None
    identity = validate_identity(pair, tumor_header, normal_header, config)
    reference = validate_reference(pair, tumor_header, normal_header, config)
    alignment = validate_alignment(pair, tumor_header, normal_header, config)
    coverage = validate_coverage_status(pair, config)
    metadata = validate_metadata_status(pair, config)
    domains = [identity, reference, alignment, coverage, metadata]
    errors = [issue for domain in domains for issue in domain["errors"]]
    warnings = [issue for domain in domains for issue in domain["warnings"]]
    readiness = "failed" if errors else ("warning" if warnings else "ready")
    failure_category = errors[0]["category"] if errors else ""
    return {
        "pair_id": pair.pair_id,
        "subject_id": pair.subject_id,
        "analysis_mode": pair.analysis_mode,
        "identity": identity,
        "reference": reference,
        "alignment": alignment,
        "coverage": coverage,
        "metadata": metadata,
        "readiness_status": readiness,
        "failure_category": failure_category,
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def validate_identity(
    pair: SomaticPair,
    tumor_header: HeaderMetadata,
    normal_header: HeaderMetadata | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    policy = config.get("identity_policy", "strict")
    _validate_sample_name(pair, "tumor", pair.tumor_sample_id, tumor_header, policy, errors, warnings)
    if pair.analysis_mode == "tumor_normal" and normal_header is not None:
        _validate_sample_name(pair, "normal", pair.normal_sample_id, normal_header, policy, errors, warnings)
        if pair.tumor_sample_id == pair.normal_sample_id:
            errors.append(_issue(pair, "tumor_normal_identity_collision", "tumor and normal sample IDs collide"))
    return _domain("identity", errors, warnings)


def validate_reference(
    pair: SomaticPair,
    tumor_header: HeaderMetadata,
    normal_header: HeaderMetadata | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    tumor_sig = pair.optional.get("tumor_reference_signature") or pair.optional.get("reference_signature")
    normal_sig = pair.optional.get("normal_reference_signature") or pair.optional.get("reference_signature")
    if pair.analysis_mode == "tumor_normal" and tumor_sig and normal_sig and tumor_sig != normal_sig:
        errors.append(_issue(pair, "tumor_normal_reference_mismatch", "tumor and normal reference signatures differ"))
    if pair.tumor_input_type.upper() == "CRAM" and not pair.reference_id:
        errors.append(_issue(pair, "tumor_reference_mismatch", "CRAM input requires a reference"))
    if pair.analysis_mode == "tumor_normal" and pair.normal_input_type.upper() == "CRAM" and not pair.reference_id:
        errors.append(_issue(pair, "normal_reference_mismatch", "CRAM input requires a reference"))
    if normal_header is not None and tumor_header.contigs and normal_header.contigs:
        tumor_names = [name for name, _ in tumor_header.contigs]
        normal_names = [name for name, _ in normal_header.contigs]
        if tumor_names != normal_names:
            if sorted(tumor_names) == sorted(normal_names):
                errors.append(_issue(pair, "contig_order_mismatch", "tumor and normal contig order differs"))
            else:
                errors.append(_issue(pair, "tumor_normal_reference_mismatch", "tumor and normal contig names differ"))
        elif [length for _, length in tumor_header.contigs] != [length for _, length in normal_header.contigs]:
            errors.append(_issue(pair, "contig_length_mismatch", "tumor and normal contig lengths differ"))
        if _chr_prefix_state(tumor_names) != _chr_prefix_state(normal_names):
            errors.append(_issue(pair, "tumor_normal_reference_mismatch", "tumor and normal chr-prefix conventions differ"))
    return _domain("reference", errors, warnings)


def validate_alignment(
    pair: SomaticPair,
    tumor_header: HeaderMetadata,
    normal_header: HeaderMetadata | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    require_rg = config.get("preflight", {}).get("require_read_groups", True)
    require_sm = config.get("preflight", {}).get("require_sample_names", True)
    for label, header in (("tumor", tumor_header), ("normal", normal_header)):
        if header is None:
            continue
        if header.sort_order != "coordinate":
            errors.append(_issue(pair, "unsorted_alignment", f"{label} alignment is not coordinate sorted"))
        if require_rg and not header.read_groups:
            errors.append(_issue(pair, "missing_read_group", f"{label} alignment has no read groups"))
        if require_sm and not header.sample_names:
            errors.append(_issue(pair, "missing_sample_tag", f"{label} alignment has no SM sample names"))
        if len(set(header.sample_names)) != len(header.sample_names):
            errors.append(_issue(pair, "ambiguous_sample_identity", f"{label} alignment has duplicate SM names"))
    return _domain("alignment", errors, warnings)


def validate_coverage_status(pair: SomaticPair, config: dict[str, Any]) -> dict[str, Any]:
    from variant_analysis_harness.somatic.manifest import validate_numeric_metadata

    errors = [
        issue
        for issue in validate_numeric_metadata(pair, config)
        if issue["category"] in {"insufficient_tumor_coverage", "insufficient_normal_coverage", "extreme_coverage_imbalance"}
    ]
    return _domain("coverage", errors, [])


def validate_metadata_status(pair: SomaticPair, config: dict[str, Any]) -> dict[str, Any]:
    from variant_analysis_harness.somatic.manifest import validate_numeric_metadata

    errors = [
        issue
        for issue in validate_numeric_metadata(pair, config)
        if issue["category"] in {"invalid_purity", "invalid_contamination", "invalid_ploidy", "missing_required_metadata"}
    ]
    return _domain("metadata", errors, [])


def parse_contigs(value: str) -> list[tuple[str, int]]:
    if not value:
        return []
    contigs = []
    for item in value.split(","):
        if not item:
            continue
        name, _, length = item.partition(":")
        if not name or not length:
            continue
        contigs.append((name, int(length)))
    return contigs


def pair_input_paths(pair: SomaticPair) -> list[Path]:
    paths = [pair.tumor_input_path]
    if pair.tumor_index_path:
        paths.append(pair.tumor_index_path)
    if pair.normal_input_path:
        paths.append(pair.normal_input_path)
    if pair.normal_index_path:
        paths.append(pair.normal_index_path)
    return paths


def _validate_sample_name(
    pair: SomaticPair,
    label: str,
    expected: str,
    header: HeaderMetadata,
    policy: str,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    if not header.sample_names:
        errors.append(_issue(pair, "missing_sample_tag", f"{label} header is missing sample names"))
        return
    if len(set(header.sample_names)) > 1:
        errors.append(_issue(pair, "ambiguous_sample_identity", f"{label} header has ambiguous sample names"))
        return
    observed = header.sample_names[0]
    if observed != expected:
        issue = _issue(pair, f"{label}_header_mismatch", f"{label} header SM {observed!r} does not match expected {expected!r}")
        if policy == "warn":
            warnings.append(issue)
        else:
            errors.append(issue)


def _domain(name: str, errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {"domain": name, "status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "errors": errors, "warnings": warnings}


def _issue(pair: SomaticPair, category: str, message: str) -> dict[str, Any]:
    return {"pair_id": pair.pair_id, "row": pair.row_number, "category": category, "message": message}


def _chr_prefix_state(names: list[str]) -> str:
    if not names:
        return "unknown"
    with_chr = [name.startswith("chr") for name in names]
    if all(with_chr):
        return "chr"
    if not any(with_chr):
        return "no_chr"
    return "mixed"
