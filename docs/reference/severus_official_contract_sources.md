# Severus Official Contract Sources

Inspection date: 2026-06-15

Repository URL: `https://github.com/KolmogorovLab/Severus`

Pinned tag: `1.7`

Pinned commit SHA: `3dc316d6a3c1711d51782b597699979e329df523`

Release inspected: official GitHub tag `1.7`.

## Source Files Used

| Purpose | Source path |
|---|---|
| CLI parser and mode behavior | `severus/main.py` |
| Output folder/table/HTML names | `severus/build_graph.py` |
| VCF filename construction and VCF formatting | `severus/vcf_output.py` |
| User-facing CLI/output documentation | `README.md` |

## CLI Help Snapshot

Normalized offline help is stored at `contracts/severus/1.7/cli_help.txt`.

Verified key flags:

- `--target-bam`
- `--control-bam`
- `--out-dir`
- `-t`, `--threads`
- `--phasing-vcf`
- `--vntr-bed`
- `--PON`
- `--min-support`
- `--vaf-thr`
- `--TIN-ratio`
- `--min-mapq`
- `--min-sv-size`
- `--use-supplementary-tag`
- `--target-sample`
- `--control-sample`

## Output Contract Snapshot

Normalized offline output contract is stored at `contracts/severus/1.7/output_contract.json`.

Source-confirmed native outputs include:

- `all_SVs/severus_all.vcf`
- `somatic_SVs/severus_somatic.vcf` when control or PoN is present
- `all_SVs/breakpoint_clusters.tsv`
- `all_SVs/breakpoint_clusters_list.tsv`
- `somatic_SVs/breakpoint_clusters.tsv`
- `somatic_SVs/breakpoint_clusters_list.tsv`
- `all_SVs/plots/severus_<cluster>.html`
- `somatic_SVs/plots/severus_<cluster>.html`
- `severus.log`
- `read_qual.txt`
- optional `read_ids.csv`
- optional `severus_LOH.bed`
- optional `severus_collaped_dup.bed`

## Offline Fixtures

The repository commits normalized contract fixtures only. It does not include Severus source code, binaries, containers, downloaded PoNs, downloaded VNTR resources, or private data.
