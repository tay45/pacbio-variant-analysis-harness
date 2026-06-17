"""PacBio dataset XML merge command construction."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.common.validation import validate_xml
from variant_analysis_harness.execution.base import wrap_tool_command
from variant_analysis_harness.models import CommandSpec, Sample, ToolConfig


def build_dataset_merge_command(sample: Sample, tool: ToolConfig, output_xml: Path) -> CommandSpec:
    xmls = [sample.input_path] + list(sample.additional_inputs)
    for xml in xmls:
        validate_xml(xml)
    inner = [
        "merge",
        "--remove-parentage",
        "--unique-collections",
        "--no-sub-datasets",
        "--name",
        sample.sample_id,
        str(output_xml),
    ] + [str(p) for p in xmls]
    argv = wrap_tool_command(tool, inner, bind_paths=[p.parent for p in xmls] + [output_xml.parent])
    return CommandSpec("dataset_merge", "dataset", argv, inputs=xmls, outputs=[output_xml], cwd=output_xml.parent)


def build_dataset_newuuid_command(tool: ToolConfig, merged_xml: Path) -> CommandSpec:
    inner = ["newuuid", "--random", str(merged_xml)]
    argv = wrap_tool_command(tool, inner, bind_paths=[merged_xml.parent])
    return CommandSpec("dataset_newuuid", "dataset", argv, inputs=[merged_xml], outputs=[merged_xml], cwd=merged_xml.parent)
