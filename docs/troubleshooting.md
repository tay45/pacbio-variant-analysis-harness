# Troubleshooting

Each failed stage writes `stage.status.json`, `stage.command.json`,
`stage.provenance.json`, `stdout.log`, and `stderr.log` under the attempt
directory.

| Problem | Likely cause | Recommended action |
|---|---|---|
| Tool not found | Native executable is absent from `PATH` | Update config or install the tool. |
| Container not found | Container path is wrong or unreadable | Correct the configured container path. |
| Container execution failure | Runtime, binds, or image problem | Inspect `stderr.log` and `stage.command.json`. |
| Reference/index mismatch | FASTA, index, or dictionary are incompatible | Rebuild or select a matching reference bundle. |
| BAM/reference contig mismatch | Aligned reads use a different reference | Use compatible BAM/reference inputs. |
| Missing BAM index | BAM index was not provided | Create the index explicitly before running or add a later indexing stage. |
| Missing PacBio `.pbi` | PacBio index is absent where required | Generate the index with a supported PacBio tool. |
| Malformed dataset XML | XML input is empty or not XML-like | Replace or regenerate the dataset XML. |
| Dataset merge failure | Invalid XML list or dataset tool failure | Inspect merge logs and source XML paths. |
| pbmm2 failure | Input/reference/tool/resource problem | Inspect alignment `stderr.log`. |
| DeepVariant failure | Model, reference, container, or resource problem | Inspect DeepVariant logs and model type. |
| DeepVariant model mismatch | Configured model does not match platform | Use `PACBIO` for PacBio HiFi germline examples. |
| Zero-byte VCF | Caller failed or output path collision | Inspect caller logs; rerun with a new attempt ID. |
| Malformed VCF | Truncated or non-VCF output | Treat as failed output and rerun after fixing upstream issue. |
| Missing gVCF | gVCF disabled or caller failed | Check `workflow.emit_gvcf` and logs. |
| pbsv discover failure | BAM/index/reference/tool issue | Inspect discover logs and BAM validity. |
| pbsv call failure | Invalid svsig or reference mismatch | Inspect call logs and upstream svsig output. |
| Missing tandem-repeat BED | Optional BED path absent | Provide a matching BED or leave it null. |
| Reference/BED contig mismatch | BED uses different contig names | Use a BED built for the configured reference. |
| Insufficient disk space | Outputs or temp files exceed storage | Change output/temp locations or free space. |
| Temporary storage exhaustion | Temp directory too small | Configure a larger `temp_root`. |
| Process interruption | Operator or scheduler stopped the process | Resume with the same attempt ID after inspection. |
| Resume signature mismatch | Inputs/config/reference/tool changed | Use a new attempt ID or explicit force after review. |
| Output already exists | Attempt would overwrite outputs | Use a new attempt ID or explicit force. |
| Permission failure | Output, input, or temp path permissions | Correct filesystem permissions. |
| Slurm script-generation errors | Invalid profile values | Validate and simplify the profile. |
| Tool probe failure | Required executable or container cannot be run | Review `qc/tool_probe.json` and fix the tool configuration. |
| BAM validation failure | quickcheck, index, header, sample, sort, or contig problem | Review `qc/bam_validation.json`; do not silently edit BAM metadata. |
| Reference validation failure | FASTA, FAI, dictionary, or BED problem | Review `qc/reference_validation.json` and `qc/reference_validation.md`. |
| Resume rejected | Stage signatures differ | Use a new attempt ID after reviewing the changed input, config, reference, or tool metadata. |
| Missing PyYAML/jsonschema | Runtime dependencies are not installed | Install declared package dependencies before production CLI use. |
| pytest resolves to repository file | A local file is shadowing the official package | Remove/rename the local file and verify with `python -c "import pytest; print(pytest.__file__)"`. |
| Plain pytest hangs after summary | Host environment plugin or shutdown hook may be interfering | Run `python scripts/run_tests.py -q`; inspect `PYTEST_PLUGIN_TRACE_BEFORE.txt` and use `python scripts/verify_pytest_exit.py`. |
| Full suite hangs inside hermetic verifier test | Pytest was launched recursively from inside pytest | Use Phase 2C.1.1 or later; verifier logic is unit-tested with injection and process-exit verification runs only as a top-level command. |
| Recursive verifier invocation rejected | `VARIANT_HARNESS_EXIT_VERIFIER_ACTIVE` is already set | Run `python scripts/verify_pytest_exit.py` from a top-level shell or CI step, not from inside another verifier. |
| Exit verifier timeout | The child pytest process did not terminate before the bounded timeout | Review `PYTEST_EXIT_VERIFICATION.txt` or `PYTEST_FULL_EXIT_VERIFICATION.txt` for captured stdout, stderr, timeout, and clean-exit fields. |
| Hermetic launcher cannot find pytest | Test dependency is missing from the active Python environment | Install project/test dependencies and rerun `python scripts/run_tests.py -q`. |
| Intentional local plugin experiment does not load | The hermetic launcher disables plugin autoload | Use plain pytest in a disposable environment for experiments; do not rely on global plugins for standard verification. |
| Remote schema reference rejected | Config/schema contains a non-bundled `$ref` | Use bundled local schemas or internal fragment references only. |
| BAI/CSI ambiguity | Both BAI and CSI indexes are present | Remove the unintended index or choose a clean input directory before rerun. |
| Dictionary length mismatch | FAI and sequence dictionary disagree | Rebuild or select a matching reference dictionary. |
| BED unsorted | BED order differs from FASTA index order | Provide a reference-order sorted BED; the harness does not rewrite it. |
| Malformed BND | Breakend ALT syntax is invalid | Inspect the raw SV VCF and caller logs. |
| Cohort validation FAIL | Duplicate IDs, invalid rows, unsupported combinations, or reference mismatch | Review `cohort_manifest.validation.md` and line-numbered errors. |
| Somatic validation FAIL | Pairing, identity, normal reuse, input, reference, coverage, metadata, or tumor-only policy problem | Review `somatic_manifest.validation.md`, `somatic_plan.json`, and `reports/somatic_preflight_report.md`; no caller was run. |
| Tumor-only row rejected | Tumor-only is disabled or acknowledgment is missing | Set explicit project policy only after study review and include `analysis_mode=tumor_only` plus acknowledgment. |
| Normal reuse rejected | Shared normal is not enabled or exceeds configured maximum | Review whether the study design supports reused normals before changing `somatic.normal_reuse`. |
| Somatic pair has ready report but no VCF | Phase 2D is preflight/planning only | DeepSomatic, Severus, CNV, and annotation execution are deferred to later phases. |
| DeepSomatic pair blocked | Model, version, pair readiness, reference, command, or metadata policy failed | Review `deepsomatic_plan.json`, `deepsomatic_preflight.json`, and failure category before rerun. |
| DeepSomatic output rejected | VCF/gVCF, index, sample, sorting, FILTER, or checksum validation failed | Review validation JSON/Markdown; partial outputs are not reusable. |
| Severus pair blocked | Tumor-normal readiness, version policy, container/executable mode, protected arguments, or tumor-only policy failed | Review `severus_plan.json`, `severus_preflight.json`, and failure category before rerun. |
| Severus native output missing | Required primary SV VCF is absent or empty | Review caller stdout/stderr and `severus_output_inventory.json`; do not treat auxiliary files as a substitute. |
| Severus BND validation FAIL | Breakend mates are missing, duplicate, self-referential, nonreciprocal, or malformed | Review `severus_bnd_validation.json` and the raw SV VCF before rerun. |
| Severus contract drift FAIL | Installed `severus --help` differs from committed contract | Run `severus-contract-check`, inspect `severus_contract_drift.json`, and do not execute until the contract is updated from official sources. |
| Array concurrency warning | `--max-concurrent` exceeds selected sample count or site expectations | Lower `--max-concurrent` before manual scheduler submission. |
| Missing cohort status records | Planning has not seeded records or task outputs were not copied back | Run `cohort-status` and inspect sharded `status/current/`. |
| Rerun manifest empty | Selection criteria matched no samples | Review `cohort_status.tsv` and relax status/stage/category filters if appropriate. |
| Incremental reuse rejected | Manifest/config/reference/tool signatures changed or are missing | Treat sample as requiring rerun unless an operator can justify a new validated attempt. |
| Scratch root rejected | Scratch is enabled without a configured safe root | Set `execution.scratch.root` or disable scratch. |
| Scratch-space unit test differs by machine | Test depends on real filesystem capacity | Use the deterministic monkeypatched scratch tests; do not force warnings with huge requested sizes. |
| Storage estimate seems high or low | Estimate uses planning factors, not observed real usage | Adjust factors in future configuration and compare with measured run data. |
| Joint identity validation FAIL | VCF header sample does not match manifest sample under strict policy | Fix upstream gVCF/sample metadata or provide an explicit one-to-one mapping file. |
| Joint reference compatibility FAIL | gVCFs use mixed reference signatures, contig order, lengths, or chr-prefix conventions | Use compatible gVCFs generated against the same reference; Phase 2C does not rewrite contigs. |
| Joint shard output invalid | Shard VCF is missing, malformed, unindexed, or outside expected interval | Review shard command, stderr, validation JSON, and rerun only affected shards. |
| Joint incremental reuse rejected | Sample set, gVCF signatures, backend, preset, or reference changed | Rerun joint genotyping for affected cohort outputs; per-sample gVCFs may remain reusable. |
## Integrated Somatic Reporting

If an integrated attempt is `inconsistent`, inspect
`validation/integrated_compatibility.md` for subject, tumor, normal, reference,
or manifest-hash mismatches. If a pair is `partial_success`, inspect
`status/integrated_rerun_recommendations.tsv` to determine whether only
DeepSomatic or only Severus needs rerun. If reports are missing, regenerate the
integrated attempt; native caller outputs are not modified by report generation.
