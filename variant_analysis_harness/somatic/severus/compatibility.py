"""Verified Severus compatibility contracts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEVERUS_CONTRACT_VERSION = 1
CONTRACT_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "severus"


@dataclass(frozen=True, order=True)
class SeverusVersion:
    major: int
    minor: int
    patch: int | None = None

    @classmethod
    def parse(cls, value: str) -> "SeverusVersion":
        match = re.fullmatch(r"v?([0-9]+)[.]([0-9]+)(?:[.]([0-9]+))?", value or "")
        if not match:
            raise ValueError(f"Malformed Severus version: {value!r}")
        major, minor, patch = match.groups()
        return cls(int(major), int(minor), int(patch) if patch is not None else None)

    @property
    def exact_key(self) -> str:
        return f"{self.major}.{self.minor}" if self.patch is None else f"{self.major}.{self.minor}.{self.patch}"

    @property
    def tag_key(self) -> str:
        return f"{self.major}.{self.minor}"

    def __str__(self) -> str:
        return self.exact_key


def _load_contract(version: str) -> dict[str, Any]:
    root = CONTRACT_ROOT / version
    cli = json.loads((root / "cli_contract.json").read_text(encoding="utf-8"))
    outputs = json.loads((root / "output_contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "source_manifest.json").read_text(encoding="utf-8"))
    flags = cli["flags"]
    mode = cli["mode_support"]
    return {
        "contract_version": cli["contract_version"],
        "entry_point": cli["entry_point"],
        "exact_version": cli["severus_version"],
        "tag": cli["tag"],
        "commit": cli["commit"],
        "target_input_flag": flags["target_bam"],
        "control_input_flag": flags["control_bam"],
        "output_directory_flag": flags["out_dir"],
        "thread_flag": flags["threads"],
        "thread_short_flag": flags["threads_short"],
        "phasing_vcf_flag": flags["phasing_vcf"],
        "vntr_bed_flag": flags["vntr_bed"],
        "pon_flag": flags["pon"],
        "supplementary_tag_flag": flags["use_supplementary_tag"],
        "target_sample_flag": flags["target_sample"],
        "control_sample_flag": flags["control_sample"],
        "optional_parameter_flags": {
            "min_support": flags["min_support"],
            "vaf_threshold": flags["vaf_threshold"],
            "tin_ratio": flags["tin_ratio"],
            "min_mapq": flags["min_mapq"],
            "min_sv_size": flags["min_sv_size"],
        },
        "tumor_normal": mode["tumor_normal"],
        "tumor_only": mode["tumor_only"],
        "multi_sample": mode["multiple_targets"],
        "maximum_unique_controls": mode["maximum_unique_controls"],
        "protected_flags": cli["protected_flags"],
        "unavailable_flags": cli["unavailable_flags"],
        "supported_flags": sorted(set(cli["protected_flags"]) | set(cli["flags"].values()) | set(cli["optional_parameter_flags"].values()) if "optional_parameter_flags" in cli else set(cli["flags"].values())),
        "required_outputs": outputs["required_outputs"],
        "conditional_required_outputs": outputs["conditional_required_outputs"],
        "optional_outputs": outputs["optional_outputs"],
        "unavailable_outputs": outputs["unavailable_outputs"],
        "source_manifest": manifest,
        "execution_verified": True,
    }


COMPATIBILITY_REGISTRY: dict[str, dict[str, Any]] = {"1.7": _load_contract("1.7")}
PROTECTED_FLAGS = set(COMPATIBILITY_REGISTRY["1.7"]["protected_flags"])
UNAVAILABLE_FLAGS = set(COMPATIBILITY_REGISTRY["1.7"]["unavailable_flags"])


def validate_version_policy(
    requested_version: str | None,
    *,
    detected_version: str | None = None,
    mismatch_policy: str = "fail",
    unknown_version_policy: str = "fail",
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    requested = None
    capability = None
    execution_allowed = True
    if requested_version:
        requested = SeverusVersion.parse(requested_version)
        capability = COMPATIBILITY_REGISTRY.get(requested.tag_key)
        if capability is None or requested.tag_key != capability["exact_version"]:
            msg = f"Unverified Severus version {requested}; executable command generation requires a pinned verified contract"
            execution_allowed = False
            if unknown_version_policy == "warn":
                warnings.append(msg)
                capability = {"execution_verified": False, "contract_version": SEVERUS_CONTRACT_VERSION}
            else:
                errors.append(msg)
    else:
        warnings.append("requested Severus version is not pinned")
        execution_allowed = False
    if requested_version and detected_version:
        detected = SeverusVersion.parse(detected_version)
        if requested and detected.tag_key != requested.tag_key:
            msg = f"Requested Severus {requested} differs from detected {detected}"
            if mismatch_policy == "warn":
                warnings.append(msg)
            else:
                errors.append(msg)
    return {
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
        "requested_version": str(requested) if requested else None,
        "detected_version": detected_version,
        "release_family": requested.tag_key if requested else None,
        "capability": capability or {},
        "execution_allowed": execution_allowed and not errors,
        "errors": errors,
        "warnings": warnings,
    }


def validate_mode_support(mode: str, capability: dict[str, Any]) -> dict[str, Any]:
    if not capability.get("execution_verified", False):
        return {"status": "WARN", "errors": [], "warnings": ["Severus execution command generation requires a verified contract; inventory-only review allowed"]}
    if mode == "tumor_normal" and capability.get("tumor_normal"):
        return {"status": "PASS", "errors": [], "warnings": []}
    if mode == "tumor_only" and capability.get("tumor_only"):
        return {"status": "PASS", "errors": [], "warnings": ["tumor-only Severus output lacks matched-normal evidence"]}
    return {"status": "FAIL", "errors": [f"Unsupported Severus analysis mode for verified contract: {mode}"], "warnings": []}


def protected_extra_arg_conflicts(extra_args: list[str]) -> list[str]:
    conflicts = []
    for arg in extra_args:
        flag = arg.split("=", 1)[0]
        if flag in PROTECTED_FLAGS or flag in UNAVAILABLE_FLAGS:
            conflicts.append(flag)
    return conflicts
