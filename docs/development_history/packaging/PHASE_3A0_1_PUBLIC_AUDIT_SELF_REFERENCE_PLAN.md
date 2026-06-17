# Phase 3A.0.1 Public Audit Self-Reference Plan

## 1. Exact Failing Test

The expected failure is `tests/unit/test_safety_slurm_portability.py::test_no_prohibited_terms_outside_legacy`.

## 2. Root Cause

The public audit implementation and generated audit artifacts store sensitive
institution/path scan values as contiguous text. The portability test scans
public files outside `legacy/`, so the audit layer detects its own pattern list
and report content.

## 3. Files Containing Prohibited Literals

Initial inspection and reproduction will determine the exact files. Expected
locations are the public audit script and public audit artifacts.

## 4. Why The Packaging Audit Detects Itself

The audit script needs runtime scan values, but storing those values directly in
source and report text makes the repository itself look contaminated. The same
issue can occur if audit output echoes matched values instead of redacted
categories.

## 5. Redaction Strategy

Public artifacts will report categories, counts, locations, actions, and
PASS/FAIL status without printing sensitive values verbatim. Matched terms will
be represented as redacted category labels.

## 6. Scan-Pattern Construction Strategy

The scanner will reconstruct intended terms at runtime using readable segmented
string construction. Source code, comments, docstrings, reports, and test names
must not store full sensitive literals contiguously.

## 7. Test Strategy

Add focused public-release tests that verify runtime reconstruction, no
contiguous leakage in public files, redacted artifacts, synthetic contamination
detection, clean temporary repository pass behavior, contaminated temporary
repository fail behavior, legacy-only handling, and non-echoing audit output.

## 8. Package-Regeneration Strategy

After patching, regenerate public audit artifacts, full test artifacts, review
manifest, and final ZIP. The final ZIP will be named
`pacbio-variant-analysis-harness-v0.2.7-alpha.1-public-r2.zip` and contain one
top-level `pacbio-variant-analysis-harness/` directory.

## 9. Files To Modify

- `scripts/audit_public_repository.py`
- `PUBLIC_RELEASE_AUDIT.txt`
- `PUBLIC_PACKAGE_AUDIT.txt`
- `PORTABILITY_SCAN.txt`
- `REVIEW_MANIFEST.txt`
- generated verification artifacts
- new `tests/public_release/test_public_audit_self_reference.py`
- optional packaging-revision note in public documentation if needed

## 10. Acceptance Criteria

The original failure is reproduced and documented; the scanner still detects all
intended categories; source and artifacts avoid contiguous sensitive literals;
public audit output is redacted; no broad audit-file allowlist is added; focused
regression tests pass; the portability test passes; the full suite passes;
network isolation, link audit, privacy audit, package audit, and exit verifiers
pass; analytical behavior remains unchanged; version remains `0.2.7a1`; release
tag recommendation remains `v0.2.7-alpha.1`; no repository is pushed.
