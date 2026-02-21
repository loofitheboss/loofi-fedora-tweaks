#!/usr/bin/env python3
"""Validate release documentation, version sync, and optional workflow artifacts.

CI gate: runs as the ``docs_gate`` job in auto-release.yml.
Checks performed:
  1. version.py == .spec == pyproject.toml  (version sync)
  2. CHANGELOG.md has entry for current version
  3. README.md exists and is non-empty
  4. docs/releases/RELEASE-NOTES-vX.Y.Z.md exists and is non-empty
  5. (optional --require-logs) workflow test-results and run-manifest present
  6. No test files contain hardcoded version/codename assertions (stale test check)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "loofi-fedora-tweaks" / "version.py"
SPEC_FILE = ROOT / "loofi-fedora-tweaks.spec"
PYPROJECT_FILE = ROOT / "pyproject.toml"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
README_FILE = ROOT / "README.md"
TESTS_DIR = ROOT / "tests"

VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
SPEC_VERSION_RE = re.compile(r"^Version:\s*(\S+)", re.MULTILINE)
PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)

# Matches assertEqual-style assertions containing a literal X.Y.Z string.
_HARDCODED_VERSION_RE = re.compile(
    r"""(?:assertEqual|assertIn|assert\s).*["']\d+\.\d+\.\d+["']"""
)
# Matches assertEqual with __version_codename__ and a capitalized word literal.
_HARDCODED_CODENAME_RE = re.compile(
    r"""assertEqual.*__version_codename__.*["'][A-Z]\w+["']"""
)


def extract_version() -> str:
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = VERSION_RE.search(content)
    if not match:
        raise RuntimeError("Unable to parse __version__ from version.py")
    return match.group(1)


def extract_spec_version() -> str:
    content = SPEC_FILE.read_text(encoding="utf-8")
    match = SPEC_VERSION_RE.search(content)
    if not match:
        raise RuntimeError("Unable to parse Version: from spec")
    return match.group(1)


def extract_pyproject_version() -> str | None:
    """Return version from pyproject.toml, or None if file missing."""
    if not PYPROJECT_FILE.exists():
        return None
    content = PYPROJECT_FILE.read_text(encoding="utf-8")
    match = PYPROJECT_VERSION_RE.search(content)
    if not match:
        return None
    return match.group(1)


def workflow_version_tag(version: str) -> str:
    parts = version.split(".")
    if len(parts) >= 2:
        return f"v{parts[0]}.{parts[1]}"
    return f"v{version}"


def release_notes_candidates(root: Path, version: str) -> List[Path]:
    name = f"RELEASE-NOTES-v{version}.md"
    return [root / "docs" / "releases" / name, root / name]


def resolve_release_notes_file(root: Path, version: str) -> Path:
    for candidate in release_notes_candidates(root, version):
        if candidate.exists():
            return candidate
    return release_notes_candidates(root, version)[0]


def scan_stale_version_tests(
    tests_dir: Path, version: str, codename: str | None
) -> List[str]:
    """Return errors for test files that hardcode the current version or codename.

    These assertions break on every version bump and must use dynamic checks
    instead (e.g. asserting non-empty, semver format, or importing the value).
    """
    errors: List[str] = []
    if not tests_dir.exists():
        return errors

    for test_file in sorted(tests_dir.glob("test_*.py")):
        try:
            content = test_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            if "# fixture-version" in line:
                continue
            if version in line and _HARDCODED_VERSION_RE.search(line):
                errors.append(
                    f"stale version assertion in {test_file.name}:{lineno} "
                    f'(hardcodes "{version}")'
                )
            if codename and codename in line and _HARDCODED_CODENAME_RE.search(line):
                errors.append(
                    f"stale codename assertion in {test_file.name}:{lineno} "
                    f'(hardcodes "{codename}")'
                )

    return errors


def _extract_codename() -> str | None:
    """Extract __version_codename__ from version.py, or None."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version_codename__\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


def validate_release_docs(root: Path, *, require_logs: bool) -> List[str]:
    errors: List[str] = []

    try:
        py_version = extract_version()
        spec_version = extract_spec_version()
    except Exception as exc:  # pragma: no cover - defensive parser guard
        return [str(exc)]

    # --- Version sync: version.py vs .spec ---
    if py_version != spec_version:
        errors.append(f"version mismatch: version.py={py_version} spec={spec_version}")

    # --- Version sync: version.py vs pyproject.toml ---
    pyproject_version = extract_pyproject_version()
    if pyproject_version is not None and py_version != pyproject_version:
        errors.append(
            f"version mismatch: version.py={py_version} pyproject.toml={pyproject_version}"
        )

    # --- CHANGELOG ---
    if (
        not CHANGELOG_FILE.exists()
        or f"## [{py_version}]" not in CHANGELOG_FILE.read_text(encoding="utf-8")
    ):
        errors.append(f"CHANGELOG missing entry for {py_version}")

    # --- README ---
    if not README_FILE.exists() or not README_FILE.read_text(encoding="utf-8").strip():
        errors.append("README.md missing or empty")

    # --- Release notes ---
    notes_file = resolve_release_notes_file(root, py_version)
    if not notes_file.exists() or not notes_file.read_text(encoding="utf-8").strip():
        expected = release_notes_candidates(root, py_version)[0]
        errors.append(f"missing release notes: {expected.relative_to(root)}")

    # --- Workflow artifacts (optional) ---
    if require_logs:
        wf_tag = workflow_version_tag(py_version)
        test_report = root / ".workflow" / "reports" / f"test-results-{wf_tag}.json"
        run_manifest = root / ".workflow" / "reports" / f"run-manifest-{wf_tag}.json"

        if not test_report.exists():
            errors.append(f"missing workflow test report: {test_report}")
        if not run_manifest.exists():
            errors.append(f"missing workflow run manifest: {run_manifest}")

        if run_manifest.exists():
            try:
                payload = json.loads(run_manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                errors.append(f"invalid JSON run manifest: {run_manifest}")
            else:
                phases = payload.get("phases")
                if not isinstance(phases, list) or not phases:
                    errors.append(f"run manifest has no phase entries: {run_manifest}")

    # --- Stale version tests ---
    codename = _extract_codename()
    stale_errors = scan_stale_version_tests(TESTS_DIR, py_version, codename)
    errors.extend(stale_errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate release docs and workflow artifacts"
    )
    parser.add_argument(
        "--require-logs",
        action="store_true",
        help="Require workflow run/test artifacts",
    )
    args = parser.parse_args()

    issues = validate_release_docs(ROOT, require_logs=args.require_logs)
    if issues:
        print("[release-doc-check] FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("[release-doc-check] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
