# Somatic Reference Validation

Somatic preflight validates tumor and normal reference signatures, contig names,
contig order, contig lengths, chr-prefix convention, and CRAM reference
availability where represented.

Reference mismatch, contig-order mismatch, and contig-length mismatch fail by
default. Phase 2D uses supplied or mocked metadata in standard tests and does
not require external tools.
