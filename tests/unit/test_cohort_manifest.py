from __future__ import annotations

from pathlib import Path

import pytest

from variant_analysis_harness.cohort.manifest import load_cohort_manifest
from variant_analysis_harness.exceptions import ManifestError


HEADER = "sample_id\tplatform\tinput_type\tinput_path\tadditional_inputs\taligned\treference_id\tread_group_sample\toutput_prefix\tanalysis\tenabled\tcohort_group\tpriority\n"


def write_cohort_manifest(path: Path, rows: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "".join(rows), encoding="utf-8")
    return path


def row(sample: str, input_path: Path, analysis: str = "combined", enabled: str = "true", output_prefix: str | None = None) -> str:
    prefix = output_prefix or sample
    return f"{sample}\tpacbio_hifi\taligned_bam\t{input_path}\t\ttrue\tref_001\t{sample}\t{prefix}\t{analysis}\t{enabled}\tgrp\t0\n"


def test_cohort_manifest_multiple_valid_samples(tmp_path, tiny_inputs):
    manifest = write_cohort_manifest(
        tmp_path / "cohort.tsv",
        [
            row("SAMPLE_002", tiny_inputs["bam"], "sv"),
            row("SAMPLE_001", tiny_inputs["bam"], "snv"),
        ],
    )
    selected, excluded, result = load_cohort_manifest(manifest)
    assert result.status == "WARN"
    assert [s.sample_id for s in selected] == ["SAMPLE_001", "SAMPLE_002"]
    assert excluded == []
    assert result.stage_counts["germline_snv"] == 1
    assert result.stage_counts["germline_sv_call"] == 1


def test_cohort_manifest_duplicate_ids_fail(tmp_path, tiny_inputs):
    manifest = write_cohort_manifest(
        tmp_path / "cohort.tsv",
        [row("SAMPLE_001", tiny_inputs["bam"]), row("SAMPLE_001", tiny_inputs["bam"], output_prefix="SAMPLE_001B")],
    )
    _, _, result = load_cohort_manifest(manifest)
    assert result.status == "FAIL"
    assert any("duplicate sample_id" in issue["message"] for issue in result.errors)


def test_cohort_manifest_duplicate_outputs_fail(tmp_path, tiny_inputs):
    manifest = write_cohort_manifest(
        tmp_path / "cohort.tsv",
        [row("SAMPLE_001", tiny_inputs["bam"], output_prefix="OUT"), row("SAMPLE_002", tiny_inputs["bam"], output_prefix="OUT")],
    )
    _, _, result = load_cohort_manifest(manifest)
    assert result.status == "FAIL"
    assert any("duplicate output_prefix" in issue["message"] for issue in result.errors)


def test_cohort_manifest_disabled_and_filters(tmp_path, tiny_inputs):
    manifest = write_cohort_manifest(
        tmp_path / "cohort.tsv",
        [row("SAMPLE_001", tiny_inputs["bam"], enabled="false"), row("SAMPLE_002", tiny_inputs["bam"])],
    )
    selected, excluded, result = load_cohort_manifest(manifest, exclude_samples={"SAMPLE_002"})
    assert selected == []
    assert {s.sample_id for s in excluded} == {"SAMPLE_001", "SAMPLE_002"}
    assert result.expected_array_tasks == 0


def test_cohort_manifest_invalid_input_combination(tmp_path, tiny_inputs):
    manifest = tmp_path / "bad.tsv"
    manifest.write_text(
        HEADER
        + f"SAMPLE_001\tpacbio_hifi\tunaligned_bam\t{tiny_inputs['unaligned']}\t\ttrue\tref_001\tSAMPLE_001\tSAMPLE_001\tcombined\ttrue\tgrp\t0\n",
        encoding="utf-8",
    )
    _, _, result = load_cohort_manifest(manifest)
    assert result.status == "FAIL"
    assert "only aligned_bam may set aligned=true" in result.errors[0]["message"]


def test_cohort_manifest_max_rows(tmp_path, tiny_inputs):
    manifest = write_cohort_manifest(tmp_path / "cohort.tsv", [row("SAMPLE_001", tiny_inputs["bam"])])
    with pytest.raises(ManifestError):
        load_cohort_manifest(manifest, max_rows=0)
