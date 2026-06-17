"""Structured failure categories for cohort reporting."""

from __future__ import annotations

FAILURE_CATEGORIES = {
    "configuration_error",
    "manifest_error",
    "missing_input",
    "reference_error",
    "tool_missing",
    "tool_version_error",
    "container_error",
    "scheduler_error",
    "resource_exhaustion",
    "disk_space_error",
    "input_validation_error",
    "alignment_failure",
    "snv_calling_failure",
    "sv_discover_failure",
    "sv_calling_failure",
    "qc_failure",
    "output_validation_failure",
    "interrupted",
    "cancelled",
    "unknown",
}

TROUBLESHOOTING_ACTIONS = {
    "configuration_error": "Review resolved configuration and schema validation messages.",
    "manifest_error": "Review the cohort manifest row and line-numbered validation error.",
    "missing_input": "Confirm the input path exists and is readable from the execution node.",
    "reference_error": "Confirm the reference FASTA, indexes, and contigs match the inputs.",
    "tool_missing": "Confirm the executable or container is available in the selected backend.",
    "tool_version_error": "Review configured and observed tool versions.",
    "container_error": "Confirm container path, digest, and runtime permissions.",
    "scheduler_error": "Review scheduler submission output and Slurm state.",
    "resource_exhaustion": "Review Slurm accounting, memory, disk, and walltime evidence.",
    "disk_space_error": "Check output and scratch filesystem capacity.",
    "input_validation_error": "Review BAM/XML integrity and index validation output.",
    "alignment_failure": "Review pbmm2 logs and aligned BAM validation output.",
    "snv_calling_failure": "Review DeepVariant logs and VCF validation output.",
    "sv_discover_failure": "Review pbsv discover logs and svsig validation output.",
    "sv_calling_failure": "Review pbsv call logs and SV VCF validation output.",
    "qc_failure": "Review QC threshold settings and generated QC metrics.",
    "output_validation_failure": "Review malformed, empty, truncated, or missing declared outputs.",
    "interrupted": "Review scheduler and operator interruption records.",
    "cancelled": "Review scheduler cancellation records.",
    "unknown": "Review raw stdout/stderr and status metadata; classification was uncertain.",
}


def classify_failure(stage: str | None, exit_code: int | None = None, slurm_state: str | None = None) -> str:
    """Return a conservative category without hiding the original error."""
    state = (slurm_state or "").upper()
    if state in {"CANCELLED", "CA", "TIMEOUT"}:
        return "cancelled" if state.startswith("CANCEL") or state == "CA" else "resource_exhaustion"
    if state in {"OUT_OF_MEMORY", "OOM"}:
        return "resource_exhaustion"
    if exit_code is None:
        return "unknown"
    if stage == "alignment":
        return "alignment_failure"
    if stage == "germline_snv":
        return "snv_calling_failure"
    if stage == "germline_sv_discover":
        return "sv_discover_failure"
    if stage == "germline_sv_call":
        return "sv_calling_failure"
    if stage and stage.endswith("_qc"):
        return "qc_failure"
    if exit_code != 0:
        return "unknown"
    return "unknown"

