# Cohort Manifest

Phase 2B supports a TSV cohort manifest for PacBio HiFi germline SNV/SV planning.
It is research-use only and does not activate somatic logic.

Required active columns:

`sample_id`, `platform`, `input_type`, `input_path`, `additional_inputs`,
`aligned`, `reference_id`, `read_group_sample`, `output_prefix`, `analysis`,
`enabled`, `cohort_group`, and `priority`.

Supported `analysis` values are `snv`, `sv`, and `combined`. Supported
`input_type` values are `aligned_bam`, `unaligned_bam`, `pacbio_dataset_xml`,
and `pacbio_dataset_xml_list`.

Validation checks safe identifiers, duplicate sample IDs, duplicate output
prefixes, supported platform/input combinations, reference consistency,
enabled/excluded rows, duplicate input/read-group warnings, deterministic
ordering, and stable array-index mapping.

Generated artifacts include `cohort_manifest.resolved.tsv`,
`cohort_manifest.validation.json`, and `cohort_manifest.validation.md`.

