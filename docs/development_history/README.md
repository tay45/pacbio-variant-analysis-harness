# Development History

Phase plans and selected verification artifacts are retained to show the
architectural path from a legacy interactive script to a public alpha
research-use harness.

## Milestones

| Phase | Version | Purpose | Key outcome |
| --- | --- | --- | --- |
| 2A | 0.2.0a1 | Germline modernization | Config-driven DeepVariant/pbsv harness. |
| 2B | 0.2.1a1 | Cohort scaling | Cohort manifests, Slurm arrays, reruns, reports. |
| 2C | 0.2.2a1 | Joint genotyping | GLnexus planning, sharding, compatibility checks. |
| 2C.1 | 0.2.3a1 | Test hardening | Hermetic pytest, exit verification, network isolation. |
| 2D | 0.2.4a1 | Somatic data model | Tumor-normal semantics and somatic preflight. |
| 2E | 0.2.5a1 | DeepSomatic | Somatic small-variant planning and validation. |
| 2F | 0.2.6a1 | Severus | Long-read somatic SV planning and validation. |
| 2F.1 | 0.2.6a2 | Contract correction | Official Severus 1.7 contract-fidelity patch. |
| 2G | 0.2.7a1 | Integrated reporting | Cross-caller somatic evidence/report layer. |
| 3A.0 | 0.2.7a1 | Public packaging | GitHub-ready repository hygiene and audits. |

The current release status is public alpha packaging for tag
`v0.2.7-alpha.1`.

The public repository identity was finalized as PacBio Variant Analysis Harness under Tay45/pacbio-variant-analysis-harness. Earlier proposed public names were superseded before publication.
