# Somatic Preflight

Somatic preflight validates manifest rows, pair identity, tumor-only policy,
normal reuse, BAM/CRAM input modeling, indexes, reference compatibility,
alignment metadata, coverage thresholds, and biological metadata requirements.

Generated artifacts include `somatic_manifest.resolved.tsv`,
`somatic_manifest.validation.json`, `somatic_plan.json`,
`somatic_array_index.tsv`, pair statuses, provenance, and
`reports/somatic_preflight_report.md`.

No somatic variants are called in Phase 2D.
