from __future__ import annotations

from pathlib import Path
import shutil

from scripts import audit_public_repository as audit


ROOT = Path(__file__).resolve().parents[2]
TITLE = "PacBio Variant Analysis Harness"
OWNER = "Tay45"
REPO = "pacbio-variant-analysis-harness"
URL = "https://github.com/Tay45/pacbio-variant-analysis-harness"
CLONE_URL = "https://github.com/Tay45/pacbio-variant-analysis-harness.git"
TAG = "v0.2.7-alpha.1"


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _active_public_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if not path.is_file():
            continue
        if any(part in {"legacy", ".pytest_cache", "__pycache__"} for part in rel.parts):
            continue
        if path.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg"}:
            continue
        files.append(path)
    return files


def test_readme_title_and_repository_url():
    readme = _text("README.md")
    assert readme.startswith(f"# {TITLE}")
    assert URL in readme or REPO in readme
    assert "Illumina and Oxford Nanopore workflows are not implemented or validated in this release." in readme


def test_clone_url_is_correct():
    assert CLONE_URL in _text("GITHUB_PUBLISHING_INSTRUCTIONS.md")


def test_citation_identity_is_correct():
    citation = _text("CITATION.cff")
    assert f'title: "{TITLE}"' in citation
    assert f'repository-code: "{URL}"' in citation
    assert 'version: "0.2.7-alpha.1"' in citation


def test_github_settings_identity_is_correct():
    settings = _text("GITHUB_REPOSITORY_SETTINGS.md")
    assert OWNER in settings
    assert REPO in settings
    assert "Research-use PacBio variant-analysis orchestration" in settings


def test_publishing_instructions_use_correct_remote():
    instructions = _text("GITHUB_PUBLISHING_INSTRUCTIONS.md")
    assert f"git remote add origin {CLONE_URL}" in instructions
    assert "git status" in instructions


def test_no_active_public_file_contains_obsolete_slug_or_owner():
    for path in _active_public_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "n2" + "n-variant-analysis-harness" not in text, path
        assert "n2" + "ngenomics" not in text, path


def test_no_active_public_branding_contains_standalone_obsolete_prefix():
    for path in _active_public_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "n2" + "n" not in text, path


def test_internal_python_package_remains_variant_analysis_harness():
    assert (ROOT / "variant_analysis_harness").is_dir()
    assert "variant_analysis_harness" in _text("pyproject.toml")


def test_cli_examples_keep_internal_module_path():
    assert "python -m variant_analysis_harness.cli --help" in _text("README.md")


def test_package_top_level_directory_constant_is_correct():
    assert REPO == "pacbio-variant-analysis-harness"


def test_release_version_and_tag_remain_consistent():
    assert audit.VERSION == "0.2.7a1"
    assert audit.TAG == TAG
    assert TAG in _text("RELEASE_NOTES.md")


def test_public_audit_checks_repository_identity():
    for path in sorted(ROOT.rglob("__pycache__"), reverse=True):
        if path.is_dir():
            shutil.rmtree(path)
    cache = ROOT / ".pytest_cache"
    if cache.exists():
        shutil.rmtree(cache)
    assert audit.audit_package(ROOT) == []
