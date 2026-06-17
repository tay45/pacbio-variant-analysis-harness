# Germline Workflow

DeepVariant is used for germline SNV/indel calling. pbsv is used for PacBio
germline structural-variant calling. These modules are separate and are not
exposed as somatic callers in Phase 2A.

Phase 2A.1 validates DeepVariant VCF/gVCF outputs and pbsv `.svsig.gz`/VCF
outputs before downstream QC.
