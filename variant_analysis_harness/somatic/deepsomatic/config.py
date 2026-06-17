"""DeepSomatic configuration resolution and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.somatic.deepsomatic.compatibility import (
    protected_extra_arg_conflicts,
    validate_model_type,
    validate_version_policy,
)


def default_deepsomatic_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "backend": "deepsomatic",
        "deepsomatic": {
            "version": "1.10.0",
            "version_mismatch_policy": "fail",
            "unknown_version_policy": "fail",
            "model_type": {"tumor_normal": "PACBIO", "tumor_only": "PACBIO_TUMOR_ONLY"},
            "execution": {"mode": "container"},
            "executable": {"path": None},
            "container": {"engine": "docker", "image": "google/deepsomatic", "tag": "1.10.0", "digest": None, "extra_args": []},
            "model": {"custom_model_path": None, "example_info_path": None, "require_example_info": "auto", "verify_model_files": True},
            "resources": {"num_shards": None, "cpus": None, "memory_gb": None, "time": None, "scratch_gb": None},
            "outputs": {"emit_vcf": True, "emit_gvcf": True, "emit_intermediate_results": False, "preserve_logs": True, "create_pass_only_vcf": False},
            "regions": {"mode": "whole_genome", "values": [], "file": None},
            "pon": {"enabled": False, "path": None, "index_path": None, "signature": None, "use_default_filtering": False},
            "advanced": {"extra_args": []},
        },
    }


def resolve_deepsomatic_config(somatic_config: dict[str, Any]) -> dict[str, Any]:
    resolved = default_deepsomatic_config()
    supplied = somatic_config.get("small_variants", {}) or {}
    _merge_dict(resolved, supplied)
    return resolved


def validate_deepsomatic_config(config: dict[str, Any], *, mode: str, detected_version: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if config.get("backend") != "deepsomatic":
        errors.append("somatic small-variant backend must be deepsomatic")
    ds = config.get("deepsomatic", {})
    try:
        version = validate_version_policy(
            ds.get("version", ""),
            detected_version=detected_version,
            mismatch_policy=ds.get("version_mismatch_policy", "fail"),
            unknown_version_policy=ds.get("unknown_version_policy", "fail"),
        )
    except ValueError as exc:
        version = {"status": "FAIL", "errors": [str(exc)], "warnings": []}
    errors.extend(version.get("errors", []))
    warnings.extend(version.get("warnings", []))
    model_type = (ds.get("model_type", {}) or {}).get(mode)
    model = validate_model_type(mode, model_type or "")
    errors.extend(model["errors"])
    extra_conflicts = protected_extra_arg_conflicts(list((ds.get("advanced", {}) or {}).get("extra_args", [])))
    if extra_conflicts:
        errors.append(f"extra_args cannot override protected DeepSomatic flags: {sorted(set(extra_conflicts))}")
    exec_mode = (ds.get("execution", {}) or {}).get("mode")
    executable = (ds.get("executable", {}) or {}).get("path")
    container = ds.get("container", {}) or {}
    if exec_mode == "executable" and not executable:
        errors.append("direct executable mode requires executable.path")
    if exec_mode == "container" and not container.get("engine"):
        errors.append("container mode requires container.engine")
    if exec_mode not in {"container", "executable"}:
        errors.append(f"unsupported DeepSomatic execution mode: {exec_mode}")
    metadata = validate_model_metadata(ds, version_policy=version.get("policy", {}), mode=mode, model_type=model_type or "")
    errors.extend(metadata["errors"])
    warnings.extend(metadata["warnings"])
    return {
        "status": "FAIL" if errors else ("WARN" if warnings else "PASS"),
        "errors": errors,
        "warnings": warnings,
        "version": version,
        "model": model,
        "model_metadata": metadata,
    }


def validate_model_metadata(ds_config: dict[str, Any], *, version_policy: dict[str, Any], mode: str, model_type: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    model_cfg = ds_config.get("model", {}) or {}
    requirement = model_cfg.get("require_example_info", "auto")
    required = bool(version_policy.get("example_info_required", False)) if requirement == "auto" else requirement is True
    info_path = model_cfg.get("example_info_path")
    model_files: list[dict[str, Any]] = []
    metadata_checksum = None
    if required and not info_path:
        if model_cfg.get("custom_model_path"):
            errors.append("model.example_info.json is required for this DeepSomatic version/policy")
        else:
            warnings.append("using container-bundled model metadata; host model metadata not supplied")
    if info_path:
        path = Path(info_path)
        if not path.exists():
            errors.append(f"model metadata file is missing: {path}")
        else:
            payload = path.read_bytes()
            metadata_checksum = hashlib.sha256(payload).hexdigest()
            try:
                data = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"model metadata is malformed JSON: {exc}")
                data = {}
            if data:
                technology = data.get("technology") or data.get("platform")
                metadata_mode = data.get("analysis_mode")
                metadata_model = data.get("model_type")
                if technology and str(technology).lower() not in {"pacbio", "pacbio_hifi"}:
                    errors.append(f"model metadata technology is not PacBio: {technology}")
                if metadata_mode and metadata_mode != mode:
                    errors.append(f"model metadata mode {metadata_mode} does not match {mode}")
                if metadata_model and metadata_model != model_type:
                    errors.append(f"model metadata model_type {metadata_model} does not match {model_type}")
                for entry in data.get("model_files", []):
                    file_path = Path(entry["path"])
                    if not file_path.is_absolute():
                        file_path = path.parent / file_path
                    sig = {"path": str(file_path), "exists": file_path.exists()}
                    if not file_path.exists():
                        errors.append(f"model file is missing: {file_path}")
                    elif file_path.stat().st_size == 0:
                        errors.append(f"model file is empty: {file_path}")
                    else:
                        sig["size"] = file_path.stat().st_size
                        if entry.get("sha256"):
                            digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
                            sig["sha256"] = digest
                            if digest != entry["sha256"]:
                                errors.append(f"model file checksum mismatch: {file_path}")
                    model_files.append(sig)
    return {"status": "FAIL" if errors else ("WARN" if warnings else "PASS"), "required": required, "metadata_checksum": metadata_checksum, "model_files": model_files, "errors": errors, "warnings": warnings}


def _merge_dict(target: dict[str, Any], supplied: dict[str, Any]) -> None:
    for key, value in supplied.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_dict(target[key], value)
        else:
            target[key] = value
