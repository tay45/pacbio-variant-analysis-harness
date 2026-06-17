# Phase 3A.1.1 CI Stabilization Report

Repository: `Tay45/pacbio-variant-analysis-harness`

Package version: `0.2.7a1`

Release tag preserved: `v0.2.7-alpha.1`

Scope: narrowly scoped GitHub Actions, packaging, public-audit, and generated-metadata stabilization. No analytical behavior was changed.

## CI Failure Timeline

The uploaded latest `main` branch already contained three manual CI fixes:

1. Setuptools package discovery was limited to `variant_analysis_harness*`.
2. GitHub Actions installed the editable package plus `pytest` with `python -m pip install -e . pytest`.
3. The public audit skipped paths containing `.git`.

Earlier failures were consistent with package-discovery, missing-test-dependency, and Git metadata issues. The latest reproducible failure after running tests was caused by generated workspace artifacts being treated as source-controlled root content or forbidden public-package content.

## Exact Failing Tests Before Final Fix

After an editable install and a full test run generated root-level scale summaries, rerunning focused public-release checks reproduced the two failures:

1. `tests/public_release/test_root_presentation.py::test_only_high_signal_files_remain_in_root`
   - Assertion: root files were not a subset of the approved high-signal file allow-list.
   - Extra root files: `SCALE_TEST_RESULTS.txt`, `JOINT_SCALE_TEST_RESULTS.txt`.

2. `tests/public_release/test_repository_identity.py::test_public_audit_checks_repository_identity`
   - Assertion: `audit.audit_package(ROOT) == []`.
   - Audit errors: `root-level evidence or phase artifact: SCALE_TEST_RESULTS.txt` and `root-level evidence or phase artifact: JOINT_SCALE_TEST_RESULTS.txt`.

The GitHub Actions public-audit step also failed after tests because it scanned expected generated metadata such as `.pytest_cache/` and `__pycache__/` as forbidden repository contents.

## Root Cause

The root cause was an audit/test disagreement about runtime-generated workspace state:

- Scale tests wrote current evidence to root-level files even though Phase 3A.1 moved canonical evidence under `docs/validation/evidence/scale_tests/`.
- The public audit intentionally rejected root-level phase and test evidence, so the scale outputs made a post-test workspace fail audit.
- The public audit skipped `.git`, but not other standard generated metadata created during CI, such as `.pytest_cache/`, `__pycache__/`, and editable-install `variant_analysis_harness.egg-info/`.

This was not a Python 3.12 compatibility issue and not an analytical-code issue.

## Manual Fixes Reviewed

Retained:

- `[tool.setuptools.packages.find] include = ["variant_analysis_harness*"]`, because editable install and wheel build both discover only the intended Python package tree.
- Explicit `.git` exclusion, but folded into a clearer generated-metadata policy.

Modified:

- The CI install command now uses declared test extras: `python -m pip install -e ".[test]"`.
- The public audit now distinguishes ignored generated metadata from genuinely forbidden public content.

Replaced:

- Ad hoc CI pytest installation was replaced by `[project.optional-dependencies] test = ["pytest>=7"]`.
- Root-level scale evidence generation was replaced with writes to `docs/validation/evidence/scale_tests/`.

## Final Package-Discovery Policy

Setuptools keeps package discovery constrained to:

```toml
[tool.setuptools.packages.find]
include = ["variant_analysis_harness*"]
```

Verification showed editable install and wheel build succeed. Installed distribution content is limited to the intended `variant_analysis_harness` package tree plus standard package metadata; `configs`, `contracts`, `schemas`, `legacy`, and `tests` are not installed as Python packages.

## Final Test-Dependency Policy

Test dependencies are declared in package metadata:

```toml
[project.optional-dependencies]
test = [
  "pytest>=7",
]
```

GitHub Actions installs them with:

```bash
python -m pip install -e ".[test]"
```

## Final Audit Metadata Policy

The public audit ignores only narrowly defined generated metadata:

- `.git/`
- `.pytest_cache/`
- `__pycache__/`
- `.mypy_cache/`
- `.ruff_cache/`
- `*.egg-info/`

The audit still fails for genuinely forbidden or non-public workspace content, including `work/`, `outputs/`, virtual environments, archives, sequencing files, reference-scale files, and container images.

## Verification Results

Python 3.10 result:

- Environment: isolated virtual environment outside the repository.
- Commands: `python -m pip install --upgrade pip`, `python -m pip install -e ".[test]"`, `python scripts/run_tests.py -q`, `python scripts/verify_pytest_exit.py`, `python scripts/audit_public_repository.py`.
- Result: `255 passed in 31.23s`; exit verifier passed; public audit passed.

Python 3.12 result:

- Environment: isolated virtual environment outside the repository.
- Commands: `python -m pip install -e ".[test]"`, `python scripts/run_tests.py -q`, `python scripts/verify_pytest_exit.py`, `python scripts/audit_public_repository.py`.
- Result: `255 passed in 24.52s`; exit verifier passed; public audit passed.

Git-checkout result:

- A temporary clean Git repository was created with `git init`, `git add .`, and `git commit -m "temporary CI reproduction"`.
- Python 3.12 workflow-style commands passed with `.git/` present.
- Result: `255 passed in 25.06s`; exit verifier passed; public audit passed.

Exported-archive result:

- The uploaded GitHub source archive without `.git/` was used as the primary working tree.
- Python 3.12 and Python 3.10 workflow-style commands passed.

Editable-install result:

- Editable install passed with `python -m pip install -e ".[test]"`.

Wheel-build result:

- `python -m build` completed successfully and produced both sdist and wheel.
- Build emitted a setuptools deprecation warning for the TOML-table license format; this is not a CI failure and was not changed in this narrow stabilization pass.

Full test result:

- `python scripts/run_tests.py --durations=30`: `255 passed in 41.78s`.
- Slowest tests were scale and mocked integration tests; no unexpected hangs were observed.

Full exit-verifier result:

- `python scripts/verify_pytest_exit.py --full`: `clean_exit=True`, `255 passed in 73.15s`.

CLI smoke-test result:

- `python -m variant_analysis_harness.cli --help` completed successfully and displayed the research-use CLI help.

Focused public/metadata result:

- `python scripts/run_tests.py -q -k "public_release or repository_identity or root_presentation or package_audit or portability or network or documentation or editable or metadata"`: `38 passed, 217 deselected`.

Public repository audit result:

- `python scripts/audit_public_repository.py`: passed after test-generated metadata was present.
- The audit still failed, as intended, when `python -m build` left `dist/variant_analysis_harness-0.2.7a1.tar.gz` in the repository tree; build artifacts were cleaned before final source packaging.

## Confirmations

- Analytical behavior did not change.
- Package version remains `0.2.7a1`.
- Release tag remains `v0.2.7-alpha.1`.
- Existing release contents were not modified.
- No force-push, retagging, or release recreation was performed.
