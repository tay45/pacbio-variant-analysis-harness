# Scaling To 3,000 Samples

Phase 2B includes a synthetic planning simulation for approximately 3,000
samples. It does not create real BAM files, execute external tools, access
Slurm, or access the network.

The scale test validates manifest parsing, deterministic array mapping, cohort
plan generation, status aggregation, incremental comparison, storage estimation,
QC aggregation, report generation, and artifact size.

The simulation demonstrates orchestration behavior only. It does not claim that
3,000 real biological samples have been processed or validated.

Phase 2B.1 keeps the sample count at 3,000 while reducing avoidable status
seeding overhead. Planning-time pending statuses are represented as compact
current status records; actual status event writes still use the normal event
record path. The official Phase 2B.1 scale artifact reported 3,000 tasks, one
array group, and a planning runtime under 10 seconds on the test machine.

Phase 2C adds a second synthetic 3,000-sample joint-planning test. It does not
create 3,000 real gVCFs; it uses deterministic synthetic metadata to validate
sample ordering, stable sample indexes, shard definitions, command input-list
strategy, joint plan generation, status aggregation, incremental comparison,
and reporting.
