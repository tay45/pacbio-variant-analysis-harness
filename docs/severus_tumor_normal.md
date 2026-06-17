# Severus Tumor-Normal Policy

The default Severus matched mode emits official `--target-bam` and `--control-bam` arguments. It requires a tumor BAM/CRAM, matched normal BAM/CRAM, compatible sample identifiers, compatible reference metadata, coordinate sorting, and read-group/sample tags.

Normal background evidence is treated as a first-class safeguard. The harness does not silently switch to tumor-only analysis when a normal is missing.
