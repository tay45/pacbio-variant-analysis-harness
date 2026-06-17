from __future__ import annotations

import json
import resource
import time
from pathlib import Path

from tests.conftest import write_config
from tests.unit.test_cohort_manifest import row, write_cohort_manifest
from variant_analysis_harness.cohort.incremental import compare_incremental
from variant_analysis_harness.cohort.manifest import load_cohort_manifest
from variant_analysis_harness.cohort.planning import generate_cohort_plan, write_array_index, write_cohort_plan
from variant_analysis_harness.cohort.qc import aggregate_qc
from variant_analysis_harness.cohort.reporting import write_cohort_report
from variant_analysis_harness.cohort.status import aggregate_status, seed_pending_statuses
from variant_analysis_harness.cohort.storage import estimate_storage, write_storage_estimate
from variant_analysis_harness.common.config import load_run_config


def test_3000_sample_planning(tmp_path, tiny_reference, tiny_inputs):
    start = time.perf_counter()
    config = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config)
    rows = [row(f"SAMPLE_{idx:04d}", tiny_inputs["bam"], analysis=("snv" if idx % 3 == 0 else "sv" if idx % 3 == 1 else "combined")) for idx in range(3000)]
    manifest = write_cohort_manifest(tmp_path / "cohort_3000.tsv", rows)
    selected, excluded, validation = load_cohort_manifest(manifest, max_rows=3000)
    assert validation.status == "WARN"
    assert len(selected) == 3000
    cohort_dir = tmp_path / "cohort_attempt"
    plan = generate_cohort_plan(
        cfg,
        config_path=config,
        manifest_path=manifest,
        selected=selected,
        excluded=excluded,
        cohort_id="COHORT_3000",
        cohort_attempt_id="cohort_attempt_001",
        sample_attempt_id="attempt_001",
        output_root=tmp_path / "results",
        max_concurrent=200,
    )
    write_cohort_plan(plan, cohort_dir)
    write_array_index(plan, cohort_dir / "array_index.tsv")
    seed_pending_statuses(cohort_dir, plan)
    status_start = time.perf_counter()
    status_summary = aggregate_status(cohort_dir)
    status_runtime = time.perf_counter() - status_start
    incremental = compare_incremental(current_samples=selected, current_config=cfg, previous_cohort_dir=None, out_dir=cohort_dir)
    storage = estimate_storage(selected)
    write_storage_estimate(storage, cohort_dir / "storage")
    qc = aggregate_qc(cohort_dir, plan, status_summary)
    report = write_cohort_report(cohort_dir, plan=plan, status_summary=status_summary, qc_summary=qc, storage_estimate=storage, incremental_summary=incremental)
    runtime = time.perf_counter() - start
    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    results = {
        "runtime_seconds": round(runtime, 3),
        "status_aggregation_seconds": round(status_runtime, 3),
        "peak_memory_kb_platform_dependent": peak_kb,
        "generated_task_count": plan["task_count"],
        "generated_array_count": len(plan["array_grouping"]),
        "report_size_bytes": report.stat().st_size,
    }
    payload = json.dumps(results, indent=2, sort_keys=True) + "\n"
    (tmp_path / "SCALE_TEST_RESULTS.txt").write_text(payload, encoding="utf-8")
    evidence_dir = Path.cwd() / "docs" / "validation" / "evidence" / "scale_tests"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "SCALE_TEST_RESULTS.txt").write_text(payload, encoding="utf-8")
    assert plan["task_count"] == 3000
    assert len(plan["array_grouping"]) == 1
    assert status_summary["status_counts"]["pending"] == 3000
    assert runtime < 30
