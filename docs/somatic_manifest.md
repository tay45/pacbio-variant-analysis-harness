# Somatic Manifest

The somatic manifest is a tab-delimited file with one row per pair-level
analysis unit. Required fields include `pair_id`, `subject_id`,
tumor specimen/sample/input fields, normal specimen/sample/input fields,
`reference_id`, `analysis_mode`, and `enabled`.

Disabled rows are preserved in resolved manifests but excluded from active
plans. Active rows receive deterministic ordering and stable row hashes.

Tumor-only rows must use `analysis_mode=tumor_only` and pass project policy.
Missing normal fields in a `tumor_normal` row are validation failures, not an
implicit tumor-only fallback.
