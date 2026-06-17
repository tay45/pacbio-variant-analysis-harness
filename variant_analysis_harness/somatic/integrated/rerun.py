"""Integrated failure aggregation and rerun recommendations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def failure_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        for category in row.get("failure_categories", []):
            out.append({"pair_id": row.get("pair_id"), "integrated_status": row.get("integrated_status"), "failure_category": category, "deepsomatic_failure": row.get("deepsomatic", {}).get("failure_category"), "severus_failure": row.get("severus", {}).get("failure_category")})
    return out


def recommend_reruns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recs = []
    for row in rows:
        status = row.get("integrated_status")
        failures = set(row.get("failure_categories", []))
        if status in {"complete", "complete_with_warnings"}:
            action = "no rerun required"
        elif "integrated_subject_mismatch" in failures or "integrated_tumor_identity_mismatch" in failures or "integrated_normal_identity_mismatch" in failures:
            action = "correct pair identity"
        elif "integrated_reference_mismatch" in failures or "integrated_contig_mismatch" in failures:
            action = "correct reference mismatch"
        elif "integrated_unvalidated_small_variant_output" in failures:
            action = "rerun DeepSomatic only"
        elif "integrated_unvalidated_sv_output" in failures or "integrated_bnd_validation_failure" in failures:
            action = "rerun Severus only"
        elif "integrated_report_generation_failure" in failures:
            action = "regenerate integrated report only"
        elif status == "small_variants_only":
            action = "rerun Severus only"
        elif status == "structural_variants_only":
            action = "rerun DeepSomatic only"
        else:
            action = "rerun Phase 2D preflight"
        recs.append({"pair_id": row.get("pair_id"), "integrated_status": status, "recommendation": action, "source_deepsomatic_attempt": row.get("deepsomatic", {}).get("attempt_id", ""), "source_severus_attempt": row.get("severus", {}).get("attempt_id", "")})
    return recs


def write_rerun_outputs(recommendations: list[dict[str, Any]], failures: list[dict[str, Any]], out_dir: Path) -> None:
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_rerun_recommendations.json").write_text(json.dumps(recommendations, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out_dir / "integrated_failure_summary.json").write_text(json.dumps(failures, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    for filename, rows in (("integrated_rerun_recommendations.tsv", recommendations), ("integrated_failure_summary.tsv", failures)):
        fields = sorted({key for row in rows for key in row}) or ["pair_id"]
        with (out_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    lines = ["# Integrated Rerun Recommendations", "", "No automatic execution or submission is performed."]
    lines.extend(f"- {r.get('pair_id')}: {r.get('recommendation')}" for r in recommendations)
    (out_dir / "integrated_rerun_recommendations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

