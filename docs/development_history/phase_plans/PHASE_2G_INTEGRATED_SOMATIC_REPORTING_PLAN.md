# Phase 2G Integrated Somatic Reporting Plan

Research-use only. Phase 2G adds a derived evidence/reporting layer above existing DeepSomatic small-variant and Severus structural-variant modules. It does not add a caller, annotation, CNV, clinical interpretation, cloud deployment, or institutional behavior.

## 1. Current Somatic Architecture

The somatic package has Phase 2D manifest/preflight/project planning, Phase 2E DeepSomatic PacBio small-variant planning/validation/QC/reporting, and Phase 2F.1 Severus PacBio somatic SV planning/official-contract/output-validation/QC/reporting. Caller-specific modules own caller commands, native outputs, validation, QC, provenance, and failure state.

## 2. DeepSomatic Output/Status Model

DeepSomatic plans expose pair statuses, commands, VCF/gVCF output paths, validation status, QC artifacts, command signatures, and failure categories. Integration consumes references to validated outputs and summaries only.

## 3. Severus Output/Status Model

Severus plans expose pair statuses, official contract version, corrected target/control argv, native output inventories, SV VCF validation, BND validation, QC, command signatures, and failure categories. Integration consumes references to official-contract outputs and summaries only.

## 4. Integration Boundaries

SNV/indel and SV remain separate analytical result classes. Integration happens above caller modules and never mutates native outputs. Unvalidated caller outputs do not contribute to summaries. Technical relationships are context, not biological proof.

## 5. Unified Project Model

Create `variant_analysis_harness/somatic/integrated/model.py` with project-level and pair-level dictionaries/dataclasses containing project IDs, attempt IDs, config/manifest signatures, reference signatures, source attempt references, pair metadata, policy, timestamps, package version, and schema versions.

## 6. Unified Pair Status Model

Centralize deterministic status derivation in `status.py` with statuses: `pending`, `not_started`, `small_variants_only`, `structural_variants_only`, `complete`, `complete_with_warnings`, `partial_success`, `blocked`, `failed`, `excluded`, `inconsistent`, `superseded`, `unknown`.

## 7. Stage Dependency Policy

DeepSomatic and Severus are independently optional/required/disabled by integrated config. One caller may succeed while the other fails. Partial success is allowed only when policy says so.

## 8. Cross-Caller Evidence Policy

Integration reports source-specific evidence side by side and derives technical relationships between small variants and SV loci. It must not call relationships concordance, causality, clonality, pathogenicity, or treatment relevance.

## 9. Cross-Caller Genomic Relationship Policy

Use deterministic contig-aware interval and breakpoint logic: inside SV interval, near local breakpoint, near end breakpoint, near BND remote breakpoint, density by event/cluster. Filtered variants are excluded by default.

## 10. Reference And Sample-Identity Compatibility

Validate pair ID, subject ID, tumor sample, normal sample, analysis mode, reference ID/signature, contigs/order/lengths, row hash, and input signatures when present. Mismatch yields `inconsistent` by default.

## 11. Variant Representation Normalization Policy

Create minimal derived reporting rows. Do not rewrite VCFs. Preserve source file and source record key. Unknown fields stay in raw maps when practical.

## 12. SNV/Indel Summary Design

Per pair: total records, PASS, filtered, SNV, indel, multiallelic, filters, VAF/depth/genotype availability, calls near SV breakpoints, calls inside SV intervals, caller version/model, validation/QC status and warnings.

## 13. SV Summary Design

Per pair: total SV records, PASS, filtered, SVTYPE counts, BND/TRA-like/complex counts, cluster counts, orphan/mate warnings, SVs with nearby small variants, Severus contract version, validation/QC status and warnings.

## 14. Integrated Event-Context Design

Per SV event: raw type, normalized category, cluster ID, breakpoints, interval, small-variant counts inside/near, VAF summaries where available, support fields where present, source attempt IDs.

## 15. QC Aggregation Design

Create domain QC records for identity, reference, DeepSomatic execution/output/QC, Severus execution/native-output/VCF/BND/QC, compatibility, relationships, report completeness, and provenance. Each domain has status, severity, reason codes, source, artifact path, and timestamp.

## 16. Failure And Warning Aggregation

Preserve caller failures and add integrated categories such as source attempt missing/ambiguous, required stage missing, partial not allowed, identity/reference mismatch, unvalidated output, BND failure, relationship failure, report failure, provenance incomplete.

## 17. Rerun Recommendation Design

Generate deterministic recommendations: rerun DeepSomatic only, rerun Severus only, rerun preflight, correct identity/reference, regenerate indexes, review BND/phasing/tumor-only policy, regenerate integrated report only, or no rerun required.

## 18. Provenance Aggregation

Record integrated config checksum, manifest checksum, integrated attempt, source attempt IDs, command signatures, output checksums, caller versions, model/contract versions, reference signatures, policy, window sizes, warning/partial policies, package version, timestamps, and no secrets.

## 19. Storage And Output Inventory

Create derived inventories for native caller outputs, derived caller outputs, integrated TSV/JSON/report artifacts, validation/QC/provenance artifacts, sizes, checksums, required/optional state, and availability. Do not duplicate large outputs.

## 20. Portfolio Evidence Design

Add report text showing architecture, caller separation, official caller contracts, orchestration, failure isolation, validation, BND/complex handling, unified QC, relationships, rerun design, provenance, synthetic 3,000-pair planning, hermetic tests, portability, and boundaries.

## 21. Recruiter-Facing Summary Design

Generate accessible 500-900 word Markdown explaining the harness, germline/somatic distinction, tumor-normal pairing, separate callers, validation, failure isolation, HPC planning, reproducibility, synthetic testing, limitations, and senior engineering signal.

## 22. Machine-Readable Report Design

Write versioned JSON/TSV outputs for summary, pair status, relationships, QC, failure summary, rerun recommendations, output inventory, and provenance.

## 23. 3,000-Pair Integration Planning

Use synthetic summary objects only. Validate deterministic ordering, mixed complete/partial/failure/mismatch states, aggregation, rerun recommendations, reports, and no filesystem explosion under 20 seconds.

## 24. Test Strategy

Add unit tests for config, status, attempt selection, compatibility, relationships, QC, rerun, and reports; mocked integration fixtures for caller combinations; performance test for interval index; scale test for 3,000 pairs. Preserve all prior tests.

## 25. Files To Create

`variant_analysis_harness/somatic/integrated/` modules, integrated schemas, docs, tests, report artifacts, performance/scale tests, and Phase 2G verification artifacts.

## 26. Files To Modify

`variant_analysis_harness/cli.py`, `variant_analysis_harness/somatic/manifest.py`, README, docs, schemas, configs, packaging scripts, and review manifest generation.

## 27. Backward-Compatibility Risks

Existing caller modules must remain untouched except for config exposure and CLI integration. Integrated reports are derived attempts and must not alter DeepSomatic or Severus attempts.

## 28. Explicit Clinical/CNV/Annotation Deferral

No pathogenicity, driver status, gene annotation, treatment recommendation, CNV, purity, clonality, chromothripsis, kataegis, clinical readiness, or real production validation is implemented.

## 29. Acceptance-Criteria Mapping

Criteria 1-17 are met by preserving prior tests and adding integrated config/model/status/source selection/compatibility. Criteria 18-25 are met by normalization and relationship modules. Criteria 26-35 are met by QC/failure/rerun/report/provenance/inventory modules. Criteria 36-43 are met by scale/performance/full hermetic verification. Criteria 44-49 are met by deferral docs, disclaimers, and portability scan.
