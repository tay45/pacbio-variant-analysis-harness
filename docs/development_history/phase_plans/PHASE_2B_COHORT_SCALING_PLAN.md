# Phase 2B Cohort Orchestration, Slurm Arrays, Failure Recovery, and Scalable Reporting Plan

## 1. Current Single-Sample Architecture

The Phase 2A.1.2 repository provides a research-use PacBio HiFi germline SNV/SV harness centered on single-sample execution. The current CLI validates a run configuration and sample manifest, builds safe subprocess argument lists, supports local execution and site-neutral Slurm script generation, records provenance/status, performs conservative QC/output validation, and preserves the legacy interactive script under `legacy/`.

Implemented analytical scope remains:

- PacBio HiFi germline SNV/indel with DeepVariant.
- PacBio HiFi germline SV with pbsv.
- SNV-only, SV-only, and combined single-sample modes.
- Aligned BAM, unaligned PacBio BAM, and PacBio dataset XML inputs.
- Optional dataset merge, pbmm2 alignment, gVCF generation, and tandem-repeat BED use.

Phase 2B must preserve this behavior and add cohort-level planning and orchestration without adding somatic, CNV, Illumina-specific, Oxford Nanopore-specific, clinical, employer-specific, or real-data functionality.

## 2. Proposed Cohort Orchestration Architecture

Add a `variant_analysis_harness/cohort/` package that is deliberately planning-first:

- `manifest.py`: parse, normalize, validate, filter, and resolve multi-sample cohort manifests.
- `planning.py`: generate cohort execution plans and stable sample-to-array mappings.
- `slurm.py`: generate site-neutral Slurm array scripts without submitting by default.
- `status.py`: write/aggregate per-sample/per-stage status records.
- `rerun.py`: create failed-sample and failed-stage rerun manifests.
- `incremental.py`: compare a new manifest/config against prior cohort metadata and decide reuse.
- `storage.py`: produce planning-only storage estimates.
- `scratch.py`: validate scratch configuration and create safe task-specific scratch paths.
- `qc.py`: aggregate existing sample-level QC/status metadata.
- `reporting.py`: write Markdown and optional dependency-light HTML cohort reports.
- `preflight_cache.py`: signature-based shared validation cache for immutable references/tools.
- `failure.py`: structured failure-category definitions and conservative classification helpers.

The cohort layer will call existing common validation, path, signature, provenance, and reporting helpers rather than replacing them.

## 3. Cohort Manifest Design

The manifest remains TSV for portability and reviewability. Required active fields:

- `sample_id`
- `platform`
- `input_type`
- `input_path`
- `additional_inputs`
- `aligned`
- `reference_id`
- `read_group_sample`
- `output_prefix`
- `analysis`
- `enabled`
- `cohort_group`
- `priority`

Optional future-compatible fields:

- `family_id`
- `population_group`
- `batch_id`
- `library_id`
- `sex`
- `notes`

Validation will enforce unique sample IDs and output prefixes, safe identifiers, supported platform/input/analysis combinations, deterministic ordering, duplicate input/read-group alias warnings or failures as appropriate, configured maximum row count, reference consistency, enabled/excluded handling, and stable array-index mapping.

Generated validation artifacts:

- `cohort_manifest.resolved.tsv`
- `cohort_manifest.validation.json`
- `cohort_manifest.validation.md`

## 4. Cohort Validation Design

`cohort-validate` will validate schema-level and cross-row constraints without running analytical tools unless future explicit probe support is added. It will report PASS/WARN/FAIL summaries, row-specific issues, global issues, tool requirements by stage, expected stage counts, expected array task counts, storage categories, concurrency warnings, and selected/excluded sample counts.

Invalid global plans return nonzero. Disabled rows are represented as `excluded`, not silently dropped.

## 5. Slurm Job-Array Design

Phase 2B will prioritize reliability: one Slurm array task executes the complete single-sample harness workflow for one selected sample. This avoids fragile cross-stage scheduler dependency logic while still isolating sample failures.

Generated artifacts:

- `array_index.tsv`
- `slurm/cohort_array.sh`
- `slurm/dependency_graph.json`
- `slurm/dependency_graph.md`

The array script uses:

```text
#SBATCH --array=1-N%M
```

where `N` is the selected sample count and `M` is a configurable bounded concurrency. Submission is never performed unless an explicit future submit path is approved; Phase 2B dry-run/generation is reviewable and site-neutral.

Future stage-array dependencies will be documented but not represented as implemented execution.

## 6. Stage-Dependency Design

For Phase 2B full-sample tasks, dependencies are internal to the existing single-sample stage order:

1. preflight
2. optional dataset merge
3. optional alignment
4. optional germline SNV
5. optional germline SV discover/call
6. QC
7. report

The plan records required stages per sample, reusable validated stages, pending stages, and blocked stages. If future stage arrays are implemented, analytical stages will use `afterok`, while QC/report aggregation may use `afterany` when failure reporting is needed.

## 7. Resource-Profile Design

Extend configuration schemas to accept nullable per-stage resources:

- `cpus`
- `memory_gb`
- `time`
- `scratch_gb`

Supported stages include preflight, dataset_merge, alignment, germline_snv, germline_sv_discover, germline_sv_call, qc, and report. Values are planning defaults, not universal recommendations. Validation flags non-positive values, malformed walltimes, and unusually high values as warnings/errors.

Resolved resources are recorded per task in `cohort_plan.json`.

## 8. Status-Store Design

Use filesystem-friendly per-task JSON status records under sharded status directories plus compact aggregate outputs:

- immutable event records in `status/events/XX/SAMPLE_ID/STAGE.TIMESTAMP.json`
- current summaries in `status/current/XX/SAMPLE_ID.json`
- aggregate `cohort_status.tsv`
- aggregate `cohort_status.json`
- aggregate `cohort_status.md`

