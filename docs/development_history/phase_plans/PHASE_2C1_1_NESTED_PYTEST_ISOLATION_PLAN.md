# Phase 2C.1.1 Nested Pytest Isolation Patch Plan

## 1. Observed Full-Suite Hang

External review observed that the normal repository tests pass when the
hermetic launcher tests are excluded, the hermetic launcher tests pass when run
alone, and `scripts/verify_pytest_exit.py` passes when run directly. The full
suite can nevertheless hang when
`tests/unit/test_hermetic_pytest.py::test_exit_verifier_subset_exits_cleanly`
starts a verifier subprocess from inside an already-running pytest process.

## 2. Exact Nested Execution Chain

The unstable chain is:

1. Top-level `python scripts/run_tests.py -q`
2. Pytest executes `tests/unit/test_hermetic_pytest.py`
3. `test_exit_verifier_subset_exits_cleanly` runs
   `python scripts/verify_pytest_exit.py`
4. The verifier runs `python scripts/run_tests.py -q <representative tests>`
5. That child invocation starts another pytest process while the parent pytest
   suite is still active.

## 3. Why The Nested Structure Is Unstable

Nested pytest execution can interact poorly with plugin state, output capture,
temporary directories, inherited environment variables, process cleanup, and
test collection. Even when every child command has a timeout, the design makes a
normal unit test responsible for process-level verification. That is a CI and
release check, not a unit-test concern.

## 4. Unit Verification Versus Process-Level Verification

Unit tests should validate command construction, environment construction,
timeout handling, result classification, formatting, and recursion protection
without launching pytest recursively. Process-level verification should remain a
standalone top-level command that can be run by CI or by an operator.

## 5. Proposed Non-Recursive Design

The ordinary suite will unit-test verifier logic through dependency injection
and mocked runners. The standalone verifier will continue to launch pytest, but
its default target will be a dedicated, fast smoke file that never invokes the
launcher, verifier, real genomics tools, Slurm, or network access.

## 6. Changes To `scripts/run_tests.py`

Refactor the launcher into small functions so tests can verify environment
construction and pytest resolution without recursively launching a full suite.
The launcher will continue to disable third-party plugin autoload, remove
explicit `PYTEST_PLUGINS`, reject repository-local pytest resolution, forward
arguments unchanged, avoid shell execution, and return pytest's exit code.

## 7. Changes To `scripts/verify_pytest_exit.py`

Refactor the verifier into testable functions:

- build the default smoke-suite command
- build the full-suite command
- build a hermetic environment
- evaluate completed processes
- handle timeouts and runner exceptions
- format structured results
- expose a recursion guard using `VARIANT_HARNESS_EXIT_VERIFIER_ACTIVE`

`main()` will parse CLI arguments, reject nested verifier invocation, call the
testable functions, print the formatted result, and return a real nonzero exit
code on timeout, failed pytest, runner error, or recursive invocation.

## 8. Changes To `tests/unit/test_hermetic_pytest.py`

Remove any unit test that launches `scripts/verify_pytest_exit.py` or starts a
representative pytest suite from inside pytest. Preserve launcher coverage for
small one-file subprocesses where needed, and add injected-runner tests for the
verifier logic. Add coverage for command construction, hermetic environment,
default versus `--full` behavior, success, nonzero return, timeout, captured
stdout/stderr, parent environment preservation, no `shell=True`, and recursion
guard behavior.

## 9. CI Changes

CI will use distinct top-level commands. The chosen design is:

1. Run the authoritative normal suite with `python scripts/run_tests.py -q`.
2. Run the representative clean-exit verifier with
   `python scripts/verify_pytest_exit.py`.

The full clean-exit verifier remains available for release verification, but CI
does not duplicate full-suite execution in the default job.

## 10. Documentation Changes

Update the README and testing/troubleshooting docs to state that process-exit
verification is a standalone top-level command. The ordinary pytest suite tests
verifier logic through dependency injection and does not launch another pytest
suite recursively. Document the dedicated smoke subset, recursion guard,
timeouts, and CI boundary.

## 11. Regression Risks

- The verifier refactor could accidentally change exit-code behavior.
- The recursion guard could be applied too broadly and block ordinary tests.
- The default smoke subset could become too broad and reintroduce recursion.
- Documentation could imply that full-suite exit verification is part of the
  normal pytest suite.
- Marker registration changes could accidentally skip standard tests.

## 12. Acceptance Criteria

- The complete normal suite exits cleanly.
- No normal test launches another representative or full pytest suite.
- `scripts/verify_pytest_exit.py` passes as a standalone command.
- `scripts/verify_pytest_exit.py --full` remains available and passes as a
  standalone command.
- The default verifier targets only `tests/smoke/test_exit_smoke_subset.py`.
- Recursive verifier invocation fails immediately with a clear diagnostic.
- All subprocess calls are bounded, capture stdout/stderr, and avoid
  `shell=True`.
- Previous Phase 2A, 2B, 2B.1, 2C, and 2C.1 behavior remains covered.

## 13. Analytical Functionality

This patch will not add analytical functionality. It will not implement somatic
SNV/indel analysis, DeepSomatic, somatic SV, Severus, CNV, germline cohort SV
joint calling, phasing, pedigree-aware workflows, clinical functionality, cloud
execution, institutional deployment, additional GLnexus features, or unrelated
cohort features.
