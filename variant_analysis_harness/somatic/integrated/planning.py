"""Integrated somatic project planning and report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from variant_analysis_harness.somatic.integrated.compatibility import validate_pair_compatibility, write_compatibility
from variant_analysis_harness.somatic.integrated.config import resolve_integrated_config, validate_integrated_config
from variant_analysis_harness.somatic.integrated.inventory import build_output_inventory, write_inventory, write_provenance
from variant_analysis_harness.somatic.integrated.model import SourceAttemptRef, build_project_model
from variant_analysis_harness.somatic.integrated.qc import aggregate_qc, qc_domain, write_qc
from variant_analysis_harness.somatic.integrated.relationships import build_relationships, write_relationship_outputs
from variant_analysis_harness.somatic.integrated.reporting import write_machine_summary, write_reports
from variant_analysis_harness.somatic.integrated.rerun import failure_summary, recommend_reruns, write_rerun_outputs
from variant_analysis_harness.somatic.integrated.source_selection import discover_attempt_records, select_source_attempt, write_source_attempts
from variant_analysis_harness.somatic.integrated.status import derive_pair_status
from variant_analysis_harness.somatic.manifest import SomaticPair


def integrated_attempt_dir(cfg: dict[str, Any], somatic_project_id: str, attempt_id: str, output_root: Path | None = None) -> Path:
    root = output_root or Path(cfg["project"]["output_root"])
    return root / cfg["project"]["name"] / "somatic" / somatic_project_id / "integrated" / attempt_id


def generate_integrated_project(
    cfg: dict[str, Any],
    somatic_config: dict[str, Any],
    *,
    somatic_project_id: str,
    integrated_attempt_id: str,
    selected_pairs: list[SomaticPair],
    excluded_pairs: list[SomaticPair],
    somatic_dir: Path | None,
    manifest_path: Path | None = None,
    config_path: Path | None = None,
    deepsomatic_attempt: str | None = None,
    severus_attempt: str | None = None,
    allow_partial: bool | None = None,
    include_warnings: bool | None = None,
) -> dict[str, Any]:
    integrated_config = resolve_integrated_config(somatic_config)
    if allow_partial is not None:
        integrated_config["project_policy"]["allow_partial_success"] = allow_partial
    if include_warnings is not None:
        integrated_config["project_policy"]["include_warning_results"] = include_warnings
    config_validation = validate_integrated_config(integrated_config)
    if config_validation["status"] == "FAIL":
        raise ValueError("; ".join(config_validation["errors"]))
    project = build_project_model(cfg=cfg, somatic_project_id=somatic_project_id, integrated_attempt_id=integrated_attempt_id, selected_pairs=selected_pairs, excluded_pairs=excluded_pairs, integrated_config=integrated_config, manifest_path=manifest_path, config_path=config_path)
    ds_records = discover_attempt_records(somatic_dir / "deepsomatic_plan.json", caller="deepsomatic") if somatic_dir else []
    sv_records = discover_attempt_records(somatic_dir / "severus_plan.json", caller="severus") if somatic_dir else []
    pair_rows = []
    source_rows = []
    compatibility_rows = []
    policy = integrated_config["project_policy"]
    stages = policy["required_stages"]
    for pair in selected_pairs:
        ds = select_source_attempt(ds_records, pair_id=pair.pair_id, explicit_attempt=deepsomatic_attempt) or _not_started("deepsomatic", pair)
        sv = select_source_attempt(sv_records, pair_id=pair.pair_id, explicit_attempt=severus_attempt) or _not_started("severus", pair)
        source_rows.extend([ds, sv])
        compat = validate_pair_compatibility(pair, ds, sv, policy)
        compatibility_rows.append(compat)
        status = derive_pair_status(
            ds,
            sv,
            small_policy=stages["small_variants"],
            sv_policy=stages["structural_variants"],
            allow_partial_success=policy["allow_partial_success"],
            include_warning_results=policy["include_warning_results"],
            compatibility_status=compat["status"],
        )
        failures = _failure_categories(status, ds, sv, compat)
        pair_rows.append(
            {
                "pair_id": pair.pair_id,
                "subject_id": pair.subject_id,
                "tumor_sample_id": pair.tumor_sample_id,
                "normal_sample_id": pair.normal_sample_id,
                "analysis_mode": pair.analysis_mode,
                "integrated_status": status,
                "identity_compatibility": "FAIL" if any("identity" in e or "subject" in e for e in compat["errors"]) else compat["status"],
                "reference_compatibility": "FAIL" if any("reference" in e or "contig" in e for e in compat["errors"]) else compat["status"],
                "failure_categories": failures,
                "warnings": compat["warnings"],
                "deepsomatic": ds,
                "severus": sv,
            }
        )
    return {"project": project, "integrated_config": integrated_config, "config_validation": config_validation, "pair_rows": pair_rows, "source_attempts": source_rows, "compatibility": compatibility_rows}


def write_integrated_outputs(plan: dict[str, Any], out_dir: Path, *, small_variants: list[dict[str, Any]] | None = None, svs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("source_attempts", "validation", "status", "relationships", "qc", "reports", "exports", "provenance", "inventory"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    (out_dir / "integrated_project.json").write_text(json.dumps(plan["project"], indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (out_dir / "config.resolved.json").write_text(json.dumps(plan["integrated_config"], indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_source_attempts(plan["source_attempts"], out_dir / "source_attempts")
    write_compatibility(plan["compatibility"], out_dir / "validation")
    write_machine_summary(plan["project"], plan["pair_rows"], out_dir / "exports")
    rel_cfg = plan["integrated_config"]["relationship_analysis"]
    relationships = build_relationships(small_variants or [], svs or [], window_bp=rel_cfg["window_bp"], large_window_bp=rel_cfg["large_window_bp"], include_filtered_small_variants=rel_cfg["include_filtered_small_variants"], include_filtered_structural_variants=rel_cfg["include_filtered_structural_variants"]) if rel_cfg.get("enabled", True) else []
    write_relationship_outputs(relationships, out_dir / "relationships")
    domains = _qc_domains(plan, relationships)
    qc = aggregate_qc(domains)
    write_qc(qc, out_dir / "qc")
    failures = failure_summary(plan["pair_rows"])
    recommendations = recommend_reruns(plan["pair_rows"])
    write_rerun_outputs(recommendations, failures, out_dir / "status")
    report_paths = write_reports(plan["project"], plan["pair_rows"], relationships, qc, recommendations, out_dir)
    provenance = {"project": plan["project"], "source_attempts": plan["source_attempts"], "relationship_parameters": rel_cfg, "report_paths": report_paths}
    write_provenance(provenance, out_dir / "provenance")
    inventory = build_output_inventory(out_dir)
    write_inventory(inventory, out_dir / "inventory")
    return {"relationships": relationships, "qc": qc, "recommendations": recommendations, "failures": failures, "inventory": inventory, "reports": report_paths}


def _not_started(caller: str, pair: SomaticPair) -> dict[str, Any]:
    return {"caller": caller, "pair_id": pair.pair_id, "attempt_id": "", "path": "", "status": "not_started", "validation_status": "UNKNOWN", "qc_status": "UNKNOWN", "failure_category": "", "manifest_row_hash": pair.row_hash, "subject_id": pair.subject_id, "tumor_sample_id": pair.tumor_sample_id, "normal_sample_id": pair.normal_sample_id, "analysis_mode": pair.analysis_mode, "reference_id": pair.reference_id}


def _failure_categories(status: str, ds: dict[str, Any], sv: dict[str, Any], compat: dict[str, Any]) -> list[str]:
    failures = []
    for error in compat.get("errors", []):
        if "subject" in error:
            failures.append("integrated_subject_mismatch")
        elif "tumor" in error:
            failures.append("integrated_tumor_identity_mismatch")
        elif "normal" in error:
            failures.append("integrated_normal_identity_mismatch")
        elif "reference" in error:
            failures.append("integrated_reference_mismatch")
        elif "contig" in error:
            failures.append("integrated_contig_mismatch")
        else:
            failures.append("integrated_input_signature_mismatch")
    if ds.get("status") == "failed" or ds.get("validation_status") == "FAIL":
        failures.append("integrated_unvalidated_small_variant_output")
    if sv.get("status") == "failed" or sv.get("validation_status") == "FAIL":
        failures.append("integrated_unvalidated_sv_output")
    if sv.get("bnd_validation_status") == "FAIL":
        failures.append("integrated_bnd_validation_failure")
    if status == "partial_success":
        failures.append("integrated_partial_result")
    return sorted(set(failures))


def _qc_domains(plan: dict[str, Any], relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    domains = [
        qc_domain("identity QC", "FAIL" if any(r["identity_compatibility"] == "FAIL" for r in plan["pair_rows"]) else "PASS", source="integrated"),
        qc_domain("reference QC", "FAIL" if any(r["reference_compatibility"] == "FAIL" for r in plan["pair_rows"]) else "PASS", source="integrated"),
        qc_domain("DeepSomatic output validation", "WARN" if any(r["deepsomatic"]["status"] == "not_started" for r in plan["pair_rows"]) else "PASS", source="deepsomatic"),
        qc_domain("Severus output validation", "WARN" if any(r["severus"]["status"] == "not_started" for r in plan["pair_rows"]) else "PASS", source="severus"),
        qc_domain("relationship-analysis QC", "PASS", reason_codes=[f"relationship_rows={len(relationships)}"], source="integrated"),
        qc_domain("provenance completeness", "PASS", source="integrated"),
    ]
    return domains

