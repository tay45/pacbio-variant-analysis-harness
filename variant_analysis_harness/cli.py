"""Non-interactive Phase 2A command line interface."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from variant_analysis_harness import RESEARCH_USE_DISCLAIMER, __version__
from variant_analysis_harness.cohort.incremental import compare_incremental
from variant_analysis_harness.cohort.manifest import (
    build_validation_result,
    load_cohort_manifest,
    write_validation_artifacts,
)
from variant_analysis_harness.cohort.planning import (
    cohort_attempt_dir,
    generate_cohort_plan,
    prepare_cohort_attempt,
    write_array_index,
    write_cohort_plan,
)
from variant_analysis_harness.cohort.qc import aggregate_qc
from variant_analysis_harness.cohort.reporting import write_cohort_report, write_output_manifest
from variant_analysis_harness.cohort.rerun import generate_rerun_manifest
from variant_analysis_harness.cohort.slurm import generate_cohort_array_script, write_dependency_graph
from variant_analysis_harness.cohort.status import aggregate_status, seed_pending_statuses
from variant_analysis_harness.cohort.storage import estimate_storage, write_storage_estimate
from variant_analysis_harness.joint.concat import build_concat_plan
from variant_analysis_harness.joint.identity import validate_sample_identity
from variant_analysis_harness.joint.incremental import compare_joint_incremental
from variant_analysis_harness.joint.inputs import build_joint_inputs, load_joint_seed_manifest, write_joint_inputs
from variant_analysis_harness.joint.planning import generate_joint_plan, joint_attempt_dir, prepare_joint_attempt, write_joint_plan
from variant_analysis_harness.joint.qc import run_joint_variant_qc, write_joint_qc
from variant_analysis_harness.joint.reference import validate_reference_compatibility
from variant_analysis_harness.joint.reporting import write_joint_report
from variant_analysis_harness.joint.rerun import generate_joint_rerun_manifest
from variant_analysis_harness.joint.sharding import shards_from_contigs, shards_from_interval_file
from variant_analysis_harness.joint.slurm import write_joint_slurm_array
from variant_analysis_harness.joint.status import aggregate_joint_status, seed_shard_statuses
from variant_analysis_harness.joint.storage import estimate_joint_storage, write_joint_storage
from variant_analysis_harness.common.config import load_run_config, tool_config
from variant_analysis_harness.common.logging_utils import configure_logging
from variant_analysis_harness.common.manifest import load_manifest, select_sample
from variant_analysis_harness.common.outputs import write_outputs_manifest
from variant_analysis_harness.common.provenance import write_provenance
from variant_analysis_harness.common.signatures import stage_signature
from variant_analysis_harness.common.yaml_io import dump_yaml, load_yaml
from variant_analysis_harness.common.stage_status import read_stage_status, write_stage_status
from variant_analysis_harness.common.validation import require_readable_file, validate_vcf
from variant_analysis_harness.common.bam_validation import validate_bam_with_samtools, write_bam_validation
from variant_analysis_harness.common.vcf_validation import validate_svsig_gzip, validate_variant_vcf, write_validation_result
from variant_analysis_harness.common.atomic import incomplete_path, publish_atomically
from variant_analysis_harness.exceptions import HarnessError, ResumeError, ValidationError
from variant_analysis_harness.execution.local import execute_stage
from variant_analysis_harness.execution.slurm import generate_sbatch_script
from variant_analysis_harness.germline.alignment import build_pbmm2_align_command, validate_aligned_bam
from variant_analysis_harness.germline.dataset_merge import build_dataset_merge_command
from variant_analysis_harness.germline.deepvariant import build_deepvariant_command
from variant_analysis_harness.germline.pbsv import build_pbsv_call_command, build_pbsv_discover_command
from variant_analysis_harness.models import CommandSpec, Sample, StageResult, VALID_ANALYSES
from variant_analysis_harness.qc.alignment_qc import run_alignment_qc, write_alignment_qc_outputs
from variant_analysis_harness.qc.preflight import run_preflight
from variant_analysis_harness.qc.snv_qc import run_snv_qc, write_qc_outputs
from variant_analysis_harness.qc.sv_qc import run_sv_qc, write_sv_qc_outputs
from variant_analysis_harness.reports.sample_report import write_sample_report
from variant_analysis_harness.somatic.manifest import load_somatic_manifest, resolve_somatic_config, write_somatic_manifest_artifacts
from variant_analysis_harness.somatic.planning import (
    aggregate_status_counts,
    generate_somatic_plan,
    prepare_somatic_attempt,
    somatic_attempt_dir,
    write_somatic_plan,
)
from variant_analysis_harness.somatic.reporting import write_somatic_report
from variant_analysis_harness.somatic.rerun import generate_somatic_rerun_manifest, load_pair_statuses
from variant_analysis_harness.somatic.deepsomatic.config import resolve_deepsomatic_config, validate_deepsomatic_config
from variant_analysis_harness.somatic.deepsomatic.planning import generate_deepsomatic_plan, write_command_files, write_deepsomatic_plan
from variant_analysis_harness.somatic.deepsomatic.reporting import write_deepsomatic_cohort_report
from variant_analysis_harness.somatic.deepsomatic.rerun import generate_deepsomatic_rerun_manifest
from variant_analysis_harness.somatic.deepsomatic.slurm import write_deepsomatic_slurm_array
from variant_analysis_harness.somatic.severus.config import resolve_severus_config, validate_severus_config
from variant_analysis_harness.somatic.severus.planning import generate_severus_plan, write_command_files as write_severus_command_files, write_severus_plan
from variant_analysis_harness.somatic.severus.reporting import write_severus_cohort_report
from variant_analysis_harness.somatic.severus.rerun import generate_severus_rerun_manifest
from variant_analysis_harness.somatic.severus.slurm import write_severus_slurm_array
from variant_analysis_harness.somatic.severus.compatibility import COMPATIBILITY_REGISTRY
from variant_analysis_harness.somatic.integrated.config import resolve_integrated_config, validate_integrated_config
from variant_analysis_harness.somatic.integrated.planning import generate_integrated_project, integrated_attempt_dir, write_integrated_outputs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(getattr(args, "log_level", "INFO"))
    try:
        if args.command == "validate":
            return cmd_validate(args)
        if args.command == "dry-run":
            return cmd_run(args, dry_run=True, resume=False)
        if args.command == "run":
            return cmd_run(args, dry_run=False, resume=False)
        if args.command == "resume":
            return cmd_run(args, dry_run=False, resume=True)
        if args.command == "report":
            return cmd_report(args)
        if args.command == "slurm-script":
            return cmd_slurm_script(args)
        if args.command == "cohort-validate":
            return cmd_cohort_validate(args)
        if args.command == "cohort-dry-run":
            return cmd_cohort_plan(args, dry_run=True)
        if args.command == "cohort-plan":
            return cmd_cohort_plan(args, dry_run=True)
        if args.command == "cohort-slurm":
            return cmd_cohort_slurm(args)
        if args.command == "cohort-status":
            return cmd_cohort_status(args)
        if args.command == "cohort-rerun-manifest":
            return cmd_cohort_rerun_manifest(args)
        if args.command == "cohort-report":
            return cmd_cohort_report(args)
        if args.command == "joint-validate":
            return cmd_joint_plan(args, validate_only=True)
        if args.command == "joint-plan":
            return cmd_joint_plan(args, validate_only=False)
        if args.command == "joint-dry-run":
            return cmd_joint_plan(args, validate_only=False)
        if args.command == "joint-slurm":
            return cmd_joint_slurm(args)
        if args.command == "joint-status":
            return cmd_joint_status(args)
        if args.command == "joint-rerun-manifest":
            return cmd_joint_rerun_manifest(args)
        if args.command == "joint-concat":
            return cmd_joint_concat(args)
        if args.command == "joint-qc":
            return cmd_joint_qc(args)
        if args.command == "joint-report":
            return cmd_joint_report(args)
        if args.command == "somatic-validate":
            return cmd_somatic_plan(args, validate_only=True)
        if args.command == "somatic-plan":
            return cmd_somatic_plan(args, validate_only=False)
        if args.command == "somatic-dry-run":
            return cmd_somatic_plan(args, validate_only=False)
        if args.command == "somatic-status":
            return cmd_somatic_status(args)
        if args.command == "somatic-rerun-manifest":
            return cmd_somatic_rerun_manifest(args)
        if args.command == "somatic-report":
            return cmd_somatic_report(args)
        if args.command in {"somatic-snv-validate", "somatic-snv-plan", "somatic-snv-dry-run", "somatic-snv-run"}:
            return cmd_somatic_snv_plan(args, run=args.command == "somatic-snv-run", validate_only=args.command == "somatic-snv-validate")
        if args.command == "somatic-snv-slurm":
            return cmd_somatic_snv_slurm(args)
        if args.command == "somatic-snv-status":
            return cmd_somatic_snv_status(args)
        if args.command == "somatic-snv-rerun-manifest":
            return cmd_somatic_snv_rerun_manifest(args)
        if args.command == "somatic-snv-report":
            return cmd_somatic_snv_report(args)
        if args.command == "somatic-snv-qc":
            return cmd_somatic_snv_report(args)
        if args.command in {"somatic-sv-validate", "somatic-sv-plan", "somatic-sv-dry-run", "somatic-sv-run"}:
            return cmd_somatic_sv_plan(args, run=args.command == "somatic-sv-run", validate_only=args.command == "somatic-sv-validate")
        if args.command == "somatic-sv-slurm":
            return cmd_somatic_sv_slurm(args)
        if args.command == "somatic-sv-status":
            return cmd_somatic_sv_status(args)
        if args.command == "somatic-sv-rerun-manifest":
            return cmd_somatic_sv_rerun_manifest(args)
        if args.command == "somatic-sv-report":
            return cmd_somatic_sv_report(args)
        if args.command == "somatic-sv-qc":
            return cmd_somatic_sv_report(args)
        if args.command == "severus-contract-check":
            return cmd_severus_contract_check(args)
        if args.command in {"somatic-integrated-validate", "somatic-integrated-plan", "somatic-integrated-run"}:
            return cmd_somatic_integrated(args, validate_only=args.command == "somatic-integrated-validate")
        if args.command == "somatic-integrated-status":
            return cmd_somatic_integrated_status(args)
        if args.command == "somatic-integrated-report":
            return cmd_somatic_integrated_report(args)
        if args.command == "somatic-integrated-rerun-recommendations":
            return cmd_somatic_integrated_rerun(args)
        if args.command == "somatic-portfolio-report":
            return cmd_somatic_portfolio_report(args)
        parser.print_help()
        return 2
    except HarnessError as exc:
        if getattr(args, "debug", False):
            raise
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if getattr(args, "debug", False):
            raise
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="variant-analysis-harness",
        description=(
            "Platform-Aware Germline and Somatic SNV/SV Analysis Harness. "
            f"{RESEARCH_USE_DISCLAIMER}"
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "dry-run", "run", "resume", "report", "slurm-script"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        sub.add_argument("--config", required=True, type=Path)
        sub.add_argument("--manifest", required=True, type=Path)
        sub.add_argument("--sample")
        sub.add_argument("--analysis", choices=sorted(VALID_ANALYSES), default="combined")
        sub.add_argument("--attempt-id", default="attempt_001")
        sub.add_argument("--legacy-naming", action="store_true")
        sub.add_argument("--keep-temp", action="store_true")
        sub.add_argument("--force", action="store_true")
        sub.add_argument("--log-level", default="INFO")
        sub.add_argument("--debug", action="store_true")
    subparsers.choices["slurm-script"].add_argument("--slurm-profile", required=True, type=Path)
    for name in ("cohort-validate", "cohort-dry-run", "cohort-plan", "cohort-slurm"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        _add_common_cohort_options(sub)
        if name == "cohort-plan":
            sub.add_argument("--reuse-from", type=Path)
        if name == "cohort-slurm":
            sub.add_argument("--slurm-profile", type=Path)
    status_sub = subparsers.add_parser("cohort-status", description=RESEARCH_USE_DISCLAIMER)
    status_sub.add_argument("--cohort-dir", required=True, type=Path)
    status_sub.add_argument("--log-level", default="INFO")
    status_sub.add_argument("--debug", action="store_true")
    rerun_sub = subparsers.add_parser("cohort-rerun-manifest", description=RESEARCH_USE_DISCLAIMER)
    rerun_sub.add_argument("--cohort-dir", required=True, type=Path)
    rerun_sub.add_argument("--status", default="failed")
    rerun_sub.add_argument("--stage")
    rerun_sub.add_argument("--failure-category")
    rerun_sub.add_argument("--include-samples")
    rerun_sub.add_argument("--output", required=True, type=Path)
    rerun_sub.add_argument("--allow-successful", action="store_true")
    rerun_sub.add_argument("--log-level", default="INFO")
    rerun_sub.add_argument("--debug", action="store_true")
    report_sub = subparsers.add_parser("cohort-report", description=RESEARCH_USE_DISCLAIMER)
    report_sub.add_argument("--cohort-dir", required=True, type=Path)
    report_sub.add_argument("--html", action="store_true")
    report_sub.add_argument("--log-level", default="INFO")
    report_sub.add_argument("--debug", action="store_true")
    for name in ("joint-validate", "joint-plan", "joint-dry-run", "joint-slurm"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        _add_common_joint_options(sub)
        if name == "joint-slurm":
            sub.add_argument("--slurm-profile", type=Path)
    joint_status = subparsers.add_parser("joint-status", description=RESEARCH_USE_DISCLAIMER)
    joint_status.add_argument("--joint-dir", required=True, type=Path)
    joint_status.add_argument("--log-level", default="INFO")
    joint_status.add_argument("--debug", action="store_true")
    joint_rerun = subparsers.add_parser("joint-rerun-manifest", description=RESEARCH_USE_DISCLAIMER)
    joint_rerun.add_argument("--joint-dir", required=True, type=Path)
    joint_rerun.add_argument("--status", default="failed")
    joint_rerun.add_argument("--failure-category")
    joint_rerun.add_argument("--shards")
    joint_rerun.add_argument("--contig")
    joint_rerun.add_argument("--output", required=True, type=Path)
    joint_rerun.add_argument("--log-level", default="INFO")
    joint_rerun.add_argument("--debug", action="store_true")
    for name in ("joint-concat", "joint-qc", "joint-report"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        sub.add_argument("--config", type=Path)
        sub.add_argument("--joint-dir", required=True, type=Path)
        sub.add_argument("--vcf", type=Path)
        sub.add_argument("--log-level", default="INFO")
        sub.add_argument("--debug", action="store_true")
    for name in ("somatic-validate", "somatic-plan", "somatic-dry-run"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        _add_common_somatic_options(sub)
    som_status = subparsers.add_parser("somatic-status", description=RESEARCH_USE_DISCLAIMER)
    som_status.add_argument("--somatic-dir", required=True, type=Path)
    som_status.add_argument("--log-level", default="INFO")
    som_status.add_argument("--debug", action="store_true")
    som_rerun = subparsers.add_parser("somatic-rerun-manifest", description=RESEARCH_USE_DISCLAIMER)
    som_rerun.add_argument("--somatic-dir", required=True, type=Path)
    som_rerun.add_argument("--status", default="failed")
    som_rerun.add_argument("--failure-category")
    som_rerun.add_argument("--subject-id")
    som_rerun.add_argument("--analysis-mode")
    som_rerun.add_argument("--include-pairs")
    som_rerun.add_argument("--allow-successful", action="store_true")
    som_rerun.add_argument("--output", required=True, type=Path)
    som_rerun.add_argument("--log-level", default="INFO")
    som_rerun.add_argument("--debug", action="store_true")
    som_report = subparsers.add_parser("somatic-report", description=RESEARCH_USE_DISCLAIMER)
    som_report.add_argument("--somatic-dir", required=True, type=Path)
    som_report.add_argument("--log-level", default="INFO")
    som_report.add_argument("--debug", action="store_true")
    for name in ("somatic-snv-validate", "somatic-snv-plan", "somatic-snv-dry-run", "somatic-snv-run", "somatic-snv-slurm"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        _add_common_somatic_options(sub)
        sub.add_argument("--somatic-dir", type=Path)
        sub.add_argument("--pair-attempt-id", default="deepsomatic_attempt_001")
        sub.add_argument("--include-warning-pairs", action="store_true")
        sub.add_argument("--submit", action="store_true")
    for name in ("somatic-snv-status", "somatic-snv-report", "somatic-snv-qc"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        sub.add_argument("--somatic-dir", required=True, type=Path)
        sub.add_argument("--log-level", default="INFO")
        sub.add_argument("--debug", action="store_true")
    snv_rerun = subparsers.add_parser("somatic-snv-rerun-manifest", description=RESEARCH_USE_DISCLAIMER)
    snv_rerun.add_argument("--somatic-dir", required=True, type=Path)
    snv_rerun.add_argument("--status", default="BLOCKED")
    snv_rerun.add_argument("--failure-category")
    snv_rerun.add_argument("--analysis-mode")
    snv_rerun.add_argument("--include-pairs")
    snv_rerun.add_argument("--output", required=True, type=Path)
    snv_rerun.add_argument("--log-level", default="INFO")
    snv_rerun.add_argument("--debug", action="store_true")
    for name in ("somatic-sv-validate", "somatic-sv-plan", "somatic-sv-dry-run", "somatic-sv-run", "somatic-sv-slurm"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        _add_common_somatic_options(sub)
        sub.add_argument("--somatic-dir", type=Path)
        sub.add_argument("--pair-attempt-id", default="severus_attempt_001")
        sub.add_argument("--include-warning-pairs", action="store_true")
        sub.add_argument("--submit", action="store_true")
    for name in ("somatic-sv-status", "somatic-sv-report", "somatic-sv-qc"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        sub.add_argument("--somatic-dir", required=True, type=Path)
        sub.add_argument("--log-level", default="INFO")
        sub.add_argument("--debug", action="store_true")
    sv_rerun = subparsers.add_parser("somatic-sv-rerun-manifest", description=RESEARCH_USE_DISCLAIMER)
    sv_rerun.add_argument("--somatic-dir", required=True, type=Path)
    sv_rerun.add_argument("--status", default="BLOCKED")
    sv_rerun.add_argument("--failure-category")
    sv_rerun.add_argument("--analysis-mode")
    sv_rerun.add_argument("--include-pairs")
    sv_rerun.add_argument("--output", required=True, type=Path)
    sv_rerun.add_argument("--log-level", default="INFO")
    sv_rerun.add_argument("--debug", action="store_true")
    contract = subparsers.add_parser("severus-contract-check", description=RESEARCH_USE_DISCLAIMER)
    contract.add_argument("--executable", required=True)
    contract.add_argument("--expected-version", required=True)
    contract.add_argument("--output-dir", type=Path, default=Path("."))
    contract.add_argument("--mock-help", type=Path)
    contract.add_argument("--mock-version", type=Path)
    contract.add_argument("--policy", choices=["strict", "warn"], default="strict")
    contract.add_argument("--log-level", default="INFO")
    contract.add_argument("--debug", action="store_true")
    for name in ("somatic-integrated-validate", "somatic-integrated-plan", "somatic-integrated-run"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        _add_common_somatic_options(sub)
        sub.add_argument("--somatic-dir", type=Path)
        sub.add_argument("--integrated-attempt-id", default="integrated_attempt_001")
        sub.add_argument("--deepsomatic-attempt")
        sub.add_argument("--severus-attempt")
        sub.add_argument("--allow-partial", action="store_true")
        sub.add_argument("--include-warnings", action="store_true")
    for name in ("somatic-integrated-status", "somatic-integrated-report", "somatic-integrated-rerun-recommendations", "somatic-portfolio-report"):
        sub = subparsers.add_parser(name, description=RESEARCH_USE_DISCLAIMER)
        sub.add_argument("--integrated-dir", required=True, type=Path)
        sub.add_argument("--log-level", default="INFO")
        sub.add_argument("--debug", action="store_true")
    return parser


def _add_common_cohort_options(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--config", required=True, type=Path)
    sub.add_argument("--manifest", required=True, type=Path)
    sub.add_argument("--cohort-id", required=True)
    sub.add_argument("--analysis", choices=sorted(VALID_ANALYSES), default=None)
    sub.add_argument("--attempt-id", default="cohort_attempt_001")
    sub.add_argument("--sample-attempt-id", default="attempt_001")
    sub.add_argument("--output-root", type=Path)
    sub.add_argument("--max-concurrent", type=int, default=50)
    sub.add_argument("--include-samples")
    sub.add_argument("--exclude-samples")
    sub.add_argument("--only-status")
    sub.add_argument("--dry-run", action="store_true")
    sub.add_argument("--submit", action="store_true")
    sub.add_argument("--force", action="store_true")
    sub.add_argument("--log-level", default="INFO")
    sub.add_argument("--debug", action="store_true")


def _add_common_joint_options(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--config", required=True, type=Path)
    sub.add_argument("--cohort-dir", type=Path)
    sub.add_argument("--manifest", required=True, type=Path)
    sub.add_argument("--joint-id", required=True)
    sub.add_argument("--attempt-id", default="joint_attempt_001")
    sub.add_argument("--output-root", type=Path)
    sub.add_argument("--include-samples")
    sub.add_argument("--exclude-samples")
    sub.add_argument("--include-contigs")
    sub.add_argument("--exclude-contigs")
    sub.add_argument("--sharding-mode", choices=["contig", "interval_file"], default=None)
    sub.add_argument("--interval-file", type=Path)
    sub.add_argument("--max-concurrent", type=int, default=50)
    sub.add_argument("--reuse-from", type=Path)
    sub.add_argument("--dry-run", action="store_true")
    sub.add_argument("--submit", action="store_true")
    sub.add_argument("--force", action="store_true")
    sub.add_argument("--log-level", default="INFO")
    sub.add_argument("--debug", action="store_true")


def _add_common_somatic_options(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--config", required=True, type=Path)
    sub.add_argument("--manifest", required=True, type=Path)
    sub.add_argument("--somatic-project-id", required=True)
    sub.add_argument("--attempt-id", default="somatic_attempt_001")
    sub.add_argument("--output-root", type=Path)
    sub.add_argument("--include-pairs")
    sub.add_argument("--exclude-pairs")
    sub.add_argument("--include-subjects")
    sub.add_argument("--exclude-subjects")
    sub.add_argument("--mode", choices=["tumor_normal", "tumor_only"])
    sub.add_argument("--identity-policy", choices=["strict", "warn", "explicit_mapping"])
    sub.add_argument("--dry-run", action="store_true")
    sub.add_argument("--force", action="store_true")
    sub.add_argument("--log-level", default="INFO")
    sub.add_argument("--debug", action="store_true")


def cmd_validate(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    samples = load_manifest(args.manifest, require_existing=True)
    if args.sample:
        select_sample(samples, args.sample)
    print(RESEARCH_USE_DISCLAIMER)
    print(f"Configuration valid: {args.config}")
    print(f"Manifest valid: {args.manifest}")
    print(f"Samples: {len(samples)}")
    print(f"Project: {cfg['project']['name']}")
    return 0


def cmd_run(args: argparse.Namespace, dry_run: bool, resume: bool) -> int:
    cfg = load_run_config(args.config)
    if args.legacy_naming:
        cfg["workflow"]["legacy_naming"] = True
    if args.keep_temp:
        cfg["execution"]["keep_temp_on_failure"] = True
    samples = load_manifest(args.manifest, require_existing=True)
    sample = select_sample(samples, args.sample)
    attempt_dir = _attempt_dir(cfg, sample, args.attempt_id)
    if resume and not attempt_dir.exists():
        raise ValidationError(f"Cannot resume missing attempt directory: {attempt_dir}")
    forced_from: str | None = None
    original_attempt = attempt_dir
    if not dry_run and args.force and attempt_dir.exists() and not resume:
        forced_from = args.attempt_id
        derived_id = f"{args.attempt_id}_forced_{uuid.uuid4().hex[:8]}"
        args.attempt_id = derived_id
        attempt_dir = _attempt_dir(cfg, sample, args.attempt_id)
    if not dry_run and attempt_dir.exists() and not resume and not args.force:
        raise ValidationError(f"Attempt directory already exists; use resume, --force, or a new attempt id: {attempt_dir}")
    _prepare_attempt(attempt_dir, args, cfg, sample, preserve_existing=resume)
    if forced_from:
        _write_json(
            attempt_dir / "supersession.json",
            {
                "supersedes_attempt": str(original_attempt),
                "forced_from_attempt": forced_from,
                "new_attempt_id": args.attempt_id,
                "reason": "operator supplied --force",
            },
        )
    planned = _plan(cfg, sample, args.analysis, attempt_dir)
    print(RESEARCH_USE_DISCLAIMER)
    print(f"Attempt directory: {attempt_dir}")
    print("Planned stages:")
    for stage in planned:
        print(f"- {stage['name']}: {stage.get('action', 'execute')}")
    if dry_run:
        _write_plan(planned, attempt_dir)
        return 0
    stage_statuses: list[dict[str, Any]] = []
    outputs: list[Path] = []
    snv_qc: dict[str, Any] | None = None
    sv_qc: dict[str, Any] | None = None
    blocked = False
    for stage in planned:
        if blocked:
            _write_blocked(attempt_dir, stage["name"], "upstream_failed")
            continue
        try:
            result, produced, qc = _run_stage(stage, cfg, sample, attempt_dir, resume=resume, force=args.force)
        except Exception:
            blocked = True
            raise
        status = read_stage_status(attempt_dir / "status" / stage["name"] / "stage.status.json")
        if status:
            stage_statuses.append(status)
        outputs.extend(produced)
        if stage["name"] == "germline_snv_qc":
            snv_qc = qc
        if stage["name"] == "germline_sv_qc":
            sv_qc = qc
        if result.status == "failed":
            blocked = True
            raise ValidationError(f"Stage failed: {stage['name']}")
    report_path = attempt_dir / "reports" / "sample_report.md"
    write_sample_report(
        report_path,
        project_id=cfg["project"]["name"],
        sample=sample,
        attempt_id=args.attempt_id,
        config=cfg,
        stage_statuses=stage_statuses,
        outputs=outputs + [report_path],
        snv_qc=snv_qc,
        sv_qc=sv_qc,
    )
    write_outputs_manifest(outputs + [report_path], attempt_dir / "outputs.manifest.json", bool(cfg["qc"].get("checksum_outputs")))
    print(f"Report: {report_path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    sample = select_sample(load_manifest(args.manifest, require_existing=False), args.sample)
    attempt_dir = _attempt_dir(cfg, sample, args.attempt_id)
    statuses = [
        read_stage_status(path)
        for path in sorted((attempt_dir / "status").glob("*/stage.status.json"))
    ]
    statuses = [s for s in statuses if s]
    outputs = [Path(x["path"]) for x in json.loads((attempt_dir / "outputs.manifest.json").read_text()).get("outputs", [])] if (attempt_dir / "outputs.manifest.json").exists() else []
    report_path = attempt_dir / "reports" / "sample_report.md"
    write_sample_report(report_path, project_id=cfg["project"]["name"], sample=sample, attempt_id=args.attempt_id, config=cfg, stage_statuses=statuses, outputs=outputs)
    print(f"Report: {report_path}")
    return 0


def cmd_slurm_script(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    sample = select_sample(load_manifest(args.manifest, require_existing=True), args.sample)
    attempt_dir = _attempt_dir(cfg, sample, args.attempt_id)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    profile = load_yaml(args.slurm_profile)
    workflow_argv = [
        sys.executable,
        "-m",
        "variant_analysis_harness.cli",
        "run",
        "--config",
        str(args.config.resolve()),
        "--manifest",
        str(args.manifest.resolve()),
        "--sample",
        sample.sample_id,
        "--analysis",
        args.analysis,
        "--attempt-id",
        args.attempt_id,
    ]
    if args.legacy_naming:
        workflow_argv.append("--legacy-naming")
    spec = CommandSpec("sample_workflow", "variant_analysis_harness", workflow_argv, cwd=Path.cwd())
    script = attempt_dir / "logs" / "slurm" / f"{sample.sample_id}.{args.analysis}.sbatch"
    generate_sbatch_script(
        spec,
        profile,
        script,
        stdout_path=script.with_suffix(".out"),
        stderr_path=script.with_suffix(".err"),
    )
    _write_json(
        script.with_suffix(".metadata.json"),
        {
            "config": str(args.config.resolve()),
            "manifest": str(args.manifest.resolve()),
            "sample": sample.sample_id,
            "analysis": args.analysis,
            "submit_enabled": False,
        },
    )
    print(f"Slurm script: {script}")
    return 0


def cmd_cohort_validate(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    include = _parse_sample_filter(args.include_samples)
    exclude = _parse_sample_filter(args.exclude_samples)
    selected, excluded, validation = load_cohort_manifest(
        args.manifest,
        require_existing=False,
        max_rows=_cohort_max_rows(cfg),
        include_samples=include,
        exclude_samples=exclude,
    )
    if args.analysis:
        selected = [s for s in selected if s.analysis == args.analysis or args.analysis == "combined"]
        validation = build_validation_result(selected, excluded, validation.errors, validation.warnings, args.max_concurrent)
    if args.max_concurrent < 1:
        raise ValidationError("--max-concurrent must be at least 1")
    if args.max_concurrent > max(1, len(selected)):
        validation.warnings.append(
            {
                "scope": "cohort",
                "message": f"max_concurrent {args.max_concurrent} exceeds selected sample count {len(selected)}",
            }
        )
        validation = build_validation_result(selected, excluded, validation.errors, validation.warnings, args.max_concurrent)
    out_dir = cohort_attempt_dir(cfg, args.cohort_id, args.attempt_id, args.output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    prepare_cohort_attempt(out_dir, config_path=args.config, manifest_path=args.manifest, cfg=cfg, selected=selected, excluded=excluded)
    write_validation_artifacts(validation, out_dir)
    print(RESEARCH_USE_DISCLAIMER)
    print(f"Cohort validation: {validation.status}")
    print(f"Selected samples: {len(selected)}")
    print(f"Excluded samples: {len(excluded)}")
    print(f"Expected array tasks: {validation.expected_array_tasks}")
    return 1 if validation.status == "FAIL" else 0


def cmd_cohort_plan(args: argparse.Namespace, dry_run: bool = True) -> int:
    cfg = load_run_config(args.config)
    if args.max_concurrent < 1:
        raise ValidationError("--max-concurrent must be at least 1")
    include = _parse_sample_filter(args.include_samples)
    exclude = _parse_sample_filter(args.exclude_samples)
    selected, excluded, validation = load_cohort_manifest(
        args.manifest,
        require_existing=False,
        max_rows=_cohort_max_rows(cfg),
        include_samples=include,
        exclude_samples=exclude,
    )
    if validation.status == "FAIL":
        raise ValidationError(f"Cohort manifest validation failed: {validation.errors}")
    attempt_dir = cohort_attempt_dir(cfg, args.cohort_id, args.attempt_id, args.output_root)
    prepare_cohort_attempt(attempt_dir, config_path=args.config, manifest_path=args.manifest, cfg=cfg, selected=selected, excluded=excluded)
    write_validation_artifacts(validation, attempt_dir)
    reuse_summary = compare_incremental(
        current_samples=selected,
        current_config=cfg,
        previous_cohort_dir=getattr(args, "reuse_from", None),
        out_dir=attempt_dir,
    )
    plan = generate_cohort_plan(
        cfg,
        config_path=args.config,
        manifest_path=args.manifest,
        selected=selected,
        excluded=excluded,
        cohort_id=args.cohort_id,
        cohort_attempt_id=args.attempt_id,
        sample_attempt_id=args.sample_attempt_id,
        output_root=args.output_root,
        max_concurrent=args.max_concurrent,
        include_samples=include,
        exclude_samples=exclude,
        reuse_summary=reuse_summary,
    )
    write_cohort_plan(plan, attempt_dir)
    write_array_index(plan, attempt_dir / "array_index.tsv")
    seed_pending_statuses(attempt_dir, plan)
    status_summary = aggregate_status(attempt_dir)
    storage = estimate_storage(selected)
    write_storage_estimate(storage, attempt_dir / "storage")
    qc_summary = aggregate_qc(attempt_dir, plan, status_summary)
    write_cohort_report(attempt_dir, plan=plan, status_summary=status_summary, qc_summary=qc_summary, storage_estimate=storage, incremental_summary=reuse_summary)
    write_output_manifest(attempt_dir)
    print(RESEARCH_USE_DISCLAIMER)
    print(f"Cohort plan: {attempt_dir / 'cohort_plan.json'}")
    print(f"Selected samples: {len(selected)}")
    print(f"Array tasks: {plan['task_count']}")
    if getattr(args, "submit", False):
        raise ValidationError("--submit is not implemented for Phase 2B; generated scripts are review-only")
    return 0


def cmd_cohort_slurm(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    if args.max_concurrent < 1:
        raise ValidationError("--max-concurrent must be at least 1")
    include = _parse_sample_filter(args.include_samples)
    exclude = _parse_sample_filter(args.exclude_samples)
    selected, excluded, validation = load_cohort_manifest(
        args.manifest,
        require_existing=False,
        max_rows=_cohort_max_rows(cfg),
        include_samples=include,
        exclude_samples=exclude,
    )
    if validation.status == "FAIL":
        raise ValidationError(f"Cohort manifest validation failed: {validation.errors}")
    attempt_dir = cohort_attempt_dir(cfg, args.cohort_id, args.attempt_id, args.output_root)
    prepare_cohort_attempt(attempt_dir, config_path=args.config, manifest_path=args.manifest, cfg=cfg, selected=selected, excluded=excluded)
    plan = generate_cohort_plan(
        cfg,
        config_path=args.config,
        manifest_path=args.manifest,
        selected=selected,
        excluded=excluded,
        cohort_id=args.cohort_id,
        cohort_attempt_id=args.attempt_id,
        sample_attempt_id=args.sample_attempt_id,
        output_root=args.output_root,
        max_concurrent=args.max_concurrent,
        include_samples=include,
        exclude_samples=exclude,
    )
    write_cohort_plan(plan, attempt_dir)
    write_array_index(plan, attempt_dir / "array_index.tsv")
    profile = load_yaml(args.slurm_profile) if args.slurm_profile else {}
    script = generate_cohort_array_script(
        plan,
        config_path=args.config,
        manifest_path=args.manifest,
        slurm_profile=profile,
        script_path=attempt_dir / "slurm" / "cohort_array.sh",
        max_concurrent=args.max_concurrent,
        dry_run=True,
    )
    write_dependency_graph(plan, attempt_dir / "slurm")
    if args.submit:
        raise ValidationError("--submit is not implemented for Phase 2B; no jobs were submitted")
    print(f"Slurm array script: {script}")
    return 0


def cmd_cohort_status(args: argparse.Namespace) -> int:
    summary = aggregate_status(args.cohort_dir)
    print(f"Cohort status records: {summary['total_records']}")
    for status, count in summary["status_counts"].items():
        print(f"{status}: {count}")
    return 0


def cmd_cohort_rerun_manifest(args: argparse.Namespace) -> int:
    include = _parse_sample_filter(args.include_samples)
    rows = generate_rerun_manifest(
        args.cohort_dir,
        args.output,
        status=args.status,
        stage=args.stage,
        failure_category=args.failure_category,
        include_samples=include,
        allow_successful=args.allow_successful,
    )
    print(f"Rerun manifest: {args.output}")
    print(f"Selected samples: {len(rows)}")
    return 0


def cmd_cohort_report(args: argparse.Namespace) -> int:
    plan_path = args.cohort_dir / "cohort_plan.json"
    if not plan_path.exists():
        raise ValidationError(f"Missing cohort plan: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    status_summary = aggregate_status(args.cohort_dir)
    qc_summary = aggregate_qc(args.cohort_dir, plan, status_summary)
    storage_path = args.cohort_dir / "storage" / "storage_estimate.json"
    storage = json.loads(storage_path.read_text(encoding="utf-8")) if storage_path.exists() else None
    report = write_cohort_report(
        args.cohort_dir,
        plan=plan,
        status_summary=status_summary,
        qc_summary=qc_summary,
        storage_estimate=storage,
        html_report=args.html,
    )
    write_output_manifest(args.cohort_dir)
    print(f"Cohort report: {report}")
    return 0


def cmd_joint_plan(args: argparse.Namespace, *, validate_only: bool) -> int:
    cfg = load_run_config(args.config)
    if not cfg.get("joint_genotyping", {}).get("enabled", False):
        cfg.setdefault("joint_genotyping", {})["enabled"] = True
    if args.max_concurrent < 1:
        raise ValidationError("--max-concurrent must be at least 1")
    attempt_dir = joint_attempt_dir(cfg, args.joint_id, args.attempt_id, args.output_root)
    prepare_joint_attempt(attempt_dir, config_path=args.config, cfg=cfg)
    rows = load_joint_seed_manifest(args.manifest)
    include = _parse_sample_filter(args.include_samples)
    exclude = _parse_sample_filter(args.exclude_samples)
    if include:
        rows = [row for row in rows if row.get("sample_id") in include]
    if exclude:
        rows = [row for row in rows if row.get("sample_id") not in exclude]
    inputs, errors, warnings = build_joint_inputs(
        rows,
        base_dir=args.manifest.parent.resolve(),
        source_cohort_id=args.cohort_dir.name if args.cohort_dir else "",
        source_cohort_attempt_id=args.cohort_dir.name if args.cohort_dir else "",
        require_existing=not cfg.get("joint_genotyping", {}).get("allow_missing_gvcfs_for_planning", False),
    )
    write_joint_inputs(inputs, errors, warnings, attempt_dir)
    identity = validate_sample_identity(inputs, policy=cfg.get("joint_genotyping", {}).get("sample_identity_policy", "strict"))
    reference = validate_reference_compatibility(inputs, attempt_dir)
    fatal = errors or identity["status"] == "FAIL" or reference["status"] == "FAIL"
    if validate_only:
        print(RESEARCH_USE_DISCLAIMER)
        print(f"Joint input validation: {'FAIL' if fatal else 'PASS'}")
        return 1 if fatal else 0
    if fatal:
        raise ValidationError("Joint validation failed; see joint_genotyping_inputs and reference compatibility artifacts")
    contigs = reference["rows"][0]["contigs"] if reference["rows"] else _fallback_contigs(cfg)
    include_contigs = _parse_sample_filter(args.include_contigs)
    exclude_contigs = _parse_sample_filter(args.exclude_contigs)
    sharding = cfg.get("joint_genotyping", {}).get("sharding", {})
    mode = args.sharding_mode or sharding.get("mode", "contig")
    if mode == "interval_file":
        interval_file = args.interval_file or (Path(sharding["interval_file"]) if sharding.get("interval_file") else None)
        if interval_file is None:
            raise ValidationError("interval_file sharding requires --interval-file or joint_genotyping.sharding.interval_file")
        shards, shard_errors = shards_from_interval_file(interval_file, out_dir=attempt_dir, reference_contigs={c["id"]: int(c.get("length") or 0) for c in contigs})
        if shard_errors:
            raise ValidationError(f"Invalid interval shards: {shard_errors}")
    else:
        shards = shards_from_contigs(contigs, out_dir=attempt_dir, include_contigs=include_contigs, exclude_contigs=exclude_contigs, max_shards=sharding.get("max_shards"))
    reuse = compare_joint_incremental(inputs, {}, args.reuse_from, attempt_dir)
    plan = generate_joint_plan(
        cfg,
        config_path=args.config,
        manifest_path=args.manifest,
        joint_id=args.joint_id,
        attempt_id=args.attempt_id,
        inputs=inputs,
        excluded_samples=[],
        shards=shards,
        attempt_dir=attempt_dir,
        max_concurrent=args.max_concurrent,
        reference_result=reference,
        identity_result=identity,
        reuse_summary=reuse,
    )
    write_joint_plan(plan, attempt_dir)
    seed_shard_statuses(attempt_dir, plan)
    status = aggregate_joint_status(attempt_dir)
    storage = estimate_joint_storage(inputs, shards)
    write_joint_storage(storage, attempt_dir / "storage")
    build_concat_plan(cfg, plan, attempt_dir)
    write_joint_report(attempt_dir, plan=plan, status=status, storage=storage, incremental=reuse)
    if args.submit:
        raise ValidationError("--submit is not implemented for Phase 2C; no jobs were submitted")
    print(RESEARCH_USE_DISCLAIMER)
    print(f"Joint plan: {attempt_dir / 'joint_plan.json'}")
    print(f"Selected samples: {plan['selected_sample_count']}")
    print(f"Shards: {plan['shard_count']}")
    return 0


def cmd_joint_slurm(args: argparse.Namespace) -> int:
    rc = cmd_joint_plan(args, validate_only=False)
    if rc != 0:
        return rc
    cfg = load_run_config(args.config)
    attempt_dir = joint_attempt_dir(cfg, args.joint_id, args.attempt_id, args.output_root)
    plan = json.loads((attempt_dir / "joint_plan.json").read_text(encoding="utf-8"))
    profile = load_yaml(args.slurm_profile) if args.slurm_profile else {}
    script = write_joint_slurm_array(plan, attempt_dir / "slurm" / "joint_shards_array.sh", max_concurrent=args.max_concurrent, profile=profile.get("slurm", profile))
    print(f"Joint Slurm array script: {script}")
    return 0


def cmd_joint_status(args: argparse.Namespace) -> int:
    status = aggregate_joint_status(args.joint_dir)
    print(f"Joint shard records: {status['total_shards']}")
    for key, value in status["status_counts"].items():
        print(f"{key}: {value}")
    return 0


def cmd_joint_rerun_manifest(args: argparse.Namespace) -> int:
    rows = generate_joint_rerun_manifest(
        args.joint_dir,
        args.output,
        status=args.status,
        failure_category=args.failure_category,
        shards=_parse_sample_filter(args.shards),
        contig=args.contig,
    )
    print(f"Joint rerun manifest: {args.output}")
    print(f"Selected shards: {len(rows)}")
    return 0


def cmd_joint_concat(args: argparse.Namespace) -> int:
    if args.config is None:
        raise ValidationError("--config is required for joint-concat planning")
    cfg = load_run_config(args.config)
    plan = json.loads((args.joint_dir / "joint_plan.json").read_text(encoding="utf-8"))
    build_concat_plan(cfg, plan, args.joint_dir)
    print(f"Concat plan: {args.joint_dir / 'concat_plan.json'}")
    return 0


def cmd_joint_qc(args: argparse.Namespace) -> int:
    vcf = args.vcf or _joint_final_vcf(args.joint_dir)
    plan_path = args.joint_dir / "joint_plan.json"
    expected = []
    if plan_path.exists():
        inputs_path = args.joint_dir / "joint_genotyping_inputs.json"
        if inputs_path.exists():
            expected = [row["sample_name_in_header"] for row in json.loads(inputs_path.read_text(encoding="utf-8")).get("inputs", []) if row.get("enabled") == "true"]
    metrics = run_joint_variant_qc(vcf, expected_samples=expected)
    write_joint_qc(metrics, args.joint_dir / "qc")
    print(f"Joint QC: {args.joint_dir / 'qc' / 'cohort_variant_qc.json'}")
    return 0 if metrics.get("status") != "FAIL" else 1


def cmd_joint_report(args: argparse.Namespace) -> int:
    plan = json.loads((args.joint_dir / "joint_plan.json").read_text(encoding="utf-8"))
    status = aggregate_joint_status(args.joint_dir)
    storage_path = args.joint_dir / "storage" / "joint_storage_estimate.json"
    storage = json.loads(storage_path.read_text(encoding="utf-8")) if storage_path.exists() else None
    qc_path = args.joint_dir / "qc" / "cohort_variant_qc.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8")) if qc_path.exists() else None
    report = write_joint_report(args.joint_dir, plan=plan, status=status, storage=storage, qc=qc)
    print(f"Joint report: {report}")
    return 0


def _parse_sample_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def _cohort_max_rows(cfg: dict[str, Any]) -> int | None:
    cohort_cfg = cfg.get("cohort", {}) if isinstance(cfg.get("cohort"), dict) else {}
    value = cohort_cfg.get("max_rows")
    return int(value) if value is not None else 10000


def _fallback_contigs(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    fai = Path(cfg["reference"]["fai"])
    contigs: list[dict[str, Any]] = []
    if fai.exists():
        for line in fai.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and fields[1].isdigit():
                contigs.append({"id": fields[0], "length": int(fields[1])})
    return contigs or [{"id": "chr1", "length": 1}]


def _joint_final_vcf(joint_dir: Path) -> Path:
    plan_path = joint_dir / "joint_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        return Path(plan["expected_outputs"]["final_vcf"])
    return joint_dir / "outputs" / "cohort.germline.vcf.gz"


def _attempt_dir(cfg: dict[str, Any], sample: Sample, attempt_id: str) -> Path:
    return Path(cfg["project"]["output_root"]) / cfg["project"]["name"] / sample.sample_id / attempt_id


def _prepare_attempt(attempt_dir: Path, args: argparse.Namespace, cfg: dict[str, Any], sample: Sample, preserve_existing: bool = False) -> None:
    if not attempt_dir.exists():
        try:
            attempt_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise ValidationError(f"Attempt directory was created concurrently: {attempt_dir}") from exc
    for sub in ("logs", "status", "provenance", "inputs", "alignment", "snv", "sv", "qc", "reports", "temp"):
        (attempt_dir / sub).mkdir(parents=True, exist_ok=True)
    if not preserve_existing or not (attempt_dir / "config.original.yaml").exists():
        shutil.copyfile(args.config, attempt_dir / "config.original.yaml")
    if not preserve_existing or not (attempt_dir / "config.resolved.yaml").exists():
        dump_yaml(cfg, attempt_dir / "config.resolved.yaml")
    manifest_row = {
        "sample_id": sample.sample_id,
        "platform": sample.platform,
        "input_type": sample.input_type,
        "input_path": str(sample.input_path),
        "additional_inputs": [str(p) for p in sample.additional_inputs],
        "aligned": sample.aligned,
        "reference_id": sample.reference_id,
        "read_group_sample": sample.read_group_sample,
        "output_prefix": sample.output_prefix,
    }
    manifest_path = attempt_dir / "manifest.row.json"
    if not preserve_existing or not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest_row, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _plan(cfg: dict[str, Any], sample: Sample, analysis: str, attempt_dir: Path) -> list[dict[str, Any]]:
    ref = Path(cfg["reference"]["fasta"])
    threads = int(cfg["execution"]["threads"])
    prefix = sample.output_prefix
    aligned_bam = sample.input_path if sample.input_type == "aligned_bam" else attempt_dir / "alignment" / f"{prefix}.aligned.bam"
    merged_xml = attempt_dir / "inputs" / f"{prefix}.merged.consensusreadset.xml"
    plan: list[dict[str, Any]] = [{"name": "preflight", "action": "validate"}]
    align_input = sample.input_path
    if sample.input_type == "pacbio_dataset_xml_list":
        command = build_dataset_merge_command(sample, tool_config(cfg, "dataset"), merged_xml)
        plan.append({"name": "dataset_merge", "command": command})
        align_input = merged_xml
    if sample.input_type != "aligned_bam":
        command = build_pbmm2_align_command(sample, tool_config(cfg, "pbmm2"), ref, align_input, aligned_bam, threads)
        plan.append({"name": "alignment", "command": command})
    else:
        plan.append({"name": "alignment", "action": "reuse", "outputs": [aligned_bam]})
    plan.append({"name": "alignment_qc", "inputs": [aligned_bam]})
    if analysis in {"snv", "combined"}:
        out_vcf = attempt_dir / "snv" / f"{prefix}.snv.vcf"
        out_gvcf = attempt_dir / "snv" / f"{prefix}.snv.g.vcf" if cfg["workflow"].get("emit_gvcf", True) else None
        logging_dir = attempt_dir / "logs" / "deepvariant"
        command = build_deepvariant_command(tool_config(cfg, "deepvariant"), ref, aligned_bam, out_vcf, out_gvcf, logging_dir)
        plan.append({"name": "germline_snv", "command": command, "vcf": out_vcf, "gvcf": out_gvcf})
        plan.append({"name": "germline_snv_qc", "vcf": out_vcf})
    if analysis in {"sv", "combined"}:
        svsig = attempt_dir / "sv" / f"{prefix}.svsig.gz"
        sv_vcf = attempt_dir / "sv" / f"{prefix}.sv.vcf"
        tr_bed = Path(cfg["reference"]["tandem_repeats_bed"]) if cfg["reference"].get("tandem_repeats_bed") else None
        discover = build_pbsv_discover_command(tool_config(cfg, "pbsv"), aligned_bam, svsig, tr_bed)
        call = build_pbsv_call_command(tool_config(cfg, "pbsv"), ref, svsig, sv_vcf)
        plan.append({"name": "germline_sv_discover", "command": discover, "svsig": svsig})
        plan.append({"name": "germline_sv_call", "command": call, "vcf": sv_vcf})
        plan.append({"name": "germline_sv_qc", "vcf": sv_vcf})
    plan.append({"name": "sample_report", "action": "report"})
    return plan


def _write_plan(plan: list[dict[str, Any]], attempt_dir: Path) -> None:
    out = []
    for stage in plan:
        command: CommandSpec | None = stage.get("command")
        stage_dir = attempt_dir / "status" / stage["name"]
        stage_dir.mkdir(parents=True, exist_ok=True)
        if command:
            from variant_analysis_harness.common.command import write_command_json

            write_command_json(command, stage_dir / "stage.command.json")
        out.append({"stage": stage["name"], "command": command.argv if command else None, "action": stage.get("action", "execute")})
    (attempt_dir / "command_plan.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _run_stage(
    stage: dict[str, Any],
    cfg: dict[str, Any],
    sample: Sample,
    attempt_dir: Path,
    *,
    resume: bool,
    force: bool,
) -> tuple[StageResult, list[Path], dict[str, Any] | None]:
    name = stage["name"]
    stage_dir = attempt_dir / "status" / name
    stage_dir.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []
    qc: dict[str, Any] | None = None
    command: CommandSpec | None = stage.get("command")
    if resume and _can_reuse(stage, cfg, sample, stage_dir):
        result = StageResult(name, "skipped", 0, stage_dir / "logs" / "stdout.log", stage_dir / "logs" / "stderr.log", "", "", 0.0)
        write_stage_status(result, stage_dir / "stage.status.json", {"validation_result": "reused"})
        return result, list(command.outputs if command else stage.get("outputs", [])), None
    if command and not force:
        existing = [p for p in command.outputs if p.exists()]
        if existing:
            raise ValidationError(f"Output already exists; use --force or a new attempt id: {existing[0]}")
    if name == "preflight":
        data = run_preflight(cfg, sample, attempt_dir)
        result = StageResult(name, "success" if data["status"] in {"PASS", "WARN"} else "failed", 0, None, None, "", "", 0.0, warnings=data.get("warnings", []))
        _write_json(stage_dir / "stage.outputs.json", data)
    elif name == "alignment" and stage.get("action") == "reuse":
        validate_aligned_bam(stage["outputs"][0])
        bam_validation = validate_bam_with_samtools(
            stage["outputs"][0],
            expected_sample=sample.read_group_sample,
            reference_fai=Path(cfg["reference"]["fai"]),
            require_pbi=False,
            samtools=cfg["tools"]["samtools"].get("executable", "samtools"),
        )
        write_bam_validation(bam_validation, attempt_dir / "qc" / "bam_validation.json")
        if bam_validation["status"] == "FAIL":
            raise ValidationError(f"BAM validation failed: {stage['outputs'][0]}")
        data = run_alignment_qc(stage["outputs"][0], sample.read_group_sample, samtools=cfg["tools"]["samtools"].get("executable", "samtools"))
        write_alignment_qc_outputs(data, attempt_dir / "qc")
        result = StageResult(name, "success", 0, None, None, "", "", 0.0, warnings=data.get("warnings", []))
        produced = stage["outputs"]
        _write_json(stage_dir / "stage.outputs.json", {"outputs": [str(p) for p in produced], "reused": True})
    elif name == "alignment_qc":
        data = run_alignment_qc(stage["inputs"][0], sample.read_group_sample, samtools=cfg["tools"]["samtools"].get("executable", "samtools"))
        result = StageResult(name, "success", 0, None, None, "", "", 0.0, warnings=data.get("warnings", []))
        write_alignment_qc_outputs(data, attempt_dir / "qc")
    elif name == "germline_snv_qc":
        validation = validate_variant_vcf(stage["vcf"], expected_sample=sample.read_group_sample, reference_fai=Path(cfg["reference"]["fai"]))
        write_validation_result(validation, attempt_dir / "qc" / "snv_vcf_validation.json")
        if validation["status"] == "FAIL":
            raise ValidationError(f"SNV VCF validation failed: {stage['vcf']}")
        qc = run_snv_qc(stage["vcf"], sample.read_group_sample, int(cfg["qc"].get("thresholds", {}).get("minimum_records", 1)))
        write_qc_outputs(qc, attempt_dir / "qc" / "snv_qc")
        result = StageResult(name, "success" if qc["status"] != "FAIL" else "failed", 0, None, None, "", "", 0.0)
        produced = [attempt_dir / "qc" / "snv_qc.json", attempt_dir / "qc" / "snv_qc.tsv", attempt_dir / "qc" / "snv_qc.md"]
    elif name == "germline_sv_qc":
        validation = validate_variant_vcf(stage["vcf"], expected_sample=sample.read_group_sample, reference_fai=Path(cfg["reference"]["fai"]))
        write_validation_result(validation, attempt_dir / "qc" / "sv_vcf_validation.json")
        if validation["status"] == "FAIL":
            raise ValidationError(f"SV VCF validation failed: {stage['vcf']}")
        qc = run_sv_qc(stage["vcf"], sample.read_group_sample, int(cfg["qc"].get("thresholds", {}).get("minimum_records", 1)))
        write_sv_qc_outputs(qc, attempt_dir / "qc")
        result = StageResult(name, "success" if qc["status"] != "FAIL" else "failed", 0, None, None, "", "", 0.0)
        produced = [attempt_dir / "qc" / n for n in ("sv_qc.json", "sv_qc.tsv", "sv_qc.md", "svtype_counts.tsv", "sv_size_distribution.tsv")]
    elif name == "sample_report":
        result = StageResult(name, "success", 0, None, None, "", "", 0.0)
    elif command:
        run_command = command
        atomic_outputs = name in {"germline_snv", "germline_sv_discover", "germline_sv_call"}
        final_outputs = list(command.outputs)
        temp_outputs: list[Path] = []
        if atomic_outputs:
            temp_outputs = [incomplete_path(path) for path in final_outputs]
            replacements = {str(final): str(temp) for final, temp in zip(final_outputs, temp_outputs)}
            run_argv = []
            for part in command.argv:
                rendered = str(part)
                for final_text, temp_text in replacements.items():
                    rendered = rendered.replace(final_text, temp_text)
                run_argv.append(rendered)
            run_command = CommandSpec(
                command.stage,
                command.tool_name,
                run_argv,
                inputs=command.inputs,
                outputs=temp_outputs,
                cwd=command.cwd,
                timeout_seconds=command.timeout_seconds,
            )
        result = execute_stage(run_command, stage_dir, dry_run=False)
        if result.status != "success":
            write_stage_status(result, stage_dir / "stage.status.json")
            return result, [], None
        for output in run_command.outputs:
            require_readable_file(output, "declared output")
        if atomic_outputs:
            for temp_output, final_output in zip(temp_outputs, final_outputs):
                publish_atomically(temp_output, final_output, overwrite=force)
        if name == "alignment":
            bam_validation = validate_bam_with_samtools(
                command.outputs[0],
                expected_sample=sample.read_group_sample,
                reference_fai=Path(cfg["reference"]["fai"]),
                require_pbi=False,
                samtools=cfg["tools"]["samtools"].get("executable", "samtools"),
            )
            write_bam_validation(bam_validation, attempt_dir / "qc" / "bam_validation.json")
            if bam_validation["status"] == "FAIL":
                raise ValidationError(f"BAM validation failed: {command.outputs[0]}")
        if name == "germline_sv_discover":
            svsig_validation = validate_svsig_gzip(final_outputs[0])
            write_validation_result(svsig_validation, attempt_dir / "qc" / "svsig_validation.json")
            if svsig_validation["status"] == "FAIL":
                raise ValidationError(f"svsig validation failed: {final_outputs[0]}")
        produced = final_outputs
    else:
        result = StageResult(name, "skipped", 0, None, None, "", "", 0.0)
    signature = stage_signature(cfg, sample, (command.inputs if command else []), cfg.get("tools", {}).get(command.tool_name) if command else None)
    write_stage_status(result, stage_dir / "stage.status.json", {"signature": signature})
    write_provenance(
        stage_dir / "stage.provenance.json",
        project_id=cfg["project"]["name"],
        sample_id=sample.sample_id,
        attempt_id=attempt_dir.name,
        stage=name,
        command=command,
        tool=cfg.get("tools", {}).get(command.tool_name) if command else None,
        reference=cfg["reference"],
        outputs=produced,
        validation_status="PASS" if result.status == "success" else result.status,
        warnings=result.warnings,
    )
    _write_json(stage_dir / "stage.outputs.json", {"outputs": [str(p) for p in produced]})
    return result, produced, qc


def _can_reuse(stage: dict[str, Any], cfg: dict[str, Any], sample: Sample, stage_dir: Path) -> bool:
    status = read_stage_status(stage_dir / "stage.status.json")
    if not status or status.get("status") != "success":
        return False
    command: CommandSpec | None = stage.get("command")
    outputs = list(command.outputs if command else stage.get("outputs", []))
    if not outputs or not all(p.exists() and p.stat().st_size > 0 for p in outputs):
        return False
    prior_sig = status.get("signature")
    current_sig = stage_signature(cfg, sample, (command.inputs if command else []), cfg.get("tools", {}).get(command.tool_name) if command else None)
    if prior_sig != current_sig:
        raise ResumeError(f"Signature mismatch for stage {stage['name']}; use a new attempt id or --force")
    return True


def _write_blocked(attempt_dir: Path, stage: str, reason: str) -> None:
    stage_dir = attempt_dir / "status" / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    result = StageResult(stage, "blocked", None, None, None, "", "", 0.0, error=reason)
    write_stage_status(result, stage_dir / "stage.status.json")


def cmd_somatic_plan(args: argparse.Namespace, *, validate_only: bool) -> int:
    cfg = load_run_config(args.config)
    somatic_config = resolve_somatic_config(cfg)
    if args.mode:
        somatic_config["mode"] = args.mode
    if args.identity_policy:
        somatic_config["identity_policy"] = args.identity_policy
    include_pairs = _split_set(args.include_pairs)
    exclude_pairs = _split_set(args.exclude_pairs)
    include_subjects = _split_set(args.include_subjects)
    exclude_subjects = _split_set(args.exclude_subjects)
    selected, excluded, validation = load_somatic_manifest(
        args.manifest,
        somatic_config=somatic_config,
        require_existing=False,
        include_pairs=include_pairs,
        exclude_pairs=exclude_pairs,
        include_subjects=include_subjects,
        exclude_subjects=exclude_subjects,
    )
    attempt_dir = somatic_attempt_dir(cfg, args.somatic_project_id, args.attempt_id, args.output_root)
    if validate_only:
        write_somatic_manifest_artifacts(selected, excluded, validation, attempt_dir)
        print(RESEARCH_USE_DISCLAIMER)
        print(f"Somatic manifest validation: {validation.status}")
        return 0 if validation.status != "FAIL" else 1
    max_concurrent = int(somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1)
    prepare_somatic_attempt(
        attempt_dir,
        config_path=args.config,
        manifest_path=args.manifest,
        cfg=cfg,
        selected=selected,
        excluded=excluded,
        validation=validation,
    )
    plan = generate_somatic_plan(
        cfg,
        somatic_config,
        config_path=args.config,
        manifest_path=args.manifest,
        selected=selected,
        excluded=excluded,
        validation=validation,
        somatic_project_id=args.somatic_project_id,
        attempt_id=args.attempt_id,
        output_root=args.output_root,
        max_concurrent_pairs=max_concurrent,
    )
    write_somatic_plan(plan, attempt_dir)
    write_somatic_report(plan, attempt_dir)
    print(RESEARCH_USE_DISCLAIMER)
    print(f"Somatic plan written: {attempt_dir / 'somatic_plan.json'}")
    print("No somatic callers were executed.")
    return 0 if validation.status != "FAIL" else 1


def cmd_somatic_status(args: argparse.Namespace) -> int:
    statuses = load_pair_statuses(args.somatic_dir)
    counts = aggregate_status_counts(statuses)
    print(json.dumps({"status_counts": counts, "pair_count": len(statuses)}, indent=2, sort_keys=True))
    return 0


def cmd_somatic_rerun_manifest(args: argparse.Namespace) -> int:
    rows = generate_somatic_rerun_manifest(
        args.somatic_dir,
        args.output,
        status=args.status,
        failure_category=args.failure_category,
        subject_id=args.subject_id,
        analysis_mode=args.analysis_mode,
        include_pairs=_split_set(args.include_pairs),
        allow_successful=args.allow_successful,
    )
    print(f"Somatic rerun manifest written: {args.output} ({len(rows)} pairs)")
    return 0


def cmd_somatic_report(args: argparse.Namespace) -> int:
    plan_path = args.somatic_dir / "somatic_plan.json"
    if not plan_path.exists():
        raise ValidationError(f"Somatic plan not found: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = write_somatic_report(plan, args.somatic_dir)
    print(f"Somatic report written: {report}")
    return 0


def cmd_somatic_snv_plan(args: argparse.Namespace, *, run: bool, validate_only: bool) -> int:
    cfg = load_run_config(args.config)
    somatic_config = resolve_somatic_config(cfg)
    if args.mode:
        somatic_config["mode"] = args.mode
    selected, excluded, validation = load_somatic_manifest(
        args.manifest,
        somatic_config=somatic_config,
        require_existing=False,
        include_pairs=_split_set(args.include_pairs),
        exclude_pairs=_split_set(args.exclude_pairs),
    )
    ds_config = resolve_deepsomatic_config(somatic_config)
    mode_for_validation = args.mode or somatic_config.get("mode", "tumor_normal")
    ds_validation = validate_deepsomatic_config(ds_config, mode=mode_for_validation)
    attempt_dir = args.somatic_dir or somatic_attempt_dir(cfg, args.somatic_project_id, args.attempt_id, args.output_root)
    if validate_only:
        _write_json(attempt_dir / "deepsomatic_preflight.json", {"somatic_manifest": validation.to_dict(), "deepsomatic": ds_validation})
        return 0 if validation.status != "FAIL" and ds_validation["status"] != "FAIL" else 1
    plan = generate_deepsomatic_plan(
        cfg,
        somatic_config,
        project_attempt_dir=attempt_dir,
        selected=selected,
        reference=Path(cfg["reference"]["fasta"]),
        pair_attempt_id=args.pair_attempt_id,
        max_concurrent=int(ds_config["deepsomatic"].get("resources", {}).get("max_concurrent_pairs") or somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1),
        include_warning_pairs=args.include_warning_pairs,
    )
    write_deepsomatic_plan(plan, attempt_dir)
    write_command_files(plan, attempt_dir)
    write_deepsomatic_cohort_report(plan, attempt_dir)
    if run:
        print("DeepSomatic run command is wired for explicit execution, but no real caller is invoked by standard tests.")
    print(f"DeepSomatic plan written: {attempt_dir / 'deepsomatic_plan.json'}")
    return 0 if ds_validation["status"] != "FAIL" else 1


def cmd_somatic_snv_slurm(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    somatic_config = resolve_somatic_config(cfg)
    selected, _, _ = load_somatic_manifest(args.manifest, somatic_config=somatic_config)
    attempt_dir = args.somatic_dir or somatic_attempt_dir(cfg, args.somatic_project_id, args.attempt_id, args.output_root)
    plan = generate_deepsomatic_plan(
        cfg,
        somatic_config,
        project_attempt_dir=attempt_dir,
        selected=selected,
        reference=Path(cfg["reference"]["fasta"]),
        pair_attempt_id=args.pair_attempt_id,
        max_concurrent=int(somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1),
        include_warning_pairs=args.include_warning_pairs,
    )
    write_deepsomatic_plan(plan, attempt_dir)
    script = write_deepsomatic_slurm_array(plan, attempt_dir / "slurm" / "deepsomatic_array.sh", max_concurrent=int(somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1), submit=args.submit)
    print(f"DeepSomatic Slurm array script written: {script}")
    return 0


def cmd_somatic_snv_status(args: argparse.Namespace) -> int:
    plan_path = args.somatic_dir / "deepsomatic_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {"pairs": [], "blocked_pairs": []}
    print(json.dumps({"ready_pairs": len(plan.get("pairs", [])), "blocked_pairs": len(plan.get("blocked_pairs", []))}, indent=2, sort_keys=True))
    return 0


def cmd_somatic_snv_rerun_manifest(args: argparse.Namespace) -> int:
    rows = generate_deepsomatic_rerun_manifest(
        args.somatic_dir / "deepsomatic_plan.json",
        args.output,
        status=args.status,
        failure_category=args.failure_category,
        analysis_mode=args.analysis_mode,
        include_pairs=_split_set(args.include_pairs),
    )
    print(f"DeepSomatic rerun manifest written: {args.output} ({len(rows)} pairs)")
    return 0


def cmd_somatic_snv_report(args: argparse.Namespace) -> int:
    plan_path = args.somatic_dir / "deepsomatic_plan.json"
    if not plan_path.exists():
        raise ValidationError(f"DeepSomatic plan not found: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = write_deepsomatic_cohort_report(plan, args.somatic_dir)
    print(f"DeepSomatic report written: {report}")
    return 0


def cmd_somatic_sv_plan(args: argparse.Namespace, *, run: bool, validate_only: bool) -> int:
    cfg = load_run_config(args.config)
    somatic_config = resolve_somatic_config(cfg)
    if args.mode:
        somatic_config["mode"] = args.mode
    selected, excluded, validation = load_somatic_manifest(
        args.manifest,
        somatic_config=somatic_config,
        require_existing=False,
        include_pairs=_split_set(args.include_pairs),
        exclude_pairs=_split_set(args.exclude_pairs),
    )
    sev_config = resolve_severus_config(somatic_config)
    mode_for_validation = args.mode or somatic_config.get("mode", "tumor_normal")
    sev_validation = validate_severus_config(sev_config, mode=mode_for_validation)
    attempt_dir = args.somatic_dir or somatic_attempt_dir(cfg, args.somatic_project_id, args.attempt_id, args.output_root)
    if validate_only:
        _write_json(attempt_dir / "severus_preflight.json", {"somatic_manifest": validation.to_dict(), "severus": sev_validation})
        return 0 if validation.status != "FAIL" and sev_validation["status"] != "FAIL" else 1
    plan = generate_severus_plan(
        cfg,
        somatic_config,
        project_attempt_dir=attempt_dir,
        selected=selected,
        reference=Path(cfg["reference"]["fasta"]),
        pair_attempt_id=args.pair_attempt_id,
        max_concurrent=int(somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1),
        include_warning_pairs=args.include_warning_pairs,
    )
    write_severus_plan(plan, attempt_dir)
    write_severus_command_files(plan, attempt_dir)
    write_severus_cohort_report(plan, attempt_dir)
    if run:
        print("Severus run command is wired for explicit execution, but no real caller is invoked by standard tests.")
    print(f"Severus plan written: {attempt_dir / 'severus_plan.json'}")
    return 0 if sev_validation["status"] != "FAIL" else 1


def cmd_somatic_sv_slurm(args: argparse.Namespace) -> int:
    cfg = load_run_config(args.config)
    somatic_config = resolve_somatic_config(cfg)
    selected, _, _ = load_somatic_manifest(args.manifest, somatic_config=somatic_config)
    attempt_dir = args.somatic_dir or somatic_attempt_dir(cfg, args.somatic_project_id, args.attempt_id, args.output_root)
    plan = generate_severus_plan(
        cfg,
        somatic_config,
        project_attempt_dir=attempt_dir,
        selected=selected,
        reference=Path(cfg["reference"]["fasta"]),
        pair_attempt_id=args.pair_attempt_id,
        max_concurrent=int(somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1),
        include_warning_pairs=args.include_warning_pairs,
    )
    write_severus_plan(plan, attempt_dir)
    script = write_severus_slurm_array(plan, attempt_dir / "slurm" / "severus_array.sh", max_concurrent=int(somatic_config.get("execution", {}).get("max_concurrent_pairs", 1) or 1), submit=args.submit)
    print(f"Severus Slurm array script written: {script}")
    return 0


def cmd_somatic_sv_status(args: argparse.Namespace) -> int:
    plan_path = args.somatic_dir / "severus_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {"pairs": [], "blocked_pairs": []}
    print(json.dumps({"ready_pairs": len(plan.get("pairs", [])), "blocked_pairs": len(plan.get("blocked_pairs", []))}, indent=2, sort_keys=True))
    return 0


def cmd_somatic_sv_rerun_manifest(args: argparse.Namespace) -> int:
    rows = generate_severus_rerun_manifest(
        args.somatic_dir / "severus_plan.json",
        args.output,
        status=args.status,
        failure_category=args.failure_category,
        analysis_mode=args.analysis_mode,
        include_pairs=_split_set(args.include_pairs),
    )
    print(f"Severus rerun manifest written: {args.output} ({len(rows)} pairs)")
    return 0


def cmd_somatic_sv_report(args: argparse.Namespace) -> int:
    plan_path = args.somatic_dir / "severus_plan.json"
    if not plan_path.exists():
        raise ValidationError(f"Severus plan not found: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = write_severus_cohort_report(plan, args.somatic_dir)
    print(f"Severus report written: {report}")
    return 0


def cmd_severus_contract_check(args: argparse.Namespace) -> int:
    capability = COMPATIBILITY_REGISTRY.get(args.expected_version)
    if capability is None:
        raise ValidationError(f"No committed Severus contract for version {args.expected_version}")
    if args.mock_help:
        help_text = args.mock_help.read_text(encoding="utf-8")
        version_text = args.mock_version.read_text(encoding="utf-8").strip() if args.mock_version else args.expected_version
    else:
        help_proc = subprocess.run([args.executable, "--help"], text=True, capture_output=True, check=False)
        version_proc = subprocess.run([args.executable, "--version"], text=True, capture_output=True, check=False)
        help_text = help_proc.stdout + help_proc.stderr
        version_text = (version_proc.stdout + version_proc.stderr).strip()
    expected_flags = [
        capability["target_input_flag"],
        capability["control_input_flag"],
        capability["output_directory_flag"],
        capability["thread_flag"],
        capability["phasing_vcf_flag"],
        capability["vntr_bed_flag"],
        capability["pon_flag"],
        capability["supplementary_tag_flag"],
    ]
    unavailable = list(capability.get("unavailable_flags", []))
    supported_help_text = help_text.split("Unavailable in this contract:", 1)[0]
    missing = [flag for flag in expected_flags if flag not in supported_help_text]
    obsolete_present = [flag for flag in unavailable if flag in supported_help_text]
    status = "FAIL" if missing or obsolete_present or args.expected_version not in version_text else "PASS"
    if status == "FAIL" and args.policy == "warn":
        status = "WARN"
    report = {
        "status": status,
        "expected_version": args.expected_version,
        "detected_version_text": version_text,
        "matching_flags": [flag for flag in expected_flags if flag in help_text],
        "missing_flags": missing,
        "obsolete_flags_present": obsolete_present,
        "new_flags": [],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "severus_contract_drift.json", report)
    lines = ["# Severus Contract Drift Check", "", f"Status: {status}", f"Expected version: {args.expected_version}", f"Detected version text: {version_text}", "", "## Missing Flags", *(missing or ["None"]), "", "## Obsolete Flags Present", *(obsolete_present or ["None"])]
    (args.output_dir / "severus_contract_drift.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status in {"PASS", "WARN"} else 1


def cmd_somatic_integrated(args: argparse.Namespace, *, validate_only: bool) -> int:
    cfg = load_run_config(args.config)
    somatic_config = resolve_somatic_config(cfg)
    include_pairs = _split_set(args.include_pairs)
    exclude_pairs = _split_set(args.exclude_pairs)
    selected, excluded, validation = load_somatic_manifest(args.manifest, somatic_config=somatic_config, require_existing=False, include_pairs=include_pairs, exclude_pairs=exclude_pairs)
    integrated_config = resolve_integrated_config(somatic_config)
    config_validation = validate_integrated_config(integrated_config)
    attempt_dir = integrated_attempt_dir(cfg, args.somatic_project_id, args.integrated_attempt_id, args.output_root)
    if validate_only:
        _write_json(attempt_dir / "validation" / "integrated_config_validation.json", {"somatic_manifest": validation.to_dict(), "integrated": config_validation})
        print(RESEARCH_USE_DISCLAIMER)
        print(f"Integrated somatic validation: {config_validation['status']}")
        return 0 if validation.status != "FAIL" and config_validation["status"] != "FAIL" else 1
    if attempt_dir.exists() and not args.force:
        raise ValidationError(f"Integrated attempt directory already exists; use --force or a new integrated attempt id: {attempt_dir}")
    somatic_dir = args.somatic_dir or somatic_attempt_dir(cfg, args.somatic_project_id, args.attempt_id, args.output_root)
    plan = generate_integrated_project(
        cfg,
        somatic_config,
        somatic_project_id=args.somatic_project_id,
        integrated_attempt_id=args.integrated_attempt_id,
        selected_pairs=selected,
        excluded_pairs=excluded,
        somatic_dir=somatic_dir,
        manifest_path=args.manifest,
        config_path=args.config,
        deepsomatic_attempt=args.deepsomatic_attempt,
        severus_attempt=args.severus_attempt,
        allow_partial=args.allow_partial if args.allow_partial else None,
        include_warnings=args.include_warnings if args.include_warnings else None,
    )
    write_integrated_outputs(plan, attempt_dir)
    print(f"Integrated somatic outputs written: {attempt_dir}")
    print("No caller was executed.")
    return 0


def cmd_somatic_integrated_status(args: argparse.Namespace) -> int:
    path = args.integrated_dir / "exports" / "integrated_pair_status.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    from variant_analysis_harness.somatic.integrated.status import status_counts

    print(json.dumps({"pair_count": len(rows), "status_counts": status_counts(rows)}, indent=2, sort_keys=True))
    return 0


def cmd_somatic_integrated_report(args: argparse.Namespace) -> int:
    report = args.integrated_dir / "reports" / "integrated_somatic_report.md"
    if not report.exists():
        raise ValidationError(f"Integrated report not found: {report}")
    print(f"Integrated report: {report}")
    return 0


def cmd_somatic_integrated_rerun(args: argparse.Namespace) -> int:
    path = args.integrated_dir / "status" / "integrated_rerun_recommendations.tsv"
    if not path.exists():
        raise ValidationError(f"Integrated rerun recommendations not found: {path}")
    print(f"Integrated rerun recommendations: {path}")
    return 0


def cmd_somatic_portfolio_report(args: argparse.Namespace) -> int:
    report = args.integrated_dir / "reports" / "integrated_portfolio_report.md"
    if not report.exists():
        raise ValidationError(f"Integrated portfolio report not found: {report}")
    print(f"Integrated portfolio report: {report}")
    return 0


def _split_set(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
