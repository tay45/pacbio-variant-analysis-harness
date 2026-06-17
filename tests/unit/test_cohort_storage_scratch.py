from __future__ import annotations

import pytest
from collections import namedtuple

from tests.unit.test_cohort_manifest import row, write_cohort_manifest
import variant_analysis_harness.cohort.scratch as scratch_module
from variant_analysis_harness.cohort.manifest import load_cohort_manifest
from variant_analysis_harness.cohort.scratch import resolve_scratch_config, task_scratch_dir, validate_scratch_space
from variant_analysis_harness.cohort.storage import estimate_storage, write_storage_estimate
from variant_analysis_harness.exceptions import ConfigError


def test_storage_estimate_modes(tmp_path, tiny_inputs):
    manifest = write_cohort_manifest(
        tmp_path / "cohort.tsv",
        [row("SAMPLE_SNV", tiny_inputs["bam"], analysis="snv"), row("SAMPLE_SV", tiny_inputs["bam"], analysis="sv")],
    )
    selected, _, _ = load_cohort_manifest(manifest)
    estimate = estimate_storage(selected)
    assert estimate["final_retained_gb"] >= 0
    write_storage_estimate(estimate, tmp_path)
    assert (tmp_path / "storage_estimate.md").exists()


def test_scratch_config_and_path_safety(tmp_path):
    cfg = {"execution": {"scratch": {"enabled": True, "root": str(tmp_path)}}}
    resolved = resolve_scratch_config(cfg)
    assert resolved["enabled"] is True
    path = task_scratch_dir(tmp_path, "COHORT_1", "SAMPLE_A", "alignment")
    assert path == tmp_path / "COHORT_1" / "SA" / "SAMPLE_A" / "alignment"
    with pytest.raises(ConfigError):
        task_scratch_dir(tmp_path, "..", "SAMPLE_A", "alignment")


def test_scratch_missing_root_rejected():
    with pytest.raises(ConfigError):
        resolve_scratch_config({"execution": {"scratch": {"enabled": True}}})


DiskUsage = namedtuple("DiskUsage", "total used free")
GIB = 1024**3


def test_scratch_space_pass_is_deterministic(monkeypatch, tmp_path):
    monkeypatch.setattr(scratch_module.shutil, "disk_usage", lambda path: DiskUsage(200 * GIB, 100 * GIB, 100 * GIB))
    result = validate_scratch_space(tmp_path, required_gb=20)
    assert result["status"] == "PASS"
    assert result["available_gb"] == 100.0
    assert result["required_gb"] == 20
    assert result["warnings"] == []


def test_scratch_space_warning_is_deterministic(monkeypatch, tmp_path):
    monkeypatch.setattr(scratch_module.shutil, "disk_usage", lambda path: DiskUsage(200 * GIB, 190 * GIB, 10 * GIB))
    result = validate_scratch_space(tmp_path, required_gb=20)
    assert result["status"] == "WARN"
    assert result["available_gb"] == 10.0
    assert result["required_gb"] == 20
    assert "below requested" in result["warnings"][0]


def test_scratch_space_nonexistent_path_uses_parent(monkeypatch, tmp_path):
    observed = {}

    def fake_disk_usage(path):
        observed["path"] = path
        return DiskUsage(5 * GIB, 2 * GIB, 3 * GIB)

    monkeypatch.setattr(scratch_module.shutil, "disk_usage", fake_disk_usage)
    missing = tmp_path / "missing" / "scratch"
    result = validate_scratch_space(missing, required_gb=1)
    assert result["status"] == "PASS"
    assert observed["path"] == missing.parent
    assert result["checked_path"] == str(missing.parent)


def test_scratch_space_inaccessible_path_reports_fail(monkeypatch, tmp_path):
    def fake_disk_usage(path):
        raise OSError("permission denied")

    monkeypatch.setattr(scratch_module.shutil, "disk_usage", fake_disk_usage)
    result = validate_scratch_space(tmp_path, required_gb=1)
    assert result["status"] == "FAIL"
    assert result["available_gb"] is None
    assert "permission denied" in result["error"]


def test_scratch_space_zero_required_and_rounding(monkeypatch, tmp_path):
    monkeypatch.setattr(scratch_module.shutil, "disk_usage", lambda path: DiskUsage(2 * GIB, 1 * GIB, int(1.23456 * GIB)))
    result = validate_scratch_space(tmp_path, required_gb=0)
    assert result["status"] == "PASS"
    assert result["available_gb"] == 1.235
    assert result["required_gb"] == 0


def test_scratch_space_negative_requirement_rejected(tmp_path):
    with pytest.raises(ConfigError):
        validate_scratch_space(tmp_path, required_gb=-1)
