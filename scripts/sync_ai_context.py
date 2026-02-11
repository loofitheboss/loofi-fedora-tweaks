#!/usr/bin/env python3
"""Create compact context bundles for Codex, Claude Code, and GitHub Copilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_ROOT = ROOT / ".workflow"
SPECS_DIR = WORKFLOW_ROOT / "specs"
CONTEXT_DIR = WORKFLOW_ROOT / "context"
LOCK_FILE = SPECS_DIR / ".race-lock.json"
STABLE_INSTRUCTIONS = ROOT / ".github" / "workflow" / "STABLE_TASK_INSTRUCTIONS.md"
ROADMAP_FILE = ROOT / "ROADMAP.md"


def normalize_version_tag(version: str) -> str:
    cleaned = version.strip()
    if not cleaned:
        raise ValueError("target version cannot be empty")
    return cleaned if cleaned.startswith("v") else f"v{cleaned}"


def safe_read(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:max_chars].strip()


def file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:12]


def git_value(args: list[str]) -> str:
    try:
        value = subprocess.check_output(args, text=True, cwd=ROOT).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return value or "unknown"


def load_lock_version() -> str:
    if not LOCK_FILE.exists():
        return "none"
    try:
        payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "invalid"
    version = payload.get("version", "invalid") if isinstance(payload, dict) else "invalid"
    return str(version)


def build_context(version_tag: str, phase: str, task: str) -> tuple[str, dict[str, object]]:
    task_file = SPECS_DIR / f"tasks-{version_tag}.md"
    arch_file = SPECS_DIR / f"arch-{version_tag}.md"
    notes_file = SPECS_DIR / f"release-notes-draft-{version_tag}.md"

    roadmap_excerpt = safe_read(ROADMAP_FILE, 3000)
    task_excerpt = safe_read(task_file, 3000)
    arch_excerpt = safe_read(arch_file, 3000)

    branch = git_value(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    head = git_value(["git", "rev-parse", "--short", "HEAD"])

    metadata = {
        "version": version_tag,
        "phase": phase,
        "task": task,
        "active_race": load_lock_version(),
        "branch": branch,
        "head": head,
        "stable_instructions": str(STABLE_INSTRUCTIONS.relative_to(ROOT)),
        "stable_instructions_hash": file_hash(STABLE_INSTRUCTIONS),
        "roadmap": str(ROADMAP_FILE.relative_to(ROOT)),
        "task_spec": str(task_file.relative_to(ROOT)),
        "arch_spec": str(arch_file.relative_to(ROOT)),
        "notes_draft": str(notes_file.relative_to(ROOT)),
    }

    context_md = f"""# Unified AI Context Bundle

## Session
- Target version: `{version_tag}`
- Active phase: `{phase}`
- Task label: `{task}`
- Active race lock: `{metadata['active_race']}`
- Git branch/head: `{branch}` / `{head}`

## Stable Instructions (load first)
- File: `{metadata['stable_instructions']}`
- Hash: `{metadata['stable_instructions_hash']}`

## Source Artifacts (priority order)
1. `{metadata['task_spec']}`
2. `{metadata['arch_spec']}`
3. `{metadata['roadmap']}`
4. `{metadata['notes_draft']}`

## Roadmap Excerpt
{roadmap_excerpt or '*No roadmap content found.*'}

## Tasks Excerpt
{task_excerpt or '*No task spec found for this version yet.*'}

## Architecture Excerpt
{arch_excerpt or '*No architecture spec found for this version yet.*'}

## Tool Handoff Commands
- Codex: `python3 scripts/workflow_runner.py --phase {phase} --target-version {version_tag}`
- Claude Code: load this file + `.github/workflow/STABLE_TASK_INSTRUCTIONS.md`, execute the same phase goal.
- GitHub Copilot Chat: open this file in editor and use `/fix` or `/startDebugging` only on files listed above.
"""

    return context_md, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Create minimal context for cross-tool handoff")
    parser.add_argument("--target-version", required=True, help="Version like 25.0 or v25.0")
    parser.add_argument("--phase", default="plan", choices=["plan", "design", "build", "test", "doc", "package", "release"])
    parser.add_argument("--task", default="general")
    args = parser.parse_args()

    version_tag = normalize_version_tag(args.target_version)
    out_dir = CONTEXT_DIR / version_tag
    out_dir.mkdir(parents=True, exist_ok=True)

    context_md, metadata = build_context(version_tag, args.phase, args.task)
    context_file = out_dir / "context.md"
    handoff_file = out_dir / "handoff.json"

    context_file.write_text(context_md + "\n", encoding="utf-8")
    handoff_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"[sync-ai-context] Wrote {context_file}")
    print(f"[sync-ai-context] Wrote {handoff_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
