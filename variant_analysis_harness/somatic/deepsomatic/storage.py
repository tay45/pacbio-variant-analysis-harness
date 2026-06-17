"""Planning-only DeepSomatic storage and scratch estimates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from variant_analysis_harness.somatic.manifest import SomaticPair


def estimate_deepsomatic_storage(pair: SomaticPair, *, preserve_intermediate: bool = False) -> dict[str, Any]:
    input_paths = [pair.tumor_input_path]
    if pair.normal_input_path:
        input_paths.append(pair.normal_input_path)
    known_input_bytes = sum(path.stat().st_size for path in input_paths if path.exists())
    multiplier = 4 if preserve_intermediate else 2
    return {
        "pair_id": pair.pair_id,
        "known_input_bytes": known_input_bytes,
        "estimated_output_bytes": max(1_000_000, known_input_bytes // 20),
        "estimated_peak_scratch_bytes": max(2_000_000, known_input_bytes * multiplier),
        "estimate_type": "planning_approximation",
        "inputs_never_deleted": True,
    }
