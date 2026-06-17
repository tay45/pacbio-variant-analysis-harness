# Phase 2A.1.1 Corrective Plan

## Scope Guard

This patch corrects validation, format handling, attempt safety, Slurm script
verification, and test reliability in the existing Phase 2A.1 PacBio HiFi
germline SNV/SV harness. It does not add somatic, CNV, cohort, array, Illumina,
ONT, clinical, or diagnostic functionality.

## Issues, Current Behavior, and Fixes

| Issue | Current behavior | Proposed fix | Files |
|---|---|---|---|
| Required dependency fallback | Production code can fall back to partial YAML/schema implementations when PyYAML/jsonschema are missing. | Require PyYAML/jsonschema for production CLI; allow fallback only under an explicit test-only environment flag and module. | `common/yaml_io.py`, `common/schema_validation.py`, `testing_only/` |
| Schema `$ref` | Fallback validator does not resolve local `$ref` fully. | Use jsonschema with local registry when installed; test-only fallback handles only test schema subset. | `schema_validation.py`, tests |
| BAI/CSI | BAM validation prefers only `.bam.bai`/`.bai` style. | Deterministically detect `.bam.bai`, `.bai`, `.bam.csi`, `.csi`, report ambiguity/zero/stale/type. | `bam_validation.py` |
| BAM/reference lengths | Compatibility checks use mostly contig names. | Compare SN/LN from BAM header with FAI names/lengths; report exact/subset/mismatch details. | `bam_validation.py` |
| FAI/dictionary lengths | Dictionary validation compares names only. | Compare SN/LN names and lengths, duplicate dictionary contigs, missing/malformed LN fields. | `reference_validation.py` |
| BED sorting | BED sorting uses naive lexical ordering. | Validate against FAI reference order and coordinate order within contigs; add configurable policy. | `reference_validation.py`, config/docs |
| VCF/gVCF validation | Internal parser is treated as enough for many checks. | Add layered external validation hooks for bcftools/tabix when configured/available plus stricter Python checks. | `vcf_validation.py` |
| SV/BND validation | SV syntax support is minimal. | Validate SVTYPE, END/SVLEN consistency, symbolic alleles, BND bracket syntax, and missing fields. | `vcf_validation.py`, `sv_qc.py` |
| svsig gzip | Validates stream by reading but needs richer reporting. | Record decompression errors, uncompressed bytes, empty-payload WARN/FAIL policy, concatenated readable stream support. | `vcf_validation.py` |
| Force attempts | `--force` can rerun within same attempt. | Preserve prior attempt; create derived attempt ID and write supersession metadata. | `cli.py` |
| Attempt collision | Directory creation is not atomic enough. | Use exclusive directory creation for new run attempts. | `cli.py` |
| Test duration | Prior run appeared slow/hung externally. | Add duration report, per-test timing in local runner, shorter mocked timeouts, no real-tool guarantee tests. | `pytest.py`, tests |
| Slurm workflow | Full workflow script exists but needs stronger verification. | Keep full CLI run script, save metadata/profile, test content and nonzero propagation. | `execution/slurm.py`, `cli.py`, tests |
| Docs | Validation/tool requirements need precision. | Update docs for runtime dependencies, tool requirements, optional checks, indexes, and limitations. | `README.md`, `docs/` |

## Tests to Add

- Dependency enforcement and no production fallback.
- Local schema `$ref` and invalid nested schema fields.
- BAI/CSI candidates, zero/stale/ambiguous index, `.pbi` independent checks.
- BAM contig exact/subset/mismatch, duplicates, chr naming mismatch.
- FAI/dictionary exact/extra/missing/length/duplicate/malformed LN.
- BED reference-order sorting, wrong order, descending coordinates, malformed rows,
  unknown contigs, empty BED, overlap warning.
- VCF/gVCF malformed FORMAT/INFO, symbolic alleles, multi-allelics, gzip/index,
  missing gVCF blocks, malformed END, unexpected contig.
- SV/BND valid and malformed records.
- svsig valid/truncated/invalid/zero/empty/concatenated gzip.
- Attempt duplicate/resume/force/supersession/concurrent creation.
- Slurm full workflow and failing harness propagation.
- Test duration and no-real-tool/network guard.

## Backward-Compatibility Impact

Configs must include `schema_version: phase2a1.v1` and must pass stricter schema
and runtime validation. Production CLI now fails fast if PyYAML or jsonschema is
missing. Existing valid Phase 2A.1 configs continue to work after adding required
tool blocks where needed.

## Acceptance Criteria

All Phase 2A.1.1 requirements are met: production dependency enforcement,
BAI/CSI support, contig length validation, dictionary length validation,
reference-order BED sorting, layered VCF/gVCF validation, BND checks, full-stream
svsig validation, force preservation, deterministic fast tests, full-workflow
Slurm generation, no new somatic/cohort functionality, and clean portability
scan.

## Risks and Unresolved Decisions

- Full VCF compliance still depends on bcftools/tabix when enabled; Python checks
  are conservative but not a replacement for a standards-grade validator.
- BED overlap policy is WARN in this patch rather than FAIL.
- Production dependency enforcement requires users to install declared Python
  dependencies before running the CLI.
- Direct Slurm submission remains deferred.
