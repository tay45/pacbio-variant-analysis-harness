# Phase 2F Severus Somatic SV Integration Plan

## 1. Current Phase 2E Architecture

The repository currently has germline single-sample execution, cohort planning,
germline joint-genotyping planning, somatic pair/preflight foundations, and an
optional DeepSomatic PacBio HiFi somatic SNV/indel layer. DeepSomatic is
implemented under `variant_analysis_harness/somatic/deepsomatic/` and remains
separate from Phase 2D pair validation.

## 2. Somatic SNV Versus Somatic SV Separation

Somatic SNV/indel and somatic structural-variant analyses remain independent
stages. DeepSomatic success is not required for Severus, and Severus success is
not required for DeepSomatic unless a future explicit workflow dependency is
configured.

## 3. Severus Integration Boundaries

Phase 2F adds optional, research-use Severus planning, command construction,
mocked execution, output discovery, SV VCF validation, BND validation, technical
QC, Slurm pair-array planning, rerun manifests, reporting, provenance-oriented
records, and synthetic scale tests. It does not add CNV, another somatic SV
caller, clinical interpretation, cloud execution, institutional deployment, or
biological accuracy claims.

## 4. Supported Severus Analysis Modes

Matched tumor-normal is the required active mode. Tumor-only remains disabled
unless a version capability policy explicitly supports it and project policy
authorizes it. Multi-sample execution remains inactive.

## 5. Version Compatibility Policy

A centralized compatibility module parses versions, records requested/detected
versions, handles mismatch/unknown policies, and defines release-family
capabilities, supported flags, expected outputs, and mode support. Unknown
versions fail under strict policy and may warn only under explicit permissive
policy.

## 6. Input Requirements

Severus planning reuses Phase 2D pair readiness and adds PacBio HiFi structural
variant checks for tumor/normal BAM or CRAM, indexes, coordinate sort metadata,
read groups, sample names, reference FASTA/FAI/dictionary metadata, contig
compatibility, auxiliary BED/PoN paths where configured, safe outputs, and
container/executable configuration.

## 7. Tumor-Normal Pairing Requirements

Tumor and normal roles are explicit and deterministic. A missing normal fails in
matched mode. Tumor/normal paths and biological identities are not swapped or
inferred.

## 8. Tumor-Only Support Policy

Tumor-only support is disabled by default. If the selected Severus version does
not explicitly support tumor-only behavior, tumor-only planning is rejected with
a clear diagnostic. Missing normal never silently triggers tumor-only.

## 9. Command-Construction Design

Commands are immutable `list[str]` argument lists. Protected flags cover tumor
input, normal input, reference, output directory, sample labels, threads, mode
flags, and version-sensitive output flags. Extra arguments cannot override
protected flags.

## 10. Container And Executable Strategy

Docker, Apptainer, Singularity-compatible, and direct executable modes are
represented without shell interpolation. Container image/tag are explicit,
digest is recorded when supplied, binds are deterministic, and standard tests do
not start containers.

## 11. Local Execution Design

The explicit run command may execute through a safe runner abstraction, while
planning and dry-run never execute Severus. Standard tests use mocked runners and
tiny output fixtures.

## 12. Slurm Pair-Array Design

The Slurm planner emits one pair per array task, stable deterministic indices,
configurable concurrency, task logs, and no submission unless `--submit` is
explicit. Blocked pairs are excluded.

## 13. Attempt/Resume/Force Model

Pair attempts are attempt-specific. Resume requires matching command/input/
reference/auxiliary/container/version signatures and prior validation success.
Force preserves prior attempts and records supersession. Partial output is never
reused as successful output.

## 14. Output Discovery Strategy

Version capabilities define required and optional native outputs. Discovery
identifies primary somatic SV VCF, optional background/germline outputs,
cluster/graph/breakpoint outputs, logs, unknown files, checksums, missing
required outputs, and empty outputs.

## 15. VCF Validation

The primary somatic SV VCF is validated for existence, index, header, contigs,
samples, sorting, coordinates, symbolic ALT/SVTYPE/END/SVLEN consistency,
FILTER declarations, FORMAT parseability, support-field parseability where
present, caller metadata, and checksums.

