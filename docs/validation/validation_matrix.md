# Validation Matrix

| Capability | Implemented | Unit tested | Mocked integration tested | Synthetic scale tested | Real tool tested | Real data tested | Biologically benchmarked | Production validated | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepVariant | Yes | Yes | Yes | Yes | No | No | No | No | Germline SNV/indel orchestration. |
| pbsv | Yes | Yes | Yes | Yes | No | No | No | No | Germline SV orchestration. |
| GLnexus | Planning | Yes | Mocked/planning | Yes | No | No | No | No | Joint-genotyping planning. |
| DeepSomatic | Yes | Yes | Yes | Yes | No | No | No | No | Somatic SNV/indel module. |
| Severus | Yes | Yes | Yes | Yes | No | No | No | No | Contract-driven somatic SV module. |
| Tumor-normal preflight | Yes | Yes | Yes | Yes | No | No | No | No | Identity/reference/readiness checks. |
| VCF validation | Yes | Yes | Yes | No | No | No | No | No | Technical VCF integrity. |
| BND validation | Yes | Yes | Yes | No | No | No | No | No | Breakend mate consistency checks. |
| Cohort orchestration | Yes | Yes | Yes | Yes | No | No | No | No | Planning and status aggregation. |
| Slurm planning | Yes | Yes | Yes | Yes | No | No | No | No | Scripts generated, not submitted in tests. |
| Integrated somatic reporting | Yes | Yes | Yes | Yes | No | No | No | No | Derived evidence layer. |
| Failure recovery | Yes | Yes | Yes | Yes | No | No | No | No | Rerun manifests and recommendations. |
| Provenance | Yes | Yes | Yes | Yes | No | No | No | No | Structured records and output manifests. |
| 3,000-sample planning | Yes | Yes | Yes | Yes | No | No | No | No | Synthetic only. |
| 3,000-pair planning | Yes | Yes | Yes | Yes | No | No | No | No | Synthetic only. |


See the [validation evidence index](evidence/README.md) for current software and packaging verification artifacts.
