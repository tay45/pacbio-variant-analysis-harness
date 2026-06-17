"""Integrated somatic configuration."""

from __future__ import annotations

from typing import Any


def default_integrated_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "project_policy": {
            "required_stages": {"small_variants": "optional", "structural_variants": "optional"},
            "allow_partial_success": True,
            "include_warning_results": False,
            "require_matching_reference": True,
            "require_matching_subject": True,
            "require_matching_tumor_identity": True,
            "require_matching_normal_identity": True,
        },
        "relationship_analysis": {
            "enabled": True,
            "window_bp": 10000,
            "large_window_bp": 100000,
            "include_filtered_small_variants": False,
            "include_filtered_structural_variants": False,
            "max_variants_per_region": None,
        },
        "outputs": {
            "create_markdown_report": True,
            "create_json_report": True,
            "create_tsv_exports": True,
            "create_html_report": False,
            "create_recruiter_summary": True,
            "create_operator_summary": True,
        },
        "portfolio": {
            "enabled": True,
            "include_architecture_summary": True,
            "include_validation_boundaries": True,
            "include_test_evidence": True,
            "include_scale_evidence": True,
            "include_failure_recovery_evidence": True,
        },
    }


def resolve_integrated_config(somatic_config: dict[str, Any]) -> dict[str, Any]:
    resolved = default_integrated_config()
    _merge_dict(resolved, (somatic_config.get("integrated", {}) or {}))
    return resolved


def validate_integrated_config(config: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    allowed_stage_values = {"required", "optional", "disabled"}
    stages = config.get("project_policy", {}).get("required_stages", {})
    for key in ("small_variants", "structural_variants"):
        if stages.get(key) not in allowed_stage_values:
            errors.append(f"invalid required-stage policy for {key}: {stages.get(key)!r}")
    rel = config.get("relationship_analysis", {})
    for key in ("window_bp", "large_window_bp"):
        value = rel.get(key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"{key} must be a non-negative integer")
    if rel.get("large_window_bp", 0) < rel.get("window_bp", 0):
        warnings.append("large_window_bp is smaller than window_bp")
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "errors": errors, "warnings": warnings}


def _merge_dict(target: dict[str, Any], supplied: dict[str, Any]) -> None:
    for key, value in supplied.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value

