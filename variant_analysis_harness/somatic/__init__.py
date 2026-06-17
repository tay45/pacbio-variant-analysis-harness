"""Somatic data model and preflight foundation.

Phase 2D intentionally models and validates somatic studies without executing
somatic variant callers.
"""

from __future__ import annotations

from variant_analysis_harness.somatic.failures import SOMATIC_FAILURE_CATEGORIES

__all__ = ["SOMATIC_FAILURE_CATEGORIES"]
