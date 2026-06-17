"""Run configuration loading, validation, and resolution."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from variant_analysis_harness.exceptions import ConfigError
from variant_analysis_harness.models import ToolConfig
from variant_analysis_harness.common.paths import resolve_path, safe_name
from variant_analysis_harness.common.schema_validation import SCHEMA_VERSION, validate_run_config_schema
from variant_analysis_harness.common.yaml_io import load_yaml

ALLOWED_TOOL_BACKENDS = {"native", "apptainer", "singularity", "docker", "conda"}
ALLOWED_EXECUTION_BACKENDS = {"local", "slurm"}
ALLOWED_DEEPVARIANT_MODELS = {"PACBIO", "WGS", "WES", "HYBRID_PACBIO_ILLUMINA"}
SHELL_FRAGMENT_CHARS = set(";|&`$")


def load_run_config(path: Path) -> dict[str, Any]:
    data = load_yaml(path)
    return resolve_and_validate_config(data, path.parent.resolve())


def resolve_and_validate_config(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    cfg = copy.deepcopy(data)
    if cfg.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(f"schema_version must be {SCHEMA_VERSION!r}")
    _reject_unknown_top_level(cfg)
    project = _require_mapping(cfg, "project")
    project["name"] = safe_name(str(project.get("name", "")), "project.name")
    project["research_use_only"] = bool(project.get("research_use_only", True))
    if not project["research_use_only"]:
        raise ConfigError("project.research_use_only must be true")
    project["output_root"] = str(resolve_path(project.get("output_root", "./results"), base_dir))

    reference = _require_mapping(cfg, "reference")
    reference["id"] = safe_name(str(reference.get("id", "")), "reference.id")
    reference["build"] = str(reference.get("build", "")).strip()
    if not reference["build"]:
        raise ConfigError("reference.build is required")
    for key in ("fasta", "fai", "sequence_dictionary", "tandem_repeats_bed"):
        if reference.get(key):
            reference[key] = str(resolve_path(reference[key], base_dir))
    reference["checksum_policy"] = reference.get("checksum_policy", "metadata")
    reference["tandem_repeats_sort_policy"] = reference.get("tandem_repeats_sort_policy", "require_sorted")

    execution = _require_mapping(cfg, "execution")
    execution["backend"] = _enum(execution.get("backend", "local"), ALLOWED_EXECUTION_BACKENDS, "execution.backend")
    execution["tool_backend"] = execution.get("tool_backend", "native")
    execution["temp_root"] = str(resolve_path(execution.get("temp_root", "./tmp"), base_dir))
    execution["threads"] = _positive_int(execution.get("threads", 1), "execution.threads")
    execution["memory_gb"] = _positive_int(execution.get("memory_gb", 1), "execution.memory_gb")
    execution["keep_temp_on_failure"] = bool(execution.get("keep_temp_on_failure", True))
    execution["cleanup_on_success"] = bool(execution.get("cleanup_on_success", False))
    execution["overwrite"] = bool(execution.get("overwrite", False))
    scratch = execution.get("scratch", {}) or {}
    if not isinstance(scratch, dict):
        raise ConfigError("execution.scratch must be a mapping")
    execution["scratch"] = {
        "enabled": bool(scratch.get("enabled", False)),
        "root": str(resolve_path(scratch["root"], base_dir)) if scratch.get("root") else None,
        "copy_inputs": bool(scratch.get("copy_inputs", False)),
        "stage_outputs_locally": bool(scratch.get("stage_outputs_locally", True)),
        "copy_back_on_success": bool(scratch.get("copy_back_on_success", True)),
        "preserve_on_failure": bool(scratch.get("preserve_on_failure", True)),
        "allow_symlinks": bool(scratch.get("allow_symlinks", False)),
    }

    tools = _require_mapping(cfg, "tools")
    for tool_name, tool in tools.items():
        if not isinstance(tool, dict):
            raise ConfigError(f"tools.{tool_name} must be a mapping")
        _validate_tool(tool_name, tool, base_dir)

    workflow = cfg.setdefault("workflow", {})
    if not isinstance(workflow, dict):
        raise ConfigError("workflow must be a mapping")
    workflow["perform_dataset_merge"] = workflow.get("perform_dataset_merge", "auto")
    workflow["perform_alignment"] = workflow.get("perform_alignment", "auto")
    workflow["call_snv"] = bool(workflow.get("call_snv", True))
    workflow["call_sv"] = bool(workflow.get("call_sv", True))
    workflow["emit_gvcf"] = bool(workflow.get("emit_gvcf", True))
    workflow["legacy_naming"] = bool(workflow.get("legacy_naming", False))
    resources = cfg.setdefault("resources", {})
    if not isinstance(resources, dict):
        raise ConfigError("resources must be a mapping")
    for stage, profile in resources.items():
        if not isinstance(profile, dict):
            raise ConfigError(f"resources.{stage} must be a mapping")
        _validate_resource_profile(stage, profile)

    qc = cfg.setdefault("qc", {})
    if not isinstance(qc, dict):
        raise ConfigError("qc must be a mapping")
    qc.setdefault("thresholds", {"minimum_records": 1})
    qc.setdefault("alignment", {"minimum_mapped_fraction": None, "minimum_mean_depth": None, "maximum_low_mapq_fraction": None})
    qc.setdefault("snv", {"minimum_total_records": qc.get("thresholds", {}).get("minimum_records", 1), "minimum_pass_fraction": None, "titv_warn_low": None, "titv_warn_high": None})
    qc.setdefault("sv", {"minimum_total_records": 0, "maximum_low_support_fraction": None})
    qc.setdefault("checksum_outputs", False)
    cohort = cfg.setdefault("cohort", {})
    if not isinstance(cohort, dict):
        raise ConfigError("cohort must be a mapping")
    if cohort.get("max_rows") is not None:
        cohort["max_rows"] = _positive_int(cohort["max_rows"], "cohort.max_rows")
    joint = cfg.setdefault("joint_genotyping", {})
    if not isinstance(joint, dict):
        raise ConfigError("joint_genotyping must be a mapping")
    _validate_joint_genotyping(joint, base_dir)
    validate_run_config_schema(cfg)
    return cfg


def tool_config(cfg: dict[str, Any], name: str) -> ToolConfig:
    raw = cfg.get("tools", {}).get(name)
    if raw is None:
        raise ConfigError(f"Missing tool configuration: {name}")
    return ToolConfig(
        name=name,
        backend=raw.get("backend", "native"),
        executable=raw.get("executable"),
        version=raw.get("version"),
        container=Path(raw["container"]) if raw.get("container") else None,
        conda_environment=raw.get("conda_environment"),
        model_type=raw.get("model_type"),
        num_shards=raw.get("num_shards"),
        ccs_mode=bool(raw.get("ccs_mode", False)),
        extra_args=list(raw.get("extra_args", [])),
    )


def _validate_tool(name: str, tool: dict[str, Any], base_dir: Path) -> None:
    backend = _enum(tool.get("backend", "native"), ALLOWED_TOOL_BACKENDS, f"tools.{name}.backend")
    tool["backend"] = backend
    for key in ("executable", "conda_environment", "version", "model_type"):
        if tool.get(key) and any(ch in str(tool[key]) for ch in SHELL_FRAGMENT_CHARS):
            raise ConfigError(f"Unsafe shell-like value in tools.{name}.{key}")
    if tool.get("container"):
        tool["container"] = str(resolve_path(tool["container"], base_dir))
    if backend in {"apptainer", "singularity", "docker"} and not tool.get("container"):
        raise ConfigError(f"tools.{name}.container is required for backend {backend}")
    if backend == "native" and not tool.get("executable"):
        raise ConfigError(f"tools.{name}.executable is required for native backend")
    if name == "deepvariant":
        model = tool.get("model_type")
        if model is None:
            raise ConfigError("tools.deepvariant.model_type is required")
        _enum(model, ALLOWED_DEEPVARIANT_MODELS, "tools.deepvariant.model_type")
        tool["num_shards"] = _positive_int(tool.get("num_shards", 1), "tools.deepvariant.num_shards")
    for arg in tool.get("extra_args", []):
        if not isinstance(arg, str) or any(ch in arg for ch in SHELL_FRAGMENT_CHARS):
            raise ConfigError(f"Unsafe extra arg in tools.{name}.extra_args")


def _reject_unknown_top_level(cfg: dict[str, Any]) -> None:
    allowed = {"schema_version", "project", "reference", "execution", "tools", "workflow", "qc", "slurm", "resources", "cohort", "joint_genotyping"}
    unknown = set(cfg) - allowed
    if unknown:
        raise ConfigError(f"Unsupported top-level config keys: {sorted(unknown)}")


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{key} is required and must be a mapping")
    return value


def _enum(value: Any, allowed: set[str], label: str) -> str:
    text = str(value)
    if text not in allowed:
        raise ConfigError(f"{label} must be one of {sorted(allowed)}; got {text!r}")
    return text


def _positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise ConfigError(f"{label} must be a positive integer")
    return number


def _validate_resource_profile(stage: str, profile: dict[str, Any]) -> None:
    for key in ("cpus", "memory_gb", "scratch_gb"):
        value = profile.get(key)
        if value is not None:
            try:
                numeric = int(value)
            except (TypeError, ValueError) as exc:
                raise ConfigError(f"resources.{stage}.{key} must be an integer or null") from exc
            if numeric <= 0:
                raise ConfigError(f"resources.{stage}.{key} must be positive when supplied")
    walltime = profile.get("time")
    if walltime is not None:
        text = str(walltime)
        parts = text.split(":")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ConfigError(f"resources.{stage}.time must use HH:MM:SS when supplied")


def _validate_joint_genotyping(joint: dict[str, Any], base_dir: Path) -> None:
    joint["enabled"] = bool(joint.get("enabled", False))
    backend = joint.get("backend", "glnexus")
    if backend != "glnexus":
        raise ConfigError("joint_genotyping.backend must be 'glnexus' in Phase 2C")
    joint["backend"] = backend
    policy = joint.get("sample_identity_policy", "strict")
    if policy not in {"strict", "warn", "explicit_mapping"}:
        raise ConfigError("joint_genotyping.sample_identity_policy must be strict, warn, or explicit_mapping")
    joint["sample_identity_policy"] = policy
    level = joint.get("input_validation_level", "header")
    if level not in {"header", "indexed_probe", "full_scan"}:
        raise ConfigError("joint_genotyping.input_validation_level must be header, indexed_probe, or full_scan")
    joint["input_validation_level"] = level
    glnexus = joint.setdefault("glnexus", {})
    if not isinstance(glnexus, dict):
        raise ConfigError("joint_genotyping.glnexus must be a mapping")
    glnexus.setdefault("executable", "glnexus_cli")
    glnexus.setdefault("config_name", "DeepVariantWGS")
    glnexus.setdefault("extra_args", [])
    if any(ch in str(glnexus.get("executable", "")) for ch in SHELL_FRAGMENT_CHARS):
        raise ConfigError("Unsafe shell-like value in joint_genotyping.glnexus.executable")
    for arg in glnexus.get("extra_args", []):
        if not isinstance(arg, str) or any(ch in arg for ch in SHELL_FRAGMENT_CHARS):
            raise ConfigError("Unsafe extra arg in joint_genotyping.glnexus.extra_args")
    container = glnexus.setdefault("container", {"engine": None, "image": None, "digest": None})
    if not isinstance(container, dict):
        raise ConfigError("joint_genotyping.glnexus.container must be a mapping")
    if container.get("image"):
        container["image"] = str(resolve_path(container["image"], base_dir))
    output = joint.setdefault("output", {})
    if not isinstance(output, dict):
        raise ConfigError("joint_genotyping.output must be a mapping")
    output.setdefault("cohort_vcf_name", "cohort.germline.vcf.gz")
    sharding = joint.setdefault("sharding", {})
    if not isinstance(sharding, dict):
        raise ConfigError("joint_genotyping.sharding must be a mapping")
    sharding.setdefault("mode", "contig")
    if sharding["mode"] not in {"contig", "interval_file"}:
        raise ConfigError("joint_genotyping.sharding.mode must be contig or interval_file in Phase 2C")
    sharding.setdefault("include_contigs", [])
    sharding.setdefault("exclude_contigs", [])
    sharding.setdefault("max_shards", None)
