"""Sample manifest parsing and validation."""

from __future__ import annotations

import csv
from pathlib import Path

from variant_analysis_harness.exceptions import ManifestError
from variant_analysis_harness.models import Sample
from variant_analysis_harness.common.paths import resolve_path, safe_name
from variant_analysis_harness.common.schema_validation import validate_manifest_row_schema

SUPPORTED_PLATFORMS = {"pacbio_hifi"}
SUPPORTED_INPUT_TYPES = {
    "aligned_bam",
    "unaligned_bam",
    "pacbio_dataset_xml",
    "pacbio_dataset_xml_list",
}
REQUIRED_COLUMNS = {
    "sample_id",
    "platform",
    "input_type",
    "input_path",
    "additional_inputs",
    "aligned",
    "reference_id",
    "read_group_sample",
    "output_prefix",
}


def load_manifest(path: Path, require_existing: bool = True) -> list[Sample]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ManifestError("Manifest is missing a header")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ManifestError(f"Manifest missing required columns: {sorted(missing)}")
        rows = list(reader)
        for row in rows:
            validate_manifest_row_schema(row)
        samples = [_row_to_sample(row, path.parent.resolve(), require_existing) for row in rows]
    _validate_unique(samples)
    return samples


def select_sample(samples: list[Sample], sample_id: str | None) -> Sample:
    if sample_id is None:
        if len(samples) != 1:
            raise ManifestError("--sample is required when manifest has multiple rows")
        return samples[0]
    for sample in samples:
        if sample.sample_id == sample_id:
            return sample
    raise ManifestError(f"Sample not found in manifest: {sample_id}")


def _row_to_sample(row: dict[str, str], base_dir: Path, require_existing: bool) -> Sample:
    try:
        sample_id = safe_name(row.get("sample_id", ""), "sample_id")
    except ValueError as exc:
        raise ManifestError(str(exc)) from exc
    platform = row.get("platform", "")
    if platform not in SUPPORTED_PLATFORMS:
        raise ManifestError(f"Unsupported platform for {sample_id}: {platform}")
    input_type = row.get("input_type", "")
    if input_type not in SUPPORTED_INPUT_TYPES:
        raise ManifestError(f"Unsupported input_type for {sample_id}: {input_type}")
    aligned = _parse_bool(row.get("aligned", ""), "aligned")
    if input_type == "aligned_bam" and not aligned:
        raise ManifestError(f"{sample_id}: input_type aligned_bam requires aligned=true")
    if input_type != "aligned_bam" and aligned:
        raise ManifestError(f"{sample_id}: only aligned_bam may set aligned=true")
    input_path = resolve_path(row.get("input_path", ""), base_dir)
    if input_path is None:
        raise ManifestError(f"{sample_id}: input_path is required")
    additional_inputs = tuple(
        p
        for p in (
            resolve_path(value.strip(), base_dir)
            for value in row.get("additional_inputs", "").split(",")
            if value.strip()
        )
        if p is not None
    )
    if input_type == "pacbio_dataset_xml_list" and not additional_inputs:
        raise ManifestError(f"{sample_id}: multiple XML input requires additional_inputs")
    paths = (input_path,) + additional_inputs
    if len(set(paths)) != len(paths):
        raise ManifestError(f"{sample_id}: duplicate input path detected")
    if require_existing:
        for path in paths:
            if not path.exists() or not path.is_file():
                raise ManifestError(f"{sample_id}: input does not exist: {path}")
    output_prefix = row.get("output_prefix") or sample_id
    try:
        output_prefix = safe_name(output_prefix, "output_prefix")
    except ValueError as exc:
        raise ManifestError(str(exc)) from exc
    read_group_sample = row.get("read_group_sample") or sample_id
    try:
        read_group_sample = safe_name(read_group_sample, "read_group_sample")
    except ValueError as exc:
        raise ManifestError(str(exc)) from exc
    return Sample(
        sample_id=sample_id,
        platform=platform,
        input_type=input_type,
        input_path=input_path,
        additional_inputs=additional_inputs,
        aligned=aligned,
        reference_id=row.get("reference_id", ""),
        read_group_sample=read_group_sample,
        output_prefix=output_prefix,
    )


def _parse_bool(value: str, label: str) -> bool:
    lower = str(value).strip().lower()
    if lower in {"true", "1", "yes"}:
        return True
    if lower in {"false", "0", "no"}:
        return False
    raise ManifestError(f"Malformed boolean for {label}: {value!r}")


def _validate_unique(samples: list[Sample]) -> None:
    sample_ids = [s.sample_id for s in samples]
    prefixes = [s.output_prefix for s in samples]
    if len(sample_ids) != len(set(sample_ids)):
        raise ManifestError("Duplicate sample_id in manifest")
    if len(prefixes) != len(set(prefixes)):
        raise ManifestError("Duplicate output_prefix in manifest")
