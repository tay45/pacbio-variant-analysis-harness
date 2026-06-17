"""Severus cohort-level reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER


def write_severus_cohort_report(plan: dict[str, Any], out_dir: Path) -> Path:
    report_dir = out_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "somatic_sv_cohort_report.md"
    sev = plan["severus_config"]["severus"]
    lines = [
        "# Somatic Structural-Variant Cohort Report",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        "Caller completion does not establish biological validity. Results are not for clinical use.",
        "",
        f"Severus requested version: {sev.get('requested_version')}",
        f"Container/executable: {sev.get('container')} / {sev.get('executable')}",
        f"Ready pair count: {len(plan.get('pairs', []))}",
        f"Blocked pair count: {len(plan.get('blocked_pairs', []))}",
        "",
        "## Output Inventory",
        "- severus_plan.json",
        "- severus_array_index.tsv",
        "- severus_execution_environment.json",
        "- severus_output_inventory.json per pair after output discovery",
        "- severus_vcf_validation.json and severus_bnd_validation.json per pair after validation",
        "",
        "## Complex Events And Clusters",
        "Native Severus complex-event, cluster, graph, and breakpoint files are inventoried when present and are not rewritten as clinical interpretations.",
        "",
        "## Normal Background Policy",
        "Matched-normal evidence is required for the default PacBio HiFi somatic SV mode. Tumor-only mode is blocked by compatibility policy.",
        "",
        "## Known Limitations",
        "- No CNV, annotation, clinical interpretation, cloud execution, institutional deployment, Sniffles2, or pbsv somatic fallback is implemented.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_aggregate_outputs(plan, report_dir)
    return path


def write_aggregate_outputs(plan: dict[str, Any], report_dir: Path) -> None:
    status_rows = plan.get("pair_statuses", [])
    qc = {
        "ready_pairs": len(plan.get("pairs", [])),
        "blocked_pairs": len(plan.get("blocked_pairs", [])),
        "tumor_only_blocked_pairs": len([r for r in status_rows if r.get("failure_category") == "tumor_only_unsupported"]),
        "complex_event_outputs_inventory_expected": True,
        "bnd_validation_expected": True,
    }
    (report_dir / "somatic_sv_cohort_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (report_dir / "somatic_sv_cohort_status.json").write_text(json.dumps(status_rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (report_dir / "somatic_sv_cohort_qc.tsv").write_text("metric\tvalue\n" + "\n".join(f"{k}\t{v}" for k, v in sorted(qc.items())) + "\n", encoding="utf-8")
    (report_dir / "somatic_sv_cohort_status.tsv").write_text("pair_id\tstatus\tfailure_category\n" + "\n".join(f"{r.get('pair_id','')}\t{r.get('caller_preflight_status','')}\t{r.get('failure_category','')}" for r in status_rows) + "\n", encoding="utf-8")
