"""DeepVariant germline SNV/indel command construction."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.execution.base import wrap_tool_command
from variant_analysis_harness.models import CommandSpec, ToolConfig


def build_deepvariant_command(
    tool: ToolConfig,
    reference_fasta: Path,
    reads_bam: Path,
    output_vcf: Path,
    output_gvcf: Path | None,
    logging_dir: Path,
) -> CommandSpec:
    if not tool.model_type:
        raise ValueError("DeepVariant model_type is required")
    inner = [
        "run_deepvariant",
        f"--model_type={tool.model_type}",
        f"--ref={reference_fasta}",
        f"--reads={reads_bam}",
        f"--output_vcf={output_vcf}",
        f"--num_shards={tool.num_shards or 1}",
        f"--logging_dir={logging_dir}",
        "--runtime_report",
    ]
    if output_gvcf:
        inner.append(f"--output_gvcf={output_gvcf}")
    inner.extend(tool.extra_args)
    outputs = [output_vcf] + ([output_gvcf] if output_gvcf else [])
    argv = wrap_tool_command(
        tool,
        inner,
        bind_paths=[reference_fasta.parent, reads_bam.parent, output_vcf.parent, logging_dir],
    )
    return CommandSpec("germline_snv", "deepvariant", argv, inputs=[reference_fasta, reads_bam], outputs=outputs, cwd=output_vcf.parent)
