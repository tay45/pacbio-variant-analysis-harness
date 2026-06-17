# Phase 2E DeepSomatic Integration Plan

## 1. Current Phase 2D Somatic Architecture

Phase 2D introduced a research-use somatic foundation under
`variant_analysis_harness/somatic/`. It provides somatic configuration defaults,
manifest parsing, tumor-normal and tumor-only policy validation, identity and
reference preflight, coverage/purity/contamination/ploidy metadata validation,
deterministic pair plans, pair statuses, rerun manifests, reports, and a
synthetic 3,000-pair planning test. It intentionally does not execute somatic
callers.

## 2. DeepSomatic Integration Boundaries

Phase 2E adds an optional DeepSomatic PacBio HiFi small-variant layer. It is the
only active somatic SNV/indel backend in this phase. It does not add Severus,
somatic SV, CNV, annotation, pathogenicity interpretation, clinical reporting,
cloud execution, or institutional deployment.

## 3. Supported Analysis Modes

Supported modes are matched `tumor_normal` and explicitly authorized
`tumor_only`. Missing normal inputs never trigger tumor-only automatically.
Tumor-only requires Phase 2D tumor-only permission and acknowledgment.

## 4. PacBio Model-Selection Policy

Matched tumor-normal PacBio HiFi mode uses `PACBIO`. Tumor-only PacBio HiFi mode
uses `PACBIO_TUMOR_ONLY`. These model types are not interchangeable and model
selection is validated before command construction or execution.

## 5. DeepSomatic Version Policy

DeepSomatic versions are parsed as semantic versions in a centralized
compatibility module. Unknown future versions fail under strict policy and may
warn under explicit permissive policy. Requested and detected versions are
recorded separately.

## 6. Model Metadata Policy

Model metadata validation supports `model.example_info.json` when required by
configuration or by version policy. Metadata is read-only, checksums are
recorded, referenced model files are validated, and missing files are never
downloaded automatically. Container-bundled models are supported without a host
model path.

## 7. Container And Executable Strategy

DeepSomatic command construction supports direct executable, Docker,
Apptainer, and Singularity-compatible wrappers. All commands are represented as
`list[str]`, with deterministic bind ordering and no shell interpolation.

## 8. Command-Construction Design

The builder creates immutable argument-list commands for `run_deepsomatic`.
Protected arguments include model type, reference, tumor/normal reads, outputs,
sample names, logging directory, intermediate directory, and num shards.
Conflicting `extra_args` are rejected.

## 9. Region And Sharding Strategy

One complete DeepSomatic run is planned per pair. DeepSomatic internal
`num_shards` is distinct from Slurm pair-array tasks. Regions may be whole
genome, explicit strings, or a region file and are validated structurally in
Phase 2E.

## 10. Local Execution Design

Planning and dry-run never execute the caller. The explicit run command may
execute through an injected runner or normal safe subprocess execution. Standard
tests use fake runners/executables and do not start DeepSomatic or containers.

## 11. Slurm Pair-Array Design

Slurm planning emits one pair per array task with deterministic indices and
configurable maximum concurrency. Submission is disabled by default and requires
explicit `--submit`.

## 12. Tumor-Only Safeguards

Tumor-only rows require explicit mode, project permission, acknowledgment,
tumor-only-compatible model, and no normal command arguments. Reports state
tumor-only limitations and do not claim equivalence to matched-normal analysis.

## 13. Optional PoN Policy

Phase 2E does not construct a panel of normals. It may validate a user-supplied
PoN path and add a command flag only when explicitly enabled.

## 14. Attempt, Resume, And Force Model

Each pair has attempt-specific DeepSomatic output directories. Resume reuses
only outputs with matching command/input/reference/model signatures and passing
output validation. Force creates a preserved new attempt and records
supersession. Partial outputs are never treated as successful.

## 15. Output Layout

