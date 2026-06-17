"""Somatic preflight reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER
from variant_analysis_harness.somatic.planning import aggregate_status_counts


def write_somatic_report(plan: dict[str, Any], out_dir: Path) -> Path:
    report_dir = out_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "somatic_preflight_report.md"
    counts = aggregate_status_counts(plan.get("pair_statuses", []))
    lines = [
        "# Somatic Preflight Report",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        "Technical readiness does not establish biological validity or clinical validity.",
        "",
        "## Project",
        f"- Somatic project ID: {plan['somatic_project_id']}",
        f"- Attempt ID: {plan['attempt_id']}",
        f"- Project mode: mixed planning model with explicit pair-level analysis modes",
        "",
        "## Pair Counts",
        f"- Selected pairs: {plan['selected_pair_count']}",
        f"- Excluded pairs: {plan['excluded_pair_count']}",
        f"- Tumor-normal pairs: {plan['tumor_normal_count']}",
        f"- Tumor-only pairs: {plan['tumor_only_count']}",
        f"- Readiness counts: {counts}",
        "",
        "## Identity And Normal Reuse",
        f"- Identity policy: {plan['identity_policy']}",
        f"- Normal reuse policy: {plan['normal_reuse_policy']}",
        "",
        "## Reference Compatibility",
        "- Reference compatibility was evaluated from supplied or mocked metadata in Phase 2D.",
        "",
        "## Alignment Metadata",
        "- BAM/CRAM metadata readiness was checked without requiring real external tools in standard tests.",
        "",
        "## Coverage And Biological Metadata",
        f"- Coverage metadata state: {plan['coverage_metadata_state']}",
        f"- Purity metadata state: {plan['purity_metadata_state']}",
        f"- Contamination metadata state: {plan['contamination_metadata_state']}",
        f"- Ploidy metadata state: {plan['ploidy_metadata_state']}",
        "- Missing metadata remains explicit; no purity, contamination, ploidy, or coverage defaults were fabricated.",
        "",
        "## Warning Pairs",
    ]
    lines.extend(_pair_lines(plan.get("warning_pairs", [])))
    lines.extend(["", "## Failed Or Blocked Pairs"])
    lines.extend(_pair_lines(plan.get("blocked_pairs", [])))
    lines.extend(
        [
            "",
            "## Tumor-Only Limitations",
            "- Tumor-only analysis is explicit and guarded by project policy.",
            "- Tumor-only designs have elevated germline contamination risk and reduced somatic specificity.",
            "- Future caller phases must enforce caller-specific tumor-only compatibility.",
            "",
            "## Future Caller Stages",
            f"- Future SNV stage: {plan['expected_future_snv_stage']}",
            f"- Future SV stage: {plan['expected_future_sv_stage']}",
            "",
            "## Output Inventory",
            f"- Somatic plan: somatic_plan.json",
            f"- Array index: {plan['array_index_path']}",
            f"- Pair statuses: status/somatic_pair_status.json",
            f"- Provenance: provenance/somatic_provenance.json",
            "",
            "## Recommended Operator Actions",
            "- Review failed and warning pairs before enabling future caller execution.",
            "- Confirm tumor-only acknowledgments and study-specific limitations.",
            "- Confirm reused-normal designs are scientifically appropriate for the study.",
            "",
            "## Phase 2D Boundary",
            "- No somatic variants were called in Phase 2D.",
            "- No DeepSomatic, Severus, somatic SV, CNV, annotation, pathogenicity interpretation, or clinical reporting was executed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _pair_lines(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- None"]
    return [
        f"- {item['pair_id']}: {item.get('readiness_status', '')} {item.get('failure_category', '')}".rstrip()
        for item in items
    ]
