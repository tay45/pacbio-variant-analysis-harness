from __future__ import annotations

from pathlib import Path

import pytest

from variant_analysis_harness.somatic.manifest import (
    default_somatic_config,
    load_somatic_manifest,
    resolve_somatic_config,
)


HEADER = [
    "pair_id",
    "subject_id",
    "tumor_sample_id",
    "tumor_specimen_id",
    "tumor_input_type",
    "tumor_input_path",
    "tumor_index_path",
    "normal_sample_id",
    "normal_specimen_id",
    "normal_input_type",
    "normal_input_path",
    "normal_index_path",
    "reference_id",
    "analysis_mode",
    "enabled",
    "tumor_read_group_sample",
    "normal_read_group_sample",
    "tumor_coverage",
    "normal_coverage",
    "tumor_purity",
    "normal_contamination",
    "tumor_contamination",
    "tumor_ploidy",
    "tumor_only_acknowledgment",
    "reference_signature",
    "tumor_reference_signature",
    "normal_reference_signature",
    "tumor_contigs",
    "normal_contigs",
]


def row(pair_id="P1", subject_id="S1", tumor="T1", normal="N1", mode="tumor_normal", enabled="true", **overrides):
    data = {
        "pair_id": pair_id,
        "subject_id": subject_id,
        "tumor_sample_id": tumor,
        "tumor_specimen_id": f"{tumor}_SPEC",
        "tumor_input_type": "BAM",
        "tumor_input_path": f"{tumor}.bam",
        "tumor_index_path": f"{tumor}.bam.bai",
        "normal_sample_id": normal,
        "normal_specimen_id": f"{normal}_SPEC",
        "normal_input_type": "BAM" if normal else "",
        "normal_input_path": f"{normal}.bam" if normal else "",
        "normal_index_path": f"{normal}.bam.bai" if normal else "",
        "reference_id": "ref_001",
        "analysis_mode": mode,
        "enabled": enabled,
        "tumor_read_group_sample": tumor,
        "normal_read_group_sample": normal,
        "tumor_coverage": "40",
        "normal_coverage": "35",
        "tumor_purity": "",
        "normal_contamination": "",
        "tumor_contamination": "",
        "tumor_ploidy": "",
        "tumor_only_acknowledgment": "",
        "reference_signature": "refsig",
        "tumor_reference_signature": "",
        "normal_reference_signature": "",
        "tumor_contigs": "chr1:10,chr2:20",
        "normal_contigs": "chr1:10,chr2:20",
    }
    data.update(overrides)
    return data


def write_manifest(path: Path, rows: list[dict[str, str]]) -> Path:
    path.write_text("\t".join(HEADER) + "\n" + "\n".join("\t".join(r.get(h, "") for h in HEADER) for r in rows) + "\n", encoding="utf-8")
    return path


def test_valid_tumor_normal_row(tmp_path):
    selected, excluded, validation = load_somatic_manifest(write_manifest(tmp_path / "somatic.tsv", [row()]), somatic_config=default_somatic_config())
    assert validation.status == "PASS"
    assert len(selected) == 1
    assert not excluded
    assert selected[0].row_hash


def test_tumor_only_rejected_by_default(tmp_path):
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(mode="tumor_only", normal="", tumor_only_acknowledgment="ack")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=default_somatic_config())
    assert validation.status == "FAIL"
    assert any(e["category"] == "tumor_only_not_allowed" for e in validation.errors)


def test_tumor_only_allowed_with_acknowledgment(tmp_path):
    cfg = default_somatic_config()
    cfg["tumor_only"]["allowed"] = True
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(mode="tumor_only", normal="", tumor_only_acknowledgment="ack")])
    selected, _, validation = load_somatic_manifest(manifest, somatic_config=cfg)
    assert selected[0].is_tumor_only
    assert not any(e["category"] == "tumor_only_not_allowed" for e in validation.errors)


def test_tumor_only_acknowledgment_missing(tmp_path):
    cfg = default_somatic_config()
    cfg["tumor_only"]["allowed"] = True
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(mode="tumor_only", normal="")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=cfg)
    assert any(e["category"] == "tumor_only_acknowledgment_missing" for e in validation.errors)


def test_missing_normal_does_not_silently_fallback(tmp_path):
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(normal="")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=default_somatic_config())
    assert any(e["category"] == "missing_normal_input" for e in validation.errors)


def test_duplicate_pair_and_tumor_ids_fail(tmp_path):
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(pair_id="P1", tumor="T1"), row(pair_id="P1", tumor="T1", normal="N2")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=default_somatic_config())
    assert any(e["category"] == "duplicate_pair_id" for e in validation.errors)
    assert any(e["category"] == "duplicate_tumor_sample" for e in validation.errors)


def test_normal_reuse_policy(tmp_path):
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(pair_id="P1", tumor="T1", normal="N1"), row(pair_id="P2", tumor="T2", normal="N1")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=default_somatic_config())
    assert any(e["category"] == "invalid_normal_reuse" for e in validation.errors)
    cfg = default_somatic_config()
    cfg["normal_reuse"]["allowed"] = True
    cfg["normal_reuse"]["maximum_pairs_per_normal"] = 2
    _, _, validation = load_somatic_manifest(manifest, somatic_config=cfg)
    assert not any(e["category"] == "invalid_normal_reuse" for e in validation.errors)
    assert validation.warnings


def test_normal_shared_across_subjects_fails_even_when_reuse_allowed(tmp_path):
    cfg = default_somatic_config()
    cfg["normal_reuse"]["allowed"] = True
    cfg["normal_reuse"]["maximum_pairs_per_normal"] = 2
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(pair_id="P1", subject_id="S1", tumor="T1", normal="N1"), row(pair_id="P2", subject_id="S2", tumor="T2", normal="N1")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=cfg)
    assert any(e["category"] == "subject_mismatch" for e in validation.errors)


def test_unsafe_ids_and_path_traversal(tmp_path):
    manifest = write_manifest(tmp_path / "somatic.tsv", [row(pair_id="../bad", tumor_input_path="../secret.bam")])
    _, _, validation = load_somatic_manifest(manifest, somatic_config=default_somatic_config())
    assert validation.status == "FAIL"


def test_resolve_somatic_config_defaults_disabled():
    cfg = resolve_somatic_config({})
    assert cfg["enabled"] is False
    assert cfg["mode"] == "tumor_normal"
    assert cfg["tumor_only"]["allowed"] is False
