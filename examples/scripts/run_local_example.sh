#!/usr/bin/env bash
set -euo pipefail
python -m variant_analysis_harness.cli run --config examples/configs/run.example.yaml --manifest examples/manifests/sample_manifest.example.tsv --sample SAMPLE_001 --analysis combined
