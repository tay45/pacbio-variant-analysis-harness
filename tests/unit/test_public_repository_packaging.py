from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_readme_has_recruiter_first_sections():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for section in [
        "# PacBio Variant Analysis Harness",
        "Research use only",
        "## Architecture At A Glance",
        "## Quick Start",
        "## Portfolio Highlights",
    ]:
        assert section in text


def test_public_docs_and_metadata_exist():
    for path in [
        "LICENSE",
        "CITATION.cff",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/README.md",
        "docs/validation/claims_audit.md",
        "docs/validation/validation_matrix.md",
        "docs/portfolio/portfolio_overview.md",
        "docs/reference/repository_map.md",
    ]:
        assert (ROOT / path).exists(), path


def test_legacy_public_package_contains_placeholder_only():
    files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "legacy").rglob("*") if path.is_file())
    assert files == ["legacy/README.md"]


def test_no_zip_or_large_sequencing_files_in_repository():
    forbidden_suffixes = {".zip", ".bam", ".bai", ".cram", ".crai", ".sam", ".fastq", ".fq", ".sif", ".img"}
    offenders = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in forbidden_suffixes:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []
