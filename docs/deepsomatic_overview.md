# DeepSomatic Overview

Phase 2E adds an optional research-use DeepSomatic layer for PacBio HiFi
somatic SNV/indel analysis. It builds on Phase 2D tumor-normal pairing and
tumor-only safeguards before command construction or execution.

Implemented: PacBio model compatibility, command construction, Docker,
Apptainer/Singularity, direct executable wrappers, local execution hooks, Slurm
pair-array planning, attempts/resume/force helpers, VCF/gVCF validation,
technical QC, rerun manifests, reporting, and synthetic/mocked tests.

Not implemented: Severus, somatic SV, CNV, annotation, purity inference,
contamination estimation, PoN construction, automatic downloads, clinical
interpretation, cloud deployment, or institutional deployment.