## 16. BND And Breakpoint Validation

BND validation checks breakend syntax, mate IDs, reciprocal mates, self-mates,
duplicate IDs, malformed brackets, invalid remote loci, EVENT linkage where
present, and configurable orphan policies.

## 17. Complex-Event Handling

Raw SVTYPE/ALT/EVENT/cluster information is preserved. Normalized categories are
secondary reporting metadata only, and unknown or complex labels are retained.

## 18. Clustered/Graph Output Handling

Auxiliary files are inventoried as native outputs, clusters, breakpoint tables,
graphs, plots, logs, or unknown files. Unknown native outputs are preserved and
listed.

## 19. Technical QC Design

QC reports total SV records, PASS/filtered counts, DEL/INS/DUP/INV/BND/TRA/
complex/unknown counts, orphan/inconsistent BND counts, per-contig counts,
inter/intrachromosomal counts, SVLEN distributions, support-field completeness,
normal support where available, validation status, output sizes, and exploratory
warnings without fabricating missing values.

## 20. Status And Failure Design

Severus-specific failure categories distinguish config, version, mode,
container/executable, preflight, command, execution, timeout, output discovery,
VCF/index/BND/QC, reference/PoN, interruption, cancellation, and unknown
failures while preserving raw diagnostics.

## 21. Rerun Design

Rerun manifests can select by pair status, caller status, output discovery, VCF
validation, BND validation, QC status, failure category, mode, explicit pair
IDs, version mismatch, or resource failure. They never submit jobs.

## 22. Provenance Design

Provenance records config/manifest/pair/input/index/reference/auxiliary/PoN
signatures, requested/detected Severus versions, compatibility policy,
container/executable identity, structured and sanitized command, regions,
threads, runtime, exit code, output inventory, validation, QC, package version,
schemas, prior attempt, and supersession without credentials.

## 23. Storage And Scratch Design

Estimates cover tumor/normal inputs, indexes, reference access, native output
directories, VCFs, standardized copies, logs, QC, reports, temporary data, peak
scratch, and copy-back volume. Estimates are labeled approximate and inputs are
never deleted.

## 24. 3,000-Pair Planning Strategy

The scale test uses mock paths and metadata only, validates deterministic order,
array mapping, command construction, container binds, resource grouping, status,
rerun selection, and reporting without real BAM/CRAM, Severus, containers,
Slurm, or network access.

## 25. Testing Strategy

Tests cover config, compatibility, commands, preflight, output discovery, VCF
validation, BND validation, QC, attempts, Slurm, mocked integration, scale, and
regression. Standard tests use synthetic and mocked fixtures only.

## 26. Files To Create

- `variant_analysis_harness/somatic/severus/`
- Severus schemas/config examples/docs
- Severus unit, integration, and scale tests
- Severus verification artifacts

## 27. Files To Modify

- `variant_analysis_harness/cli.py`
- `variant_analysis_harness/__init__.py`
- `pyproject.toml`
- somatic configuration/schema/docs
- README, testing, troubleshooting, review manifest

## 28. Backward-Compatibility Risks

The Severus configuration must remain optional and disabled by default. Existing
germline, cohort, joint, somatic preflight, and DeepSomatic behavior must remain
unchanged.

## 29. Explicit CNV And Clinical Deferral

CNV, copy-number segmentation, annotation, pathogenicity interpretation,
treatment recommendations, clinical reporting, cloud execution, and
institutional deployment remain deferred and out of scope.

## 30. Acceptance-Criteria Mapping

Phase 2F is complete when prior tests pass, Severus configuration and
version-capability validation exist, matched tumor-normal command construction
and wrappers exist, tumor-only is explicitly rejected unless supported, preflight
and Slurm arrays exist, attempts/resume/force are modeled, output discovery,
SV VCF validation, BND validation, QC, rerun, reporting, provenance, storage
estimation, mocked integration, and 3,000-pair scale tests pass, and scans
confirm no CNV, clinical, network, institutional, unsafe shell, real-container,
or real-Severus behavior in standard tests.
