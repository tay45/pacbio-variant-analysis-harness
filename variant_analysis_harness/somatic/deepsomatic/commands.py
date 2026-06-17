"""Safe DeepSomatic command construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.models import CommandSpec
from variant_analysis_harness.somatic.deepsomatic.compatibility import protected_extra_arg_conflicts
from variant_analysis_harness.somatic.deepsomatic.config import validate_deepsomatic_config
from variant_analysis_harness.somatic.manifest import SomaticPair


def deepsomatic_pair_attempt_dir(project_attempt_dir: Path, pair: SomaticPair, attempt_id: str) -> Path:
    shard = pair.pair_id[:2] if len(pair.pair_id) >= 2 else "_"
    return project_attempt_dir / "pairs" / shard / pair.pair_id / attempt_id


def deepsomatic_output_paths(pair_attempt_dir: Path, *, emit_gvcf: bool = True) -> dict[str, Path]:
    base = pair_attempt_dir / "small_variants" / "deepsomatic"
    paths = {
        "base": base,
        "logs": base / "logs",
        "intermediate": base / "intermediate",
        "temporary": base / "temporary",
        "output": base / "output",
        "validation": base / "validation",
        "qc": base / "qc",
        "provenance": base / "provenance",
        "status": pair_attempt_dir / "status",
        "vcf": base / "output" / "somatic.vcf.gz",
        "vcf_index": base / "output" / "somatic.vcf.gz.tbi",
        "gvcf": base / "output" / "somatic.g.vcf.gz",
        "gvcf_index": base / "output" / "somatic.g.vcf.gz.tbi",
    }
    if not emit_gvcf:
        paths.pop("gvcf")
        paths.pop("gvcf_index")
    return paths


def build_run_deepsomatic_argv(
    *,
    pair: SomaticPair,
    reference: Path,
    ds_config: dict[str, Any],
    output_paths: dict[str, Path],
) -> list[str]:
    ds = ds_config["deepsomatic"]
    mode = pair.analysis_mode
    validation = validate_deepsomatic_config(ds_config, mode=mode)
    if validation["status"] == "FAIL":
        raise ValueError("; ".join(validation["errors"]))
    model_type = ds["model_type"][mode]
    extra_args = list((ds.get("advanced", {}) or {}).get("extra_args", []))
    conflicts = protected_extra_arg_conflicts(extra_args)
    if conflicts:
        raise ValueError(f"extra_args cannot override protected flags: {sorted(set(conflicts))}")
    argv = [
        "run_deepsomatic",
        f"--model_type={model_type}",
        f"--ref={reference}",
        f"--reads_tumor={pair.tumor_input_path}",
        f"--output_vcf={output_paths['vcf']}",
        f"--sample_name_tumor={pair.tumor_sample_id}",
        f"--logging_dir={output_paths['logs']}",
        f"--intermediate_results_dir={output_paths['intermediate']}",
    ]
    if mode == "tumor_normal":
        if pair.normal_input_path is None or not pair.normal_sample_id:
            raise ValueError("matched tumor-normal DeepSomatic command requires a normal input and sample name")
        argv.extend([f"--reads_normal={pair.normal_input_path}", f"--sample_name_normal={pair.normal_sample_id}"])
    else:
        if pair.normal_input_path is not None or pair.normal_sample_id:
            raise ValueError("tumor-only DeepSomatic command must not include normal input fields")
    if ds.get("outputs", {}).get("emit_gvcf", True):
        argv.append(f"--output_gvcf={output_paths['gvcf']}")
    num_shards = ds.get("resources", {}).get("num_shards")
    if num_shards:
        argv.append(f"--num_shards={num_shards}")
    regions = ds.get("regions", {}) or {}
    if regions.get("mode") == "regions":
        for region in regions.get("values", []):
            argv.append(f"--regions={region}")
    if regions.get("mode") == "region_file" and regions.get("file"):
        argv.append(f"--regions={regions['file']}")
    model_cfg = ds.get("model", {}) or {}
    if model_cfg.get("custom_model_path"):
        argv.append(f"--customized_model={model_cfg['custom_model_path']}")
    pon = ds.get("pon", {}) or {}
    if pon.get("enabled") and pon.get("path"):
        argv.append(f"--pon={pon['path']}")
    argv.extend(extra_args)
    return argv


def wrap_deepsomatic_command(base_argv: list[str], ds_config: dict[str, Any], *, bind_paths: list[Path]) -> list[str]:
    ds = ds_config["deepsomatic"]
    mode = ds.get("execution", {}).get("mode", "container")
    if mode == "executable":
        executable = ds.get("executable", {}).get("path") or base_argv[0]
        return [str(executable), *base_argv[1:]]
    container = ds.get("container", {}) or {}
    engine = container.get("engine", "docker")
    image = container.get("image", "google/deepsomatic")
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
        argv.extend([image_ref, *base_argv])
        return argv
    if engine in {"apptainer", "singularity"}:
        argv = [engine, "exec"]
        if binds:
            argv.extend(["--bind", ",".join(f"{path}:{path}" for path in binds)])
        argv.extend(container.get("extra_args", []))
        argv.extend([image_ref, *base_argv])
        return argv
    raise ValueError(f"unsupported container engine: {engine}")


def build_deepsomatic_command_spec(
    *,
    pair: SomaticPair,
    reference: Path,
    ds_config: dict[str, Any],
    project_attempt_dir: Path,
    pair_attempt_id: str,
) -> tuple[CommandSpec, dict[str, Path]]:
    output_paths = deepsomatic_output_paths(
        deepsomatic_pair_attempt_dir(project_attempt_dir, pair, pair_attempt_id),
        emit_gvcf=bool(ds_config["deepsomatic"].get("outputs", {}).get("emit_gvcf", True)),
    )
    base_argv = build_run_deepsomatic_argv(pair=pair, reference=reference, ds_config=ds_config, output_paths=output_paths)
    bind_paths = [reference.parent, pair.tumor_input_path.parent, output_paths["base"]]
    if pair.normal_input_path:
        bind_paths.append(pair.normal_input_path.parent)
    argv = wrap_deepsomatic_command(base_argv, ds_config, bind_paths=bind_paths)
    outputs = [output_paths["vcf"], output_paths["vcf_index"]]
    if "gvcf" in output_paths:
        outputs.extend([output_paths["gvcf"], output_paths["gvcf_index"]])
    return CommandSpec("somatic_snv_deepsomatic", "deepsomatic", argv, inputs=[pair.tumor_input_path], outputs=outputs, cwd=output_paths["base"]), output_paths


def command_signature(argv: list[str]) -> str:
    return object_signature(argv)


def sanitized_command(argv: list[str]) -> list[str]:
    return list(argv)
