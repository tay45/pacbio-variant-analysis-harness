# QC

QC results use:

- `PASS`
- `WARN`
- `FAIL`
- `NOT_EVALUATED`

Dependency-light VCF QC is included for small variants and structural variants.
Alignment metrics requiring external tools are reported as unavailable unless
provided by later extensions.

Phase 2A.1 uses `samtools flagstat`, `samtools idxstats`, and `samtools stats`
when available. Thresholds are configured under `qc.alignment`, `qc.snv`, and
`qc.sv`; `null` means not enforced. These thresholds are not universal and need
project-specific validation.

Phase 2A.1.1 adds stricter VCF/gVCF checks, SV/BND syntax checks, full-stream
gzip validation for `.svsig.gz`, FAI/dictionary length comparison, and
reference-order BED sort checks. bcftools/tabix can provide layered external VCF
validation when configured.
