# Integrated Germline and Somatic Variant Analysis Harness - Alpha Release

Prepared for tagging as `v0.2.7-alpha.1`.

## Release Summary

This public alpha packages a research-use Python harness for PacBio HiFi germline and somatic variant-analysis orchestration. It emphasizes configuration, manifests, caller-contract validation, HPC planning, QC, provenance, failure isolation, and reports.

## Key Capabilities

- Germline DeepVariant SNV/indel and pbsv SV orchestration.
- GLnexus-oriented joint-genotyping planning.
- Somatic tumor-normal preflight and guarded tumor-only modeling.
- DeepSomatic small-variant planning and mocked integration.
- Severus long-read somatic SV planning against committed official contract fixtures.
- Integrated somatic reporting above DeepSomatic and Severus.
- Local and Slurm planning, cohort arrays, rerun manifests, and provenance.

## Test Count

The Phase 3A.0 package preserves the prior 221-test suite and adds public-packaging tests.

## Synthetic Scale Validation

Synthetic tests cover 3,000-sample germline/cohort planning and 3,000-pair somatic/integrated planning or reporting. These are software-scale tests, not real-data processing claims.

## Known Limitations

Real external-tool execution, real human datasets, biological benchmarking, production throughput validation, CNV, annotation, cloud execution, clinical interpretation, and institutional deployment remain future work or out of scope.

## Upgrade And Migration Notes

Public packaging relocates development history into `docs/development_history/` and excludes unsafe legacy institution-specific code from `legacy/`.

## Research-Use Disclaimer

This alpha release is for research-use software review only and is not clinically, diagnostically, or regulatorily validated.
