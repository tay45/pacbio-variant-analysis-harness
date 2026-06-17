from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOT_FILES = {
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "CHANGELOG.md",
    "RELEASE_NOTES.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
    "Makefile",
    ".gitignore",
    ".gitattributes",
    ".pre-commit-config.yaml",
}

REQUIRED_ROOT_DIRS = {
    ".github",
    "configs",
    "contracts",
    "docs",
    "examples",
    "legacy",
    "schemas",
    "scripts",
    "tests",
    "variant_analysis_harness",
}


def test_only_high_signal_files_remain_in_root():
    files = {path.name for path in ROOT.iterdir() if path.is_file()}
    assert files <= ALLOWED_ROOT_FILES
    assert ALLOWED_ROOT_FILES <= files


def test_phase_and_test_artifacts_are_not_in_root():
    offenders = [path.name for path in ROOT.iterdir() if path.is_file() and path.name.startswith(("PHASE_", "TEST_", "PYTEST_", "PUBLIC_", "DOCUMENTATION_LINK_"))]
    assert offenders == []


def test_github_setup_docs_moved_under_operations():
    assert (ROOT / "docs" / "operations" / "github" / "README.md").exists()
    assert (ROOT / "docs" / "operations" / "github" / "publishing_instructions.md").exists()
    assert (ROOT / "docs" / "operations" / "github" / "repository_settings.md").exists()


def test_validation_artifacts_are_under_docs_evidence():
    evidence = ROOT / "docs" / "validation" / "evidence"
    assert (evidence / "README.md").exists()
    assert (evidence / "test_summaries" / "TEST_RESULTS.txt").exists()
    assert (evidence / "public_release" / "PUBLIC_PACKAGE_AUDIT.txt").exists()
    assert (evidence / "scale_tests" / "SCALE_TEST_RESULTS.txt").exists()


def test_packaging_history_is_under_development_history():
    packaging = ROOT / "docs" / "development_history" / "packaging"
    assert (packaging / "README.md").exists()
    assert (packaging / "PHASE_3A1_REPOSITORY_PRESENTATION_CLEANUP_PLAN.md").exists()


def test_core_root_assets_and_source_directories_remain():
    assert (ROOT / "README.md").exists()
    assert (ROOT / "LICENSE").exists()
    assert (ROOT / "CITATION.cff").exists()
    dirs = {path.name for path in ROOT.iterdir() if path.is_dir() and path.name != ".git"}
    assert REQUIRED_ROOT_DIRS <= dirs
    assert (ROOT / "variant_analysis_harness").is_dir()


def test_no_required_evidence_was_deleted():
    required = [
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
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []
