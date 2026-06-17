"""Integrated somatic reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER
from variant_analysis_harness.somatic.integrated.status import status_counts

PORTFOLIO_WORDING = (
    "The integrated somatic evidence layer unifies validated DeepSomatic small-variant and Severus structural-variant results without collapsing their distinct analytical semantics. "
    "It verifies pair identity, reference compatibility, source-attempt integrity, caller output validation, and provenance before generating pair-level and cohort-level technical summaries. "
    "The layer characterizes regional relationships between small variants and structural-variant intervals or breakpoints, aggregates caller-specific QC and failures, produces stage-specific rerun recommendations, and creates operator, portfolio, and recruiter-facing reports. "
    "Validation uses synthetic and mocked data, including deterministic 3,000-pair reporting tests; biological benchmarking on real tumor cohorts remains future work."
)


def write_reports(project: dict[str, Any], pair_rows: list[dict[str, Any]], relationships: list[dict[str, Any]], qc: dict[str, Any], recommendations: list[dict[str, Any]], out_dir: Path) -> dict[str, str]:
    report_dir = out_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "integrated": report_dir / "integrated_somatic_report.md",
        "operator": report_dir / "integrated_operator_report.md",
        "portfolio": report_dir / "integrated_portfolio_report.md",
        "recruiter": report_dir / "integrated_recruiter_summary.md",
    }
    counts = status_counts(pair_rows)
    paths["integrated"].write_text(_integrated_report(project, counts, relationships, qc, recommendations), encoding="utf-8")
    paths["operator"].write_text(_operator_report(pair_rows, recommendations), encoding="utf-8")
    paths["portfolio"].write_text(_portfolio_report(project), encoding="utf-8")
    paths["recruiter"].write_text(_recruiter_summary(), encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def write_machine_summary(project: dict[str, Any], pair_rows: list[dict[str, Any]], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"project": project, "status_counts": status_counts(pair_rows), "pair_count": len(pair_rows)}
    (out_dir / "integrated_somatic_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    with (out_dir / "integrated_somatic_summary.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerow({"metric": "pair_count", "value": len(pair_rows)})
        for key, value in summary["status_counts"].items():
            writer.writerow({"metric": f"status_{key}", "value": value})
    (out_dir / "integrated_pair_status.json").write_text(json.dumps(pair_rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    fields = ["pair_id", "subject_id", "analysis_mode", "integrated_status", "identity_compatibility", "reference_compatibility"]
    with (out_dir / "integrated_pair_status.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for row in pair_rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    lines = ["# Integrated Pair Status", ""]
    lines.extend(f"- {row.get('pair_id')}: {row.get('integrated_status')}" for row in pair_rows[:200])
    (out_dir / "integrated_pair_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _integrated_report(project: dict[str, Any], counts: dict[str, int], relationships: list[dict[str, Any]], qc: dict[str, Any], recommendations: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Integrated Somatic Report",
            "",
            RESEARCH_USE_DISCLAIMER,
            "",
            "Technical completion does not establish biological validity. Outputs are not for clinical use.",
            "",
            f"Project: {project.get('somatic_project_id')}",
            f"Integrated attempt: {project.get('integrated_attempt_id')}",
            f"Pair counts: {counts}",
            f"Relationship rows: {len(relationships)}",
            f"QC readiness: {qc.get('overall_readiness')}",
            f"Rerun recommendations: {len(recommendations)}",
            "",
            "## Validation Boundaries",
            "No pathogenicity, treatment relevance, driver status, clonality, copy-number state, chromothripsis, kataegis, or clinical tiering is inferred.",
            "",
            "## Missing Data",
            "Missing caller data remains explicit and may produce partial-success status according to policy.",
        ]
    ) + "\n"


def _operator_report(pair_rows: list[dict[str, Any]], recommendations: list[dict[str, Any]]) -> str:
    lines = ["# Integrated Operator Report", "", "Operational summary only; no biological interpretation.", ""]
    for rec in recommendations[:200]:
        lines.append(f"- {rec.get('pair_id')}: {rec.get('recommendation')}")
    return "\n".join(lines) + "\n"


def _portfolio_report(project: dict[str, Any]) -> str:
    sections = [
        "# Integrated Portfolio Report",
        "",
        PORTFOLIO_WORDING,
        "",
        "## Architecture Overview",
        "DeepSomatic and Severus remain separate caller layers; integration is a derived evidence/reporting layer.",
        "",
        "## Validation Boundaries",
        "Synthetic and mocked tests demonstrate orchestration, not biological validation on production cohorts.",
    ]
    return "\n".join(sections) + "\n"


def _recruiter_summary() -> str:
    return (
        "# Integrated Recruiter Summary\n\n"
        "This research-use harness organizes germline and somatic variant workflows while keeping their scientific assumptions separate. "
        "Germline analysis asks inherited-variant questions, while somatic tumor analysis must account for tumor-normal pairing, sample identity, and caller-specific limitations. "
        "The integrated somatic evidence layer combines validated DeepSomatic small-variant results and Severus structural-variant results only after checking identity, reference compatibility, source attempts, output validation, QC, and provenance. "
        "Failures remain isolated by pair and by caller, so one failed stage does not erase usable technical evidence from the other stage. "
        "The system generates operator reports, portfolio evidence, machine-readable summaries, rerun recommendations, and reproducible provenance using synthetic and mocked tests, including deterministic 3,000-pair reporting exercises. "
        "It does not claim clinical readiness, biological benchmarking on real tumor cohorts, treatment relevance, pathogenicity classification, CNV integration, or institutional deployment. "
        "The project demonstrates senior bioinformatics engineering through explicit configuration, hermetic tests, safe command construction, scalable planning, source-attempt integrity, and careful separation between technical evidence and biological interpretation.\n"
    )
