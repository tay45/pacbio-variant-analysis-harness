"""DeepSomatic cohort-level reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER


def write_deepsomatic_cohort_report(plan: dict[str, Any], out_dir: Path) -> Path:
    report_dir = out_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "somatic_snv_cohort_report.md"
    ds = plan["deepsomatic_config"]["deepsomatic"]
    lines = [
        "# Somatic SNV/Indel Cohort Report",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        "Caller completion does not establish biological validity. Results are not for clinical use.",
        "",
        f"DeepSomatic version: {ds.get('version')}",
        f"Container/executable: {ds.get('container')} / {ds.get('executable')}",
        f"Model types: {ds.get('model_type')}",
        f"Ready pair count: {len(plan.get('pairs', []))}",
        f"Blocked pair count: {len(plan.get('blocked_pairs', []))}",
        "",
        "## PoN Policy",
        json.dumps(ds.get("pon", {}), sort_keys=True),
        "",
        "## Output Inventory",
        "- deepsomatic_plan.json",
        "- deepsomatic_array_index.tsv",
        "- deepsomatic_execution_environment.json",
        "- reports/somatic_snv_cohort_report.md",
        "",
        "## Known Limitations",
        "- No Severus, somatic SV, CNV, annotation, clinical interpretation, cloud, or institutional deployment is implemented.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_aggregate_outputs(plan, report_dir)
    return path


def write_aggregate_outputs(plan: dict[str, Any], report_dir: Path) -> None:
    status_rows = plan.get("pair_statuses", [])
    qc = {"ready_pairs": len(plan.get("pairs", [])), "blocked_pairs": len(plan.get("blocked_pairs", [])), "mixed_model_warning": False}
    (report_dir / "somatic_snv_cohort_qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (report_dir / "somatic_snv_cohort_status.json").write_text(json.dumps(status_rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (report_dir / "somatic_snv_cohort_qc.tsv").write_text("metric\tvalue\n" + "\n".join(f"{k}\t{v}" for k, v in sorted(qc.items())) + "\n", encoding="utf-8")
    (report_dir / "somatic_snv_cohort_status.tsv").write_text("pair_id\tstatus\tfailure_category\n" + "\n".join(f"{r.get('pair_id','')}\t{r.get('caller_preflight_status','')}\t{r.get('failure_category','')}" for r in status_rows) + "\n", encoding="utf-8")
