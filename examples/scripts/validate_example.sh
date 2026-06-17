#!/usr/bin/env bash
set -euo pipefail
python -m variant_analysis_harness.cli validate --config examples/configs/run.example.yaml --manifest examples/manifests/sample_manifest.example.tsv --sample SAMPLE_001
