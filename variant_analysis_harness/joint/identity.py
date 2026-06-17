"""Sample identity validation for joint genotyping inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.common.yaml_io import load_yaml
from variant_analysis_harness.joint.inputs import JointInput


def validate_sample_identity(
    inputs: list[JointInput],
    *,
    policy: str = "strict",
    mapping_file: Path | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    mapping: dict[str, str] = {}
    if policy not in {"strict", "warn", "explicit_mapping"}:
        errors.append({"scope": "identity", "message": f"unsupported sample identity policy: {policy}"})
    if policy == "explicit_mapping":
        if mapping_file is None:
            errors.append({"scope": "identity", "message": "explicit_mapping policy requires a mapping file"})
        else:
            raw = load_yaml(mapping_file)
            mapping = {str(k): str(v) for k, v in (raw.get("sample_name_mapping", raw) if isinstance(raw, dict) else {}).items()}
            if len(mapping) != len(set(mapping.values())):
                errors.append({"scope": "identity", "message": "mapping values must be one-to-one"})
    seen_headers: set[str] = set()
    for item in inputs:
        if not item.enabled:
            continue
        header = item.sample_name_in_header
        if not header:
            errors.append({"sample_id": item.sample_id, "message": "empty VCF header sample name"})
        if header in seen_headers:
            errors.append({"sample_id": item.sample_id, "message": f"duplicate VCF header sample name: {header}"})
        seen_headers.add(header)
        expected = mapping.get(header, item.sample_id) if policy == "explicit_mapping" else item.sample_id
        if header != expected:
            issue = {"sample_id": item.sample_id, "header_sample": header, "expected": expected, "message": "sample identity mismatch"}
            if policy == "warn":
                warnings.append(issue)
            else:
                errors.append(issue)
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "policy": policy, "errors": errors, "warnings": warnings, "mapping": mapping}

