# Integrated Somatic Overview

Phase 2G adds a research-use, report-only layer above DeepSomatic somatic
SNV/indel attempts and Severus somatic SV attempts. It preserves each caller's
native outputs, status, QC, provenance, and failure state, then creates derived
pair-level and project-level summaries.

The layer does not execute callers, introduce new variant callers, infer CNV,
annotate variants, classify pathogenicity, infer treatment relevance, or claim
clinical readiness.
