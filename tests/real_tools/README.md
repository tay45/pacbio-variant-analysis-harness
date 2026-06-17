# Optional Real-Tool Smoke Test

These files are for an optional local smoke test. They are skipped by standard
CI and do not download data.

Prerequisites:

- a tiny valid reference FASTA, FAI, and sequence dictionary
- a tiny PacBio-compatible aligned BAM plus BAM index
- optional tandem-repeat BED matching the reference
- native `samtools`, `pbmm2`, `pbsv`, `bgzip`, and `tabix`
- a DeepVariant container or native executable configured by the user

The smoke test validates command execution, stage logging, provenance, output
integrity, and report generation. It does not validate biological accuracy.

Copy `smoke_config.example.yaml` and `smoke_manifest.example.tsv`, replace all
placeholder paths, then run:

```bash
bash tests/real_tools/run_smoke_test.sh /path/to/smoke_config.yaml /path/to/smoke_manifest.tsv SAMPLE_ID
```

Cleanup is manual: remove the configured output directory after review.
