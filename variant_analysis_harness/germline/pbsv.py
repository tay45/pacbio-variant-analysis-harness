"""pbsv PacBio germline structural-variant command construction."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.execution.base import wrap_tool_command
from variant_analysis_harness.models import CommandSpec, ToolConfig


def build_pbsv_discover_command(
    tool: ToolConfig,
    aligned_bam: Path,
    svsig: Path,
    tandem_repeats_bed: Path | None,
) -> CommandSpec:
    inner = ["discover"]
    if tool.ccs_mode:
        inner.append("--ccs")
    if tandem_repeats_bed:
        inner.extend(["--tandem-repeats", str(tandem_repeats_bed)])
    inner.extend([str(aligned_bam), str(svsig)])
    binds = [aligned_bam.parent, svsig.parent]
    if tandem_repeats_bed:
        binds.append(tandem_repeats_bed.parent)
    argv = wrap_tool_command(tool, inner, bind_paths=binds)
    return CommandSpec("germline_sv_discover", "pbsv", argv, inputs=[aligned_bam], outputs=[svsig], cwd=svsig.parent)


def build_pbsv_call_command(tool: ToolConfig, reference_fasta: Path, svsig: Path, output_vcf: Path) -> CommandSpec:
    inner = ["call", str(reference_fasta), str(svsig), str(output_vcf)]
    argv = wrap_tool_command(tool, inner, bind_paths=[reference_fasta.parent, svsig.parent, output_vcf.parent])
    return CommandSpec("germline_sv_call", "pbsv", argv, inputs=[reference_fasta, svsig], outputs=[output_vcf], cwd=output_vcf.parent)
