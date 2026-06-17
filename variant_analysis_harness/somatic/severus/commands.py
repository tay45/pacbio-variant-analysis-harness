"""Safe Severus command construction from verified official contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.models import CommandSpec
from variant_analysis_harness.somatic.manifest import SomaticPair
from variant_analysis_harness.somatic.severus.compatibility import SEVERUS_CONTRACT_VERSION, protected_extra_arg_conflicts
from variant_analysis_harness.somatic.severus.config import decide_supplementary_tag, validate_severus_config


def severus_pair_attempt_dir(project_attempt_dir: Path, pair: SomaticPair, attempt_id: str) -> Path:
    shard = pair.pair_id[:2] if len(pair.pair_id) >= 2 else "_"
    return project_attempt_dir / "pairs" / shard / pair.pair_id / attempt_id


def severus_output_paths(pair_attempt_dir: Path) -> dict[str, Path]:
    base = pair_attempt_dir / "structural_variants" / "severus"
    return {
        "base": base,
        "logs": base / "logs",
        "temporary": base / "temporary",
        "intermediate": base / "intermediate",
        "native_outputs": base / "native_outputs",
        "standardized": base / "standardized",
        "validation": base / "validation",
        "qc": base / "qc",
        "provenance": base / "provenance",
        "status": pair_attempt_dir / "status",
        "standard_vcf": base / "standardized" / "somatic_sv.vcf",
    }


def build_severus_base_argv(*, pair: SomaticPair, reference: Path, sev_config: dict[str, Any], output_paths: dict[str, Path]) -> list[str]:
    control = pair.normal_input_path if pair.analysis_mode == "tumor_normal" else None
    return build_severus_multi_target_base_argv(
        target_bams=[pair.tumor_input_path],
        control_bam=control,
        analysis_mode=pair.analysis_mode,
        sev_config=sev_config,
        output_paths=output_paths,
    )


def build_severus_multi_target_base_argv(
    *,
    target_bams: list[Path],
    control_bam: Path | None,
    analysis_mode: str,
    sev_config: dict[str, Any],
    output_paths: dict[str, Path],
) -> list[str]:
    sev = sev_config["severus"]
    validation = validate_severus_config(sev_config, mode=analysis_mode)
    if validation["status"] == "FAIL":
        raise ValueError("; ".join(validation["errors"]))
    if not validation["version"].get("execution_allowed", False):
        raise ValueError("Severus execution command generation requires a verified contract")
    capability = validation["version"]["capability"]
    if not target_bams:
        raise ValueError("Severus command requires at least one target BAM")
    if len({str(path) for path in target_bams}) != len(target_bams):
        raise ValueError("duplicate target BAM inputs are not allowed")
    if analysis_mode == "tumor_normal" and control_bam is None:
        raise ValueError("matched tumor-normal Severus command requires normal input")
    if analysis_mode == "tumor_only" and control_bam is not None:
        raise ValueError("tumor-only Severus command must not include control input")
    if control_bam and str(control_bam) in {str(path) for path in target_bams}:
        raise ValueError("control BAM must not also be provided as a target BAM")
    if len(target_bams) > 1 and not capability.get("multi_sample"):
        raise ValueError("multiple target BAMs are not supported by the verified Severus contract")
    extra_args = list((sev.get("parameters", {}) or {}).get("extra_args", []))
    conflicts = protected_extra_arg_conflicts(extra_args)
    if conflicts:
        raise ValueError(f"extra_args cannot override protected or unavailable Severus flags: {sorted(set(conflicts))}")
    argv = [capability["entry_point"], capability["target_input_flag"], *[str(path) for path in target_bams]]
    if control_bam is not None:
        argv.extend([capability["control_input_flag"], str(control_bam)])
    argv.extend([capability["output_directory_flag"], str(output_paths["native_outputs"])])
    params = sev.get("parameters", {}) or {}
    if params.get("threads"):
        argv.extend([capability["thread_flag"], str(params["threads"])])
    phasing = sev.get("phasing", {}) or {}
    if phasing.get("phased_vcf"):
        argv.extend([capability["phasing_vcf_flag"], str(phasing["phased_vcf"])])
    if params.get("vntr_bed"):
        argv.extend([capability["vntr_bed_flag"], str(params["vntr_bed"])])
    if params.get("pon"):
        argv.extend([capability["pon_flag"], str(params["pon"])])
    for field, contract_key in (("min_support", "min_support"), ("min_mapq", "min_mapq"), ("min_sv_size", "min_sv_size"), ("vaf_threshold", "vaf_threshold"), ("tin_ratio", "tin_ratio")):
        if params.get(field) is not None:
            argv.extend([capability["optional_parameter_flags"][contract_key], str(params[field])])
    supplementary = decide_supplementary_tag(phasing)
    if supplementary["emit"]:
        argv.append(capability["supplementary_tag_flag"])
    argv.extend(extra_args)
    return argv


def wrap_severus_command(base_argv: list[str], sev_config: dict[str, Any], *, bind_paths: list[Path]) -> list[str]:
    sev = sev_config["severus"]
    mode = sev.get("execution", {}).get("mode", "container")
    if mode == "executable":
        executable = sev.get("executable", {}).get("path") or base_argv[0]
        return [str(executable), *base_argv[1:]]
    container = sev.get("container", {}) or {}
    engine = container.get("engine", "docker")
    image = container.get("image") or "severus"
    tag = container.get("tag")
    digest = container.get("digest")
    image_ref = f"{image}:{tag}" if tag else image
    if digest:
        image_ref = f"{image_ref}@{digest}"
    binds = sorted({str(path) for path in bind_paths})
    if engine == "docker":
        argv = ["docker", "run", "--rm"]
        for path in binds:
            argv.extend(["-v", f"{path}:{path}"])
        argv.extend(container.get("extra_args", []))
        return [*argv, image_ref, *base_argv]
    if engine in {"apptainer", "singularity"}:
        argv = [engine, "exec"]
        if binds:
            argv.extend(["--bind", ",".join(f"{p}:{p}" for p in binds)])
        argv.extend(container.get("extra_args", []))
        return [*argv, image_ref, *base_argv]
    raise ValueError(f"unsupported container engine: {engine}")


def build_severus_command_spec(*, pair: SomaticPair, reference: Path, sev_config: dict[str, Any], project_attempt_dir: Path, pair_attempt_id: str) -> tuple[CommandSpec, dict[str, Path]]:
    paths = severus_output_paths(severus_pair_attempt_dir(project_attempt_dir, pair, pair_attempt_id))
    base_argv = build_severus_base_argv(pair=pair, reference=reference, sev_config=sev_config, output_paths=paths)
    binds = [pair.tumor_input_path.parent, paths["base"]]
    if pair.normal_input_path:
        binds.append(pair.normal_input_path.parent)
    sev = sev_config.get("severus", {})
    for value in [
        (sev.get("phasing", {}) or {}).get("phased_vcf"),
        (sev.get("phasing", {}) or {}).get("phased_vcf_index"),
        (sev.get("parameters", {}) or {}).get("vntr_bed"),
        (sev.get("parameters", {}) or {}).get("pon"),
    ]:
        if value:
            binds.append(Path(value).parent)
    argv = wrap_severus_command(base_argv, sev_config, bind_paths=binds)
    inputs = [pair.tumor_input_path]
    if pair.normal_input_path:
        inputs.append(pair.normal_input_path)
    return CommandSpec("somatic_sv_severus", "severus", argv, inputs=inputs, outputs=[paths["standard_vcf"]], cwd=paths["base"]), paths


def command_signature(argv: list[str]) -> str:
    return object_signature({"severus_contract_version": SEVERUS_CONTRACT_VERSION, "argv": argv})


def sanitized_command(argv: list[str]) -> list[str]:
    return list(argv)
