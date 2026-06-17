# Severus Tumor-Only Policy

Official Severus 1.7 supports target-only operation by omitting `--control-bam`. Phase 2F.1 enables this only when the Phase 2D tumor-only policy is explicitly enabled and the manifest row includes the required acknowledgment.

Tumor-only SV detection is not equivalent to matched tumor-normal somatic classification. Reports retain warnings about germline/background contamination and PoN limitations.
