#!/usr/bin/env python3
"""Audit public repository packaging, privacy, links, and version consistency."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.7a1"
TAG = "v0.2.7-alpha.1"
PUBLIC_TITLE = "PacBio Variant Analysis Harness"
PUBLIC_OWNER = "Tay45"
PUBLIC_REPOSITORY = "pacbio-variant-analysis-harness"
PUBLIC_URL = "https://github.com/Tay45/pacbio-variant-analysis-harness"
PUBLIC_CLONE_URL = "https://github.com/Tay45/pacbio-variant-analysis-harness.git"
OBSOLETE_IDENTITY_PATTERNS = [
    "n2" + "n",
    "n2" + "n-variant-analysis-harness",
    "n2" + "ngenomics",
]
REQUIRED_ROOT = {
    "README.md", "LICENSE", "CITATION.cff", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
    "SECURITY.md", "CHANGELOG.md", "RELEASE_NOTES.md", "ROADMAP.md", "pyproject.toml",
    ".gitignore", ".gitattributes", ".pre-commit-config.yaml", "Makefile",
    "THIRD_PARTY_NOTICES.md",
}
REQUIRED_DIRS = {
    ".github", "configs", "contracts", "docs", "examples", "schemas", "scripts",
    "tests", "variant_analysis_harness", "legacy",
}
FORBIDDEN_DIRS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "work", "outputs"}
FORBIDDEN_SUFFIXES = {".bam", ".bai", ".cram", ".crai", ".sam", ".fastq", ".fq", ".sif", ".img", ".zip", ".tar", ".gz"}
PRIVATE_PATTERNS = [
    {"label": "institution-name pattern", "value": "City" + " of " + "Hope"},
    {"label": "legacy-cluster-name pattern", "value": "Apo" + "llo"},
    {"label": "internal-host pattern", "value": "coh" + "." + "org"},
    {"label": "internal-path pattern A", "value": "/" + "net" + "/" + "isi-dcnl"},
    {"label": "internal-path pattern B", "value": "/" + "opt" + "/" + "singularity-images"},
    {"label": "private-key marker", "value": "BEGIN" + " PRIVATE " + "KEY"},
    {"label": "cloud-secret marker", "value": "AWS" + "_" + "SECRET"},
    {"label": "api-key marker", "value": "api" + "_" + "key"},
    {"label": "token marker", "value": "token" + "="},
    {"label": "password marker", "value": "password" + "="},
    {"label": "local-home-path pattern", "value": "/" + "Users" + "/" + "thkang"},
    {"label": "local-project-path pattern", "value": "Desktop" + "/" + "SNV_SV"},
]
REQUIRED_DOCS = [
    "docs/README.md", "docs/getting_started/quick_start.md", "docs/architecture/system_architecture.md",
    "docs/reference/repository_map.md", "docs/portfolio/portfolio_overview.md",
    "docs/portfolio/sample_reports.md", "docs/validation/claims_audit.md",
    "docs/validation/validation_matrix.md", "docs/development_history/README.md",
    "docs/validation/evidence/README.md", "docs/development_history/packaging/README.md",
    "docs/operations/github/README.md", "docs/operations/github/publishing_instructions.md",
    "docs/operations/github/repository_settings.md",
]
REQUIRED_EVIDENCE = [
    "docs/validation/evidence/test_summaries/TEST_RESULTS.txt",
    "docs/validation/evidence/test_summaries/TEST_DURATION_REPORT.txt",
    "docs/validation/evidence/test_summaries/PYTEST_EXIT_VERIFICATION.txt",
    "docs/validation/evidence/test_summaries/PYTEST_FULL_EXIT_VERIFICATION.txt",
    "docs/validation/evidence/test_summaries/PYTEST_RESOLUTION_CHECK.txt",
    "docs/validation/evidence/public_release/NETWORK_ISOLATION_TEST.txt",
    "docs/validation/evidence/public_release/PORTABILITY_SCAN.txt",
    "docs/validation/evidence/public_release/PUBLIC_RELEASE_AUDIT.txt",
    "docs/validation/evidence/public_release/PUBLIC_PACKAGE_AUDIT.txt",
    "docs/validation/evidence/public_release/DOCUMENTATION_LINK_AUDIT.txt",
    "docs/validation/evidence/public_release/REVIEW_MANIFEST.txt",
]
ROOT_ARTIFACT_PREFIXES = ("PHASE_", "TEST_", "PYTEST_", "PUBLIC_", "DOCUMENTATION_LINK_", "NETWORK_ISOLATION", "PORTABILITY_SCAN", "REVIEW_MANIFEST", "SCALE_TEST", "JOINT_SCALE")

def iter_files(root: Path = ROOT):
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in FORBIDDEN_DIRS for part in rel.parts):
            continue
        if path.is_file():
            yield path

def audit_links(root: Path = ROOT) -> tuple[list[str], list[str]]:
    checked, broken = [], []
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in iter_files(root):
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in link_re.finditer(text):
            link = match.group(1).split("#", 1)[0]
            if not link or re.match(r"^[a-z]+://", link) or link.startswith("mailto:"):
                continue
            checked.append(f"{path.relative_to(root)} -> {link}")
            target = (path.parent / link).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                broken.append(f"{path.relative_to(root)}: escapes repository: {link}")
                continue
            if not target.exists():
                broken.append(f"{path.relative_to(root)}: missing {link}")
    return checked, broken

def audit_privacy(root: Path = ROOT) -> tuple[list[str], list[str]]:
    checked, findings = [], []
    for path in iter_files(root):
        if path.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg"}:
            continue
        rel = path.relative_to(root).as_posix()
        checked.append(rel)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if rel.startswith("legacy/") and path.name == "README.md":
            continue
        for pattern in PRIVATE_PATTERNS:
            if pattern["value"].lower() in text.lower():
                findings.append(f"{rel}: {pattern['label']}")
    return checked, findings

def audit_package(root: Path = ROOT) -> list[str]:
    errors = []
    root_names = {p.name for p in root.iterdir()}
    missing_root = sorted(REQUIRED_ROOT - root_names)
    missing_dirs = sorted(d for d in REQUIRED_DIRS if not (root / d).is_dir())
    errors.extend(f"missing root file: {item}" for item in missing_root)
    errors.extend(f"missing root directory: {item}" for item in missing_dirs)
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in FORBIDDEN_DIRS for part in rel.parts):
            errors.append(f"forbidden directory entry: {rel}")
        if path.is_file() and (path.name == ".DS_Store" or path.suffix.lower() in FORBIDDEN_SUFFIXES):
            errors.append(f"forbidden file entry: {rel}")
    for doc in REQUIRED_DOCS:
        if not (root / doc).exists():
            errors.append(f"missing required doc: {doc}")
    for evidence in REQUIRED_EVIDENCE:
        if not (root / evidence).exists():
            errors.append(f"missing validation evidence: {evidence}")
    for item in root.iterdir():
        if item.is_file() and item.name.startswith(ROOT_ARTIFACT_PREFIXES):
            errors.append(f"root-level evidence or phase artifact: {item.name}")
    version_text = (root / "pyproject.toml").read_text(encoding="utf-8") + "\n" + (root / "variant_analysis_harness" / "__init__.py").read_text(encoding="utf-8")
    if VERSION not in version_text:
        errors.append("package code version mismatch")
    for file_name in ("CITATION.cff", "RELEASE_NOTES.md", "CHANGELOG.md", "docs/operations/github/repository_settings.md", "docs/operations/github/publishing_instructions.md"):
        if TAG not in (root / file_name).read_text(encoding="utf-8"):
            errors.append(f"release tag missing from {file_name}")
    readme = (root / "README.md").read_text(encoding="utf-8")
    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    settings = (root / "docs/operations/github/repository_settings.md").read_text(encoding="utf-8")
    publishing = (root / "docs/operations/github/publishing_instructions.md").read_text(encoding="utf-8")
    if not readme.startswith(f"# {PUBLIC_TITLE}"):
        errors.append("README title mismatch")
    if "Illumina and Oxford Nanopore workflows are not implemented or validated in this release." not in readme:
        errors.append("README PacBio-focus limitation missing")
    if PUBLIC_URL not in citation:
        errors.append("citation repository URL mismatch")
    if f'title: "{PUBLIC_TITLE}"' not in citation:
        errors.append("citation title mismatch")
    if PUBLIC_REPOSITORY not in settings or PUBLIC_OWNER not in settings:
        errors.append("GitHub settings repository identity mismatch")
    if PUBLIC_CLONE_URL not in publishing:
        errors.append("publishing clone URL mismatch")
    if "git status" not in publishing:
        errors.append("publishing instructions missing git status")
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith("legacy/"):
            continue
        if path.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if "variant_analysis_harness" in rel:
            pass
        for pattern in OBSOLETE_IDENTITY_PATTERNS:
            if pattern.lower() in text:
                errors.append(f"obsolete public identity in {rel}")
                break
    legacy_files = sorted(p.relative_to(root).as_posix() for p in (root / "legacy").rglob("*") if p.is_file())
    if legacy_files != ["legacy/README.md"]:
        errors.append(f"unsafe legacy contents: {legacy_files}")
    return errors

def write_report(path: Path, title: str, status: str, lines: list[str]) -> None:
    path.write_text("\n".join([title, f"status={status}", "", *lines]) + "\n", encoding="utf-8")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--links-only", action="store_true")
    parser.add_argument("--privacy-only", action="store_true")
    args = parser.parse_args(argv)

    checked_links, broken_links = audit_links()
    checked_privacy, privacy_findings = audit_privacy()
    package_errors = audit_package()

    evidence_dir = ROOT / "docs" / "validation" / "evidence"
    public_dir = evidence_dir / "public_release"
    public_dir.mkdir(parents=True, exist_ok=True)
    write_report(public_dir / "DOCUMENTATION_LINK_AUDIT.txt", "Documentation link audit", "PASS" if not broken_links else "FAIL", [
        f"files_checked={sum(1 for p in iter_files() if p.suffix.lower() == '.md')}",
        f"links_checked={len(checked_links)}",
        "## Broken links",
        *(broken_links or ["None"]),
    ])
    write_report(public_dir / "PUBLIC_RELEASE_AUDIT.txt", "Public release privacy and IP audit", "PASS" if not privacy_findings else "FAIL", [
        f"files_checked={len(checked_privacy)}",
        "scan_categories=" + ", ".join(pattern["label"] + ": [REDACTED]" for pattern in PRIVATE_PATTERNS),
        "actions=Excluded institution-specific legacy code; retained legacy placeholder only.",
        "exclusions=Generated work/output folders, caches, prior archives, sequencing/reference/container data.",
        "unresolved_items=None" if not privacy_findings else "unresolved_items=Review findings below.",
        "## Findings",
        *(privacy_findings or ["None"]),
    ])
    write_report(public_dir / "PUBLIC_PACKAGE_AUDIT.txt", "Public package audit", "PASS" if not package_errors and not broken_links and not privacy_findings else "FAIL", [
        f"required_root_files={len(REQUIRED_ROOT)}",
        f"required_directories={len(REQUIRED_DIRS)}",
        f"version={VERSION}",
        f"release_tag={TAG}",
        f"display_title={PUBLIC_TITLE}",
        f"repository_owner={PUBLIC_OWNER}",
        f"repository_name={PUBLIC_REPOSITORY}",
        f"repository_url={PUBLIC_URL}",
        f"clone_url={PUBLIC_CLONE_URL}",
        "obsolete_identity_matches=0" if not any("obsolete public identity" in error for error in package_errors) else "obsolete_identity_matches=REVIEW",
        "## Errors",
        *(package_errors or ["None"]),
    ])
    if args.links_only:
        return 0 if not broken_links else 1
    if args.privacy_only:
        return 0 if not privacy_findings else 1
    return 0 if not package_errors and not broken_links and not privacy_findings else 1

if __name__ == "__main__":
    raise SystemExit(main())
