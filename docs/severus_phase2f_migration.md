# Severus Phase 2F To Phase 2F.1 Migration

Phase 2F generated Severus plans with unverified flags and invented native output names. Phase 2F.1 pins the official Severus 1.7 contract and records `severus_contract_version: 1`.

Old Phase 2F Severus command signatures are invalidated. Do not silently resume old Severus attempts under Phase 2F.1. Preserve old attempts for review, create a new attempt ID, and regenerate the plan so corrected `--target-bam`, `--control-bam`, `--out-dir`, phasing, VNTR, and uppercase `--PON` arguments are recorded.

Old native output inventories should be regenerated with the Phase 2F.1 output contract. The harness must not delete old native outputs automatically.
