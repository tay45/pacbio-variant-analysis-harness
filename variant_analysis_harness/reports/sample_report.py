"""Markdown sample report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER
from variant_analysis_harness.models import Sample


def write_sample_report(
    path: Path,
    *,
    project_id: str,
    sample: Sample,
    attempt_id: str,
    config: dict[str, Any],
    stage_statuses: list[dict[str, Any]],
    outputs: list[Path],
    snv_qc: dict[str, Any] | None = None,
    sv_qc: dict[str, Any] | None = None,
) -> None:
    lines = [
        f"# Sample Report: {sample.sample_id}",
        "",
        f"**{RESEARCH_USE_DISCLAIMER}**",
        "",
        "## Identifiers",
        f"- Project: {project_id}",
        f"- Sample: {sample.sample_id}",
        f"- Attempt: {attempt_id}",
        "",
        "## Input Summary",
        f"- Platform: {sample.platform}",
        f"- Input type: {sample.input_type}",
        f"- Primary input: {sample.input_path}",
        f"- Additional inputs: {', '.join(str(p) for p in sample.additional_inputs) or 'None'}",
        "",
        "## Reference Summary",
        f"- Reference ID: {config['reference']['id']}",
        f"- Build: {config['reference']['build']}",
        f"- FASTA: {config['reference']['fasta']}",
        f"- Checksum policy: {config['reference'].get('checksum_policy')}",
        "",
        "## Tool and Backend Summary",
    ]
    for name, tool in config.get("tools", {}).items():
        lines.append(f"- {name}: backend={tool.get('backend')}, version={tool.get('version')}")
    lines.extend(
        [
            "",
            "## Stage Status",
            "| Stage | Status | Exit code | Runtime seconds |",
            "|---|---:|---:|---:|",
        ]
    )
    for status in stage_statuses:
        lines.append(
            f"| {status.get('stage')} | {status.get('status')} | {status.get('exit_code')} | {status.get('runtime_seconds')} |"
        )
    lines.extend(["", "## Alignment Summary", "Alignment metrics are dependency-light in Phase 2A and may be NOT_EVALUATED."])
    lines.extend(["", "## Germline SNV/indel QC", _format_qc(snv_qc)])
    lines.extend(["", "## Germline SV QC", _format_qc(sv_qc)])
    lines.extend(["", "## Output Inventory"])
    lines.extend(f"- {path}" for path in outputs)
    lines.extend(
        [
            "",
            "## Known Limitations",
            "- This Phase 2A harness implements PacBio HiFi germline SNV/indel and germline SV workflows only.",
            "- Successful technical completion does not establish scientific or clinical validity.",
            "- Somatic, CNV, ONT-specific, Illumina-specific, and cohort SV joint workflows are deferred.",
            "",
            "## Recommended Manual Review",
            "- Review stage logs, status JSON, provenance JSON, raw VCFs, and QC summaries.",
            "- Confirm tool versions, reference build, model type, and sample identity before interpreting results.",
            "",
            "## Troubleshooting",
            "- See `docs/troubleshooting.md` and the stage-specific `stdout.log`, `stderr.log`, and `stage.status.json` files.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_qc(qc: dict[str, Any] | None) -> str:
    if qc is None:
        return "NOT_EVALUATED"
    return "```json\n" + json.dumps(qc, indent=2, sort_keys=True) + "\n```"
