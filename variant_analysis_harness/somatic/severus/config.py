"""Severus configuration resolution and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.somatic.severus.compatibility import (
    SEVERUS_CONTRACT_VERSION,
    protected_extra_arg_conflicts,
    validate_mode_support,
    validate_version_policy,
)


def default_severus_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "backend": "severus",
        "severus": {
            "requested_version": "1.7",
            "command_contract_version": SEVERUS_CONTRACT_VERSION,
            "version_mismatch_policy": "fail",
            "unknown_version_policy": "fail",
            "execution": {"mode": "container"},
            "executable": {"path": None},
            "container": {"engine": "docker", "image": "severus", "tag": "1.7", "digest": None, "extra_args": []},
            "mode": {"tumor_normal": True, "tumor_only": True, "multi_sample": True},
            "inputs": {"require_aligned": True, "require_coordinate_sorted": True, "require_indexes": True, "require_read_groups": True},
            "parameters": {"threads": None, "min_support": None, "min_mapq": None, "min_sv_size": None, "vaf_threshold": None, "tin_ratio": None, "vntr_bed": None, "pon": None, "pon_required_for_tumor_only": False, "extra_args": []},
            "phasing": {"mode": "auto", "phased_vcf": None, "phased_vcf_index": None, "require_phased_vcf_for_haplotagged_inputs": True, "require_hp_tags": False, "supplementary_tag_policy": "auto", "haplotagging_method": None, "source_tool": None, "source_version": None, "hp_tags": "unknown", "supplementary_hp_tags": "unknown"},
            "outputs": {"preserve_all_native_outputs": True, "create_standardized_vcf_copy": True, "create_pass_only_vcf": False, "preserve_logs": True, "preserve_intermediate": False},
            "qc": {"unknown_svtype_policy": "warn", "unknown_filter_policy": "warn", "require_bnd_mate_consistency": True, "orphan_bnd_policy": "fail", "require_sorted_vcf": True},
        },
    }


def resolve_severus_config(somatic_config: dict[str, Any]) -> dict[str, Any]:
    resolved = default_severus_config()
    supplied = somatic_config.get("structural_variants", {}) or {}
    _merge_dict(resolved, supplied)
    return resolved


def validate_severus_config(config: dict[str, Any], *, mode: str, detected_version: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if config.get("backend") != "severus":
        errors.append("somatic structural-variant backend must be severus")
    sev = config.get("severus", {}) or {}
    try:
        version = validate_version_policy(
            sev.get("requested_version"),
            detected_version=detected_version,
            mismatch_policy=sev.get("version_mismatch_policy", "fail"),
            unknown_version_policy=sev.get("unknown_version_policy", "fail"),
        )
    except ValueError as exc:
        version = {"status": "FAIL", "errors": [str(exc)], "warnings": [], "capability": {}}
    errors.extend(version.get("errors", []))
    warnings.extend(version.get("warnings", []))
    mode_result = validate_mode_support(mode, version.get("capability", {}))
    errors.extend(mode_result["errors"])
    warnings.extend(mode_result["warnings"])
    exec_mode = (sev.get("execution", {}) or {}).get("mode")
    executable = (sev.get("executable", {}) or {}).get("path")
    container = sev.get("container", {}) or {}
    if exec_mode == "executable" and not executable:
        errors.append("direct executable mode requires executable.path")
    if exec_mode == "container" and not container.get("engine"):
        errors.append("container mode requires container.engine")
    if exec_mode not in {"container", "executable"}:
        errors.append(f"unsupported Severus execution mode: {exec_mode}")
    conflicts = protected_extra_arg_conflicts(list((sev.get("parameters", {}) or {}).get("extra_args", [])))
    if conflicts:
        errors.append(f"extra_args cannot override protected Severus flags: {sorted(set(conflicts))}")
    params = sev.get("parameters", {}) or {}
    if mode == "tumor_only" and params.get("pon_required_for_tumor_only") and not params.get("pon"):
        errors.append("tumor-only Severus execution requires configured parameters.pon by policy")
    for field in ("vntr_bed", "pon"):
        value = params.get(field)
        if value and not Path(value).exists():
            warnings.append(f"configured {field} does not exist in this planning environment: {value}")
        elif value and Path(value).exists() and Path(value).stat().st_size == 0:
            errors.append(f"configured {field} is empty: {value}")
    phasing = validate_phasing_config(sev.get("phasing", {}) or {})
    errors.extend(phasing["errors"])
    warnings.extend(phasing["warnings"])
    return {
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
        "errors": errors,
        "warnings": warnings,
        "version": version,
        "mode": mode_result,
        "phasing": phasing,
    }


def validate_phasing_config(phasing: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    mode = phasing.get("mode", "auto")
    if mode not in {"auto", "phased", "unphased"}:
        errors.append(f"unsupported Severus phasing mode: {mode}")
    phased_vcf = phasing.get("phased_vcf")
    phased_index = phasing.get("phased_vcf_index")
    hp_tags = phasing.get("hp_tags", "unknown")
    supp_tags = phasing.get("supplementary_hp_tags", "unknown")
    if phased_vcf:
        path = Path(phased_vcf)
        if not path.exists():
            errors.append(f"phased VCF is missing: {path}")
        elif path.stat().st_size == 0:
            errors.append(f"phased VCF is empty: {path}")
        if not phased_index:
            errors.append("phased VCF index is required when phasing.phased_vcf is configured")
        elif not Path(phased_index).exists():
            errors.append(f"phased VCF index is missing: {phased_index}")
    elif mode == "phased":
        errors.append("phasing.mode=phased requires phasing.phased_vcf")
    elif hp_tags in {"present", "primary", "supplementary"} and phasing.get("require_phased_vcf_for_haplotagged_inputs", True):
        errors.append("haplotagged inputs require phasing.phased_vcf by policy")
    if mode == "unphased":
        warnings.append("unphased Severus mode is allowed but haplotype-specific interpretation is disabled")
    supplementary = decide_supplementary_tag(phasing)
    warnings.extend(supplementary["warnings"])
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "errors": errors, "warnings": warnings, "supplementary_tag_decision": supplementary}


def decide_supplementary_tag(phasing: dict[str, Any]) -> dict[str, Any]:
    policy = phasing.get("supplementary_tag_policy", "auto")
    source = (phasing.get("haplotagging_method") or phasing.get("source_tool") or "").lower()
    supplementary_hp = phasing.get("supplementary_hp_tags", "unknown")
    warnings: list[str] = []
    if policy is True or policy == "true":
        if supplementary_hp not in {"present", "unknown"}:
            warnings.append("supplementary tag option forced without supporting supplementary HP metadata")
        return {"emit": True, "reason": "forced_true", "warnings": warnings}
    if policy is False or policy == "false":
        if supplementary_hp == "present":
            warnings.append("supplementary HP tags appear present but --use-supplementary-tag is disabled")
        return {"emit": False, "reason": "forced_false", "warnings": warnings}
    if policy != "auto":
        warnings.append(f"unknown supplementary_tag_policy {policy!r}; option disabled")
        return {"emit": False, "reason": "unknown_policy", "warnings": warnings}
    if supplementary_hp == "present" and source in {"hiphase", "longphase"}:
        return {"emit": True, "reason": f"auto_{source}_supplementary_hp", "warnings": warnings}
    if supplementary_hp == "present":
        warnings.append("supplementary HP tags are reported but source tool is unknown; option not enabled automatically")
    return {"emit": False, "reason": "auto_no_verified_supplementary_source", "warnings": warnings}


def _merge_dict(target: dict[str, Any], supplied: dict[str, Any]) -> None:
    for key, value in supplied.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value
