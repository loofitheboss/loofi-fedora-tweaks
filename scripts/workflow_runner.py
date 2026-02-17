#!/usr/bin/env python3
"""Race-lock workflow runner for Loofi Fedora Tweaks.

This runner supports two execution modes:
- write: mutate repository state through phase execution (single-writer lock enforced)
- review: read-only assistant execution with report output
"""

from __future__ import annotations

import argparse
import getpass
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib  # Python 3.12+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_ROOT = ROOT / ".workflow"
SPECS_DIR = WORKFLOW_ROOT / "specs"
REPORTS_DIR = WORKFLOW_ROOT / "reports"
ARCHIVE_DIR = WORKFLOW_ROOT / "archive"
REVIEWS_DIR = REPORTS_DIR / "reviews"
LOCK_FILE = SPECS_DIR / ".race-lock.json"
WRITER_LOCK_FILE = SPECS_DIR / ".writer-lock.json"
MODEL_ROUTER_FILE = ROOT / ".github" / "workflow" / "model-router.toml"
PROMPTS_DIR = ROOT / ".github" / "workflow" / "prompts"
FEDORA_REVIEW_CHECK_SCRIPT = ROOT / "scripts" / "check_fedora_review.py"
FEDORA_REVIEW_GATED_PHASES = {"package", "release"}

PHASE_ORDER = ["plan", "design", "build", "test", "doc", "package", "release"]
DEFAULT_PHASE_MODELS = {
    "plan": "gpt-5.3-codex",
    "design": "gpt-5.3-codex",
    "build": "gpt-4o",
    "test": "gpt-4o",
    "doc": "gpt-4o-mini",
    "package": "gpt-4o-mini",
    "release": "gpt-4o-mini",
}
TASK_REQUIRED_MARKERS = ("ID:", "Files:", "Dep:", "Agent:", "Description:")
TASK_REQUIRED_CONTINUATION = ("Acceptance:", "Docs:", "Tests:")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(moment: datetime | None = None) -> str:
    base = moment or utc_now()
    return base.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: str) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value[:-1] + "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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
        "run_manifest": REPORTS_DIR / f"run-manifest-{version_tag}.json",
    }


def review_output_path(version_tag: str, assistant: str, phase: str) -> Path:
    safe_version = version_tag.replace("/", "-")
    return REVIEWS_DIR / assistant / f"{safe_version}-{phase}.md"


def major_version(version_tag: str) -> int:
    value = version_tag[1:] if version_tag.startswith("v") else version_tag
    first = value.split(".", 1)[0]
    try:
        return int(first)
    except ValueError:
        return 0


def should_enforce_task_contract(version_tag: str) -> bool:
    return major_version(version_tag) >= 26


def validate_task_contract(tasks_file: Path) -> list[str]:
    if not tasks_file.exists():
        return [f"missing task artifact: {tasks_file}"]

    lines = tasks_file.read_text(encoding="utf-8").splitlines()
    issues: list[str] = []
    task_indexes = [idx for idx, line in enumerate(
        lines) if line.startswith("- [") and "ID:" in line]

    if not task_indexes:
        return ["task artifact has no task entries with ID field"]

    for index in task_indexes:
        line = lines[index]
        missing = [token for token in TASK_REQUIRED_MARKERS if token not in line]
        if missing:
            issues.append(
                f"line {index + 1}: missing markers {', '.join(missing)}")

        continuation_window = lines[index + 1:index + 5]
        for token in TASK_REQUIRED_CONTINUATION:
            if not any(item.strip().startswith(token) for item in continuation_window):
                issues.append(
                    f"line {index + 1}: missing continuation field '{token}'")
    return issues


