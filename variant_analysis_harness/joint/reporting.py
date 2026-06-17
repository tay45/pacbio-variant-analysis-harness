"""Joint-genotyping reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER

PORTFOLIO_WORDING = (
    "This repository implements a research-use PacBio HiFi germline SNV/SV workflow harness with tested "
    "single-sample analysis logic, scalable cohort orchestration, and a germline SNV/indel joint-genotyping "
    "layer. The joint-genotyping implementation includes validated gVCF discovery, sample and reference "
    "compatibility checks, deterministic genome sharding, GLnexus command generation, Slurm shard arrays, "
    "failure recovery, technical cohort VCF validation, and cohort-level variant QC. Planning and orchestration "
    "are tested using synthetic and mocked inputs, including a 3,000-sample cohort simulation. Full biological "
    "validation with production-scale datasets remains future work."
)


def write_joint_report(
    joint_dir: Path,
    *,
    plan: dict[str, Any],
    status: dict[str, Any] | None = None,
    storage: dict[str, Any] | None = None,
    qc: dict[str, Any] | None = None,
    incremental: list[dict[str, Any]] | None = None,
) -> Path:
    reports = joint_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "joint_genotyping_report.md"
    lines = [
        "# Joint Genotyping Report",
        "",
        RESEARCH_USE_DISCLAIMER,
        "",
        "Technical completion does not establish biological or clinical validity.",
        "",
        "## Joint-Genotyping Identifiers",
        f"- Joint ID: {plan.get('joint_id')}",
        f"- Attempt: {plan.get('joint_attempt_id')}",
        "",
        "## Source Cohort",
        f"- Source cohort ID: {plan.get('source_cohort_id') or 'not recorded'}",
        "",
        "## Selected Samples",
        f"- Count: {plan.get('selected_sample_count')}",
        "",
        "## Excluded Samples",
        f"- Count: {plan.get('excluded_sample_count')}",
        "",
        "## Input gVCF Validation",
        f"- Sample identity status: {plan.get('sample_identity', {}).get('status')}",
        "",
        "## Reference Compatibility",
        f"- Status: {plan.get('reference_compatibility', {}).get('status')}",
        "",
        "## Backend And Preset",
        f"- Backend: {plan.get('backend')}",
        f"- Preset: {plan.get('backend_preset')}",
        "",
        "## Shard Design",
        f"- Shards: {plan.get('shard_count')}",
        f"- Max concurrency: {plan.get('max_concurrency')}",
        "",
        "## Shard Status Summary",
    ]
    lines.extend([f"- {k}: {v}" for k, v in (status or {}).get("status_counts", {}).items()] or ["- not evaluated"])
    lines.extend(["", "## Failed And Warning Shards", "- See joint_status.tsv and rerun manifest artifacts."])
    lines.extend(["", "## Reused Per-Sample Inputs", "- Per-sample gVCFs may be reused when signatures remain compatible."])
    lines.extend(["", "## Incremental Comparison"])
    lines.append(f"- Rows: {len(incremental or [])}")
    lines.extend(["", "## Concatenation Status", "- Planned with nonoverlapping shard concatenation semantics."])
    lines.extend(["", "## Final VCF Validation", "- Technical validation is available through joint validation helpers."])
    lines.extend(["", "## Cohort Variant QC"])
    lines.append(f"- Total variants: {(qc or {}).get('total_variants', 'not evaluated')}")
    lines.extend(["", "## Storage Estimate"])
    lines.append(f"- Peak scratch GB: {(storage or {}).get('peak_scratch_gb', 'not evaluated')}")
    lines.extend(["", "## Known Limitations", "- No somatic, CNV, cohort SV joint calling, phasing, pedigree-aware refinement, pathogenicity interpretation, or clinical use is implemented."])
    lines.extend(["", "## Recommended Operator Actions", "- Review all manifests, shard commands, validation artifacts, and reports before manual execution."])
    lines.extend(["", "## Portfolio Wording", PORTFOLIO_WORDING])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (joint_dir / "joint_outputs.manifest.json").write_text(json.dumps({"outputs": [str(p.relative_to(joint_dir)) for p in sorted(joint_dir.rglob("*")) if p.is_file()]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

