from __future__ import annotations

import json
import time
from pathlib import Path

from tests.conftest import write_config
from tests.unit.test_joint_genotyping import write_joint_manifest
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.joint.incremental import compare_joint_incremental
from variant_analysis_harness.joint.inputs import build_joint_inputs, write_joint_inputs
from variant_analysis_harness.joint.planning import generate_joint_plan, write_joint_plan
from variant_analysis_harness.joint.reference import validate_reference_compatibility
from variant_analysis_harness.joint.reporting import write_joint_report
from variant_analysis_harness.joint.sharding import shards_from_contigs
from variant_analysis_harness.joint.status import aggregate_joint_status, seed_shard_statuses
from variant_analysis_harness.joint.storage import estimate_joint_storage


def test_3000_sample_joint_planning(tmp_path, tiny_reference):
    start = time.perf_counter()
    config = write_config(tmp_path, tiny_reference)
    cfg = load_run_config(config)
    rows = []
    for idx in range(3000):
        rows.append({"sample_id": f"SAMPLE_{idx:04d}", "gvcf_path": str(tmp_path / "synthetic" / f"SAMPLE_{idx:04d}.g.vcf.gz"), "reference_id": "ref_001", "reference_signature": "refsig", "sample_name_in_header": f"SAMPLE_{idx:04d}"})
    inputs, errors, warnings = build_joint_inputs(rows, base_dir=tmp_path, require_existing=False)
    assert not errors
    assert len(inputs) == 3000
    attempt_dir = tmp_path / "joint"
    write_joint_inputs(inputs, errors, warnings, attempt_dir)
    contigs = [{"id": "chr1", "length": 12}, {"id": "chr2", "length": 20}]
    shards = shards_from_contigs(contigs, out_dir=attempt_dir)
    reference = {"status": "PASS", "errors": [], "warnings": [], "rows": [{"sample_id": "synthetic", "reference_id": "ref_001", "contigs": contigs}]}
    identity = {"status": "PASS", "errors": [], "warnings": []}
    incremental = compare_joint_incremental(inputs, {}, None, attempt_dir)
    plan = generate_joint_plan(
        cfg,
        config_path=config,
        manifest_path=None,
        joint_id="JOINT_3000",
        attempt_id="joint_attempt_001",
        inputs=inputs,
        excluded_samples=[],
        shards=shards,
        attempt_dir=attempt_dir,
        max_concurrent=100,
        reference_result=reference,
        identity_result=identity,
        reuse_summary=incremental,
    )
    write_joint_plan(plan, attempt_dir)
    seed_shard_statuses(attempt_dir, plan)
    status = aggregate_joint_status(attempt_dir)
    storage = estimate_joint_storage(inputs, shards)
    report = write_joint_report(attempt_dir, plan=plan, status=status, storage=storage, incremental=incremental)
    runtime = time.perf_counter() - start
    metrics = {
        "runtime_seconds": round(runtime, 3),
        "selected_samples": len(inputs),
        "shard_count": len(shards),
        "array_count": len(plan["array_grouping"]),
        "report_size_bytes": report.stat().st_size,
    }
    payload = json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    (tmp_path / "JOINT_SCALE_TEST_RESULTS.txt").write_text(payload, encoding="utf-8")
    (Path.cwd() / "JOINT_SCALE_TEST_RESULTS.txt").write_text(payload, encoding="utf-8")
    assert plan["selected_sample_count"] == 3000
    assert plan["shard_count"] == 2
    assert runtime < 20
