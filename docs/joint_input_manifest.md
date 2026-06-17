# Joint Input Manifest

The seed manifest is TSV and minimally requires `sample_id`, `gvcf_path`, and
`reference_id`. Phase 2C resolves this into `joint_genotyping_inputs.tsv` with
stable sample indexes, gVCF/index paths, source cohort/sample attempts,
reference signatures, gVCF signatures, VCF header sample names, validation
status, and enabled state.

Strict identity policy requires the manifest sample ID and VCF header sample
name to match. Explicit mapping is supported only when a one-to-one mapping file
is provided and recorded.

