"""Severus somatic structural-variant integration.

Phase 2F provides research-use Severus planning, mocked execution hooks, output
discovery, SV VCF validation, BND validation, and technical QC. It does not
implement CNV or clinical interpretation.
"""

from __future__ import annotations

from variant_analysis_harness.somatic.severus.config import default_severus_config

__all__ = ["default_severus_config"]
