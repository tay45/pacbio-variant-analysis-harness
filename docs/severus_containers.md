# Severus Containers

Command construction supports direct executable mode and Docker, Apptainer, or Singularity wrappers. Commands are built as argument lists, not shell strings.

The harness does not pull images automatically. Operators must provide and verify container images outside standard tests.
