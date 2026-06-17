from __future__ import annotations

import json

import pytest

from variant_analysis_harness.exceptions import ValidationError
from variant_analysis_harness.somatic.integrated.source_selection import discover_attempt_records, select_source_attempt


def test_discover_attempt_records_preserves_identity_and_reference(tmp_path):
    plan = {
        "pair_attempt_id": "deepsomatic_attempt_001",
        "pair_statuses": [
            {
                "pair_id": "P1",
                "subject_id": "S1",
                "tumor_sample_id": "T1",
                "normal_sample_id": "N1",
                "analysis_mode": "tumor_normal",
                "reference_id": "ref_001",
                "reference_signature": "refsig",
                "manifest_row_hash": "rowhash",
                "caller_preflight_status": "READY",
                "output_checksum": "sha256:abc",
            }
        ],
    }
    path = tmp_path / "deepsomatic_plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")

    rows = discover_attempt_records(path, caller="deepsomatic")

    assert rows[0]["status"] == "complete"
    assert rows[0]["validation_status"] == "PASS"
    assert rows[0]["subject_id"] == "S1"
    assert rows[0]["tumor_sample_id"] == "T1"
    assert rows[0]["reference_id"] == "ref_001"
    assert rows[0]["output_checksum"] == "sha256:abc"


def test_select_source_attempt_latest_validated_excludes_superseded():
    records = [
        {"pair_id": "P1", "attempt_id": "attempt_001", "status": "complete", "validation_status": "PASS", "superseded": True, "path": "a"},
        {"pair_id": "P1", "attempt_id": "attempt_002", "status": "complete", "validation_status": "WARN", "superseded": False, "path": "b"},
        {"pair_id": "P1", "attempt_id": "attempt_003", "status": "failed", "validation_status": "FAIL", "superseded": False, "path": "c"},
    ]

    selected = select_source_attempt(records, pair_id="P1")

    assert selected is not None
    assert selected["attempt_id"] == "attempt_002"


def test_select_source_attempt_rejects_ambiguous_latest_attempt():
    records = [
        {"pair_id": "P1", "attempt_id": "attempt_002", "status": "complete", "validation_status": "PASS", "path": "a"},
        {"pair_id": "P1", "attempt_id": "attempt_002", "status": "complete", "validation_status": "PASS", "path": "b"},
    ]

    with pytest.raises(ValidationError):
        select_source_attempt(records, pair_id="P1")
