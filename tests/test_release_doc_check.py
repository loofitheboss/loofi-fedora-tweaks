"""Tests for scripts/check_release_docs.py."""

import importlib.util
import sys
from pathlib import Path


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_release_files(root: Path, *, use_legacy_root_notes: bool = False) -> None:
    (root / "loofi-fedora-tweaks").mkdir(parents=True, exist_ok=True)
    (root / "loofi-fedora-tweaks" / "version.py").write_text('__version__ = "26.0.1"\n', encoding="utf-8")
    (root / "loofi-fedora-tweaks.spec").write_text("Version:        26.0.1\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("## [26.0.1] - 2026-02-11\n", encoding="utf-8")
    (root / "README.md").write_text("Loofi\n", encoding="utf-8")
    notes_root = root if use_legacy_root_notes else root / "docs" / "releases"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "RELEASE-NOTES-v26.0.1.md").write_text("notes\n", encoding="utf-8")


def test_release_doc_check_passes_when_required_files_exist(tmp_path):
    module = _load_module("check_release_docs_test_ok", Path("scripts/check_release_docs.py"))
    _write_release_files(tmp_path)

    module.VERSION_FILE = tmp_path / "loofi-fedora-tweaks" / "version.py"
    module.SPEC_FILE = tmp_path / "loofi-fedora-tweaks.spec"
    module.CHANGELOG_FILE = tmp_path / "CHANGELOG.md"
    module.README_FILE = tmp_path / "README.md"

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert issues == []


def test_release_doc_check_requires_release_notes(tmp_path):
    module = _load_module("check_release_docs_test_missing", Path("scripts/check_release_docs.py"))
    _write_release_files(tmp_path)
    (tmp_path / "docs" / "releases" / "RELEASE-NOTES-v26.0.1.md").unlink()

    module.VERSION_FILE = tmp_path / "loofi-fedora-tweaks" / "version.py"
    module.SPEC_FILE = tmp_path / "loofi-fedora-tweaks.spec"
    module.CHANGELOG_FILE = tmp_path / "CHANGELOG.md"
    module.README_FILE = tmp_path / "README.md"

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert any("missing release notes" in item for item in issues)


def test_release_doc_check_supports_legacy_root_release_notes(tmp_path):
    module = _load_module("check_release_docs_test_legacy_notes", Path("scripts/check_release_docs.py"))
    _write_release_files(tmp_path, use_legacy_root_notes=True)

    module.VERSION_FILE = tmp_path / "loofi-fedora-tweaks" / "version.py"
    module.SPEC_FILE = tmp_path / "loofi-fedora-tweaks.spec"
    module.CHANGELOG_FILE = tmp_path / "CHANGELOG.md"
    module.README_FILE = tmp_path / "README.md"

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert issues == []


def test_release_doc_check_require_logs_flags_missing_artifacts(tmp_path):
    module = _load_module("check_release_docs_test_logs", Path("scripts/check_release_docs.py"))
    _write_release_files(tmp_path)

    module.VERSION_FILE = tmp_path / "loofi-fedora-tweaks" / "version.py"
    module.SPEC_FILE = tmp_path / "loofi-fedora-tweaks.spec"
    module.CHANGELOG_FILE = tmp_path / "CHANGELOG.md"
    module.README_FILE = tmp_path / "README.md"

    issues = module.validate_release_docs(tmp_path, require_logs=True)
    assert any("missing workflow run manifest" in item for item in issues)
