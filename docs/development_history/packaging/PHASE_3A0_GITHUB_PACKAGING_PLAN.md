# Phase 3A.0 GitHub Public Repository Packaging Plan

## 1. Current Repository State

The Phase 2G repository is functionally validated and contains source code,
schemas, configs, examples, tests, contract fixtures, documentation, historical
phase plans, defect reports, and many root-level verification artifacts. The
root is not yet suitable for quick public review because implementation files,
release evidence, and development history are mixed together.

## 2. Public-Release Goals

Prepare a clean public alpha package named `pacbio-variant-analysis-harness` for
GitHub publication, technical review, job applications, recruiter review,
future tagging, and continued development. Preserve analytical behavior and
test coverage while improving readability, repository metadata, auditability,
and validation-boundary clarity.

## 3. Files To Preserve

Preserve production source code, schemas, configs, examples, tests, scripts,
official Severus contract fixtures, current CLI behavior, hermetic test
infrastructure, provenance logic, attempt/resume/force logic, scale tests,
failure-recovery behavior, and public-safe documentation/history.

## 4. Files To Relocate

Move phase plans to `docs/development_history/phase_plans/`, defect reports to
`docs/development_history/defect_reports/`, and historical runtime/test
artifacts to `docs/development_history/test_runtime_history/`. Keep only
current high-signal verification files in the root.

## 5. Files To Remove From The Public Package

Exclude previous ZIPs, caches, virtual environments, generated work/output
folders, real sequencing/reference/container files, binary caller assets,
personal files, private data, and unresolved legacy content. The existing
`legacy/` script contains institution-specific paths and deployment assumptions,
so public packaging will exclude that historical code and retain only a
placeholder `legacy/README.md`.

## 6. Root-Directory Simplification Plan

Keep root files limited to README, license/citation/community metadata,
release/roadmap files, package metadata, test/audit result summaries, and the
standard top-level directories: `.github/`, `configs/`, `contracts/`, `docs/`,
`examples/`, `schemas/`, `scripts/`, `tests/`, `variant_analysis_harness/`, and
`legacy/`.

## 7. README Redesign Plan

Rewrite README for recruiter-first and engineer-second review: immediate title,
description, static badges, research-use disclaimer, capabilities, validation
boundaries, architecture diagram, quick-start links, repository map, portfolio
highlights, roadmap, license, and citation.

## 8. Documentation Information Architecture

Create `docs/README.md` as an index with sections for getting started,
architecture, germline, somatic, operations, validation, portfolio, development
history, and reference. Add dedicated quick-start, architecture, repository map,
claims audit, validation matrix, portfolio overview, and sample report pages.

## 9. Phase-Plan Archival Strategy

Move all `PHASE_*.md` files into `docs/development_history/phase_plans/`,
including this Phase 3A.0 plan after it is created. Preserve chronological
context in `docs/development_history/README.md`.

## 10. Verification-Artifact Archival Strategy

Current release verification outputs remain in the root where requested.
Historical/baseline verification files move to
`docs/development_history/test_runtime_history/`.

## 11. GitHub Metadata Plan

Add issue templates, PR template, `.gitignore`, `.gitattributes`,
`.pre-commit-config.yaml`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
`SECURITY.md`, repository settings recommendations, and safe publishing
instructions. Review or add CI only if it is hermetic and does not run external
callers, containers, Slurm, or private-data workflows.

## 12. Release/Tag Recommendation

Keep package code version `0.2.7a1` and recommend public tag
`v0.2.7-alpha.1`. Do not claim a release has been created.

## 13. Licensing Review

If no license exists, add MIT License with copyright holder Tae Hyuk Kang and
year 2026. Third-party tools are external dependencies, not bundled code, and
will be documented in `THIRD_PARTY_NOTICES.md`.

## 14. Security/Privacy Scan

Scan for employer/institution names, private paths, usernames, emails, internal
hosts, credentials, tokens, patient/sample identifiers, private SOP references,
hidden files, ZIPs, binary data, large files, Git metadata, and unsafe legacy
content. Packaging fails on unresolved employer-IP or privacy concerns.

## 15. Claims Audit

Create `docs/validation/claims_audit.md`; classify public claims as directly
tested, mocked, synthetic-scale validated, structurally validated, planned,
not validated, or prohibited. Correct language around validation, production,
clinical readiness, deployment, biological accuracy, and 3,000 sample/pair
testing.

## 16. Validation-Boundary Audit

Ensure all public pages state research-use boundaries and distinguish software
validation, mocked execution, synthetic-scale planning, real-tool smoke testing,
real-data validation, biological benchmarking, and production validation.

## 17. Broken-Link Audit

Add a public audit script that checks Markdown relative links and required docs.
Generate `DOCUMENTATION_LINK_AUDIT.txt` and fail if broken links remain.

## 18. Packaging Acceptance Criteria

All prior tests pass; root is simplified; README is recruiter-first; architecture
diagram, quick start, docs index, repository map, portfolio pages, sample
reports, claims audit, validation matrix, third-party notices, public-release
audit, documentation-link audit, package audit, and publishing instructions
exist; versions and release tag recommendation are consistent; no private data,
unsafe legacy code, previous ZIPs, real sequencing data, reference genomes,
credentials, employer-owned code, or institution-specific deployment material is
included; final ZIP has one top-level `pacbio-variant-analysis-harness/` directory.
