from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from tests.conftest import write_config
from variant_analysis_harness.cli import main
from variant_analysis_harness.common.config import load_run_config
from variant_analysis_harness.joint.commands import build_glnexus_command
from variant_analysis_harness.joint.identity import validate_sample_identity
from variant_analysis_harness.joint.incremental import compare_joint_incremental
from variant_analysis_harness.joint.inputs import build_joint_inputs, load_joint_seed_manifest
from variant_analysis_harness.joint.planning import generate_joint_plan, joint_attempt_dir, prepare_joint_attempt, write_joint_plan
from variant_analysis_harness.joint.qc import run_joint_variant_qc
from variant_analysis_harness.joint.reference import validate_reference_compatibility
from variant_analysis_harness.joint.rerun import generate_joint_rerun_manifest
from variant_analysis_harness.joint.sharding import shards_from_contigs, shards_from_interval_file
from variant_analysis_harness.joint.slurm import write_joint_slurm_array
from variant_analysis_harness.joint.status import aggregate_joint_status, seed_shard_statuses, write_shard_status
from variant_analysis_harness.joint.validation import validate_joint_vcf


def write_gvcf(path: Path, sample: str, contigs: list[tuple[str, int]] | None = None, record_contig: str = "chr1") -> Path:
    contigs = contigs or [("chr1", 12), ("chr2", 20)]
    header = ["##fileformat=VCFv4.2"]
    header.extend(f"##contig=<ID={name},length={length}>" for name, length in contigs)
    header.append(f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{sample}")
    body = f"{record_contig}\t1\t.\tA\t<NON_REF>\t.\tPASS\tEND=10\tGT\t0/0\n"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(header) + "\n" + body)
    Path(str(path) + ".tbi").write_text("index\n", encoding="utf-8")
    return path


def write_joint_manifest(path: Path, rows: list[tuple[str, Path, str]]) -> Path:
    path.write_text(
        "sample_id\tgvcf_path\treference_id\treference_signature\tenabled\n"
        + "".join(f"{sample}\t{gvcf}\tref_001\trefsig\ttrue\n" for sample, gvcf, _ in rows),
        encoding="utf-8",
    )
    return path


def test_joint_input_manifest_valid_and_deterministic(tmp_path):
    a = write_gvcf(tmp_path / "B.g.vcf.gz", "B")
    b = write_gvcf(tmp_path / "A.g.vcf.gz", "A")
    rows = load_joint_seed_manifest(write_joint_manifest(tmp_path / "joint.tsv", [("B", a, "ref"), ("A", b, "ref")]))
    inputs, errors, warnings = build_joint_inputs(rows, base_dir=tmp_path)
    assert not errors
    assert not warnings
    assert [i.sample_id for i in inputs] == ["A", "B"]
    assert [i.cohort_sample_index for i in inputs] == [1, 2]


def test_joint_input_duplicates_and_missing(tmp_path):
    gvcf = write_gvcf(tmp_path / "A.g.vcf.gz", "A")
    rows = [
        {"sample_id": "A", "gvcf_path": str(gvcf), "reference_id": "ref"},
        {"sample_id": "A", "gvcf_path": str(gvcf), "reference_id": "ref"},
        {"sample_id": "C", "gvcf_path": str(tmp_path / "missing.g.vcf.gz"), "reference_id": "ref"},
    ]
    _, errors, _ = build_joint_inputs(rows, base_dir=tmp_path)
    messages = " ".join(e["message"] for e in errors)
    assert "duplicate sample_id" in messages
    assert "duplicate gVCF path" in messages
    assert "missing or empty gVCF" in messages


def test_sample_identity_policies(tmp_path):
    gvcf = write_gvcf(tmp_path / "A.g.vcf.gz", "HEADER_A")
    inputs, _, _ = build_joint_inputs([{"sample_id": "A", "gvcf_path": str(gvcf), "reference_id": "ref"}], base_dir=tmp_path)
    assert validate_sample_identity(inputs, policy="strict")["status"] == "FAIL"
    assert validate_sample_identity(inputs, policy="warn")["status"] == "WARN"
    mapping = tmp_path / "map.yaml"
    mapping.write_text("sample_name_mapping:\n  HEADER_A: HEADER_A\n", encoding="utf-8")
    assert validate_sample_identity(inputs, policy="explicit_mapping", mapping_file=mapping)["status"] == "PASS"


def test_reference_compatibility_mixed_order_and_length(tmp_path):
    a = write_gvcf(tmp_path / "A.g.vcf.gz", "A", [("chr1", 12), ("chr2", 20)])
    b = write_gvcf(tmp_path / "B.g.vcf.gz", "B", [("chr2", 20), ("chr1", 99)], record_contig="chr2")
    inputs, _, _ = build_joint_inputs(
        [{"sample_id": "A", "gvcf_path": str(a), "reference_id": "ref", "reference_signature": "x"}, {"sample_id": "B", "gvcf_path": str(b), "reference_id": "ref", "reference_signature": "x"}],
        base_dir=tmp_path,
    )
    result = validate_reference_compatibility(inputs)
    assert result["status"] == "FAIL"
    assert any("contig order" in e["message"] for e in result["errors"])


