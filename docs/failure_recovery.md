# Failure Recovery

Phase 2B records structured failure categories and can generate deterministic
rerun manifests from cohort status records.

Use:

```bash
python -m variant_analysis_harness.cli cohort-rerun-manifest \
  --cohort-dir PATH \
  --status failed \
  --output rerun_failed.tsv
```

Rerun manifests preserve original cohort manifest fields and append rerun
metadata. Successful samples are excluded unless explicitly selected with
`--allow-successful`.

No rerun command submits jobs automatically.

