from __future__ import annotations

import hashlib
import json

from variant_analysis_harness.somatic.deepsomatic.compatibility import SemanticVersion, validate_model_type, validate_version_policy
from variant_analysis_harness.somatic.deepsomatic.config import default_deepsomatic_config, validate_deepsomatic_config, validate_model_metadata


def test_valid_tumor_normal_and_tumor_only_config():
    cfg = default_deepsomatic_config()
    assert validate_deepsomatic_config(cfg, mode="tumor_normal")["status"] in {"PASS", "WARN"}
    assert validate_deepsomatic_config(cfg, mode="tumor_only")["status"] in {"PASS", "WARN"}


def test_unsupported_backend_model_and_malformed_version():
    cfg = default_deepsomatic_config()
    cfg["backend"] = "other"
    cfg["deepsomatic"]["version"] = "bad"
    cfg["deepsomatic"]["model_type"]["tumor_normal"] = "WGS"
    result = validate_deepsomatic_config(cfg, mode="tumor_normal")
    assert result["status"] == "FAIL"
    assert result["errors"]


def test_version_mismatch_and_unknown_future_version_policy():
    assert SemanticVersion.parse("1.10.0").release_family == "1.10"
    strict = validate_version_policy("9.0.0")
    assert strict["status"] == "FAIL"
    warn = validate_version_policy("9.0.0", unknown_version_policy="warn")
    assert warn["status"] == "WARN"
    mismatch = validate_version_policy("1.10.0", detected_version="1.9.0")
    assert mismatch["status"] == "FAIL"


def test_model_mode_compatibility():
    assert validate_model_type("tumor_normal", "PACBIO")["status"] == "PASS"
    assert validate_model_type("tumor_only", "PACBIO_TUMOR_ONLY")["status"] == "PASS"
    assert validate_model_type("tumor_only", "PACBIO")["status"] == "FAIL"


def test_protected_extra_arg_conflict():
    cfg = default_deepsomatic_config()
    cfg["deepsomatic"]["advanced"]["extra_args"] = ["--ref=/tmp/other.fa"]
    result = validate_deepsomatic_config(cfg, mode="tumor_normal")
    assert result["status"] == "FAIL"
    assert "protected" in " ".join(result["errors"])


def test_model_metadata_validation(tmp_path):
    model = tmp_path / "model.ckpt"
    model.write_text("model\n", encoding="utf-8")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    info = tmp_path / "model.example_info.json"
    info.write_text(json.dumps({"technology": "pacbio_hifi", "analysis_mode": "tumor_normal", "model_type": "PACBIO", "model_files": [{"path": "model.ckpt", "sha256": digest}]}), encoding="utf-8")
    cfg = default_deepsomatic_config()["deepsomatic"]
    cfg["model"]["example_info_path"] = str(info)
    result = validate_model_metadata(cfg, version_policy={"example_info_required": True}, mode="tumor_normal", model_type="PACBIO")
    assert result["status"] == "PASS"
    assert result["metadata_checksum"]
    cfg["model"]["example_info_path"] = str(tmp_path / "missing.json")
    assert validate_model_metadata(cfg, version_policy={"example_info_required": True}, mode="tumor_normal", model_type="PACBIO")["status"] == "FAIL"
