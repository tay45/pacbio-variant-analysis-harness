"""Cohort Markdown and dependency-light HTML reporting."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER


PORTFOLIO_WORDING = (
    "This repository implements a research-use, configuration-driven germline SNV/SV workflow harness "
    "with tested single-sample execution logic and scalable cohort orchestration. Cohort planning, "
    "Slurm array generation, failure recovery, status aggregation, and reporting are tested using "
    "mocked and synthetic inputs, including a 3,000-sample planning simulation. Full biological "
    "validation with production-scale sequencing datasets remains future work."
)


def write_cohort_report(
    cohort_dir: Path,
    *,
    plan: dict[str, Any],
    status_summary: dict[str, Any],
    qc_summary: dict[str, Any],
    storage_estimate: dict[str, Any] | None = None,
    incremental_summary: list[dict[str, Any]] | None = None,
    html_report: bool = False,
) -> Path:
    reports = cohort_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "cohort_report.md"
    lines = [
        "# Cohort Report",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        "Technical completion does not establish biological or clinical validity.",
        "",
        "## Cohort Identifiers",
        f"- Cohort ID: {plan.get('cohort_id')}",
        f"- Cohort attempt: {plan.get('cohort_attempt_id')}",
        f"- Package version: {plan.get('workflow_package_version')}",
        "",
        "## Cohort Size",
        f"- Selected samples: {len(plan.get('selected_samples', []))}",
        f"- Excluded samples: {len(plan.get('excluded_samples', []))}",
        "",
        "## Analysis Modes",
    ]
    mode_counts: dict[str, int] = {}
    input_counts: dict[str, int] = {}
    for sample in plan.get("selected_samples", []):
        mode_counts[sample["analysis"]] = mode_counts.get(sample["analysis"], 0) + 1
        input_counts[sample["input_type"]] = input_counts.get(sample["input_type"], 0) + 1
    lines.extend(_counts(mode_counts))
    lines.extend(["", "## Input Types"])
    lines.extend(_counts(input_counts))
    lines.extend(
        [
            "",
            "## Reference Summary",
            f"- Reference signature: {plan.get('reference_signature')}",
            "",
            "## Tool/Container Summary",
            f"- Tool/container signature: {plan.get('tool_container_signatures')}",
            "",
            "## Execution Plan",
            f"- Array task count: {plan.get('task_count')}",
            f"- Maximum concurrency: {plan.get('maximum_concurrency')}",
            "",
            "## Slurm Plan Or Execution Summary",
            "- Site-neutral Slurm array scripts are generated only; submission is disabled by default.",
            "",
            "## Status Counts",
        ]
    )
    lines.extend(_counts(status_summary.get("status_counts", {})))
    lines.extend(["", "## Completion Rate"])
    success = status_summary.get("status_counts", {}).get("success", 0)
    total = max(1, len(plan.get("selected_samples", [])))
    lines.append(f"- Success or warning records: {success}/{total}")
    lines.extend(["", "## Failure Categories"])
    lines.extend(_counts(status_summary.get("failure_category_counts", {})))
    lines.extend(["", "## Warning Summary", "- See cohort_status and cohort_qc artifacts for per-sample warnings."])
    lines.extend(["", "## Alignment QC Summary", "- Aggregated only when sample-level metrics are available."])
    lines.extend(["", "## Germline SNV QC Summary", "- Aggregated only for selected SNV/combined samples with available metrics."])
    lines.extend(["", "## Germline SV QC Summary", "- Aggregated only for selected SV/combined samples with available metrics."])
    lines.extend(["", "## Missing Metrics", f"- Rows with missing metrics: {sum(1 for r in qc_summary.get('rows', []) if r.get('missing_metrics'))}"])
    lines.extend(["", "## Reused Prior Outputs"])
    reused = [r for r in (incremental_summary or []) if r.get("decision") == "reuse_candidate"]
    lines.append(f"- Reuse candidates: {len(reused)}")
    lines.extend(["", "## New Samples"])
    new = [r for r in (incremental_summary or []) if r.get("decision") == "new"]
    lines.append(f"- New samples: {len(new)}")
    lines.extend(["", "## Rerun Candidates", "- Generate with cohort-rerun-manifest after status aggregation."])
    lines.extend(["", "## Runtime/Resource Summary", "- Runtime and resource usage are populated from status records when available."])
    lines.extend(["", "## Storage Estimate"])
    if storage_estimate:
        lines.append(f"- Final retained estimate GB: {storage_estimate.get('final_retained_gb')}")
        lines.append(f"- Temporary peak estimate GB: {storage_estimate.get('temporary_peak_gb')}")
    else:
        lines.append("- Not generated.")
    lines.extend(["", "## Output Inventory", "- See cohort_outputs.manifest.json."])
    lines.extend(
        [
            "",
            "## Known Limitations",
            "- Research-use only.",
            "- No somatic, CNV, Illumina-specific, Oxford Nanopore-specific, clinical, or diagnostic functionality is implemented.",
            "- 3,000-sample scale testing uses synthetic planning data, not real sequencing data.",
            "- Cohort SV joint calling remains future work.",
            "",
            "## Recommended Operator Actions",
            "- Review validation artifacts, array scripts, status summaries, and per-sample reports before rerun or manual submission.",
            "",
            "## Portfolio Wording",
            PORTFOLIO_WORDING,
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if html_report:
        html_path = reports / "cohort_report.html"
        body = "<br>\n".join(html.escape(line) for line in lines)
        html_path.write_text(f"<!doctype html><html><body>{body}</body></html>\n", encoding="utf-8")
    return path


def write_output_manifest(cohort_dir: Path) -> None:
    outputs = [str(path.relative_to(cohort_dir)) for path in sorted(cohort_dir.rglob("*")) if path.is_file()]
    (cohort_dir / "cohort_outputs.manifest.json").write_text(json.dumps({"outputs": outputs}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _counts(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- none"]
    return [f"- {key}: {value}" for key, value in sorted(counts.items())]
