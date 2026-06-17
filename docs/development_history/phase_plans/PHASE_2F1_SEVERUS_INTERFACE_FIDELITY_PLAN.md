# Phase 2F.1 Severus Interface Fidelity Plan

Research-use only. This corrective patch fixes Phase 2F Severus assumptions that were not faithful to the official Severus interface and native output contract.

## 1. Current Incorrect Phase 2F Assumptions

Phase 2F used invented or unverified flags: `--tumor-bam`, `--normal-bam`, `--reference`, `--tumor-sample`, `--normal-sample`, and lowercase `--pon`. It also assumed compressed native VCF names and graph/table names that are not emitted by the inspected official 1.7 source.

## 2. Official Command-Line Contract

Pinned contract: `KolmogorovLab/Severus` tag `1.7`, commit `3dc316d6a3c1711d51782b597699979e329df523`.

Verified parser flags include `--target-bam`, `--control-bam`, `--out-dir`, `-t`/`--threads`, `--phasing-vcf`, `--vntr-bed`, `--PON`, `--min-support`, `--vaf-thr`, `--TIN-ratio`, `--min-mapq`, `--min-sv-size`, `--use-supplementary-tag`, `--target-sample`, and `--control-sample`.

## 3. Official Supported Analysis Modes

The official parser requires one or more target BAMs and allows zero or more control BAMs, with code enforcing at most one unique control. Without a control and without PoN, output is `all_SVs`; with control or PoN, output includes `somatic_SVs`.

## 4. Official Version/Tag Selected

Primary support is pinned to Severus tag `1.7`, exact commit `3dc316d6a3c1711d51782b597699979e329df523`. No shared major/minor compatibility inference is used.

## 5. Future/Unknown-Version Policy

Unknown versions fail by default. Permissive mode may allow inventory-only review but must not generate executable commands.

## 6. Official Output Contract

Source-confirmed outputs include `all_SVs/severus_all.vcf`, `somatic_SVs/severus_somatic.vcf`, per-mode `breakpoint_clusters.tsv`, `breakpoint_clusters_list.tsv`, `plots/severus_<cluster>.html`, `severus.log`, `read_qual.txt`, optional `read_ids.csv`, optional `severus_LOH.bed`, and optional `severus_collaped_dup.bed`.

README-documented `breakpoint_double.csv` is recorded as documentation-only/uncertain for 1.7 because the inspected source files do not emit that filename.

## 7. Phasing And Haplotagging Requirements

Add explicit phasing configuration with modes `auto`, `phased`, and `unphased`. Validate phased VCF existence, index, nonzero size, sample identity, and reference metadata when supplied. HP-tag state must be accepted from metadata or probe results; it must not be fabricated.

## 8. Tumor-Only Policy Correction

Tumor-only target-only operation is supported by the official CLI. The harness will support it only when Phase 2D tumor-only policy and acknowledgment are enabled. Reports must warn that tumor-only calls lack matched-normal evidence and are not equivalent to matched tumor-normal classification.

## 9. Multiple-Target Policy

The compatibility registry records `--target-bam` as `nargs="+"`. Phase 2F.1 will represent multiple targets in command-building helpers and tests, while the production somatic manifest remains primarily pair-oriented.

## 10. PoN Policy

Use exact uppercase `--PON`. PoN is disabled by default, recommended or required by policy for tumor-only, validated for existence/nonzero size, and never downloaded or constructed.

## 11. VNTR BED Policy

Use exact `--vntr-bed`. Validate existence, nonzero size, BED-like structure, sorted order, and reference contig compatibility where metadata is available. No automatic download.

## 12. Compatibility Registry Redesign

Replace fabricated `1.0` registry with contract-backed `1.7`. Registry entries include exact flags, modes, multi-target behavior, supplementary-tag support, output names/patterns, and deprecated/unavailable flags.

## 13. Command-Builder Corrections

Emit official `severus --target-bam ... --control-bam ... --out-dir ... --threads N` style argv. Remove invented reference and sample-name flags from default pair commands. Preserve safe `list[str]` command construction and protected-flag rejection.

## 14. Output-Discovery Corrections

Discover source-confirmed native paths under `all_SVs/` and `somatic_SVs/`, HTML graphs under `plots/`, official cluster tables, logs, and unknown files. Do not require `graph.gfa`, `breakpoints.tsv`, or compressed invented VCF names.

## 15. Test-Contract Redesign

New contract tests read committed fixtures under `contracts/severus/1.7/`. Old tests that encoded invented flags are replaced with official-contract assertions.

## 16. Migration Impact

Phase 2F Severus command signatures are invalid. Add `severus_contract_version: 1` to plans/provenance and reject resume of old contract attempts unless revalidated.

## 17. Backward-Compatibility Impact

Non-Severus functionality remains unchanged. DeepSomatic, germline, cohort, GLnexus, and somatic preflight behavior are preserved.

## 18. Files To Modify

`variant_analysis_harness/somatic/severus/*`, `variant_analysis_harness/cli.py`, schemas, configs, docs, README, tests, and packaging artifacts.

## 19. Files To Add

`contracts/severus/1.7/*`, official-source documentation, defect report, contract tests, phasing tests, migration docs, and Phase 2F.1 verification artifacts.

## 20. Acceptance-Criteria Mapping

Acceptance criteria 1-4 are met by official-source docs and fixtures. Criteria 5-14 are met by command registry/builders/tests. Criteria 15-21 are met by tumor-only, multi-target, phasing, and supplementary-tag validation. Criteria 22-28 are met by output discovery/table/HTML validation. Criteria 29-31 are met by contract-version migration behavior. Criteria 32-41 are met by contract tests, full suite, network isolation, portability scan, and research-use documentation.

## Regression Test Mapping

| Old test | Old assumption | Official evidence | New test |
|---|---|---|---|
| `test_severus_commands` | `--tumor-bam`, `--normal-bam`, `--reference` | `main.py` parser uses `--target-bam`, `--control-bam`, no reference flag | `tests/contracts/test_severus_official_cli_contract.py` |
| `test_severus_output_discovery` | `severus_somatic.vcf.gz`, `graph.gfa` | `vcf_output.py` and `build_graph.py` emit `.vcf` and HTML plots | `tests/contracts/test_severus_official_output_contract.py` |
| tumor-only blocked test | official tumor-only unsupported | `main.py` allows omitted control | phasing/CLI contract tumor-only tests |
