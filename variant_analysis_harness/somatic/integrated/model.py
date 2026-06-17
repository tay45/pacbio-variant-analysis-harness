"""Integrated somatic project and pair models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from variant_analysis_harness import __version__
from variant_analysis_harness.common.signatures import object_signature
from variant_analysis_harness.somatic.integrated import INTEGRATED_SCHEMA_VERSION
from variant_analysis_harness.somatic.manifest import SomaticPair


@dataclass(frozen=True)
class SourceAttemptRef:
    caller: str
    attempt_id: str
    path: Path | None
    status: str = "not_started"
    validation_status: str = "UNKNOWN"
    qc_status: str = "UNKNOWN"
    output_checksum: str | None = None
    command_signature: str | None = None
    caller_version: str | None = None
    failure_category: str | None = None
    superseded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "path": str(self.path) if self.path else None}


@dataclass(frozen=True)
class IntegratedPairRecord:
    pair_id: str
    subject_id: str
    tumor_sample_id: str
    normal_sample_id: str
    analysis_mode: str
    manifest_row_hash: str
    reference_id: str
    reference_signature: str | None = None
    deepsomatic: SourceAttemptRef = field(default_factory=lambda: SourceAttemptRef("deepsomatic", "", None))
    severus: SourceAttemptRef = field(default_factory=lambda: SourceAttemptRef("severus", "", None))
    identity_compatibility: str = "UNKNOWN"
    reference_compatibility: str = "UNKNOWN"
    integrated_status: str = "unknown"
    failure_categories: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_pair(cls, pair: SomaticPair, *, deepsomatic: SourceAttemptRef | None = None, severus: SourceAttemptRef | None = None) -> "IntegratedPairRecord":
        return cls(
            pair_id=pair.pair_id,
            subject_id=pair.subject_id,
            tumor_sample_id=pair.tumor_sample_id,
            normal_sample_id=pair.normal_sample_id,
            analysis_mode=pair.analysis_mode,
            manifest_row_hash=pair.row_hash,
            reference_id=pair.reference_id,
            reference_signature=pair.optional.get("reference_signature") or None,
            deepsomatic=deepsomatic or SourceAttemptRef("deepsomatic", "", None),
            severus=severus or SourceAttemptRef("severus", "", None),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "subject_id": self.subject_id,
            "tumor_sample_id": self.tumor_sample_id,
            "normal_sample_id": self.normal_sample_id,
            "analysis_mode": self.analysis_mode,
            "manifest_row_hash": self.manifest_row_hash,
            "reference_id": self.reference_id,
            "reference_signature": self.reference_signature,
            "deepsomatic": self.deepsomatic.to_dict(),
            "severus": self.severus.to_dict(),
            "identity_compatibility": self.identity_compatibility,
            "reference_compatibility": self.reference_compatibility,
            "integrated_status": self.integrated_status,
            "failure_categories": list(self.failure_categories),
            "warnings": list(self.warnings),
        }


def build_project_model(
    *,
    cfg: dict[str, Any],
    somatic_project_id: str,
    integrated_attempt_id: str,
    selected_pairs: list[SomaticPair],
    excluded_pairs: list[SomaticPair],
    integrated_config: dict[str, Any],
    manifest_path: Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": INTEGRATED_SCHEMA_VERSION,
        "package_version": __version__,
        "root_project_id": cfg.get("project", {}).get("name", ""),
        "somatic_project_id": somatic_project_id,
        "integrated_attempt_id": integrated_attempt_id,
        "source_manifest_signature": object_signature(str(manifest_path)) if manifest_path else None,
        "source_config_signature": object_signature(str(config_path)) if config_path else None,
        "reference_id": cfg.get("reference", {}).get("id"),
        "reference_signature": object_signature(cfg.get("reference", {})),
        "selected_pairs": [p.pair_id for p in selected_pairs],
        "excluded_pairs": [p.pair_id for p in excluded_pairs],
        "integration_policy": integrated_config,
        "partial_success_policy": integrated_config.get("project_policy", {}).get("allow_partial_success", True),
        "warning_inclusion_policy": integrated_config.get("project_policy", {}).get("include_warning_results", False),
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
    }

