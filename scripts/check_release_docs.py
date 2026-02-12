#!/usr/bin/env python3
"""Validate release documentation, version sync, and optional workflow artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "loofi-fedora-tweaks" / "version.py"
SPEC_FILE = ROOT / "loofi-fedora-tweaks.spec"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
README_FILE = ROOT / "README.md"

VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')
SPEC_VERSION_RE = re.compile(r"^Version:\s*(\S+)", re.MULTILINE)


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


def validate_release_docs(root: Path, *, require_logs: bool) -> List[str]:
    errors: List[str] = []

    try:
        py_version = extract_version()
        spec_version = extract_spec_version()
    except Exception as exc:  # pragma: no cover - defensive parser guard
        return [str(exc)]

    if py_version != spec_version:
        errors.append(f"version mismatch: version.py={py_version} spec={spec_version}")

    if not CHANGELOG_FILE.exists() or f"## [{py_version}]" not in CHANGELOG_FILE.read_text(encoding="utf-8"):
        errors.append(f"CHANGELOG missing entry for {py_version}")

    if not README_FILE.exists() or not README_FILE.read_text(encoding="utf-8").strip():
        errors.append("README.md missing or empty")

    notes_file = resolve_release_notes_file(root, py_version)
    if not notes_file.exists() or not notes_file.read_text(encoding="utf-8").strip():
        expected = release_notes_candidates(root, py_version)[0]
        errors.append(f"missing release notes: {expected.relative_to(root)}")

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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release docs and workflow artifacts")
    parser.add_argument("--require-logs", action="store_true", help="Require workflow run/test artifacts")
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
