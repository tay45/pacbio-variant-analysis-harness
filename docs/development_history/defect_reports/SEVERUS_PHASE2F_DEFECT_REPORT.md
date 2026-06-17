# Severus Phase 2F Defect Report

Research-use only. This report records the incorrect Phase 2F assumptions found by external review and primary-source inspection.

## Official Source Baseline

Repository: `https://github.com/KolmogorovLab/Severus`

Pinned tag: `1.7`

Pinned commit: `3dc316d6a3c1711d51782b597699979e329df523`

Inspected source: `severus/main.py`, `severus/build_graph.py`, `severus/vcf_output.py`, official README.

## CLI Assumption Classification

| Phase 2F assumption | Official equivalent/status | Classification |
|---|---|---|
| `--tumor-bam` | Official parser uses `--target-bam` with one or multiple values | incorrect, must be removed |
| `--normal-bam` | Official parser uses optional `--control-bam`; at most one unique control | incorrect, must be removed |
| `--reference` | No inspected 1.7 parser flag; reference lengths are read from BAM headers | incorrect, must be removed |
| `--tumor-sample` | Official parser has optional `--target-sample`, but default harness pair command does not need invented tumor sample flag | incorrect as implemented |
| `--normal-sample` | Official parser has optional `--control-sample`, but default harness pair command does not need invented normal sample flag | incorrect as implemented |
| lowercase `--pon` | Official parser uses uppercase `--PON` | incorrect, must be removed |
| `--out-dir` | Official required output directory flag | verified correct |
| `--threads`/`-t` | Official parser supports both | verified correct |
| `--phasing-vcf` | Official parser supports this flag | verified correct and must be modeled |
| `--vntr-bed` | Official parser supports this flag | verified correct |
| `--use-supplementary-tag` | Official parser supports this flag | verified correct and policy-gated |

## Output Assumption Classification

| Phase 2F assumption | Official evidence/status | Classification |
|---|---|---|
| `severus_somatic.vcf.gz` | Source emits `somatic_SVs/severus_somatic.vcf` | incorrect |
| `severus_all.vcf.gz` | Source emits `all_SVs/severus_all.vcf` | incorrect |
| `breakpoints.tsv` | Not source-confirmed in inspected 1.7 files | undocumented/incorrect |
| `clusters.tsv` | Source emits `breakpoint_clusters.tsv` | incorrect |
| `graph.gfa` | Source emits `plots/severus_<n>.html` | incorrect |
| `breakpoint_clusters_list.tsv` | Source-confirmed | verified correct |
| `breakpoint_double.csv` | README-documented, not found in inspected output source | uncertain/version-specific |

## Scientific And Workflow Defects

Phase 2F incorrectly described tumor-only as categorically unsupported. Official Severus accepts target-only input, but the harness must still distinguish tumor-only detection from matched-normal somatic confidence and require explicit tumor-only policy acknowledgment.

Phase 2F conflated workflow reference validation with a nonexistent Severus `--reference` CLI argument. Reference compatibility remains important for BAMs, phased VCFs, VNTR BED, PoN, and output VCF validation, but no unverified reference flag may be emitted.

Phase 2F did not model phasing, phased VCFs, HP tags, supplementary-alignment HP tags, or the official `--use-supplementary-tag` option.

## Corrective Action

Phase 2F.1 replaces fabricated assumptions with a pinned offline contract fixture, corrects command construction and output discovery, adds phasing validation, supports explicit tumor-only planning, invalidates old Severus command signatures, and adds contract tests that reject obsolete flags.
