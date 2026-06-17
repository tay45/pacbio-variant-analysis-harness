"""Cohort orchestration helpers for research-use germline workflows."""

from __future__ import annotations

COHORT_STATUS_VALUES = {
    "pending",
    "submitted",
    "queued",
    "running",
    "success",
    "warning",
    "failed",
    "blocked",
    "skipped",
    "excluded",
    "interrupted",
    "cancelled",
    "unknown",
}

