# Third-Party Notices

This repository references external tools but does not bundle their code, binaries, models, containers, or licenses. Users are responsible for installing, licensing, citing, and validating external dependencies.

| Tool | External dependency status |
| --- | --- |
| DeepVariant | Referenced for germline SNV/indel workflows; not bundled. |
| pbsv | Referenced for PacBio germline SV workflows; not bundled. |
| GLnexus | Referenced for joint-genotyping planning; not bundled. |
| DeepSomatic | Referenced for somatic small-variant workflows; not bundled. |
| Severus | Referenced for long-read somatic SV workflows; not bundled. |
| Docker | Optional execution backend concept; not bundled or required for tests. |
| Apptainer/Singularity | Optional execution backend concept; not bundled or required for tests. |
| Slurm | Planning target only in standard tests; not bundled. |
| samtools | Referenced for validation/QC; not bundled. |
| bcftools | Referenced in joint/VCF contexts where applicable; not bundled. |