Outputs live under each somatic pair attempt in
`small_variants/deepsomatic/`, including command JSON, command script, logs,
intermediate/temporary/output directories, validation, QC, provenance, and
status.

## 16. Output VCF/gVCF Validation

Validation checks existence, nonzero size, index presence/freshness, VCF header,
fileformat, contigs, samples, sort order, coordinates, REF/ALT, FILTER
declarations, truncation, region bounds where supplied, and checksums. gVCF
validation is optional when gVCF output is disabled.

## 17. FILTER Interpretation

Primary outputs retain all records. Non-PASS records do not make a technically
valid VCF invalid by themselves. Unknown or undeclared filters produce
configurable warnings or failures. PASS-only export is optional and secondary.

## 18. Technical QC Design

QC records counts by FILTER, SNV/indel/multiallelic counts, Ti/Tv where
meaningful, VAF/DP/AD/GQ distributions when present, contig counts, missing
fields, malformed records, runtime, output size, validation status, model type,
and caller version. It does not infer missing FORMAT values.

## 19. Status And Failure Design

DeepSomatic-specific failure categories cover config, model, metadata,
container/executable, command conflict, execution, timeout, output validation,
index validation, unknown filters, QC, PoN, interruption, cancellation, and
unknown failures while preserving raw diagnostics.

## 20. Rerun Design

Rerun manifests can select failed/blocked/caller-failed/validation-failed/QC
warning pairs by status, caller status, validation status, QC status, failure
category, analysis mode, pair IDs, and resource/model failures. They do not
submit jobs.

## 21. Provenance Design

Provenance records config/manifest/pair signatures, input/index/reference/model
signatures, requested/detected DeepSomatic versions, container/executable
identity, structured and sanitized commands, regions, PoN signature, Slurm IDs
where present, runtime, exit code, output checksums, validation/QC results,
package version, schema versions, prior attempt, and supersession.

## 22. 3,000-Pair Planning Strategy

The 3,000-pair test uses synthetic metadata and mock paths only. It validates
deterministic order, stable array mapping, model selection, command planning,
container bind planning, status generation, rerun selection, and reporting
without creating thousands of command files.

## 23. Testing Strategy

Unit tests cover config/model compatibility, command construction, wrappers,
preflight, VCF/gVCF validation, QC, attempts/resume/force, Slurm arrays, and
rerun selection. Mocked integration tests use fake runners and tiny generated
VCFs. Standard tests do not run real DeepSomatic, Docker, Apptainer, Slurm, or
network downloads.

## 24. Files To Create

- `variant_analysis_harness/somatic/deepsomatic/`
- DeepSomatic schemas/config examples/docs
- DeepSomatic unit, integration, and scale tests
- DeepSomatic verification artifacts

## 25. Files To Modify

- `variant_analysis_harness/cli.py`
- `variant_analysis_harness/__init__.py`
- `pyproject.toml`
- somatic configuration/schema/docs
- README, testing, troubleshooting, review manifest

## 26. Backward-Compatibility Risks

The new DeepSomatic configuration must remain optional and disabled by default.
Existing germline, cohort, joint, and Phase 2D somatic preflight commands must
continue to pass unchanged.

## 27. Explicit Severus Deferral

Severus and all somatic SV/CNV functionality remain deferred. Phase 2E is
strictly DeepSomatic PacBio HiFi SNV/indel integration.

## 28. Acceptance-Criteria Mapping

Phase 2E is complete when prior tests pass, DeepSomatic configuration and
model/version/metadata validation exist, safe command construction and execution
wrappers exist, local and Slurm planning exist, attempts/resume/force are
modeled, VCF/gVCF validation and technical QC exist, rerun/report/provenance
artifacts are generated, a 3,000-pair DeepSomatic planning test passes, mocked
integration tests pass, and scans confirm no Severus, CNV, clinical, network,
institutional, unsafe shell, or real-container behavior in standard tests.
