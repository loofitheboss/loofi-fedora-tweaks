#!/usr/bin/env python3
"""
bump_version.py — Version bump cascade for Loofi Fedora Tweaks.

Updates version across all files that reference it:
1. loofi-fedora-tweaks/version.py  (__version__, __version_codename__)
2. loofi-fedora-tweaks.spec        (Version:)
3. pyproject.toml                  (version)
4. .workflow/specs/.race-lock.json (target_version)
5. Regenerates project stats       (scripts/project_stats.py)
6. Re-renders templates            (scripts/sync_ai_adapters.py --render)
7. Scaffolds release notes         (docs/releases/RELEASE-NOTES-vX.Y.Z.md)
8. Scans tests for hardcoded versions (warns if found)

Usage:
  python3 scripts/bump_version.py 41.0.0 --codename "Scaffold"
  python3 scripts/bump_version.py 41.0.0 --dry-run
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "loofi-fedora-tweaks" / "version.py"
SPEC_FILE = PROJECT_ROOT / "loofi-fedora-tweaks.spec"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"
RACE_LOCK = PROJECT_ROOT / ".workflow" / "specs" / ".race-lock.json"
STATS_SCRIPT = PROJECT_ROOT / "scripts" / "project_stats.py"
SYNC_SCRIPT = PROJECT_ROOT / "scripts" / "sync_ai_adapters.py"
TESTS_DIR = PROJECT_ROOT / "tests"
RELEASE_NOTES_DIR = PROJECT_ROOT / "docs" / "releases"

# Patterns that indicate hardcoded version strings in test files.
# Matches assertEqual/assertIn/etc. with quoted version-like strings.
HARDCODED_VERSION_RE = re.compile(
    r"""(?:assertEqual|assertIn|assert\s).*["']\d+\.\d+\.\d+["']"""
)
# Matches assertEqual with quoted codename-like single words (capitalized).
HARDCODED_CODENAME_RE = re.compile(
    r"""assertEqual.*__version_codename__.*["'][A-Z]\w+["']"""
)


def read_current_version() -> tuple[str, str]:
    """Read current version and codename from version.py."""
    version = "unknown"
    codename = "unknown"
    text = VERSION_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__") and "codename" not in line:
            version = line.split("=", 1)[1].strip().strip("\"'")
        elif line.startswith("__version_codename__"):
            codename = line.split("=", 1)[1].strip().strip("\"'")
    return version, codename


def update_version_py(
    new_version: str, codename: str | None, dry_run: bool
) -> list[str]:
    """Update version.py."""
    text = VERSION_FILE.read_text(encoding="utf-8")
    changes = []

    # Replace __version__
    new_text = re.sub(
        r'^(__version__\s*=\s*)["\'].*["\']',
        f'\\1"{new_version}"',
        text,
        flags=re.MULTILINE,
    )
    if new_text != text:
        changes.append(f"  version.py: __version__ -> {new_version}")
    text = new_text

    # Replace __version_codename__ if provided
    if codename:
        new_text = re.sub(
            r'^(__version_codename__\s*=\s*)["\'].*["\']',
            f'\\1"{codename}"',
            text,
            flags=re.MULTILINE,
        )
        if new_text != text:
            changes.append(f"  version.py: __version_codename__ -> {codename}")
        text = new_text

    if not dry_run and changes:
        VERSION_FILE.write_text(text, encoding="utf-8")

    return changes


def update_spec(new_version: str, dry_run: bool) -> list[str]:
    """Update .spec file Version: field."""
    text = SPEC_FILE.read_text(encoding="utf-8")
    changes = []

    new_text = re.sub(
        r"^(Version:\s*).*$",
        f"\\g<1>{new_version}",
        text,
        flags=re.MULTILINE,
    )
    if new_text != text:
        changes.append(f"  .spec: Version -> {new_version}")

    if not dry_run and changes:
        SPEC_FILE.write_text(new_text, encoding="utf-8")

    return changes


def update_pyproject(new_version: str, dry_run: bool) -> list[str]:
    """Update pyproject.toml version field."""
    changes: list[str] = []
    if not PYPROJECT_FILE.exists():
        changes.append("  pyproject.toml: file not found (skipped)")
        return changes

    text = PYPROJECT_FILE.read_text(encoding="utf-8")

    new_text = re.sub(
        r'^(version\s*=\s*")[^"]*(")',
        f"\\g<1>{new_version}\\2",
        text,
        flags=re.MULTILINE,
    )
    if new_text != text:
        changes.append(f"  pyproject.toml: version -> {new_version}")

    if not dry_run and changes:
        PYPROJECT_FILE.write_text(new_text, encoding="utf-8")

    return changes


def update_race_lock(new_version: str, dry_run: bool) -> list[str]:
    """Update race-lock target version."""
    changes: list[str] = []
    if not RACE_LOCK.exists():
        changes.append("  race-lock: file not found (skipped)")
        return changes

    lock = json.loads(RACE_LOCK.read_text(encoding="utf-8"))
    old_ver = lock.get("target_version", "unknown")
    new_ver = f"v{new_version}" if not new_version.startswith("v") else new_version

    if old_ver != new_ver:
        lock["target_version"] = new_ver
        lock["status"] = "active"
        lock["bumped_at"] = datetime.now(timezone.utc).isoformat()
        changes.append(f"  race-lock: {old_ver} -> {new_ver}")

        if not dry_run:
            RACE_LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    return changes


