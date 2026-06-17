# DeepSomatic Containers

Phase 2E supports Docker, Apptainer, Singularity-compatible wrappers, and direct
executable mode. Commands are built as argument lists with deterministic bind
ordering and no shell interpolation. Standard tests do not start containers.
