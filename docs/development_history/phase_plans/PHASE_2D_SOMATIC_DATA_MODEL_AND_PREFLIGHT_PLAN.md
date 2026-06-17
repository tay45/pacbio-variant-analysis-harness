# Phase 2D Somatic Data Model And Preflight Foundation Plan

## 1. Current Germline Architecture Summary

The repository currently provides a research-use, configuration-driven germline
PacBio HiFi harness with shared infrastructure for YAML/JSON schema validation,
manifest parsing, command construction, provenance, status records, reporting,
Slurm script planning, cohort orchestration, germline joint-genotyping planning,
and hermetic pytest execution. Phase 2C.1.1 additionally separates pytest unit
tests from standalone process-exit verification.

## 2. Germline And Somatic Semantic Separation

Somatic workflows will be implemented under a dedicated `somatic/` package and
dedicated CLI commands. Shared infrastructure may be reused, but germline sample
assumptions will not be reused where tumor, normal, specimen, subject, and pair
semantics differ scientifically.

## 3. Somatic Project Model

Add an optional `somatic` configuration block. Somatic remains disabled by
default. Supported Phase 2D modes are `tumor_normal` and `tumor_only`.
Tumor-only requires explicit permission and acknowledgment. Caller execution is
not represented as active work in this phase.

## 4. Tumor-Normal Pairing Model

Each active row represents a pair-level analysis unit with explicit `pair_id`,
`subject_id`, tumor specimen/sample/input fields, and normal specimen/sample/input
fields when mode is `tumor_normal`. Missing normal fields are valid only for
explicit tumor-only rows allowed by policy.

## 5. Tumor-Only Policy

Tumor-only mode is disabled by default. Missing normal data never silently falls
back to tumor-only. Tumor-only rows require `analysis_mode=tumor_only`,
project-level permission, and acknowledgment when configured.

## 6. Pair And Specimen Identity Strategy

Subject, pair, sample, specimen, library, read-group sample, VCF sample, and
BAM/CRAM SM names remain distinct. Strict identity validation compares expected
sample IDs to header sample names where supplied or probed. Explicit mapping is
modeled but does not infer identities silently.

## 7. Metadata Model

Coverage, purity, contamination, ploidy, sex, disease, site, batch, notes, source
method, source file, confidence, and timestamp are represented as metadata. Null
is preserved for missing values. No purity, contamination, sex, ploidy, or
coverage value is fabricated.

## 8. Input Compatibility Checks

Phase 2D supports aligned BAM and CRAM modeling. It checks path readability,
index presence, index freshness, tumor/normal path collision, input type, sort
order metadata, read groups, sample names, and format compatibility using
manifest/header fixtures and injectable abstractions in tests.

## 9. Reference Compatibility Checks

Tumor and normal reference IDs, signatures, contig names, contig order, contig
lengths, chr-prefix convention, and CRAM reference availability are validated.
Mismatches fail by default.

## 10. Coverage And Alignment Metadata

Supplied or mocked coverage/alignment metadata is validated for finite,
nonnegative numeric values and optional threshold policies. Coverage thresholds
are configurable and are not universal best-practice claims.

## 11. Contamination And Purity Metadata Policy

Purity and contamination values must be in `[0, 1]`; ploidy must be greater than
zero. Source metadata is recorded when supplied and may be required by strict
metadata policy. No estimation or inference is implemented.

## 12. Pair-Level Preflight Design

Each pair receives identity, reference, input, coverage, metadata, tumor-only,
and readiness status. Status values include PASS/WARN/FAIL/EXCLUDED for
validation domains and ready/warning/failed/excluded for pair readiness.

## 13. Cohort-Level Preflight Design

The somatic plan aggregates selected, excluded, failed, warning, tumor-normal,
and tumor-only pair counts; stable array indices; blocked pairs; warning pairs;
and readiness summaries. Disabled rows are preserved in resolved manifests.

## 14. Status And Provenance Model

Pair status records include project ID, attempt ID, pair ID, subject ID, tumor
sample ID, normal sample ID, mode, validation domains, readiness, failure
category, warning count, signatures, and timestamps. Provenance records config,
manifest, row hashes, input/index signatures, identity policy, normal reuse
policy, tumor-only acknowledgment, package version, and schema versions.

## 15. Failure Classification

Somatic-specific failure categories are added as constants and propagated through
validation results without overwriting original diagnostics. Uncertain errors are
left as `unknown`.

## 16. Slurm Planning Foundation

Phase 2D creates a stable `somatic_array_index.tsv` and resource/group
placeholders only. No caller command generation or Slurm submission is
implemented. Future SNV and SV stages are represented as deferred stages.

## 17. Reporting Design

Generate `reports/somatic_preflight_report.md` with project identifiers,
research-use disclaimer, pair counts, validation summaries, tumor-only
limitations, metadata status, future caller placeholders, output inventory,
operator actions, and explicit statements that no somatic variants were called
and technical readiness is not biological or clinical validity.

## 18. Synthetic Testing Strategy

Tests will use tiny synthetic TSV rows, mock paths, lightweight header metadata,
and no real BAM/CRAM parsing or external tools. A 3,000-pair scale test will
exercise deterministic ordering, validation, planning, status aggregation,
rerun-manifest generation, and reporting without creating thousands of alignment
files.

## 19. Files To Create

- `variant_analysis_harness/somatic/`
- `schemas/somatic_config.schema.json`
- `schemas/somatic_manifest.schema.json`
- `schemas/somatic_plan.schema.json`
- `configs/somatic_project.example.yaml`
- `examples/manifests/somatic_manifest.example.tsv`
- somatic documentation pages
- somatic unit and scale tests

## 20. Files To Modify

- `variant_analysis_harness/cli.py`
- `variant_analysis_harness/__init__.py`
- `pyproject.toml`
- `README.md`
- `docs/testing.md`
- `docs/troubleshooting.md`
- `schemas/run_config.schema.json`
- `REVIEW_MANIFEST.txt`

## 21. Backward-Compatibility Risks

The main risk is accidentally making the new `somatic` config block required for
existing germline configs. Schemas and config parsing will keep somatic optional
and disabled by default. Existing CLI commands must remain unchanged.

## 22. Deferred Caller Implementation

DeepSomatic, Mutect2, Strelka2, VarScan, Severus, Sniffles2, CNV callers,
annotation, benchmarking, population filtering, and clinical interpretation are
deferred. Phase 2D produces plans and readiness reports only.

## 23. Acceptance-Criteria Mapping

The implementation will provide schemas, manifest parsing, tumor-normal and
tumor-only policies, identity/reference/input/coverage/metadata preflight,
normal reuse policy, pair status, failure categories, rerun manifests, stable
array indices, reporting, 3,000-pair synthetic tests, hermetic verification
artifacts, and packaging. It will explicitly avoid caller execution, clinical
claims, network access, real tools, institutional paths, and fabricated metadata
defaults.
