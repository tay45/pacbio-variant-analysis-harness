# Scaling To 3,000 Somatic Pairs

Phase 2D includes a synthetic 3,000-pair planning test. It uses mock paths and
metadata only, validates deterministic ordering, produces a stable pair array
index, aggregates status, generates rerun manifests, and writes reports.

No real BAMs, CRAMs, callers, Slurm installation, network access, or reference
genomes are required for the standard scale test.

Phase 2F adds a synthetic 3,000-pair Severus planning test. It generates stable
pair-array indexes and version-aware commands without executing Severus,
containers, Slurm, or real sequencing data. One failed pair does not block plan
generation for other pairs.

Phase 2G adds a synthetic 3,000-pair integrated somatic reporting test. It
builds pair-level DeepSomatic and Severus source references, derives integrated
status, isolates failed SV attempts as partial-success rows, writes reports,
inventories derived outputs, and verifies actionable rerun recommendations
without running callers, containers, Slurm, network access, or real data.
