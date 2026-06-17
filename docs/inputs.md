# Inputs

The manifest explicitly declares input type. Supported Phase 2A values are:

- `aligned_bam`
- `unaligned_bam`
- `pacbio_dataset_xml`
- `pacbio_dataset_xml_list`

Multiple dataset XML inputs are represented as comma-delimited paths in
`additional_inputs` or as a primary path plus additional paths. Raw
whitespace-separated shell fragments are not accepted.

Aligned BAM inputs are validated with `samtools` when available. The harness
checks quickcheck, BAI/CSI index presence, index size/staleness, header
readability, read groups, expected sample name, sort order, and reference contig
name/length compatibility. CSI may be necessary for large references or large
contigs where BAI is insufficient. PacBio `.pbi` validation is independent of
BAI/CSI validation.
