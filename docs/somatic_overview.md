# Somatic Overview

Phase 2D adds a research-use somatic workflow foundation. It models
tumor-normal and tumor-only studies explicitly, validates biological pairing and
alignment compatibility, tracks purity, contamination, ploidy, and coverage
metadata without fabricating missing values, and produces deterministic
pair-level execution plans, status records, failure-recovery manifests, and
technical readiness reports.

Somatic caller execution is intentionally deferred to later phases so biological
assumptions and pairing safeguards are established before DeepSomatic and
long-read somatic SV integration.

Implemented: somatic data model, manifest parsing, tumor-normal pairing,
guarded tumor-only policy, identity/reference/coverage/metadata preflight,
status, rerun manifests, reports, and synthetic scale tests.

Not implemented: somatic SNV/indel calling, DeepSomatic, somatic SV calling,
Severus, Sniffles2, CNV, annotation, benchmarking, clinical interpretation, or
production tumor cohort processing.
