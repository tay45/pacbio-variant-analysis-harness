# Integrated Status Model

Supported statuses include `not_started`, `complete`,
`complete_with_warnings`, `partial_success`, `small_variants_only`,
`structural_variants_only`, `blocked`, `failed`, `excluded`, `inconsistent`,
`superseded`, and `unknown`.

Status is derived from caller status, output validation, QC status, stage policy,
warning policy, partial-success policy, and compatibility checks. One caller can
succeed while the other fails.
