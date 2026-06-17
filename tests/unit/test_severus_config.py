from __future__ import annotations

from variant_analysis_harness.somatic.severus.config import default_severus_config, resolve_severus_config, validate_severus_config


def test_default_severus_config_resolves_disabled():
    cfg = resolve_severus_config({})
    assert cfg["enabled"] is False
    assert cfg["backend"] == "severus"
    assert validate_severus_config(cfg, mode="tumor_normal")["status"] == "PASS"


def test_unsupported_backend_and_malformed_version_fail():
    cfg = default_severus_config()
    cfg["backend"] = "pbsv"
    cfg["severus"]["requested_version"] = "not-a-version"
    result = validate_severus_config(cfg, mode="tumor_normal")
    assert result["status"] == "FAIL"
    assert any("backend" in error for error in result["errors"])
    assert any("Malformed" in error for error in result["errors"])


def test_version_mismatch_and_unknown_version_policy():
    cfg = default_severus_config()
    mismatch = validate_severus_config(cfg, mode="tumor_normal", detected_version="1.1.0")
    assert mismatch["status"] == "FAIL"
    cfg["severus"]["requested_version"] = "9.9.9"
    assert validate_severus_config(cfg, mode="tumor_normal")["status"] == "FAIL"
    cfg["severus"]["unknown_version_policy"] = "warn"
    assert validate_severus_config(cfg, mode="tumor_normal")["status"] == "WARN"


def test_execution_and_extra_arg_validation():
    cfg = default_severus_config()
    cfg["severus"]["execution"]["mode"] = "executable"
    assert validate_severus_config(cfg, mode="tumor_normal")["status"] == "FAIL"
    cfg["severus"]["executable"]["path"] = "/usr/local/bin/severus"
    assert validate_severus_config(cfg, mode="tumor_normal")["status"] == "PASS"
    cfg["severus"]["parameters"]["extra_args"] = ["--tumor-bam=wrong.bam"]
    assert validate_severus_config(cfg, mode="tumor_normal")["status"] == "FAIL"


def test_tumor_only_mode_is_unsupported_by_default():
    result = validate_severus_config(default_severus_config(), mode="tumor_only")
    assert result["status"] == "WARN"
    assert any("tumor-only" in warning for warning in result["warnings"])
