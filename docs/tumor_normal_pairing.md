# Tumor-Normal Pairing

Tumor sample, normal sample, specimen ID, subject ID, library ID, read-group SM,
and pair ID are separate concepts. Strict policy requires tumor and normal
sample IDs to differ, specimen IDs to differ, and expected sample IDs to match
supplied or probed header sample names.

Normal reuse is disabled by default and must be explicitly enabled with a
maximum reuse count. Reused normals are reported and require study-specific
review; the harness does not assume shared-normal designs are biologically
appropriate.
