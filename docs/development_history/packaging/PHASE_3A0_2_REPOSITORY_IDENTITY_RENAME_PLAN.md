# Phase 3A.0.2 Repository Identity Rename Plan

## 1. Current Obsolete Public Identity

The Phase 3A.0.1 public package uses a superseded repository slug, title, and
owner. The exact obsolete values are intentionally not repeated in this public
artifact; they are represented in the inventory as redacted old-identity
categories.

## 2. Intended Public Identity

The intended public repository is `Tay45/pacbio-variant-analysis-harness`.
The intended display title is `PacBio Variant Analysis Harness`, and the
intended repository URL is
`https://github.com/Tay45/pacbio-variant-analysis-harness`.

## 3. Files Containing The Obsolete Prefix

An inventory will be generated before replacements. Expected files include
README, citation metadata, GitHub settings, publishing instructions, release
notes, changelog, review manifests, public audit files, development-history
plans, tests, and packaging/audit expectations.

## 4. Directory Names Containing The Obsolete Prefix

The unpacked ZIP top-level directory uses the superseded slug. The final ZIP
must instead contain exactly one top-level directory named
`pacbio-variant-analysis-harness/`.

## 5. URLs Requiring Replacement

Replace active references to the obsolete repository URL and clone URL with:

- `https://github.com/Tay45/pacbio-variant-analysis-harness`
- `https://github.com/Tay45/pacbio-variant-analysis-harness.git`

## 6. Display Titles Requiring Replacement

Replace active display titles with `PacBio Variant Analysis Harness`. Preserve
the internal Python package/import identity `variant_analysis_harness`.

## 7. Tests Requiring Updated Expectations

Add identity consistency tests under
`tests/public_release/test_repository_identity.py`. Update public package audit
logic so README, citation, GitHub settings, publishing instructions, URL, owner,
slug, and obsolete identity checks expect the PacBio public identity.

## 8. Files That Must Not Be Renamed

Do not rename:

- `variant_analysis_harness/`
- imports using `variant_analysis_harness`
- `python -m variant_analysis_harness.cli`
- internal schemas, model names, provenance keys, or package paths that refer to
  the Python package rather than the public repository.

## 9. Versioning Policy

Keep analytical package version `0.2.7a1` and release tag recommendation
`v0.2.7-alpha.1`. Add public package revision `3A.0.2`; do not create a new
analytical release version.

## 10. Packaging Plan

Regenerate public audit artifacts and verification files after the rename. Build
`pacbio-variant-analysis-harness-v0.2.7-alpha.1-public-r2.zip` with exactly one
top-level directory named `pacbio-variant-analysis-harness/`.

## 11. Acceptance Criteria

The rename is complete only when active public files contain no obsolete public
identity references;
README title, citation, GitHub settings, publishing instructions, audits, and
tests use the new identity; internal Python package identity remains unchanged;
all prior and new tests pass; audits pass; no analytical behavior changes; and
no GitHub repository is created or pushed.
