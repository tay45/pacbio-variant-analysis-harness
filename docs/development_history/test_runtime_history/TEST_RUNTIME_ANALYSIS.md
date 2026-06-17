# Phase 2B.1 Test Runtime Analysis

## Summary

Before-state artifacts were captured before implementation/test edits:

- `TEST_RESULTS_BEFORE.txt`: 89 passed in 42.82s
- `TEST_DURATION_REPORT_BEFORE.txt`: 89 passed in 80.22s

After-state artifacts:

- `TEST_RESULTS.txt`: 94 passed in 51.41s
- `TEST_DURATION_REPORT.txt`: 94 passed in 50.77s
- `SCRATCH_TEST_RESULTS.txt`: 9 passed in 0.40s
- `SCALE_TEST_RESULTS.txt`: 3,000-sample planning runtime 9.295s

The quiet full suite remains under the 60s target while adding five deterministic
scratch tests. The duration-report run improved from 80.22s to 50.77s.

## Tests Over 2 Seconds Before

| Test | Before duration | Why slow | Intentional | Safe reduction |
|---|---:|---|---|---|
| `tests/scale/test_3000_sample_planning.py::test_3000_sample_planning` | 15.23s | 3,000-row manifest parsing/planning plus per-sample status serialization | Yes, scale coverage | Reduced status seeding overhead |
| `tests/integration/test_cli_mocked.py::test_resume_skips_successful_stage` | 11.53s | Full mocked workflow followed by resume | Yes, integration coverage | Tried SV-only path; retained as full workflow coverage |
| `tests/unit/test_phase2a1_hardening.py::test_force_preserves_prior_attempt` | 11.35s | Full mocked SNV run just to test `--force` attempt preservation | No | Replaced stage execution with deterministic stub after existing-attempt setup |
| `tests/unit/test_phase2a1_hardening.py::test_attempt_collision_rejected` | 10.10s | Full mocked SNV run used only to create an attempt directory | No | Replaced first run with dry-run attempt creation |
| `tests/integration/test_cli_mocked.py::test_mock_failure_blocks_downstream` | 10.03s | Full mocked workflow through failing DeepVariant stage | Yes | Retained; process boundary and failure propagation are the behavior |
| `tests/integration/test_cli_mocked.py::test_combined_mock_run` | 9.10s | Full mocked SNV+SV workflow | Yes | Retained; verifies both output branches |

## Tests Over 2 Seconds After

| Test | After duration | Optimization applied | Remaining justification |
|---|---:|---|---|
| `tests/integration/test_cli_mocked.py::test_mock_failure_blocks_downstream` | 11.10s | None; retained as mocked failure integration | Exercises actual CLI/stage failure path and downstream blocking |
| `tests/integration/test_cli_mocked.py::test_combined_mock_run` | 10.60s | None; retained as full mocked integration | Verifies both SNV and SV mocked outputs through the CLI |
| `tests/integration/test_cli_mocked.py::test_resume_skips_successful_stage` | 10.03s | Switched from SNV to SV-only, but runtime was similar | Preserves real resume behavior through the CLI |
| `tests/scale/test_3000_sample_planning.py::test_3000_sample_planning` | 9.74s | Planning-time pending status seeding writes compact current records instead of event+current pairs | Required 3,000-sample planning coverage; now under 10s call time |

## Scratch-Space Determinism

The prior scratch warning test requested `10**9` GB and depended on real host
free space. Phase 2B.1 now monkeypatches the `shutil.disk_usage` lookup used by
`variant_analysis_harness.cohort.scratch` and covers deterministic PASS, WARN,
missing-path parent fallback, inaccessible path FAIL, zero required space,
negative requirement rejection, and rounding behavior.

## Sleep And Timeout Review

No uncontrolled `sleep` or `time.sleep` calls remain in standard tests. Existing
production subprocess timeout constants remain bounded and are not test delays.
No package installation, environment creation, archive extraction, Slurm access,
network access, or real genomics tools are used by the standard suite.

## Optimization Notes

- `test_attempt_collision_rejected` now uses dry-run to create the first attempt
  directory and then verifies a real run rejects the collision.
- `test_force_preserves_prior_attempt` now stubs stage execution after creating
  a prior attempt, preserving force/supersession assertions without repeating a
  full mocked SNV workflow.
- Cohort pending-status seeding avoids writing immutable event records during
  planning-only initialization. Actual status updates still use the event-writing
  path.

## Remaining Slow-Test Justification

Three mocked integration tests remain around or slightly above 10 seconds on the
measured machine. They intentionally exercise real CLI orchestration and mocked
external process boundaries, so reducing them further would risk converting
integration coverage into unit coverage. They are documented here rather than
hidden or skipped.
