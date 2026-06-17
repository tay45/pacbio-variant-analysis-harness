from __future__ import annotations

import json

from tests.conftest import write_config
from tests.unit.test_cohort_manifest import row, write_cohort_manifest
from variant_analysis_harness.cli import main
from variant_analysis_harness.cohort.status import aggregate_status, write_status_event
from variant_analysis_harness.common.config import load_run_config


def test_cohort_slurm_array_script(tmp_path, tiny_reference, tiny_inputs):
    config = write_config(tmp_path, tiny_reference)
    manifest = write_cohort_manifest(
        tmp_path / "cohort.tsv",
        [row("SAMPLE_A", tiny_inputs["bam"]), row("SAMPLE_B", tiny_inputs["bam"])],
    )
    rc = main(["cohort-slurm", "--config", str(config), "--manifest", str(manifest), "--cohort-id", "COHORT_1", "--max-concurrent", "2"])
    assert rc == 0
    cfg = load_run_config(config)
    script = tmp_path / "results" / cfg["project"]["name"] / "cohorts" / "COHORT_1" / "cohort_attempt_001" / "slurm" / "cohort_array.sh"
    text = script.read_text()
    assert "#SBATCH --array=1-2%2" in text
    assert '--manifest "${SAMPLE_MANIFEST}"' in text
    assert "sbatch" not in text.lower().replace("#SBATCH".lower(), "")


def test_status_aggregation_and_values(tmp_path):
    cohort_dir = tmp_path / "cohort"
    write_status_event(cohort_dir, {"sample_id": "SAMPLE_A", "stage": "workflow", "status": "failed", "failure_category": "alignment_failure", "warning_count": 0})
    write_status_event(cohort_dir, {"sample_id": "SAMPLE_B", "stage": "workflow", "status": "success", "warning_count": 1})
    summary = aggregate_status(cohort_dir)
    assert summary["status_counts"] == {"failed": 1, "success": 1}
    assert summary["failure_category_counts"] == {"alignment_failure": 1}
    assert (cohort_dir / "cohort_status.tsv").exists()
    assert json.loads((cohort_dir / "cohort_status.json").read_text())["total_records"] == 2