def regenerate_stats(dry_run: bool) -> list[str]:
    """Run project_stats.py to refresh cached stats."""
    if dry_run:
        return ["  stats: would regenerate .project-stats.json"]

    if not STATS_SCRIPT.exists():
        return ["  stats: script not found (skipped)"]

    try:
        subprocess.run(
            [sys.executable, str(STATS_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            timeout=30,
        )
        return ["  stats: regenerated .project-stats.json"]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return [f"  stats: failed ({e})"]


def render_templates(dry_run: bool) -> list[str]:
    """Run sync_ai_adapters.py --render to update template variables."""
    if dry_run:
        return ["  templates: would re-render"]

    if not SYNC_SCRIPT.exists():
        return ["  templates: script not found (skipped)"]

    try:
        result = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--render"],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        rendered_count = result.stdout.count("Rendered")
        return [f"  templates: re-rendered ({rendered_count} files)"]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return [f"  templates: failed ({e})"]


def scaffold_release_notes(
    new_version: str, codename: str | None, dry_run: bool
) -> list[str]:
    """Create a skeleton release notes file if one does not already exist."""
    changes: list[str] = []
    notes_file = RELEASE_NOTES_DIR / f"RELEASE-NOTES-v{new_version}.md"

    if notes_file.exists():
        changes.append(f"  release notes: already exists ({notes_file.name})")
        return changes

    title = f"v{new_version}"
    if codename:
        title += f' "{codename}"'

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    skeleton = (
        f"# Release Notes -- {title}\n"
        f"\n"
        f"**Release Date:** {today}\n"
        f"**Codename:** {codename or 'TBD'}\n"
        f"**Theme:** TODO — one-line summary of the release theme\n"
        f"\n"
        f"## Summary\n"
        f"\n"
        f"TODO — 2-3 sentence overview.\n"
        f"\n"
        f"## Highlights\n"
        f"\n"
        f"- TODO\n"
        f"\n"
        f"## Changes\n"
        f"\n"
        f"### Changed\n"
        f"\n"
        f"- TODO\n"
        f"\n"
        f"### Added\n"
        f"\n"
        f"- TODO\n"
        f"\n"
        f"### Fixed\n"
        f"\n"
        f"- TODO\n"
        f"\n"
        f"## Stats\n"
        f"\n"
        f"- **Tests:** TODO passed, TODO skipped, 0 failed\n"
        f"- **Lint:** 0 errors\n"
        f"- **Coverage:** TODO%\n"
        f"\n"
        f"## Upgrade Notes\n"
        f"\n"
        f'TODO — or "No user-facing changes."\n'
    )

    changes.append(f"  release notes: scaffolded {notes_file.name}")

    if not dry_run:
        RELEASE_NOTES_DIR.mkdir(parents=True, exist_ok=True)
        notes_file.write_text(skeleton, encoding="utf-8")

    return changes


def scan_stale_version_tests(old_version: str, old_codename: str) -> list[str]:
    """Scan tests/ for hardcoded version or codename strings that will break after bump.

    Returns a list of warnings (never blocks the bump).
    """
    warnings: list[str] = []
    if not TESTS_DIR.exists():
        return warnings

    for test_file in sorted(TESTS_DIR.glob("test_*.py")):
        try:
            content = test_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            # Check for hardcoded old version in assertions
            if old_version in line and HARDCODED_VERSION_RE.search(line):
                warnings.append(
                    f"  WARNING: {test_file.name}:{lineno} "
                    f'hardcodes version "{old_version}"'
                )
            # Check for hardcoded old codename in assertions
            if old_codename in line and HARDCODED_CODENAME_RE.search(line):
                warnings.append(
                    f"  WARNING: {test_file.name}:{lineno} "
                    f'hardcodes codename "{old_codename}"'
                )

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump version across all project files."
    )
    parser.add_argument("version", help="New version (e.g. 41.0.0)")
    parser.add_argument("--codename", help="Version codename (e.g. 'Scaffold')")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing"
    )
    args = parser.parse_args()

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", args.version):
        print(f"ERROR: Invalid version format '{args.version}'. Expected X.Y.Z")
        return 1

    current_ver, current_codename = read_current_version()
    print(
        f"{'[DRY RUN] ' if args.dry_run else ''}Bumping version: {current_ver} -> {args.version}"
    )
    if args.codename:
        print(f"  Codename: {current_codename} -> {args.codename}")
    print()

    all_changes: list[str] = []

    # 1. version.py
    all_changes.extend(update_version_py(args.version, args.codename, args.dry_run))

    # 2. .spec
    all_changes.extend(update_spec(args.version, args.dry_run))

    # 3. pyproject.toml
    all_changes.extend(update_pyproject(args.version, args.dry_run))

    # 4. race-lock
    all_changes.extend(update_race_lock(args.version, args.dry_run))

    # 5. Stats
    all_changes.extend(regenerate_stats(args.dry_run))

    # 6. Templates
    all_changes.extend(render_templates(args.dry_run))

    # 7. Release notes scaffold
    all_changes.extend(
        scaffold_release_notes(args.version, args.codename, args.dry_run)
    )

    # Summary
    print("Changes:")
    for c in all_changes:
        print(c)

    if not all_changes:
        print("  (no changes needed)")

    # 8. Scan for stale version tests (advisory, never blocks)
    stale_warnings = scan_stale_version_tests(current_ver, current_codename)
    if stale_warnings:
        print(f"\nStale version references in tests ({len(stale_warnings)}):")
        for w in stale_warnings:
            print(w)
        print("  Fix: replace hardcoded version assertions with dynamic checks.")
        print("  See: AGENTS.md rule #11 (no hardcoded versions in tests).")

    if args.dry_run:
        print("\nNo files were modified (dry-run mode).")
    else:
        print(f"\nVersion bumped to {args.version} across {len(all_changes)} targets.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