def test_sharding_contig_and_interval(tmp_path):
    contigs = [{"id": "chr1", "length": 12}, {"id": "chr2", "length": 20}]
    shards = shards_from_contigs(contigs, out_dir=tmp_path, exclude_contigs={"chr2"})
    assert [s.shard_id for s in shards] == ["shard_00001_chr1"]
    bed = tmp_path / "intervals.bed"
    bed.write_text("chr1\t0\t5\nchr1\t5\t10\n", encoding="utf-8")
    interval_shards, errors = shards_from_interval_file(bed, out_dir=tmp_path, reference_contigs={"chr1": 12})
    assert not errors
    assert [s.start for s in interval_shards] == [1, 6]


def test_glnexus_command_uses_input_list(tmp_path, tiny_reference):
    cfg = load_run_config(write_config(tmp_path, tiny_reference))
    cfg["joint_genotyping"]["enabled"] = True
    gvcf = write_gvcf(tmp_path / "A.g.vcf.gz", "A")
    inputs, _, _ = build_joint_inputs([{"sample_id": "A", "gvcf_path": str(gvcf), "reference_id": "ref"}], base_dir=tmp_path)
    shard = shards_from_contigs([{"id": "chr1", "length": 12}], out_dir=tmp_path)[0]
    spec, input_list = build_glnexus_command(cfg, shard, inputs, tmp_path)
    assert "--list" in spec.argv
    assert str(input_list) in spec.argv
    assert "chr1:1-12" in spec.argv
    assert input_list.read_text().strip() == str(gvcf)


def test_joint_slurm_status_rerun_and_validation(tmp_path):
    plan = {"joint_id": "J1", "joint_attempt_id": "A1", "backend": "glnexus", "shard_count": 2, "shard_definitions": [
        {"shard_index": 1, "shard_id": "shard_00001_chr1", "contig": "chr1", "start": 1, "end": 12, "enabled": "true", "output_vcf": str(tmp_path / "s1.vcf.gz")},
        {"shard_index": 2, "shard_id": "shard_00002_chr2", "contig": "chr2", "start": 1, "end": 20, "enabled": "true", "output_vcf": str(tmp_path / "s2.vcf.gz")},
    ]}
    write_joint_slurm_array(plan, tmp_path / "slurm" / "array.sh", max_concurrent=4)
    assert "#SBATCH --array=1-2%4" in (tmp_path / "slurm" / "array.sh").read_text()
    seed_shard_statuses(tmp_path, plan)
    write_shard_status(tmp_path, {"shard_id": "shard_00002_chr2", "shard_index": 2, "contig": "chr2", "status": "failed", "failure_category": "shard_execution_failure"})
    status = aggregate_joint_status(tmp_path)
    assert status["status_counts"]["failed"] == 1
    rows = generate_joint_rerun_manifest(tmp_path, tmp_path / "failed.tsv")
    assert [r["shard_id"] for r in rows] == ["shard_00002_chr2"]


def test_joint_vcf_validation_and_qc(tmp_path):
    vcf = write_gvcf(tmp_path / "cohort.germline.vcf.gz", "A")
    assert validate_joint_vcf(vcf, expected_samples=["A"])["status"] == "PASS"
    metrics = run_joint_variant_qc(vcf, expected_samples=["A"])
    assert metrics["total_samples"] == 1
    assert metrics["total_variants"] == 1


def test_incremental_added_sample_invalidates_joint_shards(tmp_path):
    a = write_gvcf(tmp_path / "A.g.vcf.gz", "A")
    inputs, _, _ = build_joint_inputs([{"sample_id": "A", "gvcf_path": str(a), "reference_id": "ref"}], base_dir=tmp_path)
    prior = tmp_path / "prior"
    prior.mkdir()
    (prior / "joint_plan.json").write_text(json.dumps({"sample_list_checksum": "old"}) + "\n", encoding="utf-8")
    rows = compare_joint_incremental(inputs, {}, prior, tmp_path)
    assert rows[0]["decision"] == "added_sample_invalidates_joint_shards"


def test_joint_cli_plan(tmp_path, tiny_reference):
    cfg = write_config(tmp_path, tiny_reference)
    gvcf = write_gvcf(tmp_path / "A.g.vcf.gz", "A")
    manifest = write_joint_manifest(tmp_path / "joint.tsv", [("A", gvcf, "ref")])
    rc = main(["joint-plan", "--config", str(cfg), "--manifest", str(manifest), "--joint-id", "J1", "--max-concurrent", "2"])
    assert rc == 0
    plan = tmp_path / "results" / "test_project" / "joint_genotyping" / "J1" / "joint_attempt_001" / "joint_plan.json"
    assert json.loads(plan.read_text())["shard_count"] == 2
