# Somatic Identity Validation

Supported identity policies are `strict`, `warn`, and `explicit_mapping`.
Strict policy treats mismatched header SM values, missing SM values, ambiguous
sample identities, and tumor-normal sample collisions as failures.

Explicit mapping is modeled for future workflows and must be recorded in
provenance when used. Phase 2D does not infer identities from filenames or
replace missing values with fabricated defaults.
