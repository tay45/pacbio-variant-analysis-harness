"""Dependency-light validation helpers."""

from __future__ import annotations

import gzip
from pathlib import Path

from variant_analysis_harness.exceptions import ValidationError


def require_readable_file(path: Path, label: str) -> None:
    if not path.exists() or not path.is_file():
        raise ValidationError(f"{label} does not exist: {path}")
    if path.stat().st_size == 0:
        raise ValidationError(f"{label} is zero bytes: {path}")


def validate_xml(path: Path) -> None:
    require_readable_file(path, "dataset XML")
    text = path.read_text(encoding="utf-8", errors="replace").lstrip()
    if not text.startswith("<"):
        raise ValidationError(f"Malformed XML-like file: {path}")


def validate_vcf(path: Path, expected_sample: str | None = None) -> list[str]:
    require_readable_file(path, "VCF")
    warnings: list[str] = []
    opener = gzip.open if path.suffix == ".gz" else open
    has_fileformat = False
    header_samples: list[str] = []
    malformed = 0
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("##fileformat=VCF"):
                has_fileformat = True
            elif line.startswith("#CHROM"):
                parts = line.split("\t")
                if len(parts) > 9:
                    header_samples = parts[9:]
            elif line and not line.startswith("#"):
                if len(line.split("\t")) < 8:
                    malformed += 1
    if not has_fileformat:
        raise ValidationError(f"VCF header is missing fileformat: {path}")
    if malformed:
        raise ValidationError(f"VCF has malformed records: {path}")
    if expected_sample and header_samples and expected_sample not in header_samples:
        raise ValidationError(f"Expected sample {expected_sample!r} not found in VCF header")
    if expected_sample and not header_samples:
        warnings.append("VCF has no sample columns")
    return warnings


def validate_bam_like(path: Path) -> None:
    require_readable_file(path, "BAM")
    if path.suffix.lower() not in {".bam", ".cram"}:
        raise ValidationError(f"Expected BAM/CRAM file: {path}")


def validate_reference_files(reference: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    require_readable_file(Path(reference["fasta"]), "reference FASTA")
    require_readable_file(Path(reference["fai"]), "reference FASTA index")
    if reference.get("sequence_dictionary"):
        require_readable_file(Path(reference["sequence_dictionary"]), "sequence dictionary")
    else:
        warnings.append("sequence_dictionary not configured")
    if reference.get("tandem_repeats_bed"):
        require_readable_file(Path(reference["tandem_repeats_bed"]), "tandem repeat BED")
    else:
        warnings.append("tandem_repeats_bed not configured")
    return warnings
