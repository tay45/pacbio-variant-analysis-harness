"""Platform-aware germline SNV/SV analysis harness.

Phase 2G implements PacBio HiFi germline single-sample execution, cohort
orchestration, optional germline SNV/indel joint-genotyping planning,
non-recursive hermetic pytest verification, and a somatic data-model/preflight
foundation with optional DeepSomatic PacBio SNV/indel and Severus somatic SV
planning plus integrated somatic evidence/reporting across validated caller outputs.
"""

__version__ = "0.2.7a1"

RESEARCH_USE_DISCLAIMER = (
    "This workflow is for research use only. It is not a clinically validated, "
    "diagnostic, or treatment-decision system."
)
