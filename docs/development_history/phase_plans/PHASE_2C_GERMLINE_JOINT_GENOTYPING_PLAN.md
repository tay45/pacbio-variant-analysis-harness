# Phase 2C Germline Cohort Joint Genotyping Plan

## 1. Current Phase 2B.1 Architecture

Phase 2B.1 provides a research-use PacBio HiFi germline SNV/SV harness with
single-sample DeepVariant/pbsv execution, cohort manifest validation, cohort
planning, Slurm array generation, status aggregation, rerun manifests,
incremental comparisons, storage estimates, QC aggregation, and deterministic
test/runtime hardening. Phase 2C must add an optional germline SNV/indel joint
genotyping layer on top of validated per-sample DeepVariant gVCFs without
changing per-sample behavior.

## 2. Per-Sample gVCF Assumptions

Joint genotyping consumes one validated DeepVariant gVCF per biological sample.
Each input gVCF is expected to be compressed, indexed, single-sample, reference
compatible, and linked to source sample/cohort provenance where available.
Missing provenance can warn or fail depending on validation context.

## 3. Joint-Genotyping Backend Decision

Phase 2C implements GLnexus only. The backend interface records executable,
container engine/image/digest, preset/config name, extra arguments, version
metadata where known, and command provenance. The code is backend-aware so a
future backend can be added without mixing scientific assumptions.

## 4. GLnexus Command Architecture

Each shard receives a deterministic input-list file and a safe argument-list
command. Commands never use shell interpolation, shell globbing, `shell=True`, or
`os.system`. Container wrapping is represented as an argv prefix when configured.
Shard outputs are planned as temporary paths followed by validation and atomic
publication.

## 5. Cohort Input Manifest Design

Generate `joint_genotyping_inputs.tsv/json/validation.md` with stable
`cohort_sample_index`, `sample_id`, gVCF/index paths, source cohort/sample
attempts, reference IDs/signatures, gVCF signatures, header sample names,
validation status, and enabled state. Ordering is deterministic by sample ID
unless a future explicit ordering file is added.

## 6. Sample Identity Validation

Policies:

- `strict`: manifest sample ID must match the VCF header sample name.
- `warn`: mismatches warn but remain visible.
- `explicit_mapping`: a one-to-one mapping file is required and recorded.

No biological sample names are silently rewritten.

## 7. Reference And Contig Compatibility Validation

All gVCFs must share reference ID/signature and compatible contig declarations.
Default policy fails on mixed reference signatures, contig length mismatches,
contig order mismatches, and chr-prefix mismatches. Extra/missing contigs are
reported and can be hardened in future policies.

## 8. Genome Sharding Strategy

Phase 2C implements deterministic contig and interval-file sharding. The default
is contig mode using reference order from FAI or gVCF contig headers. Target-base
sharding is documented as deferred unless later explicitly requested.

## 9. Slurm Array Design

Generate one shard per array task using stable `array_index.tsv` and
`#SBATCH --array=1-N%M`. Submission remains disabled by default. Final
concatenation is blocked until required shards validate successfully.

## 10. Per-Shard Validation

Shard outputs are technically validated for existence, nonzero size, VCF header,
expected samples, duplicate sample names, sorted records, expected region bounds,
index presence, and basic truncation/readability. This is technical validation,
not biological accuracy validation.

## 11. Final Concatenation Strategy

Use concatenation semantics for nonoverlapping shards, never `bcftools merge`.
Planned commands include `bcftools concat`, optional `bcftools norm/sort`, and
`tabix`/`bcftools index`. Outputs are staged through temporary paths and
published atomically after validation.

## 12. Normalization And Indexing Strategy

Normalization is optional and configurable. Indexing is explicit and recorded.
The final cohort VCF receives validation JSON, checksum where configured, and an
output manifest.

## 13. Incremental Cohort Strategy

Prior per-sample validated gVCFs remain reusable. Adding/removing/changing
samples invalidates prior joint-called shards by default because joint genotyping
depends on the cohort sample set. Reference/backend/preset/config changes also
invalidate joint shards.

## 14. Failed-Shard Recovery Strategy

Shard statuses are independent. `joint-rerun-manifest` selects failed, blocked,
warning, or explicit shards and writes deterministic rerun TSV plus
recommendations. No submission occurs automatically.

## 15. Cohort VCF QC Design

Generate technical SNV/indel QC including variant counts, SNV/indel split,
PASS/FILTER counts, Ti/Tv, missingness, call rate, singleton/doubleton counts,
allele-count/frequency summaries, per-contig counts, and per-sample genotype
counts where parseable. No pathogenicity interpretation is implemented.

## 16. Provenance Design

Record config/manifest/sample-list/shard checksums, gVCF signatures, reference
signature, backend/preset/container identity, per-shard command signatures,
Slurm script checksum, output checksums, package version, timestamps, and
hostname where appropriate. No credentials or private tokens are recorded.

## 17. Files To Create

- `variant_analysis_harness/joint/`
- joint modules for inputs, identity, reference compatibility, sharding,
  commands, Slurm, status, validation, concat, QC, rerun, incremental, storage,
  reporting, and provenance helpers.
- `schemas/joint_plan.schema.json`
- joint documentation files.
- joint unit and scale tests.

## 18. Files To Modify

- `variant_analysis_harness/cli.py`
- `variant_analysis_harness/common/config.py`
- `schemas/run_config.schema.json`
- `README.md`
- `pyproject.toml`
- `variant_analysis_harness/__init__.py`
- testing/troubleshooting/scaling docs.
- `REVIEW_MANIFEST.txt`

## 19. Backward-Compatibility Risks

Joint genotyping must remain optional. Existing single-sample and cohort
commands must retain their arguments and outputs. New config keys must be
optional. Joint command construction must not require GLnexus in standard tests.

## 20. Testing Strategy

Use official pytest with synthetic/mock gVCF metadata and tiny generated VCFs.
Tests cover manifest discovery, identity policy, reference compatibility,
sharding, GLnexus command argv/input-list strategy, Slurm arrays, shard/final
validation, concatenation planning, rerun manifests, incremental invalidation,
QC metrics, 3,000-sample joint planning, no network, no Slurm, no real tools,
and all prior tests.

## 21. Explicitly Deferred Functionality

Somatic calling, DeepSomatic, tumor-normal workflows, somatic SV, Severus, CNV,
germline cohort SV joint calling, pangenome graph calling, family phasing,
pedigree-aware refinement, pathogenicity interpretation, clinical use, cloud
execution, institutional deployment, Illumina-specific workflows, Oxford
Nanopore-specific workflows, and biological accuracy benchmarking are deferred.

## 22. Acceptance-Criteria Mapping

Phase 2C is complete when all prior tests pass, joint input manifests,
identity/reference checks, sharding, GLnexus command generation, input-list
strategy, Slurm shard arrays, shard status, failed-shard recovery, safe
concatenation planning, final VCF technical validation, cohort variant QC,
incremental safeguards, storage estimates, reports, provenance, and the
3,000-sample joint planning test are implemented with no new analytical,
somatic, CNV, clinical, institutional, network, Slurm, or real-tool dependency
in the standard test suite.
