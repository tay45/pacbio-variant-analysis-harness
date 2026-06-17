# Phase 2B.1 Test Determinism, Runtime Optimization, and Verification Hardening Plan

## 1. Current Failing Or Unstable Test

The target unstable test is:

```text
tests/unit/test_cohort_storage_scratch.py::test_scratch_space_warning
```

The current assertion attempts to force a warning by requesting an extremely
large scratch size. This usually works, but it depends on host filesystem
capacity and therefore is not a deterministic unit test.

## 2. Root Cause Of Scratch-Space Instability

`validate_scratch_space()` calls `shutil.disk_usage()` on the real filesystem.
The test uses `required_gb=10**9` to make the result likely to be `WARN`.
That value is artificial and still depends on the execution environment,
filesystem virtualization, sparse filesystems, mounted storage, or CI runner
configuration.

The deterministic fix is to monkeypatch the `shutil.disk_usage` lookup used by
`variant_analysis_harness.cohort.scratch`, returning controlled total/used/free
values.

## 3. Current Full-Suite Duration

The most recent Phase 2B official artifact reported:

```text
89 passed in 78.50s
```

This patch will regenerate:

- `TEST_RESULTS_BEFORE.txt`
- `TEST_DURATION_REPORT_BEFORE.txt`

before code or test changes.

## 4. Current Slowest Tests

The most recent Phase 2B duration report showed these tests over 2 seconds:

- `tests/scale/test_3000_sample_planning.py::test_3000_sample_planning` - 14.68s
- `tests/unit/test_phase2a1_hardening.py::test_force_preserves_prior_attempt` - 11.94s
- `tests/integration/test_cli_mocked.py::test_resume_skips_successful_stage` - 11.46s
- `tests/integration/test_cli_mocked.py::test_mock_failure_blocks_downstream` - 10.72s
- `tests/unit/test_phase2a1_hardening.py::test_attempt_collision_rejected` - 9.83s
- `tests/integration/test_cli_mocked.py::test_combined_mock_run` - 9.58s

## 5. Likely Latency Sources

Likely avoidable costs:

- artificial `sleep` calls in test helpers or mocked tools,
- repeated end-to-end CLI invocations where a narrower mode would preserve the
  assertion,
- repeated execution of combined SNV+SV paths when one branch is sufficient for
  attempt/resume/collision behavior,
- repeated 3,000-sample per-sample file writes during planning status seeding,
- repeated JSON serialization in scale tests,
- unnecessary subprocess waits or large timeout defaults.

## 6. Planned Code Changes

Production code changes will be limited to legitimate efficiency or validation
improvements, if needed. Candidate changes:

- add explicit validation for negative scratch-space requirements,
- ensure scratch-space checks retain deterministic PASS/WARN behavior,
- optionally make cohort status seeding/serialization more efficient without
  changing status semantics.

No production analytical behavior will be changed.

## 7. Planned Test Changes

- Replace host-filesystem-dependent scratch warning test with monkeypatched
  deterministic disk-usage tests.
- Add scratch tests for:
  - sufficient free space,
  - insufficient free space,
  - nonexistent scratch path using parent path,
  - inaccessible path error handling,
  - zero required space,
  - invalid negative requirement,
  - deterministic rounding.
- Search for and remove unnecessary sleeps or reduce them to the smallest
  deterministic value.
- Prefer SNV-only or SV-only fixture runs for attempt/resume tests when combined
  analysis is not required for the behavior under test.
- Preserve subprocess/CLI coverage where process boundaries are the behavior.

## 8. Files To Modify

Expected files:

- `variant_analysis_harness/cohort/scratch.py`
- `tests/unit/test_cohort_storage_scratch.py`
- selected slow tests if latency can be reduced safely
- `README.md`
- `docs/testing.md`
- `docs/troubleshooting.md`
- `docs/scaling_to_3000_samples.md`
- `pyproject.toml`
- `variant_analysis_harness/__init__.py`
- `REVIEW_MANIFEST.txt`

## 9. Regression Risks

- Over-optimizing integration tests could reduce coverage of resume, force,
  collision, or mocked workflow behavior.
- Changing scratch validation could accidentally weaken production checks.
- Reducing timing delays could make race-condition tests flaky unless replaced
  with deterministic readiness signals.
- Scale-test optimization must still exercise 3,000 selected samples through
  production planning code.

## 10. Acceptance Criteria

- Official pytest before-state artifacts are captured before edits.
- Scratch tests no longer depend on real filesystem free space.
- Official pytest passes with zero failures and no accidental skips.
- The 3,000-sample test still uses 3,000 samples and remains offline.
- Full-suite runtime is materially improved, targeting under 60 seconds.
- Individual standard tests target under 10 seconds; any exception is documented
  with evidence.
- No artificial multi-second sleep remains unless explicitly justified.
- Phase 2A.1.2 and Phase 2B behavior remains covered and passing.
- Portability scan shows no new institutional, unsafe shell, network, or
  testing-fallback leakage.

## 11. No Analytical Functionality Added

This patch will not add somatic SNV/indel, DeepSomatic, somatic SV, Severus,
CNV, Illumina-specific workflows, Oxford Nanopore-specific workflows, germline
joint genotyping, cohort joint SV calling, cloud execution, institutional
deployment profiles, clinical functionality, or unrelated cohort features.
