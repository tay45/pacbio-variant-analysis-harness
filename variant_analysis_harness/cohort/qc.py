"""Cohort-level QC aggregation from sample status and QC artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def aggregate_qc(cohort_dir: Path, plan: dict[str, Any], status_summary: dict[str, Any]) -> dict[str, Any]:
    rows = []
    records = {r.get("sample_id"): r for r in status_summary.get("records", [])}
    for sample in plan.get("selected_samples", []):
        record = records.get(sample["sample_id"], {})
        rows.append(
            {
                "sample_id": sample["sample_id"],
                "status": record.get("status", "pending"),
                "analysis": sample["analysis"],
                "input_type": sample["input_type"],
                "mapped_fraction": None,
                "mean_depth": None,
                "snv_count": None,
                "indel_count": None,
                "titv": None,
                "sv_count": None,
                "svtype_counts": {},
                "warnings": record.get("warning_count", 0),
                "failure_category": record.get("failure_category"),
                "missing_metrics": True,
            }
        )
    result = {
        "assumptions": "Aggregation uses available sample-level QC/status artifacts only and is not biological validation.",
        "rows": rows,
        "status_counts": status_summary.get("status_counts", {}),
    }
    write_qc_outputs(result, cohort_dir / "qc")
    return result


def write_qc_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cohort_qc.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    headers = ["sample_id", "status", "analysis", "input_type", "mapped_fraction", "mean_depth", "snv_count", "indel_count", "titv", "sv_count", "warnings", "failure_category", "missing_metrics"]
    lines = ["\t".join(headers)]
    for row in result["rows"]:
        lines.append("\t".join(str(row.get(h, "") or "") for h in headers))
    (out_dir / "cohort_qc.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    md = ["# Cohort QC", "", result["assumptions"], "", "## Status Counts"]
    for status, count in sorted(result.get("status_counts", {}).items()):
        md.append(f"- {status}: {count}")
    (out_dir / "cohort_qc.md").write_text("\n".join(md) + "\n", encoding="utf-8")

