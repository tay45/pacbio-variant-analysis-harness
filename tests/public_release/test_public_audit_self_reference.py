from __future__ import annotations

from pathlib import Path

from scripts import audit_public_repository as audit


ROOT = Path(__file__).resolve().parents[2]


def _terms() -> list[str]:
    return [pattern["value"] for pattern in audit.PRIVATE_PATTERNS]


def _active_public_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if not path.is_file():
            continue
        if any(part in {".git", "legacy", ".pytest_cache", "__pycache__"} for part in rel.parts):
            continue
        if path.suffix.lower() in {".pyc", ".sif", ".simg"}:
            continue
        files.append(path)
    return files


def test_scanner_reconstructs_intended_terms_at_runtime():
    terms = _terms()
    assert len(terms) >= 10
    assert any(term.startswith("City") and term.endswith("Hope") for term in terms)
    assert any(term.startswith("/net/") for term in terms)
    assert any(term.endswith("=") for term in terms)


def test_no_prohibited_term_appears_contiguously_in_active_public_files():
    offenders = []
    for path in _active_public_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in _terms():
            if term in text:
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_public_audit_artifacts_use_redacted_labels():
    artifact_paths = [
        ROOT / "docs" / "validation" / "evidence" / "public_release" / "PUBLIC_RELEASE_AUDIT.txt",
        ROOT / "docs" / "validation" / "evidence" / "public_release" / "PUBLIC_PACKAGE_AUDIT.txt",
        ROOT / "docs" / "validation" / "evidence" / "public_release" / "PORTABILITY_SCAN.txt",
        ROOT / "docs" / "validation" / "evidence" / "public_release" / "DOCUMENTATION_LINK_AUDIT.txt",
    ]
    for path in artifact_paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in _terms():
            assert term not in text
    assert "[REDACTED]" in (ROOT / "docs" / "validation" / "evidence" / "public_release" / "PUBLIC_RELEASE_AUDIT.txt").read_text(encoding="utf-8", errors="ignore")


def test_scanner_comments_and_docstrings_do_not_leak_terms():
    text = (ROOT / "scripts" / "audit_public_repository.py").read_text(encoding="utf-8")
    header = "\n".join(line for line in text.splitlines() if line.strip().startswith(('"""', "#")))
    for term in _terms():
        assert term not in header


def test_runtime_scanning_detects_generated_contaminated_file(tmp_path):
    contaminated = tmp_path / "repo"
    contaminated.mkdir()
    (contaminated / "bad.txt").write_text("\n".join(_terms()), encoding="utf-8")
    _, findings = audit.audit_privacy(contaminated)
    assert len(findings) == len(_terms())
    for finding in findings:
        assert "[REDACTED]" not in finding
        for term in _terms():
            assert term not in finding


def test_clean_temporary_repository_passes_privacy_scan(tmp_path):
    clean = tmp_path / "repo"
    clean.mkdir()
    (clean / "README.md").write_text("clean public package\n", encoding="utf-8")
    _, findings = audit.audit_privacy(clean)
    assert findings == []


def test_contaminated_temporary_repository_fails_privacy_scan(tmp_path):
    contaminated = tmp_path / "repo"
    contaminated.mkdir()
    (contaminated / "README.md").write_text(_terms()[0], encoding="utf-8")
    _, findings = audit.audit_privacy(contaminated)
    assert findings


def test_legacy_only_placeholder_policy_is_handled(tmp_path):
    repo = tmp_path / "repo"
    legacy = repo / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "README.md").write_text("\n".join(_terms()), encoding="utf-8")
    _, findings = audit.audit_privacy(repo)
    assert findings == []


def test_audit_output_does_not_echo_sensitive_values(tmp_path):
    output = tmp_path / "audit.txt"
    audit.write_report(output, "audit", "FAIL", ["finding: institution-name pattern"])
    text = output.read_text(encoding="utf-8")
    for term in _terms():
        assert term not in text


def test_existing_portability_behavior_is_not_weakened(tmp_path):
    contaminated = tmp_path / "repo"
    contaminated.mkdir()
    (contaminated / "bad.txt").write_text(_terms()[1], encoding="utf-8")
    _, findings = audit.audit_privacy(contaminated)
    assert findings == ["bad.txt: legacy-cluster-name pattern"]
