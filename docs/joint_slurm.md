# Joint Slurm Arrays

Phase 2C generates reviewable shard-array scripts with:

```text
#SBATCH --array=1-N%M
```

`N` is the enabled shard count and `M` is the configured maximum concurrent
shards. No jobs are submitted by default.

