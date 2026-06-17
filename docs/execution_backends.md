# Execution Backends

Fully supported in Phase 2A.1:

- native local execution
- Apptainer/Singularity-compatible local execution
- full-sample Slurm script generation

Experimental or scaffold-only:

- Docker execution
- conda/micromamba execution
- GPU execution
- direct Slurm submission

Scientific modules produce argv lists. Backend modules wrap those lists for the
selected runtime.

Phase 2A.1.2 does not change analytical command semantics.
