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


def _write_release_files(
    root: Path,
    *,
    use_legacy_root_notes: bool = False,
    include_pyproject: bool = True,
) -> None:
    (root / "loofi-fedora-tweaks").mkdir(parents=True, exist_ok=True)
    (root / "loofi-fedora-tweaks" / "version.py").write_text(
        '__version__ = "26.0.1"\n__version_codename__ = "TestRelease"\n',
        encoding="utf-8",
    )
    (root / "loofi-fedora-tweaks.spec").write_text(
        "Version:        26.0.1\n", encoding="utf-8"
    )
    if include_pyproject:
        (root / "pyproject.toml").write_text(
            '[project]\nname = "test"\nversion = "26.0.1"\n', encoding="utf-8"
        )
    (root / "CHANGELOG.md").write_text("## [26.0.1] - 2026-02-11\n", encoding="utf-8")
    (root / "README.md").write_text("Loofi\n", encoding="utf-8")
    notes_root = root if use_legacy_root_notes else root / "docs" / "releases"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "RELEASE-NOTES-v26.0.1.md").write_text("notes\n", encoding="utf-8")
    # Empty tests dir (no stale tests)
    (root / "tests").mkdir(exist_ok=True)


def _set_module_paths(module, tmp_path: Path) -> None:
    """Point the module's file constants at the tmp_path fixture."""
    module.VERSION_FILE = tmp_path / "loofi-fedora-tweaks" / "version.py"
    module.SPEC_FILE = tmp_path / "loofi-fedora-tweaks.spec"
    module.PYPROJECT_FILE = tmp_path / "pyproject.toml"
    module.CHANGELOG_FILE = tmp_path / "CHANGELOG.md"
    module.README_FILE = tmp_path / "README.md"
    module.TESTS_DIR = tmp_path / "tests"


def test_release_doc_check_passes_when_required_files_exist(tmp_path):
    module = _load_module(
        "check_release_docs_test_ok", Path("scripts/check_release_docs.py")
    )
    _write_release_files(tmp_path)
    _set_module_paths(module, tmp_path)

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert issues == []


def test_release_doc_check_requires_release_notes(tmp_path):
    module = _load_module(
        "check_release_docs_test_missing", Path("scripts/check_release_docs.py")
    )
    _write_release_files(tmp_path)
    (tmp_path / "docs" / "releases" / "RELEASE-NOTES-v26.0.1.md").unlink()
    _set_module_paths(module, tmp_path)

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert any("missing release notes" in item for item in issues)


def test_release_doc_check_supports_legacy_root_release_notes(tmp_path):
    module = _load_module(
        "check_release_docs_test_legacy_notes",
        Path("scripts/check_release_docs.py"),
    )
    _write_release_files(tmp_path, use_legacy_root_notes=True)
    _set_module_paths(module, tmp_path)

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert issues == []


def test_release_doc_check_require_logs_flags_missing_artifacts(tmp_path):
    module = _load_module(
        "check_release_docs_test_logs", Path("scripts/check_release_docs.py")
    )
    _write_release_files(tmp_path)
    _set_module_paths(module, tmp_path)

    issues = module.validate_release_docs(tmp_path, require_logs=True)
    assert any("missing workflow run manifest" in item for item in issues)


def test_release_doc_check_catches_pyproject_version_mismatch(tmp_path):
    """pyproject.toml version != version.py should be flagged."""
    module = _load_module(
        "check_release_docs_test_pyproject",
        Path("scripts/check_release_docs.py"),
    )
    _write_release_files(tmp_path)
    # Desync pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "25.0.0"\n', encoding="utf-8"
    )
    _set_module_paths(module, tmp_path)

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert any("pyproject.toml" in item for item in issues)


def test_release_doc_check_passes_without_pyproject(tmp_path):
    """Missing pyproject.toml should not fail (graceful skip)."""
    module = _load_module(
        "check_release_docs_test_no_pyproject",
        Path("scripts/check_release_docs.py"),
    )
    _write_release_files(tmp_path, include_pyproject=False)
    _set_module_paths(module, tmp_path)

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert issues == []


def test_release_doc_check_catches_hardcoded_version_in_tests(tmp_path):
    """Test files with hardcoded assertEqual(__version__, 'X.Y.Z') should be flagged."""
    module = _load_module(
        "check_release_docs_test_stale",
        Path("scripts/check_release_docs.py"),
    )
    _write_release_files(tmp_path)
    _set_module_paths(module, tmp_path)

    # Create a test file with a hardcoded version assertion
    (tmp_path / "tests" / "test_bad_version.py").write_text(
        'self.assertEqual(__version__, "26.0.1")  # stale!\n',
        encoding="utf-8",
    )

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert any("stale version assertion" in item for item in issues)
    assert any("test_bad_version.py" in item for item in issues)


def test_release_doc_check_catches_hardcoded_codename_in_tests(tmp_path):
    """Test files with hardcoded codename assertions should be flagged."""
    module = _load_module(
        "check_release_docs_test_stale_codename",
        Path("scripts/check_release_docs.py"),
    )
    _write_release_files(tmp_path)
    _set_module_paths(module, tmp_path)

    # Create a test file with a hardcoded codename assertion
    (tmp_path / "tests" / "test_bad_codename.py").write_text(
        'self.assertEqual(__version_codename__, "TestRelease")  # stale!\n',
        encoding="utf-8",
    )

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert any("stale codename assertion" in item for item in issues)
    assert any("test_bad_codename.py" in item for item in issues)


def test_release_doc_check_allows_dynamic_version_tests(tmp_path):
    """Test files that use dynamic version checks should NOT be flagged."""
    module = _load_module(
        "check_release_docs_test_dynamic",
        Path("scripts/check_release_docs.py"),
    )
    _write_release_files(tmp_path)
    _set_module_paths(module, tmp_path)

    # Create test files with dynamic (version-agnostic) assertions
    (tmp_path / "tests" / "test_good_version.py").write_text(
        "self.assertTrue(len(__version__) > 0)\n"
        'parts = __version__.split(".")\n'
        "self.assertEqual(len(parts), 3)\n",
        encoding="utf-8",
    )

    issues = module.validate_release_docs(tmp_path, require_logs=False)
    assert issues == []
