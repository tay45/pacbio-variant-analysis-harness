# Phase 2A.1 Hardening Plan

## 1. Current Architecture Summary

The Phase 2A harness is a Python package named `variant_analysis_harness`.
It provides a non-interactive CLI, TSV manifests, YAML run configuration, safe
argv command construction, local execution, dry-run, resume checks, neutral
Slurm script generation, stage status/provenance/logs, dependency-light SNV/SV
VCF QC, and preserved legacy files.

## 2. Weaknesses in Phase 2A

- YAML parsing uses a custom subset parser.
- JSON Schema files exist but are not enforced through a schema-validation layer.
- Tool validation is mostly command construction rather than real preflight
  probing.
- BAM validation is shallow and does not use `samtools` when available.
- Reference validation checks existence but not full FAI/dictionary/BED
  compatibility.
- Alignment QC is mostly placeholder output.
- VCF and svsig validation are dependency-light and need stronger integrity
  checks.
- Slurm generation emits a single analytical command rather than a complete
  workflow driver script.
- Attempt collision and force semantics need stronger protection.
- Atomic output handling is not represented as a reusable primitive.

## 3. Files to Modify

- `pyproject.toml`
- `README.md`
- CLI and common modules under `variant_analysis_harness/`
- execution, germline, QC, and report modules
- schemas and example configs
- documentation under `docs/`
- tests under `tests/`

## 4. New Files to Add

- `variant_analysis_harness/common/yaml_io.py`
- `variant_analysis_harness/common/schema_validation.py`
- `variant_analysis_harness/common/tool_probe.py`
- `variant_analysis_harness/common/bam_validation.py`
- `variant_analysis_harness/common/reference_validation.py`
- `variant_analysis_harness/common/vcf_validation.py`
- `variant_analysis_harness/common/atomic.py`
- optional real-tool smoke-test files under `tests/real_tools/`
- new hardening tests

## 5. Schema-Validation Strategy

Use `jsonschema` when installed and declare it as a package dependency. Provide a
small compatibility validator for the no-network test sandbox. Validation will
run during `validate`, `dry-run`, `run`, and `resume`, reject unknown keys where
schemas require it, and report field paths and invalid values.

## 6. YAML-Parser Replacement Strategy

Use PyYAML `SafeLoader` with duplicate-key rejection as the primary parser and
declare PyYAML in packaging metadata. Retain the previous parser only as an
explicit compatibility fallback when PyYAML is unavailable.

## 7. BAM/Reference Validation Strategy

Implement `samtools`-backed BAM validation where available: quickcheck, index
presence/staleness, header parsing, read-group/sample validation, sort order, SQ
contigs, reference compatibility, and `.pbi` checks for PacBio downstream
requirements. Strengthen reference validation with FAI, dictionary, contig,
checksum metadata, and BED parsing.

## 8. Tool/Version Probing Strategy

Probe required tools before analytical stages. Native tools resolve through
`shutil.which()` or absolute paths and execute tool-specific version/help
commands. Container tools validate runtime, image path, readability, optional
checksum, and minimal execution. Record results as machine-readable JSON.

## 9. Output-Integrity Validation Strategy

Add explicit VCF/gVCF validation, gzip integrity validation for `.svsig.gz`,
index validation where configured, malformed record checks, sample checks, and
reference contig compatibility. Preserve raw caller outputs.

## 10. Slurm Workflow-Generation Strategy

Generate a full sample workflow driver script that invokes
`python -m variant_analysis_harness.cli run ...` for the selected sample and
analysis. Keep submission disabled by default. Store the script and metadata
inside the attempt directory.

## 11. Resume and Attempt-Protection Strategy

Fail a new `run` when the attempt directory exists unless `resume` or `--force`
is explicit. Preserve prior attempts. Expand signatures to include schema
version, package version, command argv, tool version/probe metadata, reference
metadata, and input signatures.

## 12. QC Expansion Plan

Alignment QC will consume `samtools flagstat`, `idxstats`, and `stats` output
where available. SNV/SV QC will evaluate configurable thresholds and report
observed values, threshold sources, and PASS/WARN/FAIL/NOT_EVALUATED decisions.

## 13. Real-Tool Smoke-Test Design

Add skipped-by-default scripts and example config/manifest under
`tests/real_tools/`. Users provide tiny real inputs, indexes, tools, and
containers. The smoke test validates execution and output integrity, not
biological accuracy.

## 14. Migration Risks

- PyYAML/jsonschema become declared dependencies for normal installation.
- Stricter validation may reject previously accepted loose configs.
- Real preflight may fail earlier when tools or indexes are missing.
- Slurm scripts change from first-command scripts to full workflow driver
  scripts.

## 15. Acceptance-Test Mapping

- YAML/schema: duplicate keys, invalid nested fields, unknown keys, unsafe tags.
- Tool/container probing: missing tools, version mismatch, runtime/image checks.
- BAM/reference: quickcheck, header, index, contig, BED/dictionary validation.
- VCF/SV: malformed files, wrong sample, missing fields, svsig gzip integrity.
- Attempts/resume: duplicate attempt, signature mismatch, force preservation.
- Slurm: full workflow driver, neutral options, safe quoting.
- Portability: prohibited-term scan outside legacy.
