"""Preflight validation."""

from __future__ import annotations

from pathlib import Path

from variant_analysis_harness.common.config import tool_config
from variant_analysis_harness.common.reference_validation import validate_reference_bundle
from variant_analysis_harness.common.tool_probe import REQUIRED_TOOL_NAMES, probe_tool, write_probe_results
from variant_analysis_harness.common.reference_validation import write_reference_validation
from variant_analysis_harness.models import Sample


def run_preflight(config: dict, sample: Sample, attempt_dir: Path | None = None) -> dict:
    warnings: list[str] = []
    ref_validation = validate_reference_bundle(config["reference"])
    if attempt_dir:
        write_reference_validation(
            ref_validation,
            attempt_dir / "qc" / "reference_validation.json",
            attempt_dir / "qc" / "reference_validation.md",
        )
    if ref_validation["status"] == "FAIL":
        warnings.append("reference validation failed")
    inputs = [sample.input_path] + list(sample.additional_inputs)
    for path in inputs:
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError(f"Input missing or empty: {path}")
    probes = []
    for tool_name in REQUIRED_TOOL_NAMES:
        try:
            tool = tool_config(config, tool_name)
        except Exception:
            probes.append({"tool": tool_name, "status": "FAIL", "checks": [{"name": "tool_configured", "status": "FAIL"}]})
            continue
        probes.append(probe_tool(tool, checksum=bool(config.get("qc", {}).get("checksum_outputs"))))
    if attempt_dir:
        write_probe_results(probes, attempt_dir / "qc" / "tool_probe.json")
    if any(p["status"] == "FAIL" for p in probes):
        warnings.append("one or more required tool probes failed")
    return {
        "status": "FAIL" if any(p["status"] == "FAIL" for p in probes) or ref_validation["status"] == "FAIL" else ("WARN" if warnings else "PASS"),
        "warnings": warnings,
        "inputs": [str(Path(p)) for p in inputs],
        "reference_validation": ref_validation,
        "tool_probes": probes,
    }
