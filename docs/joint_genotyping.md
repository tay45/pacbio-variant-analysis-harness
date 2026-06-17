# Joint Genotyping

Phase 2C implements an optional research-use germline SNV/indel joint-genotyping
planning layer on top of validated per-sample DeepVariant gVCF outputs.

Implemented:

- gVCF input manifest generation and validation
- sample identity checks
- reference/contig compatibility checks
- deterministic contig and interval-file sharding
- GLnexus command construction with input-list files
- generic Slurm shard array generation
- shard status aggregation
- failed-shard rerun manifests
- final VCF concatenation planning
- technical final VCF validation helpers
- cohort variant QC helpers
- incremental safeguards
- storage estimates
- Markdown reporting

Not implemented:

- biological accuracy benchmarking
- production-scale biological validation
- somatic calling
- cohort SV joint calling
- phasing or pedigree-aware refinement
- pathogenicity interpretation
- cloud execution
- clinical use

