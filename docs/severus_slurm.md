# Severus Slurm

`somatic-sv-slurm` writes a review-only Slurm pair-array script with configurable concurrency. Direct submission is disabled by default and no standard test requires Slurm.

Array indexes are stable and include pair ID, subject ID, tumor and normal sample IDs, attempt ID, manifest row hash, command signature, and resource class.
