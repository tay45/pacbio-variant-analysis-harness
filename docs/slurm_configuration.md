# Slurm Configuration

`configs/slurm_profile.example.yaml` is site-neutral. All partition, account,
QoS, constraint, GRES, and setup values are optional and user-supplied.

Phase 2A.1 generates a neutral batch script that invokes the complete selected
sample workflow through `python -m variant_analysis_harness.cli run`. It does
not implement cohort arrays, dependencies, or automatic submission.

Generated scripts include the research-use banner, explicit working directory,
stdout/stderr paths, selected config, manifest, sample, and analysis mode.
