"""Optional germline SNV/indel joint-genotyping planning layer."""

from __future__ import annotations

JOINT_STATUS_VALUES = {
    "pending",
    "submitted",
    "queued",
    "running",
    "success",
    "warning",
    "failed",
    "blocked",
    "skipped",
    "interrupted",
    "cancelled",
    "superseded",
    "unknown",
}

JOINT_FAILURE_CATEGORIES = {
    "joint_config_error",
    "joint_manifest_error",
    "incompatible_reference",
    "incompatible_sample_identity",
    "missing_gvcf",
    "invalid_gvcf",
    "stale_gvcf_index",
    "backend_missing",
    "backend_version_error",
    "container_error",
    "scheduler_error",
    "resource_exhaustion",
    "disk_space_error",
    "shard_execution_failure",
    "shard_output_missing",
    "shard_output_invalid",
    "concat_failure",
    "normalization_failure",
    "indexing_failure",
    "qc_failure",
    "interrupted",
    "cancelled",
    "unknown",
}

