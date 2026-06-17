# Phase 2C.1 Hermetic Pytest Environment Plan

## 1. Observed Issue

The repository test suite can pass and print a successful pytest summary while a
host-specific pytest plugin or shutdown hook may delay or prevent clean process
termination in some environments. This is an environment isolation problem, not
a variant-analysis feature problem.

## 2. Evidence That Tests Pass Before Process Hang

The Phase 2C verification artifact showed:

```text
105 passed in 52.61s
```

Before implementation changes, Phase 2C.1 will regenerate:

- `PYTEST_BASELINE_RESULT.txt`
- `PYTEST_PLUGIN_TRACE_BEFORE.txt`

to capture current pass count, summary behavior, process exit behavior, elapsed
time, and loaded plugins.

## 3. Likely External Pytest Plugin Interference

Potential sources include any globally installed pytest plugin, not only one
specific package. Examples include tracing, coverage, asyncio/anyio, xdist,
hypothesis, profiling, telemetry, IDE, and organization-local plugins. These
plugins may install background threads, shutdown hooks, event loops, or tracing
state unrelated to repository tests.

## 4. Why Repository Tests Must Not Depend On Arbitrary Global Plugins

Repository verification must be reproducible in local development, CI, Codex,
containers, and unknown user environments. Tests should depend on core pytest
only unless a plugin is explicitly declared and intentionally loaded.
Auto-loading arbitrary host plugins makes results environment-dependent.

## 5. Proposed Hermetic Test Strategy

Create `scripts/run_tests.py`, a repository-controlled launcher that sets
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` for the child pytest invocation, imports the
official installed pytest package, forwards arbitrary arguments, and returns
pytest's real exit code.

No root-level `pytest.py` shim will be created.

## 6. Local Developer Command

Authoritative command:

```bash
python scripts/run_tests.py -q
```

Equivalent direct environment command:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Plain `python -m pytest -q` is not forbidden, but it is not the authoritative
hermetic verification command because it may load unrelated host plugins.

## 7. CI Command

CI standard tests will set:

```yaml
PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"
```

and run:

```bash
python scripts/run_tests.py -q
```

## 8. Subprocess Termination Verification

Create `scripts/verify_pytest_exit.py`. It runs the hermetic launcher as a
subprocess with a bounded timeout, captures stdout/stderr, confirms the success
summary appears, confirms return code zero, and reports elapsed time. By default
it runs a representative subset; `--full` runs the full suite.

## 9. Files To Modify

- `scripts/run_tests.py`
- `scripts/verify_pytest_exit.py`
- `.github/workflows/ci.yml`
- `tests/unit/test_hermetic_pytest.py`
- `README.md`
- `docs/testing.md`
- `docs/troubleshooting.md`
- `pyproject.toml`
- `variant_analysis_harness/__init__.py`
- `REVIEW_MANIFEST.txt`

## 10. Tests To Add

Tests will verify that the launcher:

- sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` only for the child process,
- preserves unrelated environment variables,
- forwards pytest arguments and test paths,
- returns pytest's real exit code,
- handles invalid pytest arguments,
- resolves official pytest outside the repository,
- prevents loading a controlled fake external plugin,
- exits cleanly on a representative subset.

## 11. Regression Risks

- Accidentally relying on a plugin fixture would fail once autoload is disabled.
- Running a full suite inside a normal unit test would cause unacceptable test
  recursion and latency.
- Environment-variable handling must not mutate the parent process permanently.
- CI must not keep a plain pytest command as the authoritative path.

## 12. Acceptance Criteria

- Hermetic launcher exists and is documented.
- CI uses the launcher and disables plugin autoload.
- Official hermetic full suite passes with zero accidental skips.
- Exit verifier confirms clean termination for subset and full suite.
- Plugin trace after isolation shows external plugin autoload disabled.
- No process/thread leaks are found in repository tests.
- Runtime remains under 60 seconds where practical.
- Existing 105 tests and new hermetic tests pass.
- Network/tool isolation and portability scans remain clean.

## 13. No Analytical Functionality Added

This patch will not add somatic analysis, DeepSomatic, somatic SV, Severus, CNV,
germline cohort SV joint calling, phasing, pedigree-aware workflows, clinical
functionality, cloud execution, institutional deployment, or any unrelated
cohort/joint-genotyping feature.
