#!/usr/bin/env python3
"""Race-lock workflow runner for Loofi Fedora Tweaks.

This script enforces version integrity between workflow phases and archives
previous workspace specs whenever a new plan starts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_ROOT = ROOT / ".workflow"
SPECS_DIR = WORKFLOW_ROOT / "specs"
REPORTS_DIR = WORKFLOW_ROOT / "reports"
ARCHIVE_DIR = WORKFLOW_ROOT / "archive"
LOCK_FILE = SPECS_DIR / ".race-lock.json"
PROMPTS_DIR = ROOT / ".claude" / "workflow" / "prompts"


def normalize_version_tag(version: str) -> str:
    version = version.strip()
    if not version:
        raise ValueError("target version cannot be empty")
    return version if version.startswith("v") else f"v{version}"


def get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def artifact_paths(version_tag: str) -> dict[str, Path]:
    return {
        "tasks": SPECS_DIR / f"tasks-{version_tag}.md",
        "arch": SPECS_DIR / f"arch-{version_tag}.md",
        "notes_draft": SPECS_DIR / f"release-notes-draft-{version_tag}.md",
        "test_report": REPORTS_DIR / f"test-results-{version_tag}.json",
    }


def load_lock() -> dict[str, str] | None:
    """Read active race metadata from lock file."""
    if not LOCK_FILE.exists():
        return None

    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict):
        return None

    version = data.get("version")
    if not isinstance(version, str) or not version:
        return None

    return data


def create_lock(version_tag: str) -> None:
    """Lock workspace to one active version race."""
    data = {
        "version": version_tag,
        "started_at": get_timestamp(),
        "status": "active",
    }
    LOCK_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[workflow] RACE LOCK: workspace locked to {version_tag}")


def archive_workspace() -> None:
    """Archive current specs workspace before starting a new race."""
    if not SPECS_DIR.exists():
        return

    entries = [p for p in SPECS_DIR.iterdir() if p.name != ".gitkeep"]
    if not entries:
        return

    lock = load_lock()
    lock_version = lock["version"] if lock else "unknown"
    archive_name = f"{lock_version}_{get_timestamp()}"
    target_dir = ARCHIVE_DIR / archive_name
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[workflow] ARCHIVE: moving specs to {target_dir}")
    for path in entries:
        shutil.move(str(path), str(target_dir / path.name))

    if LOCK_FILE.exists():
        LOCK_FILE.unlink()

    (SPECS_DIR / ".gitkeep").touch(exist_ok=True)


def validate_race(version_tag: str) -> None:
    """Require strict version match between lock and requested phase."""
    lock = load_lock()
    if not lock:
        print("ERROR: no active race lock found.", file=sys.stderr)
        print("Run '--phase plan' first to start a race.", file=sys.stderr)
        raise SystemExit(1)

    locked_version = lock["version"]
    if locked_version != version_tag:
        print("ERROR: race version mismatch.", file=sys.stderr)
        print(f"  locked:    {locked_version}", file=sys.stderr)
        print(f"  requested: {version_tag}", file=sys.stderr)
        print("To switch versions, start a new plan for the requested version.", file=sys.stderr)
        raise SystemExit(1)

    print(f"[workflow] RACE CHECK PASSED: {version_tag}")


def run_agent(
    phase_name: str,
    model: str,
    inputs: Iterable[Path],
    prompt_file: Path,
    instruction: str,
    dry_run: bool,
) -> int:
    if not dry_run and shutil.which("codex") is None:
        print("ERROR: 'codex' command not found in PATH.", file=sys.stderr)
        return 127

    valid_inputs: list[Path] = []
    for path in inputs:
        if path.exists():
            valid_inputs.append(path)
        else:
            print(f"WARN: skipping missing input: {path}")

    if not valid_inputs:
        print("ERROR: no valid inputs found for this phase.", file=sys.stderr)
        return 2

    if not prompt_file.exists():
        print(f"ERROR: missing prompt file: {prompt_file}", file=sys.stderr)
        return 2

    phase_prompt = prompt_file.read_text(encoding="utf-8")
    input_paths = "\n".join(f"- {path}" for path in valid_inputs)
    combined_prompt = (
        f"{phase_prompt}\n\n"
        f"WORKFLOW PHASE: {phase_name}\n"
        f"INPUT PATHS (read these from the repository):\n{input_paths}\n\n"
        f"EXECUTION INSTRUCTION:\n{instruction}\n"
    )
    cmd = ["codex", "exec", "--model", model, "--cd", str(ROOT)]

    print(f"\n[workflow] Phase: {phase_name}")
    print(f"[workflow] Model: {model}")
    print(f"[workflow] Prompt: {prompt_file}")
    print(f"[workflow] Instruction: {instruction}")

    if dry_run:
        print("[workflow] Dry run command:")
        print(" ".join(cmd))
        return 0

    result = subprocess.run(cmd, input=combined_prompt, text=True, check=False)
    if result.returncode != 0:
        print(f"ERROR: phase '{phase_name}' failed with exit code {result.returncode}", file=sys.stderr)
    return result.returncode


def run_phase(phase: str, version_tag: str, dry_run: bool, *, skip_race_check: bool = False) -> int:
    artifacts = artifact_paths(version_tag)
    roadmap = ROOT / "ROADMAP.md"
    agents_md = ROOT / "AGENTS.md"
    memory = ROOT / ".claude" / "agent-memory" / "project-coordinator" / "MEMORY.md"

    if phase == "plan":
        if not dry_run:
            archive_workspace()
            create_lock(version_tag)
        return run_agent(
            phase_name="P1 PLAN",
            model="gpt-5.3-codex",
            inputs=[roadmap, memory],
            prompt_file=PROMPTS_DIR / "plan.md",
            instruction=f"Write output only to {artifacts['tasks']}",
            dry_run=dry_run,
        )

    if not skip_race_check:
        validate_race(version_tag)

    if phase == "design":
        return run_agent(
            phase_name="P2 DESIGN",
            model="gpt-5.3-codex",
            inputs=[artifacts["tasks"], agents_md],
            prompt_file=PROMPTS_DIR / "design.md",
            instruction=(
                f"Write architecture spec to {artifacts['arch']} and "
                f"release-notes draft to {artifacts['notes_draft']}"
            ),
            dry_run=dry_run,
        )

    if phase == "build":
        return run_agent(
            phase_name="P3 BUILD",
            model="gpt-4o",
            inputs=[artifacts["arch"], artifacts["tasks"]],
            prompt_file=PROMPTS_DIR / "implement.md",
            instruction="Implement the architecture spec using minimal diffs.",
            dry_run=dry_run,
        )

    if phase == "test":
        return run_agent(
            phase_name="P4 TEST",
            model="gpt-4o",
            inputs=[artifacts["tasks"], ROOT / "tests"],
            prompt_file=PROMPTS_DIR / "test.md",
            instruction=f"Write test summary JSON to {artifacts['test_report']}",
            dry_run=dry_run,
        )

    if phase == "doc":
        return run_agent(
            phase_name="P5 DOC",
            model="gpt-4o-mini",
            inputs=[artifacts["tasks"], artifacts["notes_draft"], ROOT / "CHANGELOG.md", ROOT / "README.md"],
            prompt_file=PROMPTS_DIR / "document.md",
            instruction=f"Finalize release notes and update docs for {version_tag}.",
            dry_run=dry_run,
        )

    if phase == "package":
        return run_agent(
            phase_name="P6 PACKAGE",
            model="gpt-4o-mini",
            inputs=[ROOT / "loofi-fedora-tweaks" / "version.py", ROOT / "loofi-fedora-tweaks.spec"],
            prompt_file=PROMPTS_DIR / "package.md",
            instruction=f"Validate packaging metadata for {version_tag}.",
            dry_run=dry_run,
        )

    if phase == "release":
        return run_agent(
            phase_name="P7 RELEASE",
            model="gpt-4o-mini",
            inputs=[ROOT / "loofi-fedora-tweaks" / "version.py", ROOT / "CHANGELOG.md"],
            prompt_file=PROMPTS_DIR / "release.md",
            instruction=f"Prepare release steps for {version_tag}.",
            dry_run=dry_run,
        )

    print(f"ERROR: unknown phase '{phase}'", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Race-lock workflow runner")
    parser.add_argument(
        "--phase",
        choices=["plan", "design", "build", "test", "doc", "package", "release", "all"],
        required=True,
        help="Workflow phase to execute",
    )
    parser.add_argument("--target-version", required=True, help="Version, e.g. 24.0 or v24.0")
    parser.add_argument("--dry-run", action="store_true", help="Print command instead of executing")
    args = parser.parse_args()

    version_tag = normalize_version_tag(args.target_version)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if args.phase == "all":
        sequence = ["plan", "design", "build", "test", "doc", "package", "release"]
        for index, phase in enumerate(sequence):
            # During all+dry-run, skip lock checks after plan to avoid mutating lock state.
            skip_race_check = bool(args.dry_run and index > 0)
            code = run_phase(phase, version_tag, args.dry_run, skip_race_check=skip_race_check)
            if code != 0:
                return code
        return 0

    return run_phase(args.phase, version_tag, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
