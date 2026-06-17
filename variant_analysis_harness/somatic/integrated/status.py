"""Centralized integrated somatic status derivation."""

from __future__ import annotations

from typing import Any

VALID_STATUSES = {
    "pending",
    "not_started",
    "small_variants_only",
    "structural_variants_only",
    "complete",
    "complete_with_warnings",
    "partial_success",
    "blocked",
    "failed",
    "excluded",
    "inconsistent",
    "superseded",
    "unknown",
}


def is_valid_source(source: dict[str, Any], *, include_warning_results: bool = False) -> bool:
    status = source.get("status")
    validation = source.get("validation_status")
    qc = source.get("qc_status")
    if source.get("superseded"):
        return False
    valid_status = status in {"complete", "caller_success", "PASS"}
    valid_validation = validation == "PASS" or (include_warning_results and validation == "WARN")
    valid_qc = qc in {"PASS", "NOT_APPLICABLE", "UNKNOWN"} or (include_warning_results and qc == "WARN")
    return bool(valid_status and valid_validation and valid_qc)


def derive_pair_status(
    small_source: dict[str, Any] | None,
    sv_source: dict[str, Any] | None,
    *,
    small_policy: str = "optional",
    sv_policy: str = "optional",
    allow_partial_success: bool = True,
    include_warning_results: bool = False,
    compatibility_status: str = "PASS",
    excluded: bool = False,
) -> str:
    if excluded:
        return "excluded"
    if compatibility_status == "FAIL":
        return "inconsistent"
    small_source = small_source or {"status": "not_started"}
    sv_source = sv_source or {"status": "not_started"}
    if small_source.get("superseded") or sv_source.get("superseded"):
        return "superseded"
    small_enabled = small_policy != "disabled"
    sv_enabled = sv_policy != "disabled"
    small_valid = small_enabled and is_valid_source(small_source, include_warning_results=include_warning_results)
    sv_valid = sv_enabled and is_valid_source(sv_source, include_warning_results=include_warning_results)
    small_warn = small_source.get("validation_status") == "WARN" or small_source.get("qc_status") == "WARN"
    sv_warn = sv_source.get("validation_status") == "WARN" or sv_source.get("bnd_validation_status") == "WARN" or sv_source.get("qc_status") == "WARN"
    small_started = small_source.get("status") not in {"", "not_started", "pending", None}
    sv_started = sv_source.get("status") not in {"", "not_started", "pending", None}
    if not small_started and not sv_started:
        return "not_started"
    if small_policy == "required" and not small_valid:
        return "blocked" if not small_started else "failed"
    if sv_policy == "required" and not sv_valid:
        return "blocked" if not sv_started else "failed"
    if small_valid and sv_valid:
        return "complete_with_warnings" if small_warn or sv_warn else "complete"
    if small_valid and not sv_valid:
        if not sv_enabled:
            return "small_variants_only"
        return "partial_success" if allow_partial_success else "failed"
    if sv_valid and not small_valid:
        if not small_enabled:
            return "structural_variants_only"
        return "partial_success" if allow_partial_success else "failed"
    if small_started or sv_started:
        return "failed"
    return "unknown"


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("integrated_status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))

