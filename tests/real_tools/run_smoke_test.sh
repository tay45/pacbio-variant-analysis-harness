#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:?config yaml required}"
MANIFEST="${2:?manifest tsv required}"
SAMPLE="${3:?sample id required}"

python -m variant_analysis_harness.cli validate --config "${CONFIG}" --manifest "${MANIFEST}" --sample "${SAMPLE}"
python -m variant_analysis_harness.cli dry-run --config "${CONFIG}" --manifest "${MANIFEST}" --sample "${SAMPLE}" --analysis combined --attempt-id smoke_dry_run
python -m variant_analysis_harness.cli run --config "${CONFIG}" --manifest "${MANIFEST}" --sample "${SAMPLE}" --analysis combined --attempt-id smoke_run
