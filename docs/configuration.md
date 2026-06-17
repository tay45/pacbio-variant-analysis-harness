# Configuration

Run configuration is YAML and follows `schemas/run_config.schema.json`.
Run configuration must include `schema_version: phase2a1.v1`.

All paths are configurable. Relative paths resolve relative to the configuration
file. The original config is preserved in each attempt directory and the resolved
config is written as `config.resolved.yaml`.

Do not put shell command fragments in configuration. Use structured fields such
as `backend`, `executable`, `container`, `version`, and `extra_args`.

PyYAML safe loading is required for production CLI execution. Duplicate keys are
rejected. jsonschema is required for production JSON Schema validation during
validate, dry-run, run, resume, and Slurm script generation. Local schemas are
bundled and resolved locally; standard validation does not retrieve remote
schemas.

Allowed schema references are internal fragments such as `#/$defs/...` and
registered bundled local schema files. Remote references such as `http://`,
`https://`, `ftp://`, protocol-relative URLs, and unknown URI schemes are
rejected before any network lookup.
