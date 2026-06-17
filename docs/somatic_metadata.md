# Somatic Metadata

Phase 2D supports supplied metadata for coverage, purity, tumor contamination,
normal contamination, ploidy, sex, source method, source file, confidence, and
timestamp.

Purity and contamination must be between 0 and 1. Ploidy must be greater than
zero. Missing values remain null. The harness does not infer purity, estimate
contamination, infer sex, or assume diploidy.
