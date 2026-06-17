"""Version-aware DeepSomatic model compatibility policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SUPPORTED_MODELS = {"PACBIO", "PACBIO_TUMOR_ONLY"}
MODEL_BY_MODE = {"tumor_normal": "PACBIO", "tumor_only": "PACBIO_TUMOR_ONLY"}
PROTECTED_FLAGS = {
    "--model_type",
    "--ref",
    "--reads_normal",
    "--reads_tumor",
    "--output_vcf",
    "--output_gvcf",
    "--sample_name_tumor",
    "--sample_name_normal",
    "--num_shards",
    "--logging_dir",
    "--intermediate_results_dir",
}


@dataclass(frozen=True, order=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        match = re.fullmatch(r"([0-9]+)[.]([0-9]+)[.]([0-9]+)", value or "")
        if not match:
            raise ValueError(f"Malformed DeepSomatic version: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    @property
    def release_family(self) -> str:
        return f"{self.major}.{self.minor}"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


COMPATIBILITY_REGISTRY: dict[str, dict[str, Any]] = {
    "1.9": {"models": SUPPORTED_MODELS, "example_info_required": False},
    "1.10": {"models": SUPPORTED_MODELS, "example_info_required": True},
}


def validate_version_policy(
    requested_version: str,
    *,
    detected_version: str | None = None,
    mismatch_policy: str = "fail",
    unknown_version_policy: str = "fail",
) -> dict[str, Any]:
    requested = SemanticVersion.parse(requested_version)
    warnings: list[str] = []
    errors: list[str] = []
    policy = COMPATIBILITY_REGISTRY.get(requested.release_family)
    if policy is None:
        message = f"Unknown DeepSomatic release family {requested.release_family}"
        if unknown_version_policy == "warn":
            warnings.append(message)
        else:
            errors.append(message)
    if detected_version:
        detected = SemanticVersion.parse(detected_version)
        if detected != requested:
            message = f"Requested DeepSomatic {requested} differs from detected {detected}"
            if mismatch_policy == "warn":
                warnings.append(message)
            else:
                errors.append(message)
    return {
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
        "requested_version": str(requested),
        "detected_version": detected_version,
        "release_family": requested.release_family,
        "policy": policy or {},
        "errors": errors,
        "warnings": warnings,
    }


def expected_model_for_mode(mode: str) -> str:
    if mode not in MODEL_BY_MODE:
        raise ValueError(f"Unsupported somatic analysis mode for DeepSomatic: {mode}")
    return MODEL_BY_MODE[mode]


def validate_model_type(mode: str, model_type: str, *, platform: str = "pacbio_hifi") -> dict[str, Any]:
    errors = []
    expected = expected_model_for_mode(mode)
    if model_type not in SUPPORTED_MODELS:
        errors.append(f"Unsupported DeepSomatic model type: {model_type}")
    if model_type != expected:
        errors.append(f"Model {model_type} is incompatible with {mode}; expected {expected}")
    if platform == "pacbio_hifi" and not model_type.startswith("PACBIO"):
        errors.append(f"Non-PacBio model {model_type} is incompatible with PacBio HiFi under strict policy")
    return {"status": "FAIL" if errors else "PASS", "expected_model_type": expected, "model_type": model_type, "errors": errors, "warnings": []}


def protected_extra_arg_conflicts(extra_args: list[str]) -> list[str]:
    conflicts = []
    for arg in extra_args:
        flag = arg.split("=", 1)[0]
        if flag in PROTECTED_FLAGS:
            conflicts.append(flag)
    return conflicts
