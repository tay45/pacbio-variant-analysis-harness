"""GLnexus and final VCF command construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.models import CommandSpec
from variant_analysis_harness.joint.inputs import JointInput
from variant_analysis_harness.joint.sharding import JointShard


def build_glnexus_command(cfg: dict[str, Any], shard: JointShard, inputs: list[JointInput], attempt_dir: Path) -> tuple[CommandSpec, Path]:
    joint_cfg = cfg.get("joint_genotyping", {})
    glnexus = joint_cfg.get("glnexus", {})
    backend = joint_cfg.get("backend", "glnexus")
    if backend != "glnexus":
        raise ValueError("Phase 2C supports only GLnexus")
    input_list = attempt_dir / "inputs" / f"{shard.shard_id}.gvcfs.list"
    input_list.parent.mkdir(parents=True, exist_ok=True)
    input_list.write_text("\n".join(str(item.gvcf_path) for item in inputs if item.enabled) + "\n", encoding="utf-8")
    output_tmp = shard.output_vcf.with_name(shard.output_vcf.name + ".tmp")
    executable = glnexus.get("executable") or "glnexus_cli"
    preset = glnexus.get("config_name") or "DeepVariantWGS"
    argv = [executable, "--config", preset, "--bed", f"{shard.contig}:{shard.start}-{shard.end}", "--list", str(input_list), "--output", str(output_tmp)]
    argv.extend(str(arg) for arg in glnexus.get("extra_args", []))
    container = glnexus.get("container") or {}
    if container.get("engine") and container.get("image"):
        argv = [container["engine"], "exec", container["image"], *argv]
    spec = CommandSpec(
        stage="joint_genotyping_shard",
        tool_name="glnexus",
        argv=argv,
        inputs=[input_list],
        outputs=[output_tmp],
        cwd=attempt_dir,
    )
    return spec, input_list


def build_concat_commands(cfg: dict[str, Any], shard_outputs: list[Path], final_vcf: Path) -> list[CommandSpec]:
    tools = cfg.get("tools", {})
    bcftools = tools.get("bcftools", {}).get("executable") or "bcftools"
    tabix = tools.get("tabix", {}).get("executable") or "tabix"
    tmp = final_vcf.with_name(final_vcf.name + ".tmp")
    concat = CommandSpec("joint_genotyping_concat", "bcftools", [bcftools, "concat", "-Oz", "-o", str(tmp), *[str(p) for p in shard_outputs]], inputs=shard_outputs, outputs=[tmp])
    index = CommandSpec("joint_genotyping_index", "tabix", [tabix, "-f", "-p", "vcf", str(final_vcf)], inputs=[final_vcf], outputs=[Path(str(final_vcf) + ".tbi")])
    return [concat, index]


def command_signature(spec: CommandSpec) -> str:
    return object_signature({"argv": spec.argv, "inputs": [str(p) for p in spec.inputs], "outputs": [str(p) for p in spec.outputs]})

