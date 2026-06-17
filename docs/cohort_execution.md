# Cohort Execution

Phase 2B cohort commands are planning and orchestration commands. They do not
run analytical tools during validation or planning.

Implemented commands:

- `cohort-validate`
- `cohort-dry-run`
- `cohort-plan`
- `cohort-slurm`
- `cohort-status`
- `cohort-rerun-manifest`
- `cohort-report`

The chosen execution design is one full single-sample harness workflow per
selected Slurm array task. This keeps samples independently restartable and
prevents one failed sample from blocking unrelated samples.

Direct scheduler submission is disabled in Phase 2B. Generated scripts are
reviewable artifacts.

