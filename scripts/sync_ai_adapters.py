#!/usr/bin/env python3
"""Sync Claude/Copilot/Codex adapter files from canonical .github sources."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class FileMapping:
    source: Path
    target: Path


@dataclass(frozen=True)
class DirMapping:
    source: Path
    target: Path


def canonical_file_mappings() -> list[FileMapping]:
    return [
        FileMapping(
            source=ROOT / ".github" / "workflow" / "QUICKSTART.md",
            target=ROOT / ".claude" / "workflow" / "QUICKSTART.md",
        ),
        FileMapping(
            source=ROOT / ".github" / "workflow" / "PIPELINE.md",
            target=ROOT / ".claude" / "workflow" / "PIPELINE.md",
        ),
        FileMapping(
            source=ROOT / ".github" / "workflow" / "model-router.md",
            target=ROOT / ".claude" / "workflow" / "model-router.md",
        ),
        FileMapping(
            source=ROOT / ".github" / "workflow" / "model-router.toml",
            target=ROOT / ".claude" / "workflow" / "model-router.toml",
        ),
        FileMapping(
            source=ROOT / ".github" / "copilot-instructions.md",
            target=ROOT / ".github" / "instructions" / "copilot.instructions.md",
        ),
        FileMapping(
            source=ROOT / ".github" / "agent-memory" / "project-coordinator" / "MEMORY.md",
            target=ROOT / ".claude" / "agent-memory" / "project-coordinator" / "MEMORY.md",
        ),
        FileMapping(
            source=ROOT / ".github" / "agent-memory" / "release-planner" / "MEMORY.md",
            target=ROOT / ".claude" / "agent-memory" / "release-planner" / "MEMORY.md",
        ),
    ]


def canonical_dir_mappings() -> list[DirMapping]:
    return [
        DirMapping(
            source=ROOT / ".github" / "claude-agents",
            target=ROOT / ".claude" / "agents",
        ),
        DirMapping(
            source=ROOT / ".github" / "workflow" / "prompts",
            target=ROOT / ".claude" / "workflow" / "prompts",
        ),
    ]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sync_file(mapping: FileMapping, check: bool, diffs: list[str]) -> None:
    if not mapping.source.exists():
        diffs.append(f"missing source: {mapping.source}")
        return

    source_text = read_text(mapping.source)
    target_exists = mapping.target.exists()
    target_text = read_text(mapping.target) if target_exists else ""

    if not target_exists or source_text != target_text:
        diffs.append(f"file drift: {mapping.target} <- {mapping.source}")
        if not check:
            ensure_parent(mapping.target)
            mapping.target.write_text(source_text, encoding="utf-8")


def iter_relative_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path.relative_to(root)


def sync_directory(mapping: DirMapping, check: bool, diffs: list[str]) -> None:
    if not mapping.source.exists():
        diffs.append(f"missing source directory: {mapping.source}")
        return

    source_files = list(iter_relative_files(mapping.source))
    target_files = list(iter_relative_files(mapping.target)) if mapping.target.exists() else []

    for rel in source_files:
        source_file = mapping.source / rel
        target_file = mapping.target / rel
        source_text = read_text(source_file)
        target_text = read_text(target_file) if target_file.exists() else ""
        if not target_file.exists() or source_text != target_text:
            diffs.append(f"directory drift: {target_file} <- {source_file}")
            if not check:
                ensure_parent(target_file)
                target_file.write_text(source_text, encoding="utf-8")

    stale_files = sorted(set(target_files) - set(source_files))
    for rel in stale_files:
        stale_target = mapping.target / rel
        diffs.append(f"stale adapter file: {stale_target}")
        if not check:
            stale_target.unlink(missing_ok=True)


def write_codex_adapter_manifest(check: bool, diffs: list[str]) -> None:
    target = ROOT / ".codex" / "adapter-manifest.json"
    payload = {
        "canonical_root": ".github",
        "claude_agents": ".github/claude-agents",
        "workflow_prompts": ".github/workflow/prompts",
        "workflow_router": ".github/workflow/model-router.toml",
        "copilot_instructions": ".github/copilot-instructions.md",
        "runtime_artifacts": ".workflow",
    }
    rendered = json.dumps(payload, indent=2) + "\n"
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if current != rendered:
        diffs.append(f"file drift: {target} (generated)")
        if not check:
            ensure_parent(target)
            target.write_text(rendered, encoding="utf-8")


def archive_legacy_workflow(check: bool, diffs: list[str]) -> None:
    legacy_file = ROOT / ".claude" / "workflow" / "tasks-v23.0.md"
    archive_file = ROOT / ".claude" / "archive" / "workflow-legacy" / "tasks-v23.0.md"
    if not legacy_file.exists():
        return

    diffs.append(f"legacy workflow artifact should be archived: {legacy_file}")
    if check:
        return

    archive_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(legacy_file), str(archive_file))


def run(check: bool) -> list[str]:
    diffs: list[str] = []

    for mapping in canonical_file_mappings():
        sync_file(mapping, check, diffs)

    for mapping in canonical_dir_mappings():
        sync_directory(mapping, check, diffs)

    archive_legacy_workflow(check, diffs)
    write_codex_adapter_manifest(check, diffs)
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync AI adapter files from canonical .github sources")
    parser.add_argument("--check", action="store_true", help="Only verify drift; do not write changes")
    args = parser.parse_args()

    diffs = run(check=args.check)
    if not diffs:
        print("[sync-ai] OK: adapters are in sync")
        return 0

    if args.check:
        print("[sync-ai] DRIFT DETECTED:")
        for item in diffs:
            print(f"- {item}")
        return 1

    print("[sync-ai] Updated adapter files:")
    for item in diffs:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
