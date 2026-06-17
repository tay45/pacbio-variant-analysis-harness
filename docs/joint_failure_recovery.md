# Joint Failure Recovery

Shard statuses are independent. `joint-rerun-manifest` selects failed, blocked,
warning, or explicit shards and writes deterministic TSV output plus a retry
recommendation report. Valid shards can be retained for later concat planning.

