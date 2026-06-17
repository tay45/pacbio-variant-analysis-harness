"""PacBio HiFi pbmm2 alignment command construction."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.common.validation import validate_bam_like
from variant_analysis_harness.execution.base import wrap_tool_command
from variant_analysis_harness.models import CommandSpec, Sample, ToolConfig


def build_pbmm2_align_command(
    sample: Sample,
    tool: ToolConfig,
    reference_fasta: Path,
    input_reads: Path,
    output_bam: Path,
    threads: int,
) -> CommandSpec:
    inner = [
        "align",
        str(reference_fasta),
        str(input_reads),
        str(output_bam),
        "--sort",
        "--preset",
        "CCS",
        "--sample",
        sample.read_group_sample,
        "-j",
        str(threads),
    ]
    argv = wrap_tool_command(
        tool,
        inner,
        bind_paths=[reference_fasta.parent, input_reads.parent, output_bam.parent],
    )
    return CommandSpec("alignment", "pbmm2", argv, inputs=[reference_fasta, input_reads], outputs=[output_bam], cwd=output_bam.parent)


def validate_aligned_bam(path: Path) -> None:
    validate_bam_like(path)
