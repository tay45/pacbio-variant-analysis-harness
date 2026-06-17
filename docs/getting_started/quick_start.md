# Quick Start

These commands are safe planning, dry-run, or mocked-test examples. They
do not assume Docker, Slurm, DeepVariant, DeepSomatic, Severus, pbsv, or
GLnexus are installed unless explicitly stated.

## Environment Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Help

```bash
python -m variant_analysis_harness.cli --help
```

## Example Config And Manifest

Use `configs/pacbio_hifi_germline.example.yaml`,
`configs/somatic_project.example.yaml`, and manifests under
`examples/manifests/` as templates.

## Germline Dry-Run

```bash
python -m variant_analysis_harness.cli dry-run \
  --config configs/pacbio_hifi_germline.example.yaml \
  --manifest examples/manifests/sample_manifest.example.tsv \
  --sample SAMPLE_001 \
  --analysis combined
```

## Germline Cohort Plan

```bash
python -m variant_analysis_harness.cli cohort-plan \
  --config configs/pacbio_hifi_germline.example.yaml \
  --manifest examples/manifests/cohort_manifest.example.tsv \
  --cohort-id COHORT_001
```

## Somatic Preflight

```bash
python -m variant_analysis_harness.cli somatic-validate \
  --config configs/somatic_project.example.yaml \
  --manifest examples/manifests/somatic_manifest.example.tsv \
  --somatic-project-id SOMATIC_001
```

## DeepSomatic Dry-Run

```bash
python -m variant_analysis_harness.cli somatic-snv-dry-run \
  --config configs/somatic_project.example.yaml \
  --manifest examples/manifests/somatic_manifest.example.tsv \
  --somatic-project-id SOMATIC_001
```

## Severus Dry-Run

```bash
python -m variant_analysis_harness.cli somatic-sv-dry-run \
  --config configs/somatic_project.example.yaml \
  --manifest examples/manifests/somatic_manifest.example.tsv \
  --somatic-project-id SOMATIC_001
```

## Integrated Somatic Report Generation

```bash
python -m variant_analysis_harness.cli somatic-integrated-plan \
  --config configs/somatic_project.example.yaml \
  --manifest examples/manifests/somatic_manifest.example.tsv \
  --somatic-project-id SOMATIC_001 \
  --somatic-dir results/example_project/somatic/SOMATIC_001/somatic_attempt_001
```

## Mocked Test Execution

```bash
python scripts/run_tests.py -q
python scripts/verify_pytest_exit.py
```

Real external-tool execution requires the relevant caller, reference,
model/container, and site profile to be installed and reviewed separately.
