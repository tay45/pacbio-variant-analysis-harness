# Testing

Standard development tests use the official pytest package through a
repository-controlled hermetic launcher.

```bash
python scripts/run_tests.py -q
python scripts/run_tests.py --durations=30
python scripts/run_tests.py -q tests/scale/test_3000_sample_planning.py
python scripts/run_tests.py -q tests/scale/test_3000_sample_joint_planning.py
python scripts/run_tests.py -q tests/scale/test_3000_pair_somatic_planning.py
python scripts/run_tests.py -q tests/scale/test_3000_pair_deepsomatic_planning.py
python scripts/run_tests.py -q tests/unit/test_cohort_storage_scratch.py
python scripts/run_tests.py -q tests/smoke/test_exit_smoke_subset.py
python scripts/verify_pytest_exit.py
python scripts/verify_pytest_exit.py --full
```

The authoritative repository test command disables automatic discovery of
third-party pytest plugins so results are not affected by unrelated packages
installed in the host environment. The direct equivalent is:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Plain `python -m pytest -q` may load external plugins from the host environment.
That is sometimes useful for local experimentation, but it is not the
authoritative hermetic verification path.

The repository must not contain a root-level `pytest.py`; that would shadow the
official pytest package. `PYTEST_RESOLUTION_CHECK.txt` records the verification
that pytest resolves outside this repository.

To intentionally experiment with a plugin locally, run plain pytest or invoke
pytest with an explicit plugin in a throwaway environment. Do not make standard
tests depend on globally installed plugins unless the dependency is declared and
loaded intentionally.

Process-exit verification is executed as a standalone top-level command. The
ordinary pytest suite tests verifier logic through dependency injection and does
not launch another pytest suite recursively. The default verifier runs only the
dedicated `tests/smoke/test_exit_smoke_subset.py` file, which contains fast
core, cohort-planning, and joint-planning checks that do not invoke subprocess
pytest, the verifier, real genomics tools, Slurm, or the network.

`python scripts/verify_pytest_exit.py --full` remains available for release
verification. It launches `python scripts/run_tests.py -q` from a top-level
process, captures stdout and stderr, uses a bounded timeout, and reports
`summary_printed`, `process_exited`, `timeout`, and `clean_exit`. It must not be
called from inside pytest. The recursion guard
`VARIANT_HARNESS_EXIT_VERIFIER_ACTIVE` rejects nested verifier invocation with a
nonzero exit code and a clear diagnostic.

CI uses the standard full suite plus the representative exit verifier as
separate top-level steps. The full-suite verifier is intentionally left for
explicit release verification so the default CI job does not duplicate the full
suite unnecessarily.

Real-tool smoke tests under `tests/real_tools/` are marked/documented as optional
and are excluded from standard testing. Standard tests use temporary fixtures and
mocked executables only. They do not require network access, Slurm, containers,
large sequencing data, institutional resources, or real genomics tools.

Network access is blocked during standard tests. Remote JSON Schema references
must be rejected before DNS, socket, urllib, requests, or schema-retrieval code
can run.

Testing-only fallback modules under `variant_analysis_harness/testing_only/` are
not production behavior and are not scientifically or operationally supported.
They exist only for isolated fallback experiments and are not activated by
normal CLI commands.

Phase 2B includes a synthetic 3,000-sample planning simulation. It uses mocked
paths and tiny fixtures only; it does not create real BAM files, invoke
analytical tools, access Slurm, or access the network.

Phase 2B.1 makes scratch-space unit tests deterministic by monkeypatching the
`shutil.disk_usage` lookup used by the scratch module. Unit tests cover
sufficient free space, insufficient free space, nonexistent paths that fall back
to the parent path, inaccessible path handling, zero required space, negative
requirements, and rounding. These tests intentionally do not depend on the host
filesystem capacity.

Runtime targets for standard tests:

- unit tests normally under 1 second,
- mocked integration tests normally under 5 seconds when feasible,
- scale test under 20 seconds,
- full standard suite under 60 seconds.

Any retained slow mocked integration tests should be justified in
`TEST_RUNTIME_ANALYSIS.md`.

Phase 2C joint-genotyping tests use tiny generated gVCF headers or synthetic
metadata. Standard tests do not require GLnexus, bcftools, Slurm, network
access, or real gVCF cohort data.

Phase 2D somatic tests use synthetic TSV rows, mock BAM/CRAM paths, and supplied
metadata only. Standard tests do not execute DeepSomatic, Severus, somatic
variant callers, CNV callers, Slurm, network access, or real alignment files.
The 3,000-pair somatic scale test validates planning and reporting only.

Phase 2E DeepSomatic tests use fake runners, tiny generated VCFs, and synthetic
pair metadata. Standard tests do not execute real DeepSomatic, Docker,
Apptainer, Singularity, Slurm, or network downloads.

Phase 2F Severus tests use fake runners, synthetic manifests, tiny generated SV
VCFs, and mocked output directories. Standard tests do not execute real
Severus, Docker, Apptainer, Singularity, Slurm, Sniffles2, pbsv somatic mode,
CNV callers, or network downloads.

Phase 2F.1 adds official-contract tests under `tests/contracts/`. These tests
read committed offline fixtures in `contracts/severus/1.7/` and reject obsolete
Phase 2F flags such as `--tumor-bam`, `--normal-bam`, lowercase `--pon`, and
the nonexistent Severus `--reference` argument.
## Phase 2G Integrated Somatic Tests

Phase 2G adds hermetic tests for integrated configuration, source-attempt
selection, pair status derivation, compatibility checks, indexed relationship
generation, QC aggregation, rerun recommendations, report generation, mocked CLI
integration, and deterministic 3,000-pair reporting.

These tests use synthetic JSON/TSV records and do not run DeepSomatic, Severus,
containers, Slurm, network calls, or real sequencing data.
