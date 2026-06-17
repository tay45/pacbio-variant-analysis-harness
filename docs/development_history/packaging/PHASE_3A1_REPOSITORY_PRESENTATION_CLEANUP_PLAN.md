# Phase 3A.1 Repository Presentation Cleanup Plan

## 1. Current Root Inventory

The current `main` branch root contains the expected source repository files and directories, but it also contains packaging plans, public-release correction records, test logs, audit transcripts, identity scans, and scale-test summaries. These files are valuable evidence, but they make the root look like a build workspace rather than a polished public repository.

## 2. Root Files That Should Remain

The final root should keep only high-signal public files: `README.md`, `LICENSE`, `CITATION.cff`, `CHANGELOG.md`, `RELEASE_NOTES.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, `pyproject.toml`, `Makefile`, `.gitignore`, `.gitattributes`, and `.pre-commit-config.yaml`.

## 3. Root Files That Should Move

Move root-level `PHASE_*` artifacts, `TEST_*` logs, `PYTEST_*` logs, network/portability/audit transcripts, identity scan outputs, scale summaries, GitHub setup docs, and review manifests into organized documentation directories.

## 4. Destination Directory Design

Use `docs/validation/evidence/` for current and historical verification evidence, with subdirectories for `test_summaries/`, `scale_tests/`, `caller_contracts/`, `public_release/`, and `historical/`. Use `docs/development_history/packaging/` for packaging plans and correction records. Use `docs/operations/github/` for GitHub publishing and repository settings documentation.

## 5. Link-Repair Strategy

Update README, docs index, repository map, development-history index, validation matrix, claims audit, portfolio pages, and sample-report docs to point to the new evidence and operations locations. Run the documentation-link audit afterward.

## 6. Test-Path Impact

Public-release tests and audit logic currently expect some root artifacts. Update tests to verify the new canonical paths and to ensure no phase/test/audit artifacts remain in the root.

## 7. Audit-Path Impact

Update `scripts/audit_public_repository.py` so it rejects root-level phase/test/audit artifacts, verifies canonical evidence paths, verifies GitHub operation docs under `docs/operations/github/`, and preserves privacy, identity, link, and forbidden-file checks.

## 8. Release-Tag Preservation Policy

Do not change, recreate, retag, move, or overwrite `v0.2.7-alpha.1`. This cleanup is a normal post-release `main` branch presentation commit.

## 9. Version-Preservation Policy

Keep package version `0.2.7a1` and release-tag recommendation `v0.2.7-alpha.1`. Do not create a new software version.

## 10. Acceptance Criteria

Root clutter is removed; validation evidence and packaging history are preserved under `docs/`; GitHub operation docs move under `docs/operations/github/`; README and docs indexes link to moved material; root-presentation tests pass; public audit passes; full tests and exit verifiers pass; no analytical behavior changes; and the final ZIP contains one top-level `pacbio-variant-analysis-harness/` directory.
