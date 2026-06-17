# Somatic Failure Recovery

Somatic pair statuses include ready, warning, failed, blocked, excluded,
interrupted, cancelled, superseded, and unknown. Failure categories distinguish
manifest errors, identity collisions, missing inputs, stale indexes, reference
mismatches, coverage failures, invalid metadata, and tumor-only policy failures.

`somatic-rerun-manifest` selects failed or warning pairs deterministically by
status, category, subject, analysis mode, or explicit pair list. It never
submits jobs or runs callers.
