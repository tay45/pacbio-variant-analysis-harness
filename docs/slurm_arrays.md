# Slurm Arrays

Phase 2B generates site-neutral Slurm array scripts using a stable
`array_index.tsv` mapping.

The generated script uses:

```text
#SBATCH --array=1-N%M
```

`N` is the selected sample count and `M` is the configured `--max-concurrent`
value. Unlimited concurrency is not the default.

Each array task resolves exactly one sample row and invokes the existing
single-sample CLI. Task stdout and stderr paths are sharded by Slurm job and
array task IDs.

Submission is not performed by default. `--submit` currently returns an error so
operators cannot accidentally submit jobs from a dry-run workflow.

