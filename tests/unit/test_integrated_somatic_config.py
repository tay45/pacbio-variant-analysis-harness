from __future__ import annotations

from variant_analysis_harness.somatic.integrated.config import default_integrated_config, resolve_integrated_config, validate_integrated_config


def test_integrated_config_defaults_disabled_and_valid():
    cfg = default_integrated_config()
    assert cfg["enabled"] is False
    assert validate_integrated_config(cfg)["status"] == "PASS"


def test_integrated_config_policies_and_windows():
    cfg = resolve_integrated_config({"integrated": {"project_policy": {"allow_partial_success": False, "required_stages": {"small_variants": "required", "structural_variants": "optional"}}}})
    assert cfg["project_policy"]["allow_partial_success"] is False
    assert validate_integrated_config(cfg)["status"] == "PASS"
    cfg["project_policy"]["required_stages"]["small_variants"] = "maybe"
    assert validate_integrated_config(cfg)["status"] == "FAIL"
    cfg = default_integrated_config()
    cfg["relationship_analysis"]["window_bp"] = -1
    assert validate_integrated_config(cfg)["status"] == "FAIL"

