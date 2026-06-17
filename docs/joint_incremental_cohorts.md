# Joint Incremental Cohorts

Per-sample validated gVCFs remain reusable when signatures are compatible.
Adding or removing samples invalidates prior joint-called shards by default
because joint genotyping depends on the cohort sample set.

Generated artifacts:

- `joint_incremental_comparison.tsv`
- `joint_incremental_comparison.json`
- `joint_incremental_comparison.md`

