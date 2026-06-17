# Phase 2A Implementation Plan

## 1. Current Repository Inventory

The uploaded archive contains a historical README, one interactive Python script at
`script/variantDetect.py`, `.gitattributes`, and `.DS_Store`. The script prompts
users for PacBio dataset merging, pbmm2 alignment, DeepVariant germline
SNV/indel calling, pbsv germline structural-variant calling, and simple SVTYPE
counting.

## 2. Files to Preserve

- `script/variantDetect.py` will be copied byte-for-byte to
  `legacy/variantDetect.py`.
- `README.md` will be copied byte-for-byte to `legacy/README.legacy.md`.
- The active harness will not execute legacy files.

## 3. Legacy Checksum Procedure

1. Copy the original files from the uploaded archive extraction.
2. Compute SHA-256 checksums for the original and legacy copies.
3. Verify that each original checksum matches its legacy copy.
4. Record legacy checksums in `legacy/LEGACY_CHECKSUMS.sha256`.

## 4. Files to Create

- `variant_analysis_harness/` package with CLI, typed exceptions, models, common
  utilities, execution backends, germline modules, QC modules, and reports.
- `configs/`, `schemas/`, `examples/`, `docs/`, `tests/`, and `.github/`.
- Primary `README.md`, `.gitignore`, `pyproject.toml`, and `legacy/`.

## 5. Files to Modify

The workspace root will receive a new active harness. `.DS_Store` will not be
kept in the active tree and `.gitignore` will ignore it.

## 6. Site-Specific Assumptions to Remove

The active implementation will remove site-specific server names, internal
mounts, private user paths, module names, container locations, accounts,
partitions, queues, and manually loaded environment assumptions. Tool locations
will come from config, environment variables, or CLI overrides.

## 7. General Execution-Backend Design

Scientific modules construct safe argv lists. Execution modules wrap those argv
lists for native execution or Apptainer/Singularity-compatible containers.
Docker and Slurm scaffolds will exist as neutral extension points.

## 8. Generic Slurm-Profile Design

`configs/slurm_profile.example.yaml` and `execution/slurm.py` will support
optional partition/account/qos/constraint/gres fields, configurable stdout and
stderr, and no site defaults. Phase 2A generates scripts only.

## 9. Config and Manifest Design

Run configuration is YAML validated by strict code and documented with JSON
Schema. Sample manifests are TSV files with explicit platform and input type.
Relative paths resolve relative to the config or manifest file.

## 10. Command-Execution Safety Design

All external tools use `subprocess.run()` with argument lists. The harness does
not use `os.system()` or `shell=True` in active workflow code. Commands capture
stdout, stderr, exit code, timing, and provenance.

## 11. Stage-State and Resume Design

Each stage has status, command, provenance, outputs, stdout, and stderr files.
Resume skips only stages with successful status, existing declared outputs, and
matching input/config/reference/tool signatures.

## 12. Path and Cleanup Safety Design

Path handling uses `pathlib`. Cleanup is opt-in, limited to the declared attempt
temp directory, and protected against empty, root, home, or parent-directory
paths. Inputs and references are never deleted.

## 13. QC Design

Phase 2A includes basic alignment reuse/validation status, germline SNV/indel
VCF QC, and germline SV VCF QC. Metrics are classified as PASS, WARN, FAIL, or
NOT_EVALUATED and written as JSON, TSV, and Markdown.

## 14. Report Design

`reports/sample_report.md` summarizes project/sample/attempt identifiers, the
research-use disclaimer, inputs, reference, tools, execution backend, stage
statuses, QC, outputs, runtimes, limitations, and troubleshooting pointers.

## 15. Testing Plan

Tests will cover config validation, manifest validation, command construction,
execution with mocked tools, resume behavior, output validation, QC parsing,
cleanup path safety, Slurm script generation, and portability scans.

## 16. Portability Test Plan

An automated scan will fail if prohibited legacy site terms or original internal
mount paths appear outside `legacy/`, this implementation plan, and approved
tests that define the prohibited terms. Active configs and docs must use only
neutral placeholders.

## 17. Risk List

- Minimal YAML parsing intentionally supports a strict subset.
- Real bioinformatics tool behavior is represented by safe command construction
  and mocked tests in Phase 2A.
- Version-specific optional flags require confirmation for local deployments.
- VCF QC is intentionally lightweight and dependency-free.
- Slurm support generates scripts but does not yet submit arrays.

## 18. Acceptance-Criteria Mapping

- Legacy preservation: `legacy/` plus checksum file.
- Institution-agnostic active code: portability scan.
- Config/manifest CLI: `validate`, `dry-run`, `run`, `resume`, `report`.
- Safe execution: centralized command runner and argv-only command builders.
- Germline-only scope: separate DeepVariant and pbsv modules.
- Restart/resume: per-stage status and signatures.
- QC/reporting: SNV/SV QC files and sample Markdown report.
- Tests: unit, mocked integration, and portability tests.
