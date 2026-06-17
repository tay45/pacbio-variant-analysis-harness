# Installation

Use Python 3.10 or newer.

```bash
python -m pip install -e .
```

Standard tests do not require real sequencing tools, containers, network access,
or large data. Real analysis requires user-provided DeepVariant, pbsv, pbmm2,
and PacBio dataset tools or containers.

Normal installation should install declared dependencies:

- PyYAML for safe YAML parsing with duplicate-key rejection
- jsonschema for active JSON Schema validation

Production CLI commands fail fast if these dependencies are missing. A minimal
compatibility fallback exists only under `variant_analysis_harness/testing_only`
and is activated only by the local dependency-free test runner.
