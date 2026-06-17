# DeepSomatic Configuration

DeepSomatic is configured under `somatic.small_variants` and is disabled by
default. The only supported backend in Phase 2E is `deepsomatic`.

Tumor-normal PacBio mode uses `PACBIO`. Explicit tumor-only mode uses
`PACBIO_TUMOR_ONLY`. Versions, containers, model metadata, extra arguments,
regions, PoN inputs, outputs, and resources are recorded explicitly. No model or
reference is downloaded automatically.