def load_phase_models() -> dict[str, str]:
    models = dict(DEFAULT_PHASE_MODELS)
    if tomllib is None or not MODEL_ROUTER_FILE.exists():
        return models

    try:
        payload = tomllib.loads(MODEL_ROUTER_FILE.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return models

    phase_table = payload.get("phases")
    if not isinstance(phase_table, dict):
        return models

    for phase_name in PHASE_ORDER:
        candidate = phase_table.get(phase_name)
        if isinstance(candidate, str) and candidate.strip():
            models[phase_name] = candidate.strip()
    return models


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def load_lock() -> dict[str, str] | None:
    data = load_json_file(LOCK_FILE)
    if not data:
        return None

    version = data.get("version")
    if not isinstance(version, str) or not version:
        return None
    return data


def create_lock(version_tag: str) -> None:
    data = {
        "version": version_tag,
        "started_at": get_timestamp(),
        "status": "active",
    }
    LOCK_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[workflow] RACE LOCK: workspace locked to {version_tag}")


def archive_workspace() -> None:
    if not SPECS_DIR.exists():
        return

    entries = [p for p in SPECS_DIR.iterdir() if p.name not in {
        ".gitkeep", WRITER_LOCK_FILE.name}]
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


def validate_race(version_tag: str) -> tuple[bool, str]:
    lock = load_lock()
    if not lock:
        return False, "no active race lock found. Run '--phase plan' first to start a race."

    locked_version = lock["version"]
    if locked_version != version_tag:
        message = (
            "race version mismatch. "
            f"locked={locked_version}, requested={version_tag}. "
            "Start a new plan for the requested version."
        )
        return False, message

    print(f"[workflow] RACE CHECK PASSED: {version_tag}")
    return True, "ok"


def load_writer_lock() -> dict[str, Any] | None:
    data = load_json_file(WRITER_LOCK_FILE)
    if not data:
        return None

    required = {"assistant", "owner", "version",
                "phase", "acquired_at", "expires_at"}
    if not required.issubset(data):
        return None
    return data


def writer_lock_expired(lock: dict[str, Any]) -> bool:
    expires_at = parse_iso8601(str(lock.get("expires_at", "")))
    if expires_at is None:
        return True
    return utc_now() >= expires_at.astimezone(timezone.utc)


def ensure_writer_lock(
    version_tag: str,
    phase: str,
    assistant: str,
    owner: str,
    ttl_minutes: int,
    dry_run: bool,
    *,
    allow_version_switch: bool = False,
) -> tuple[bool, str]:
    existing = load_writer_lock()
    now = utc_now()

    if existing and writer_lock_expired(existing):
        print("[workflow] WRITER LOCK: previous lock expired, taking over")
        if not dry_run:
            WRITER_LOCK_FILE.unlink(missing_ok=True)
        existing = None

    if existing:
        same_owner = existing.get(
            "assistant") == assistant and existing.get("owner") == owner
        same_version = existing.get("version") == version_tag
        if not same_owner:
            return (
                False,
                "writer lock is held by "
                f"{existing.get('assistant')}:{existing.get('owner')} "
                f"for {existing.get('version')} phase {existing.get('phase')}",
            )
        if not same_version and not allow_version_switch:
            return (
                False,
                "writer lock is tied to "
                f"{existing.get('version')}. Release it or start with --phase plan for a new version.",
            )

    lock_data = {
        "assistant": assistant,
        "owner": owner,
        "version": version_tag,
        "phase": phase,
        "acquired_at": isoformat_utc(now),
        "expires_at": isoformat_utc(now + timedelta(minutes=max(ttl_minutes, 1))),
    }

    if dry_run:
        print(f"[workflow] WRITER LOCK (dry-run): {json.dumps(lock_data)}")
        return True, "ok"

    WRITER_LOCK_FILE.write_text(json.dumps(
        lock_data, indent=2) + "\n", encoding="utf-8")
    print(
        f"[workflow] WRITER LOCK: {assistant}:{owner} -> {version_tag}/{phase}")
    return True, "ok"


def release_writer_lock(assistant: str, owner: str, dry_run: bool, force: bool) -> tuple[bool, str]:
    existing = load_writer_lock()
    if not existing:
        return True, "no writer lock present"

    held_by = f"{existing.get('assistant')}:{existing.get('owner')}"
    caller = f"{assistant}:{owner}"
    if not force and held_by != caller:
        return False, f"writer lock held by {held_by}, caller is {caller}"

    if dry_run:
        return True, f"dry-run would release writer lock held by {held_by}"

    WRITER_LOCK_FILE.unlink(missing_ok=True)
    return True, f"released writer lock held by {held_by}"


def load_manifest(path: Path, version_tag: str, assistant: str, owner: str, mode: str, issue: str | None) -> dict[str, Any]:
    current = load_json_file(path)
    if current:
        return current
    return {
        "version": version_tag,
        "assistant": assistant,
        "owner": owner,
        "mode": mode,
        "issue": issue,
        "started_at": isoformat_utc(),
        "updated_at": isoformat_utc(),
        "phases": [],
    }


def append_manifest_entry(path: Path, base_manifest: dict[str, Any], entry: dict[str, Any], dry_run: bool) -> None:
    manifest = dict(base_manifest)
    phases = manifest.get("phases")
    if not isinstance(phases, list):
        phases = []
    phases.append(entry)
    manifest["phases"] = phases
    manifest["updated_at"] = isoformat_utc()

    if dry_run:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_review_instruction(base_instruction: str, phase: str, issue: str | None, review_path: Path) -> str:
    issue_text = f"Issue: #{issue}" if issue else "Issue: not provided"
    return (
        "Review-only mode. Do not modify repository files. "
        "Produce a concise markdown review with findings, risks, and next steps. "
        f"{issue_text}. "
        f"Phase: {phase}. "
        f"Base execution objective: {base_instruction}. "
        f"The runner will store your response at: {review_path}."
    )


def write_review_output(review_path: Path, stdout: str, stderr: str, returncode: int) -> None:
    review_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        f"# {review_path.stem}",
        "",
        f"- Exit code: {returncode}",
        "",
        "## Assistant Output",
        "",
        stdout.strip() or "(no output)",
    ]
    if stderr.strip():
        payload.extend(
            ["", "## STDERR", "", f"```text\n{stderr.strip()}\n```"])
    review_path.write_text("\n".join(payload) + "\n", encoding="utf-8")