Status values:

- pending
- submitted
- queued
- running
- success
- warning
- failed
- blocked
- skipped
- excluded
- interrupted
- cancelled
- unknown

Writes are atomic. No shared mutable JSON file is written by all array tasks.

## 9. Failed-Sample Recovery Design

`cohort-rerun-manifest` will select rows by sample status, stage status, failure category, warning status, or explicit sample list. It will preserve original fields, append rerun metadata fields, produce deterministic TSV output, and never submit jobs automatically.

Generated artifacts may include:

- failed-sample manifest
- failed-stage manifest
- blocked-sample manifest
- retry recommendation Markdown

## 10. Incremental-Cohort Design

`cohort-plan --reuse-from PREVIOUS_COHORT_DIR` will compare:

- sample IDs
- manifest row hashes
- config signatures
- reference signatures
- tool/container signatures when known

Outputs:

- `incremental_comparison.tsv`
- `incremental_comparison.json`
- `incremental_comparison.md`

Prior cohort directories are never mutated. Reuse is rejected when signatures are incompatible or missing.

## 11. Cohort-Report Design

`cohort-report` will generate `reports/cohort_report.md` and optionally a dependency-light HTML file. The report includes research-use disclaimers, cohort identifiers, enabled/excluded samples, analysis modes, references, tool/container summaries, Slurm plan, status counts, failure categories, warnings, QC summaries, missing metrics, reuse/new sample summaries, storage estimates, output inventory, known limitations, and operator actions.

## 12. Files to Create

- `variant_analysis_harness/cohort/__init__.py`
- `variant_analysis_harness/cohort/manifest.py`
- `variant_analysis_harness/cohort/planning.py`
- `variant_analysis_harness/cohort/slurm.py`
- `variant_analysis_harness/cohort/status.py`
- `variant_analysis_harness/cohort/rerun.py`
- `variant_analysis_harness/cohort/incremental.py`
- `variant_analysis_harness/cohort/storage.py`
- `variant_analysis_harness/cohort/scratch.py`
- `variant_analysis_harness/cohort/qc.py`
- `variant_analysis_harness/cohort/reporting.py`
- `variant_analysis_harness/cohort/preflight_cache.py`
- `variant_analysis_harness/cohort/failure.py`
- `schemas/cohort_manifest.schema.json`
- `schemas/cohort_plan.schema.json`
- `examples/manifests/cohort_manifest.example.tsv`
- `docs/cohort_manifest.md`
- `docs/cohort_execution.md`
- `docs/slurm_arrays.md`
- `docs/cohort_status.md`
- `docs/failure_recovery.md`
- `docs/incremental_cohorts.md`
- `docs/storage_and_scratch.md`
- `docs/cohort_reporting.md`
- `docs/scaling_to_3000_samples.md`
- `tests/unit/test_cohort_manifest.py`
- `tests/unit/test_cohort_planning.py`
- `tests/unit/test_cohort_slurm_status.py`
- `tests/unit/test_cohort_recovery_incremental.py`
- `tests/unit/test_cohort_storage_scratch.py`
- `tests/scale/test_3000_sample_planning.py`

## 13. Files to Modify

- `variant_analysis_harness/cli.py`
- `variant_analysis_harness/__init__.py`
- `pyproject.toml`
- `README.md`
- existing configuration schemas as needed for cohort resources/scratch.
- `docs/testing.md`
- `docs/troubleshooting.md`
- `REVIEW_MANIFEST.txt`

## 14. Migration and Backward-Compatibility Risks

- CLI additions must not change existing single-sample command semantics.
- Cohort manifest parsing must remain distinct from existing single-sample manifest behavior.
- New resource/scratch schema fields must be optional so older configs continue to validate.
- Slurm generation must remain site-neutral and must not introduce default submission.
- Planning reuse must be conservative; false reuse is more dangerous than unnecessary rerun.

## 15. Test Strategy

Use official pytest only. Standard tests must not require Slurm, network, external analytical tools, private paths, or real sequencing data.

Test categories:

- cohort manifest parsing/validation/filtering/ordering
- deterministic array index generation
- cohort plan generation and resource resolution
- Slurm array script generation and dry-run-only behavior
- status event aggregation and sharding
- failure-category handling
- rerun manifest generation
- incremental comparison and reuse rejection
- scratch safety and storage estimation
- cohort QC/report generation
- 3,000-sample synthetic planning scale test
- regression tests proving Phase 2A.1.2 tests still pass
- portability and no-somatic/no-CNV scans

## 16. 3,000-Sample Simulation Strategy

Generate an in-memory or temporary synthetic TSV manifest with 3,000 enabled rows using neutral fake paths and dry-run/mock settings. Avoid creating BAM files. Validate parsing, deterministic ordering, plan generation, array mapping, status aggregation, rerun selection, incremental comparison, report generation, runtime, and output size.

The test records timing and task counts in `SCALE_TEST_RESULTS.txt`. Peak memory is reported if available through the standard library on the current platform.

## 17. Acceptance-Criteria Mapping

Phase 2B is complete when:

- all Phase 2A.1.2 tests still pass,
- cohort manifests validate and produce resolved artifacts,
- cohort plans and stable array mappings are generated,
- site-neutral Slurm arrays use bounded configurable concurrency,
- status aggregation and failure categories are implemented,
- rerun manifests and incremental comparisons are deterministic,
- shared preflight cache and scratch configuration are safe and signature-based,
- storage estimates, QC aggregation, and cohort reports are generated,
- the 3,000-sample synthetic planning test passes,
- documentation accurately separates implemented and deferred functionality,
- no somatic, CNV, Illumina-specific, ONT-specific, clinical, institutional, or private-data functionality is added.
