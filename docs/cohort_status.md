# Cohort Status

Cohort status uses per-sample JSON records under sharded directories plus
aggregate TSV, JSON, and Markdown summaries.

Supported status values are `pending`, `submitted`, `queued`, `running`,
`success`, `warning`, `failed`, `blocked`, `skipped`, `excluded`, `interrupted`,
`cancelled`, and `unknown`.

Use:

```bash
python -m variant_analysis_harness.cli cohort-status --cohort-dir PATH
```

Outputs:

- `cohort_status.tsv`
- `cohort_status.json`
- `cohort_status.md`

