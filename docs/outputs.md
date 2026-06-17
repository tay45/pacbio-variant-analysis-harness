# Outputs

Outputs are written under:

```text
results/PROJECT_ID/SAMPLE_ID/ATTEMPT_ID/
```

Previous attempts are preserved. The harness does not silently overwrite
validated outputs and does not delete user inputs or reference data.

Phase 2A.1 prevents a new `run` from reusing an existing attempt directory
unless `resume` or explicit `--force` is used. Validation and QC artifacts are
stored under `qc/`.

In Phase 2A.1.1, `--force` does not overwrite the existing attempt. It creates a
derived attempt ID and writes `supersession.json` linking the new attempt to the
preserved prior attempt.
