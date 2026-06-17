# Phase 2A.1.2 Test Infrastructure, Dependency Isolation, and Offline Schema Resolution Plan

## Scope

This corrective patch is limited to test infrastructure, dependency isolation, schema-reference handling, and the public exception contract for unsafe manifest identifiers.

No analytical workflow expansion is included. This patch does not add somatic, cohort, CNV, Illumina, Oxford Nanopore, clinical, diagnostic, or regulatory functionality.

## Objectives

1. Remove repository-level pytest shadowing so the standard `python -m pytest` workflow uses the official pytest package.
2. Require production dependencies explicitly instead of silently using test-only fallbacks.
3. Keep optional fallback parsers isolated to testing support and a deliberately named helper script.
4. Resolve bundled JSON Schema `$ref` values offline without network access.
5. Reject remote or unresolved schema references with actionable configuration errors.
6. Convert unsafe manifest sample/read-group/output-prefix names into the documented `ManifestError` contract.
7. Add tests proving dependency failures, schema behavior, network isolation, and pytest resolution.

## Planned Changes

- Delete the root-level `pytest.py` shim.
- Add `variant_analysis_harness/common/dependencies.py` for explicit dependency loading and actionable missing-package messages.
- Update YAML loading to require PyYAML in production.
- Update schema validation to require jsonschema in production and inline bundled local schema references.
- Reject remote schema references before validation.
- Remove production use of test-only fallback modules and fallback environment variables.
- Keep `scripts/run_tests_minimal.py` as an explicitly optional dependency-limited helper.
- Update `pyproject.toml` with official pytest configuration, test paths, marker defaults, and package version.
- Add or update tests covering:
  - official pytest is not resolved from the repository root,
  - fallback environment is unset by default,
  - missing PyYAML and jsonschema raise `ConfigError`,
  - bundled local schema references resolve offline,
  - remote and unresolved schema refs fail without socket/network access,
  - unsafe manifest identifiers raise `ManifestError`.
- Regenerate review artifacts:
  - `TEST_RESULTS.txt`,
  - `TEST_DURATION_REPORT.txt`,
  - `PYTEST_RESOLUTION_CHECK.txt`,
  - `NETWORK_ISOLATION_TEST.txt`,
  - `PORTABILITY_SCAN.txt`,
  - `REVIEW_MANIFEST.txt`.

## Acceptance Criteria

- `python -m pytest` runs through the official pytest package when dependencies are installed.
- No root-level `pytest.py` exists.
- Standard tests pass with official pytest.
- Production code does not import `variant_analysis_harness.testing_only`.
- Production code does not enable dependency fallbacks via environment variables.
- Bundled schema references resolve without network access.
- Remote schema references are rejected deterministically.
- Unsafe manifest identifiers raise `ManifestError`, not raw `ValueError`.
- Portability scan reports no active institution-specific paths outside legacy material.
- The final ZIP excludes virtual environments, caches, large data, container images, `.git/`, and generated run outputs.

## Deferred Items

- Real-tool smoke tests with actual pbmm2, DeepVariant, pbsv, samtools, and bcftools installations.
- Direct Slurm submission execution.
- Cohort/job-array orchestration.
- Somatic small-variant and SV modules.
- CNV modules.
- Additional sequencing-platform modules.
- Benchmark-data profiles and large-data CI.

## Risk Notes

- The production CLI now requires PyYAML and jsonschema; missing packages fail early by design.
- Test artifacts may contain local pytest runtime paths because pytest records its root directory in session output.
- JSON Schema metaschema declarations remain in schema files, but runtime validation is configured to avoid fetching remote schemas.
