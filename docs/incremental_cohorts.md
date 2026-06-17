# Incremental Cohorts

Incremental planning compares the current manifest and configuration with a
previous cohort plan using signatures.

Use:

```bash
python -m variant_analysis_harness.cli cohort-plan \
  --config run.yaml \
  --manifest expanded.tsv \
  --cohort-id COHORT_002 \
  --reuse-from previous_cohort_dir
```

Outputs:

- `incremental_comparison.tsv`
- `incremental_comparison.json`
- `incremental_comparison.md`

Reuse decisions are conservative. Outputs are not reused when required
signatures are missing or incompatible.

