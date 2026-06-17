"""DeepSomatic PacBio HiFi small-variant integration.

Phase 2E provides research-use command construction, optional execution,
validation, and QC for DeepSomatic. It does not implement somatic SV, CNV, or
clinical interpretation.
"""

from __future__ import annotations

from variant_analysis_harness.somatic.deepsomatic.config import default_deepsomatic_config

__all__ = ["default_deepsomatic_config"]
