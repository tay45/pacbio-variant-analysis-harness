# DeepSomatic Slurm

Slurm planning emits one array task per pair and a stable
`deepsomatic_array_index.tsv`. Submission is disabled by default. DeepSomatic
internal `num_shards` is distinct from Slurm pair-array tasks.
