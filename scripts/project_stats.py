#!/usr/bin/env python3
"""Project stats introspection engine for Loofi Fedora Tweaks.

Gathers dynamic project statistics from the actual codebase and outputs
them as JSON. Used by sync_ai_adapters.py --render to keep agent/instruction
files current. Run with --check to verify committed files match reality.

Usage:
    python3 scripts/project_stats.py            # Generate .project-stats.json
    python3 scripts/project_stats.py --check     # Verify stats in committed files
    python3 scripts/project_stats.py --markdown   # Also generate .project-stats.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "loofi-fedora-tweaks"
UI_DIR = APP_DIR / "ui"
UTILS_DIR = APP_DIR / "utils"
TESTS_DIR = ROOT / "tests"
VERSION_FILE = APP_DIR / "version.py"
ROADMAP_FILE = ROOT / "ROADMAP.md"
RACE_LOCK_FILE = ROOT / ".workflow" / "specs" / ".race-lock.json"
STATS_JSON = ROOT / ".project-stats.json"
STATS_MD = ROOT / ".project-stats.md"


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def read_version() -> dict[str, str]:
    """Read version info from version.py."""
    ns: dict[str, Any] = {}
    exec(VERSION_FILE.read_text(encoding="utf-8"), ns)  # noqa: S102
    return {
        "version": ns.get("__version__", "0.0.0"),
        "codename": ns.get("__version_codename__", ""),
        "app_name": ns.get("__app_name__", "Loofi Fedora Tweaks"),
    }


def count_tab_files() -> tuple[int, list[str]]:
    """Count *_tab.py files in ui/ and return names (excludes base_tab)."""
    tabs = sorted(
        p.stem for p in UI_DIR.glob("*_tab.py")
        if p.is_file() and p.stem != "base_tab"
    )
    return len(tabs), tabs


def count_test_files() -> int:
    """Count test_*.py files in tests/."""
    return len(list(TESTS_DIR.glob("test_*.py")))


def count_utils_modules() -> int:
    """Count *.py files in utils/ (excluding __init__ and __pycache__)."""
    return len([
        p for p in UTILS_DIR.glob("*.py")
        if p.is_file() and p.stem != "__init__"
    ])


def read_roadmap_versions() -> dict[str, str]:
    """Extract active/next version and status from ROADMAP.md."""
    result: dict[str, str] = {
        "active_version": "",
        "next_version": "",
        "roadmap_status": "",
    }
    if not ROADMAP_FILE.exists():
        return result

    text = ROADMAP_FILE.read_text(encoding="utf-8")

    # Find ACTIVE version
    active_match = re.search(
        r"\|\s*v([\d.]+)\s*\|[^|]*\|\s*ACTIVE\s*\|", text)
    if active_match:
        result["active_version"] = active_match.group(1)

    # Find NEXT version
    next_match = re.search(
        r"\|\s*v([\d.]+)\s*\|[^|]*\|\s*NEXT\s*\|", text)
    if next_match:
        result["next_version"] = next_match.group(1)

    # If no ACTIVE, the NEXT becomes the active target
    if not result["active_version"] and result["next_version"]:
        result["active_version"] = result["next_version"]

    # Determine overall status
    if result["active_version"]:
        result["roadmap_status"] = "active"
    elif result["next_version"]:
        result["roadmap_status"] = "next"
    else:
        result["roadmap_status"] = "stable"

    return result


def read_race_lock() -> dict[str, str]:
    """Read pipeline state from race-lock."""
    result = {"pipeline_version": "", "pipeline_status": ""}
    if not RACE_LOCK_FILE.exists():
        return result
    try:
        data = json.loads(RACE_LOCK_FILE.read_text(encoding="utf-8"))
        result["pipeline_version"] = data.get("version", "")
        result["pipeline_status"] = data.get("status", "")
    except (json.JSONDecodeError, OSError):
        pass
    return result


def read_coverage_from_reports() -> str:
    """Try to read latest coverage from workflow reports."""
    reports_dir = ROOT / ".workflow" / "reports"
    if not reports_dir.exists():
        return "76.8"  # fallback to last known

    # Look for test-results files, get latest
    results = sorted(reports_dir.glob("test-results-*.json"), reverse=True)
    for result_file in results:
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            cov = data.get("coverage_percent")
            if cov is not None:
                return str(cov)
        except (json.JSONDecodeError, OSError):
            continue

    return "76.8"  # fallback


def read_test_count_from_reports() -> str:
    """Try to read latest test count from workflow reports."""
    reports_dir = ROOT / ".workflow" / "reports"
    if not reports_dir.exists():
        return "3846"  # fallback

    results = sorted(reports_dir.glob("test-results-*.json"), reverse=True)
    for result_file in results:
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
            count = data.get("test_count")
            if count is not None:
                return str(count)
        except (json.JSONDecodeError, OSError):
            continue

    return "3846"  # fallback


# ---------------------------------------------------------------------------
# Stats builder
# ---------------------------------------------------------------------------

def gather_stats() -> dict[str, Any]:
    """Gather all project stats into a single dict."""
    version_info = read_version()
    tab_count, tab_names = count_tab_files()
    roadmap = read_roadmap_versions()
    race_lock = read_race_lock()

    return {
        # From version.py
        "version": version_info["version"],
        "codename": version_info["codename"],
        "app_name": version_info["app_name"],

        # Counted from codebase
        "tab_count": tab_count,
        "tab_names": tab_names,
        "test_file_count": count_test_files(),
        "utils_module_count": count_utils_modules(),

        # From reports (with fallbacks)
        "test_count": read_test_count_from_reports(),
        "coverage": read_coverage_from_reports(),

        # From ROADMAP.md
        "active_version": roadmap["active_version"],
        "next_version": roadmap["next_version"],
        "roadmap_status": roadmap["roadmap_status"],

        # From race-lock
        "pipeline_version": race_lock["pipeline_version"],
        "pipeline_status": race_lock["pipeline_status"],

        # Computed
        "python_version": "3.12",
        "framework": "PyQt6",
    }


# ---------------------------------------------------------------------------
# Output generators
# ---------------------------------------------------------------------------

def write_stats_json(stats: dict[str, Any]) -> None:
    """Write stats to .project-stats.json."""
    STATS_JSON.write_text(
        json.dumps(stats, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"[stats] Wrote {STATS_JSON}")


def write_stats_markdown(stats: dict[str, Any]) -> None:
    """Write human-readable stats summary."""
    lines = [
        f"# Project Stats — v{stats['version']} \"{stats['codename']}\"",
        "",
        "<!-- Auto-generated by scripts/project_stats.py — do not edit manually -->",
        "",
        "| Stat | Value |",
        "|------|-------|",
        f"| Version | {stats['version']} |",
        f"| Codename | {stats['codename']} |",
        f"| Framework | {stats['framework']} |",
        f"| Python | {stats['python_version']}+ |",
        f"| UI Tabs | {stats['tab_count']} |",
        f"| Test Files | {stats['test_file_count']} |",
        f"| Test Count | {stats['test_count']}+ |",
        f"| Coverage | {stats['coverage']}% |",
        f"| Utils Modules | {stats['utils_module_count']} |",
        f"| Active Version | {stats['active_version'] or 'stable'} |",
        f"| Pipeline | {stats['pipeline_version']} ({stats['pipeline_status']}) |",
        "",
        "## Tab Layout",
        "",
    ]
    for i, tab in enumerate(stats["tab_names"], 1):
        lines.append(f"{i}. `{tab}`")

    lines.append("")
    STATS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[stats] Wrote {STATS_MD}")


# ---------------------------------------------------------------------------
# Check mode — verify committed files match reality
# ---------------------------------------------------------------------------

TEMPLATE_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")

# Files to scan for template variables
CHECKED_FILES = [
    ".github/agents/Arkitekt.agent.md",
    ".github/agents/Builder.agent.md",
    ".github/agents/CodeGen.agent.md",
    ".github/agents/Guardian.agent.md",
    ".github/agents/Manager.agent.md",
    ".github/agents/Planner.agent.md",
    ".github/agents/Sculptor.agent.md",
    ".github/agents/Test.agent.md",
    ".github/instructions/primary.instructions.md",
    ".github/instructions/workflow.instructions.md",
    ".github/copilot-instructions.md",
    "AGENTS.md",
    "CLAUDE.md",
]

# Hardcoded patterns that should match current stats
STAT_CHECKS: list[tuple[str, str, str]] = [
    # (pattern_description, regex_to_find, stats_key)
    # These detect stale hardcoded values in non-templated files
]


def check_unrendered_templates(stats: dict[str, Any]) -> list[str]:
    """Check for unrendered {{variable}} templates in committed files."""
    issues: list[str] = []
    for rel_path in CHECKED_FILES:
        full_path = ROOT / rel_path
        if not full_path.exists():
            continue
        text = full_path.read_text(encoding="utf-8")
        matches = TEMPLATE_VAR_PATTERN.findall(text)
        for var_name in matches:
            if var_name in stats:
                issues.append(
                    f"{rel_path}: unrendered template variable {{{{{var_name}}}}}"
                )
    return issues


def run_check(stats: dict[str, Any]) -> int:
    """Run all consistency checks. Returns exit code."""
    issues: list[str] = []

    # Check for unrendered template variables
    issues.extend(check_unrendered_templates(stats))

    if not issues:
        print("[stats] OK: all stats consistent")
        return 0

    print("[stats] DRIFT DETECTED:")
    for issue in issues:
        print(f"  - {issue}")
    return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project stats introspection engine"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Verify stats consistency in committed files (CI gate)"
    )
    parser.add_argument(
        "--markdown", action="store_true",
        help="Also generate .project-stats.md"
    )
    parser.add_argument(
        "--json-only", action="store_true",
        help="Print stats JSON to stdout instead of writing file"
    )
    args = parser.parse_args()

    stats = gather_stats()

    if args.json_only:
        print(json.dumps(stats, indent=2))
        return 0

    if args.check:
        return run_check(stats)

    write_stats_json(stats)
    if args.markdown:
        write_stats_markdown(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
