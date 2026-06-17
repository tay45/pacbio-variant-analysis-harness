# Portfolio Overview

This project demonstrates senior bioinformatics and research-computing
capability by turning an interactive long-read variant workflow into a
modular, testable, configuration-driven harness.

## Why It Matters

The hard parts of research-scale variant analysis are often orchestration
and trust boundaries: reference compatibility, manifests, sample identity,
caller-version drift, HPC planning, retry behavior, provenance, validation
artifacts, and honest reporting.

## Engineering Signals

- Platform-aware PacBio HiFi first design.
- Germline and somatic logic are scientifically separated.
- DeepVariant, pbsv, GLnexus, DeepSomatic, and Severus are caller-specific modules.
- Severus behavior is anchored to committed official-contract fixtures.
- Tumor-normal semantics and guarded tumor-only policy are explicit.
- Long-read phasing and BND validation are represented.
- Local and Slurm planning support cohort-scale operation.
- Synthetic 3,000-sample/pair tests exercise planning and reporting scale.
- Failure recovery isolates failed samples, pairs, shards, and callers.
- Provenance, output validation, and rerun recommendations are first-class outputs.
- Recruiter-facing reports summarize the architecture without overstating science.

## Validation Boundaries

Testing is synthetic and mocked unless otherwise stated. The repository
does not claim biological benchmarking, clinical readiness, diagnostic
use, treatment relevance, production deployment, CNV, or annotation.


See the [validation evidence index](../validation/evidence/README.md) for current software and packaging verification artifacts.