def resolve_model_for_assistant(assistant: str, model: str) -> str:
    if assistant != "copilot":
        return model

    copilot_models = {
        "gpt-5.3-codex": "gpt-5",
        "gpt-4o": "gpt-4.1",
        "gpt-4o-mini": "gpt-4.1",
    }
    return copilot_models.get(model, model)


def build_agent_command(
    assistant: str,
    model: str,
    sandbox: str,
    combined_prompt: str,
) -> tuple[list[str], bool, str]:
    if assistant == "copilot":
        resolved_model = resolve_model_for_assistant(assistant, model)
        cmd = [
            "copilot",
            "--model",
            resolved_model,
            "-p",
            combined_prompt,
            "--allow-all",
            "--no-ask-user",
            "--add-dir",
            str(ROOT),
            "--stream",
            "off",
            "--no-color",
        ]
        display = (
            "copilot "
            f"--model {resolved_model} -p <prompt> --allow-all --no-ask-user "
            f"--add-dir {ROOT} --stream off --no-color"
        )
        return cmd, False, display

    if assistant == "claude":
        # Claude Code CLI: claude -p <prompt> --allowedTools '*' --model <model>
        claude_model_map = {
            "gpt-5.3-codex": "claude-sonnet-4-20250514",
            "gpt-4o": "claude-sonnet-4-20250514",
            "gpt-4o-mini": "claude-haiku-3-5-20241022",
            "claude-opus-4-20250514": "claude-opus-4-20250514",
            "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
            "claude-haiku-3-5-20241022": "claude-haiku-3-5-20241022",
        }
        resolved_model = claude_model_map.get(
            model, "claude-sonnet-4-20250514")
        write_tools = "Edit,Write,Bash,Read,MultiEdit"
        read_tools = "Read,Bash"
        allowed_tools = read_tools if sandbox == "read-only" else write_tools
        cmd = [
            "claude",
            "-p",
            combined_prompt,
            "--allowedTools",
            allowed_tools,
            "--model",
            resolved_model,
        ]
        display = (
            f"claude -p <prompt> --allowedTools {allowed_tools} "
            f"--model {resolved_model}"
        )
        return cmd, False, display

    cmd = ["codex", "exec", "--model", model,
           "--sandbox", sandbox, "--cd", str(ROOT)]
    display = " ".join(cmd)
    return cmd, True, display


def run_agent(
    phase_name: str,
    model: str,
    inputs: Iterable[Path],
    prompt_file: Path,
    instruction: str,
    dry_run: bool,
    *,
    assistant: str,
    mode: str,
    review_output: Path | None,
) -> tuple[int, dict[str, Any]]:
    sandbox = "read-only" if mode == "review" else "workspace-write"

    if not dry_run:
        agent_binary = "copilot" if assistant == "copilot" else "codex"
        if shutil.which(agent_binary) is None:
            return 127, {"status": "error", "error": f"'{agent_binary}' command not found in PATH"}

    valid_inputs: list[Path] = []
    for path in inputs:
        if path.exists():
            valid_inputs.append(path)
        else:
            print(f"WARN: skipping missing input: {path}")

    if not valid_inputs:
        return 2, {"status": "error", "error": "no valid inputs found for this phase"}

    if not prompt_file.exists():
        return 2, {"status": "error", "error": f"missing prompt file: {prompt_file}"}

    phase_prompt = prompt_file.read_text(encoding="utf-8")
    input_paths = "\n".join(f"- {path}" for path in valid_inputs)
    combined_prompt = (
        f"{phase_prompt}\n\n"
        f"WORKFLOW PHASE: {phase_name}\n"
        f"INPUT PATHS (read these from the repository):\n{input_paths}\n\n"
        f"EXECUTION INSTRUCTION:\n{instruction}\n"
    )
    cmd, uses_stdin_prompt, command_display = build_agent_command(
        assistant, model, sandbox, combined_prompt)

    print(f"\n[workflow] Phase: {phase_name}")
    print(f"[workflow] Mode: {mode}")
    print(f"[workflow] Assistant: {assistant}")
    print(f"[workflow] Model: {model}")
    print(f"[workflow] Prompt: {prompt_file}")
    print(f"[workflow] Instruction: {instruction}")

    metadata: dict[str, Any] = {
        "phase_name": phase_name,
        "mode": mode,
        "model": model,
        "prompt": str(prompt_file),
        "inputs": [str(path) for path in valid_inputs],
        "instruction": instruction,
        "command": command_display,
        "timestamp": isoformat_utc(),
        "status": "pending",
    }

    if dry_run:
        print("[workflow] Dry run command:")
        print(" ".join(cmd))
        metadata["status"] = "dry_run"
        return 0, metadata

    if mode == "review":
        if uses_stdin_prompt:
            result = subprocess.run(
                cmd, input=combined_prompt, text=True, capture_output=True, check=False)
        else:
            result = subprocess.run(
                cmd, text=True, capture_output=True, check=False)
        metadata["status"] = "success" if result.returncode == 0 else "failed"
        metadata["exit_code"] = result.returncode
        if review_output is not None:
            write_review_output(review_output, result.stdout,
                                result.stderr, result.returncode)
            metadata["review_output"] = str(review_output)
        if result.returncode != 0:
            print(
                f"ERROR: phase '{phase_name}' failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode, metadata

    if uses_stdin_prompt:
        result = subprocess.run(
            cmd, input=combined_prompt, text=True, check=False)
    else:
        result = subprocess.run(cmd, text=True, check=False)
    metadata["status"] = "success" if result.returncode == 0 else "failed"
    metadata["exit_code"] = result.returncode
    if result.returncode != 0:
        print(
            f"ERROR: phase '{phase_name}' failed with exit code {result.returncode}", file=sys.stderr)
    return result.returncode, metadata


def validate_phase_ordering(phase: str, version_tag: str) -> tuple[bool, str]:
    """Enforce strict phase ordering: each phase requires all prior phases to be completed.

    Checks the run manifest for prior phase completion. Returns (ok, reason).
    Use --force-phase to bypass this check.
    """
    if phase == "plan":
        return True, "ok"  # plan is always allowed

    manifest_path = artifact_paths(version_tag)["run_manifest"]
    manifest = load_json_file(manifest_path)

    completed_phases: set[str] = set()
    if manifest and isinstance(manifest.get("phases"), list):
        for entry in manifest["phases"]:
            if (isinstance(entry, dict)
                    and entry.get("status") == "success"
                    and isinstance(entry.get("phase"), str)):
                completed_phases.add(entry["phase"])

    phase_idx = PHASE_ORDER.index(phase)
    required_phases = PHASE_ORDER[:phase_idx]
    missing = [p for p in required_phases if p not in completed_phases]

    if missing:
        return (
            False,
            f"phase '{phase}' requires prior phases to complete first: "
            f"{', '.join(missing)}. Use --force-phase to bypass.",
        )
    return True, "ok"


def run_fedora_review_gate(timeout_seconds: int = 60) -> tuple[bool, str]:
    """Run lightweight Fedora review prerequisite checks."""
    if not FEDORA_REVIEW_CHECK_SCRIPT.exists():
        return False, f"missing checker script: {FEDORA_REVIEW_CHECK_SCRIPT}"

    command = [sys.executable, str(FEDORA_REVIEW_CHECK_SCRIPT)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"checker timed out after {timeout_seconds}s"
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"checker execution failed: {exc}"

    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        details = stdout or stderr or f"exit code {result.returncode}"
        return False, details

    return True, "ok"


def run_phase(
    phase: str,
    version_tag: str,
    dry_run: bool,
    *,
    phase_models: dict[str, str],
    assistant: str,
    mode: str,
    owner: str,
    issue: str | None,
    lock_ttl_minutes: int,
    skip_race_check: bool = False,
    force_phase: bool = False,
) -> tuple[int, dict[str, Any]]:
    artifacts = artifact_paths(version_tag)
    roadmap = ROOT / "ROADMAP.md"
    agents_md = ROOT / "AGENTS.md"
    memory = ROOT / ".github" / "agent-memory" / "project-coordinator" / "MEMORY.md"

    # Phase ordering enforcement (write mode only)
    if mode == "write" and not force_phase:
        phase_ok, phase_reason = validate_phase_ordering(phase, version_tag)
        if not phase_ok:
            return 1, {"phase": phase, "status": "blocked", "error": phase_reason, "timestamp": isoformat_utc()}

    if mode == "write":
        ok, reason = ensure_writer_lock(
            version_tag,
            phase,
            assistant,
            owner,
            lock_ttl_minutes,
            dry_run,
            allow_version_switch=(phase == "plan"),
        )
        if not ok:
            return 1, {"phase": phase, "status": "blocked", "error": reason, "timestamp": isoformat_utc()}

    if mode == "write" and phase in FEDORA_REVIEW_GATED_PHASES and not dry_run:
        gate_ok, gate_reason = run_fedora_review_gate()
        if not gate_ok:
            return (
                1,
                {
                    "phase": phase,
                    "status": "blocked",
                    "error": f"fedora-review gate failed: {gate_reason}",
                    "timestamp": isoformat_utc(),
                },
            )

    if phase == "plan":
        base_instruction = f"Write output only to {artifacts['tasks']}"
        if mode == "write" and not dry_run:
            archive_workspace()
            create_lock(version_tag)

        review_path = review_output_path(
            version_tag, assistant, phase) if mode == "review" else None
        instruction = (
            build_review_instruction(
                base_instruction, "P1 PLAN", issue, review_path)
            if mode == "review" and review_path
            else base_instruction
        )
        code, metadata = run_agent(
            phase_name="P1 PLAN",
            model=phase_models["plan"],
            inputs=[roadmap, memory],
            prompt_file=PROMPTS_DIR / "plan.md",
            instruction=instruction,
            dry_run=dry_run,
            assistant=assistant,
            mode=mode,
            review_output=review_path,
        )
        metadata.update({"phase": phase, "artifacts": [
                        str(artifacts["tasks"])], "issue": issue})
        return code, metadata

    if mode == "write" and not skip_race_check:
        valid, race_reason = validate_race(version_tag)
        if not valid:
            return 1, {"phase": phase, "status": "blocked", "error": race_reason, "timestamp": isoformat_utc()}

    if phase != "plan" and should_enforce_task_contract(version_tag):
        contract_issues = validate_task_contract(artifacts["tasks"])
        if contract_issues:
            return (
                2,
                {
                    "phase": phase,
                    "status": "blocked",
                    "error": "task artifact contract validation failed",
                    "details": contract_issues,
                    "timestamp": isoformat_utc(),
                },
            )

    phase_map: dict[str, dict[str, Any]] = {
        "design": {
            "phase_name": "P2 DESIGN",
            "model": phase_models["design"],
            "inputs": [artifacts["tasks"], agents_md],
            "prompt": PROMPTS_DIR / "design.md",
            "instruction": (
                f"Write architecture spec to {artifacts['arch']} and "
                f"release-notes draft to {artifacts['notes_draft']}"
            ),
            "artifacts": [artifacts["arch"], artifacts["notes_draft"]],
        },
        "build": {
            "phase_name": "P3 BUILD",
            "model": phase_models["build"],
            "inputs": [artifacts["arch"], artifacts["tasks"]],
            "prompt": PROMPTS_DIR / "build.md",
            "instruction": "Implement the architecture spec using minimal diffs.",
            "artifacts": [],
        },
        "test": {
            "phase_name": "P4 TEST",
            "model": phase_models["test"],
            "inputs": [artifacts["tasks"], ROOT / "tests"],
            "prompt": PROMPTS_DIR / "test.md",
            "instruction": f"Write test summary JSON to {artifacts['test_report']}",
            "artifacts": [artifacts["test_report"]],
        },
        "doc": {
            "phase_name": "P5 DOC",
            "model": phase_models["doc"],
            "inputs": [artifacts["tasks"], artifacts["notes_draft"], ROOT / "CHANGELOG.md", ROOT / "README.md"],
            "prompt": PROMPTS_DIR / "document.md",
            "instruction": f"Finalize release notes and update docs for {version_tag}.",
            "artifacts": [],
        },
        "package": {
            "phase_name": "P6 PACKAGE",
            "model": phase_models["package"],
            "inputs": [ROOT / "loofi-fedora-tweaks" / "version.py", ROOT / "loofi-fedora-tweaks.spec"],
            "prompt": PROMPTS_DIR / "package.md",
            "instruction": f"Validate packaging metadata for {version_tag}.",
            "artifacts": [],
        },
        "release": {
            "phase_name": "P7 RELEASE",
            "model": phase_models["release"],
            "inputs": [
                ROOT / "loofi-fedora-tweaks" / "version.py",
                ROOT / "CHANGELOG.md",
                artifacts["tasks"],
                artifacts["test_report"],
                ROOT / "docs" / "releases" / f"RELEASE-NOTES-{version_tag}.md",
            ],
            "prompt": PROMPTS_DIR / "release.md",
            "instruction": (
                f"Prepare release steps for {version_tag} using only the provided artifacts. "
                "Do not execute shell commands, do not run tests, and do not modify repository files."
            ),
            "artifacts": [artifacts["run_manifest"]],
        },
    }

    if phase not in phase_map:
        return 2, {"phase": phase, "status": "error", "error": f"unknown phase '{phase}'", "timestamp": isoformat_utc()}

    config = phase_map[phase]
    review_path = review_output_path(
        version_tag, assistant, phase) if mode == "review" else None
    instruction = (
        build_review_instruction(
            config["instruction"], config["phase_name"], issue, review_path)
        if mode == "review" and review_path
        else config["instruction"]
    )

    code, metadata = run_agent(
        phase_name=config["phase_name"],
        model=config["model"],
        inputs=config["inputs"],
        prompt_file=config["prompt"],
        instruction=instruction,
        dry_run=dry_run,
        assistant=assistant,
        mode=mode,
        review_output=review_path,
    )
    metadata.update(
        {
            "phase": phase,
            "artifacts": [str(path) for path in config["artifacts"]],
            "issue": issue,
        }
    )
    return code, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Race-lock workflow runner")
    parser.add_argument(
        "--phase",
        choices=["plan", "design", "build", "test",
                 "doc", "package", "release", "all"],
        required=False,
        help="Workflow phase to execute",
    )
    parser.add_argument("--target-version", help="Version, e.g. 24.0 or v24.0")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print command instead of executing")

    parser.add_argument(
        "--assistant", choices=["codex", "claude", "copilot"], default="codex")
    parser.add_argument("--mode", choices=["write", "review"], default="write")
    parser.add_argument("--issue", help="Optional issue id for traceability")
    parser.add_argument("--owner", default=getpass.getuser(),
                        help="Writer lock owner metadata")
    parser.add_argument("--lock-ttl-minutes", type=int,
                        default=120, help="Writer lock expiry in minutes")
    parser.add_argument("--release-writer-lock", action="store_true",
                        help="Release .writer-lock.json and exit")
    parser.add_argument("--force-release-lock",
                        action="store_true", help="Force-release writer lock")
    parser.add_argument("--force-phase", action="store_true",
                        help="Bypass strict phase ordering enforcement")

    args = parser.parse_args()

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    if args.release_writer_lock:
        ok, message = release_writer_lock(
            args.assistant, args.owner, args.dry_run, args.force_release_lock)
        if ok:
            print(f"[workflow] {message}")
            return 0
        print(f"ERROR: {message}", file=sys.stderr)
        return 1

    if not args.phase or not args.target_version:
        parser.error(
            "--phase and --target-version are required unless --release-writer-lock is used")

    try:
        version_tag = normalize_version_tag(args.target_version)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    phase_models = load_phase_models()
    manifest_path = artifact_paths(version_tag)["run_manifest"]
    manifest_base = load_manifest(
        manifest_path, version_tag, args.assistant, args.owner, args.mode, args.issue)

    if args.phase == "all":
        for index, phase in enumerate(PHASE_ORDER):
            skip_race_check = bool(
                args.dry_run and args.mode == "write" and index > 0)
            code, entry = run_phase(
                phase,
                version_tag,
                args.dry_run,
                phase_models=phase_models,
                assistant=args.assistant,
                mode=args.mode,
                owner=args.owner,
                issue=args.issue,
                lock_ttl_minutes=args.lock_ttl_minutes,
                skip_race_check=skip_race_check,
                force_phase=True,  # "all" mode runs sequentially, no ordering check needed
            )
            append_manifest_entry(
                manifest_path, manifest_base, entry, args.dry_run)
            manifest_base = load_manifest(
                manifest_path, version_tag, args.assistant, args.owner, args.mode, args.issue)
            if code != 0:
                return code
        return 0

    code, entry = run_phase(
        args.phase,
        version_tag,
        args.dry_run,
        phase_models=phase_models,
        assistant=args.assistant,
        mode=args.mode,
        owner=args.owner,
        issue=args.issue,
        lock_ttl_minutes=args.lock_ttl_minutes,
        force_phase=args.force_phase,
    )
    append_manifest_entry(manifest_path, manifest_base, entry, args.dry_run)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
