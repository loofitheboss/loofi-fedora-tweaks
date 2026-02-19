#!/usr/bin/env python3
"""
Loofi Fedora Tweaks — MCP Workflow Server

A lightweight stdio-based MCP (Model Context Protocol) server that exposes
workflow operations as tools for AI agents in VS Code.

Protocol: JSON-RPC 2.0 over stdio (MCP specification 2024-11-05)
Transport: stdin/stdout
No external dependencies — uses only Python 3.12+ stdlib.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = PROJECT_ROOT / ".workflow"
SPECS_DIR = WORKFLOW_DIR / "specs"
REPORTS_DIR = WORKFLOW_DIR / "reports"
STATS_FILE = PROJECT_ROOT / ".project-stats.json"

# MCP protocol version
MCP_PROTOCOL_VERSION = "2024-11-05"

# Server info
SERVER_INFO = {
    "name": "loofi-workflow",
    "version": "1.0.0",
}

# Tool definitions
TOOLS = [
    {
        "name": "workflow_status",
        "description": "Get the current workflow status: active version, phase, race-lock state, and writer lock.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "project_stats",
        "description": "Get live project statistics: tab count, test count, utils count, version, coverage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "refresh": {
                    "type": "boolean",
                    "description": "If true, regenerate stats from source before returning. Default: false (use cached).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks for the active (or specified) version with their completion status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Version to list tasks for (e.g. 'v33.0.0'). Default: active version from race-lock.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "workflow_tasks",
        "description": "Alias of list_tasks. List tasks for the active (or specified) version with their completion status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Version to list tasks for (e.g. 'v33.0.0'). Default: active version from race-lock.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "validate_release",
        "description": "Run release validation checks: version alignment, lint, tests, docs presence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "quick": {
                    "type": "boolean",
                    "description": "If true, skip running full test suite (only check version alignment and docs). Default: false.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "workflow_validate",
        "description": "Alias of validate_release. Run release validation checks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "quick": {
                    "type": "boolean",
                    "description": "If true, skip running full test suite. Default: false.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "workflow_run_phase",
        "description": "Run a workflow phase through scripts/workflow_runner.py.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "description": "Phase to run: plan/design/build/test/doc/package/release/all",
                },
                "version": {
                    "type": "string",
                    "description": "Target version (e.g. 'v33.0.0'). Default: active version.",
                },
                "mode": {
                    "type": "string",
                    "description": "Runner mode: write or review. Default: review.",
                },
                "assistant": {
                    "type": "string",
                    "description": "Assistant identity: codex/claude/copilot. Default: codex.",
                },
                "force": {
                    "type": "boolean",
                    "description": "Bypass phase ordering checks (maps to --force).",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Run in dry-run mode. Default: true.",
                },
            },
            "required": ["phase"],
        },
    },
    {
        "name": "bump_version",
        "description": "Check what version bump would do (dry-run). Shows files that would change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "new_version": {
                    "type": "string",
                    "description": "New version string (e.g. '33.0.0').",
                },
                "codename": {
                    "type": "string",
                    "description": "Version codename (e.g. 'Nexus').",
                },
            },
            "required": ["new_version"],
        },
    },
    {
        "name": "phase_status",
        "description": "Check which workflow phases have been completed for a version.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Version to check (e.g. 'v33.0.0'). Default: active version.",
                },
            },
            "required": [],
        },
    },
]

RESOURCES = [
    {
        "uri": "workflow://race-lock",
        "name": "Workflow Race Lock",
        "description": "Current race-lock state from .workflow/specs/.race-lock.json",
        "mimeType": "application/json",
    },
    {
        "uri": "workflow://tasks/{version}",
        "name": "Workflow Tasks",
        "description": "Task spec markdown for a given version (example: workflow://tasks/v33.0.0)",
        "mimeType": "text/markdown",
    },
    {
        "uri": "workflow://arch/{version}",
        "name": "Workflow Architecture",
        "description": "Architecture spec markdown for a given version (example: workflow://arch/v33.0.0)",
        "mimeType": "text/markdown",
    },
    {
        "uri": "workflow://stats",
        "name": "Project Stats",
        "description": "Current project stats JSON from .project-stats.json",
        "mimeType": "application/json",
    },
]


def read_json(path: Path) -> dict | None:
    """Read a JSON file, return None if missing or invalid."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _resolve_resource_content(uri: str) -> tuple[str, str, str]:
    """Resolve MCP resource URI to content tuple: (uri, mimeType, text)."""
    if uri == "workflow://race-lock":
        lock_path = SPECS_DIR / ".race-lock.json"
        lock = read_json(lock_path) or {"error": "race-lock not found"}
        return uri, "application/json", json.dumps(lock, indent=2)

    if uri == "workflow://stats":
        if not STATS_FILE.exists():
            stats_script = PROJECT_ROOT / "scripts" / "project_stats.py"
            if stats_script.exists():
                try:
                    subprocess.run(
                        [sys.executable, str(stats_script)],
                        cwd=str(PROJECT_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
                    pass
        stats = read_json(STATS_FILE) or {"error": "stats not available"}
        return uri, "application/json", json.dumps(stats, indent=2)

    if uri.startswith("workflow://tasks/"):
        version = uri.split("workflow://tasks/", 1)[1].strip()
        if not version:
            raise ValueError("tasks resource requires a version in URI")
        path = SPECS_DIR / f"tasks-{version}.md"
        if not path.exists():
            raise FileNotFoundError(f"Task spec not found: {path.name}")
        return uri, "text/markdown", path.read_text(encoding="utf-8")

    if uri.startswith("workflow://arch/"):
        version = uri.split("workflow://arch/", 1)[1].strip()
        if not version:
            raise ValueError("arch resource requires a version in URI")
        path = SPECS_DIR / f"arch-{version}.md"
        if not path.exists():
            raise FileNotFoundError(f"Arch spec not found: {path.name}")
        return uri, "text/markdown", path.read_text(encoding="utf-8")

    raise ValueError(f"Unknown resource URI: {uri}")


def get_race_lock() -> dict:
    """Read the race-lock file."""
    lock = read_json(SPECS_DIR / ".race-lock.json")
    return lock if lock else {"target_version": "unknown", "status": "no-lock"}


def get_active_version() -> str:
    """Get the active version from race-lock."""
    lock = get_race_lock()
    value = lock.get("target_version", "unknown")
    return str(value) if value is not None else "unknown"


def get_version_from_source() -> tuple[str, str]:
    """Read version and codename from version.py."""
    version_file = PROJECT_ROOT / "loofi-fedora-tweaks" / "version.py"
    version = "unknown"
    codename = "unknown"
    try:
        text = version_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"\'')
            elif line.startswith("__version_codename__"):
                codename = line.split("=")[1].strip().strip('"\'')
    except FileNotFoundError:
        pass
    return version, codename


def get_spec_version() -> str:
    """Read version from .spec file."""
    spec_file = PROJECT_ROOT / "loofi-fedora-tweaks.spec"
    try:
        for line in spec_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    return "unknown"


# --- Tool Handlers ---


def handle_workflow_status(_args: dict) -> dict:
    """Get current workflow status."""
    lock = get_race_lock()
    version, codename = get_version_from_source()
    spec_ver = get_spec_version()

    # Check writer lock
    writer_lock_file = SPECS_DIR / ".writer-lock.json"
    writer_lock = read_json(writer_lock_file)

    # Check run manifest
    ver = lock.get("target_version", "unknown")
    manifest_file = REPORTS_DIR / f"run-manifest-{ver}.json"
    manifest = read_json(manifest_file)

    result = {
        "race_lock": lock,
        "source_version": version,
        "codename": codename,
        "spec_version": spec_ver,
        "version_aligned": version == spec_ver,
        "writer_lock": writer_lock if writer_lock else "none",
        "manifest_phases_completed": [],
    }

    if manifest and "phases" in manifest:
        result["manifest_phases_completed"] = [
            p["phase"] for p in manifest["phases"]
            if p.get("status") == "completed"
        ]

    return result


def handle_project_stats(args: dict) -> dict:
    """Get project statistics."""
    refresh = args.get("refresh", False)

    if refresh:
        # Run project_stats.py to regenerate
        stats_script = PROJECT_ROOT / "scripts" / "project_stats.py"
        if stats_script.exists():
            try:
                subprocess.run(
                    [sys.executable, str(stats_script)],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

    stats = read_json(STATS_FILE)
    if stats:
        return stats
    else:
        # Generate live if no cached stats
        return _gather_live_stats()


def _gather_live_stats() -> dict:
    """Quick live stats without running the full script."""
    src = PROJECT_ROOT / "loofi-fedora-tweaks"
    tests_dir = PROJECT_ROOT / "tests"

    tab_files = list(src.glob("ui/*_tab.py"))
    tab_count = len([f for f in tab_files if f.name != "base_tab.py"])
    test_files = list(tests_dir.glob("test_*.py"))
    util_files = list(src.glob("utils/*.py"))
    util_count = len([f for f in util_files if f.name != "__init__.py"])

    version, codename = get_version_from_source()

    return {
        "version": version,
        "codename": codename,
        "tab_count": tab_count,
        "test_file_count": len(test_files),
        "utils_module_count": util_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "live",
    }


def handle_list_tasks(args: dict) -> dict:
    """List tasks for a version."""
    version = args.get("version") or get_active_version()
    tasks_file = SPECS_DIR / f"tasks-{version}.md"

    if not tasks_file.exists():
        return {"error": f"No task file found: {tasks_file.name}", "version": version}

    text = tasks_file.read_text(encoding="utf-8")

    # Parse task entries
    tasks = []
    for line in text.splitlines():
        line = line.strip()
        # Match lines like "| 1 | Task name | ..." or "- [ ] T1: ..."
        if line.startswith("|") and "|" in line[1:]:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3 and parts[0].isdigit():
                tasks.append({
                    "id": parts[0],
                    "task": parts[1],
                    "done": "[x]" in line.lower() or "✅" in line or parts[-1].strip().lower() in ("done", "yes", "x", "[x]"),
                })
        elif line.startswith("- ["):
            done = line.startswith("- [x]") or line.startswith("- [X]")
            task_text = line[5:].strip() if done else line[5:].strip()
            tasks.append({"task": task_text, "done": done})

    return {
        "version": version,
        "task_count": len(tasks),
        "completed": sum(1 for t in tasks if t.get("done")),
        "tasks": tasks,
    }


def handle_validate_release(args: dict) -> dict:
    """Validate release readiness."""
    quick = args.get("quick", False)
    checks: list[dict[str, Any]] = []

    # 1. Version alignment
    version, codename = get_version_from_source()
    spec_ver = get_spec_version()
    checks.append({
        "check": "version_alignment",
        "passed": version == spec_ver,
        "detail": f"version.py={version}, spec={spec_ver}",
    })

    # 2. CHANGELOG has version entry
    changelog = PROJECT_ROOT / "CHANGELOG.md"
    has_changelog_entry = False
    if changelog.exists():
        text = changelog.read_text(encoding="utf-8")
        has_changelog_entry = f"[{version}]" in text
    checks.append({
        "check": "changelog_entry",
        "passed": has_changelog_entry,
        "detail": f"Looking for [{version}] in CHANGELOG.md",
    })

    # 3. README version
    readme = PROJECT_ROOT / "README.md"
    has_readme_ver = False
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        has_readme_ver = version in text
    checks.append({
        "check": "readme_version",
        "passed": has_readme_ver,
        "detail": f"Looking for {version} in README.md",
    })

    # 4. Lint check (unless quick)
    if not quick:
        try:
            result = subprocess.run(
                ["flake8", "loofi-fedora-tweaks/", "--max-line-length=150",
                 "--ignore=E501,W503,E402,E722,E203", "--count", "-q"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            lint_passed = result.returncode == 0
            lint_detail = result.stdout.strip() or "clean"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            lint_passed = False
            lint_detail = "flake8 not available or timed out"
        checks.append({
            "check": "lint",
            "passed": lint_passed,
            "detail": lint_detail,
        })

    # 5. Tests (unless quick)
    if not quick:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
                env={**os.environ,
                     "PYTHONPATH": str(PROJECT_ROOT / "loofi-fedora-tweaks")},
            )
            test_passed = result.returncode == 0
            # Extract summary line
            lines = result.stdout.strip().splitlines()
            test_detail = lines[-1] if lines else "no output"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            test_passed = False
            test_detail = str(e)
        checks.append({
            "check": "tests",
            "passed": test_passed,
            "detail": test_detail,
        })

    all_passed = all(c["passed"] for c in checks)
    return {
        "version": version,
        "codename": codename,
        "ready": all_passed,
        "checks": checks,
    }


def handle_bump_version(args: dict) -> dict:
    """Dry-run version bump — show what would change."""
    new_version = args.get("new_version", "")
    codename = args.get("codename", "")

    if not new_version:
        return {"error": "new_version is required"}

    current_version, current_codename = get_version_from_source()
    spec_ver = get_spec_version()

    changes = []

    # version.py
    changes.append({
        "file": "loofi-fedora-tweaks/version.py",
        "field": "__version__",
        "from": current_version,
        "to": new_version,
    })
    if codename:
        changes.append({
            "file": "loofi-fedora-tweaks/version.py",
            "field": "__version_codename__",
            "from": current_codename,
            "to": codename,
        })

    # .spec
    changes.append({
        "file": "loofi-fedora-tweaks.spec",
        "field": "Version:",
        "from": spec_ver,
        "to": new_version,
    })

    # race-lock
    lock = get_race_lock()
    changes.append({
        "file": ".workflow/specs/.race-lock.json",
        "field": "target_version",
        "from": lock.get("target_version", "unknown"),
        "to": f"v{new_version}",
    })

    return {
        "dry_run": True,
        "current_version": current_version,
        "new_version": new_version,
        "codename": codename or current_codename,
        "changes": changes,
        "note": "Use scripts/bump_version.py to apply changes.",
    }


def handle_phase_status(args: dict) -> dict:
    """Check phase completion status for a version."""
    version = args.get("version") or get_active_version()
    manifest_file = REPORTS_DIR / f"run-manifest-{version}.json"
    manifest = read_json(manifest_file)

    all_phases = ["plan", "design", "build", "test", "doc", "package", "release"]

    if not manifest or "phases" not in manifest:
        return {
            "version": version,
            "manifest_exists": False,
            "phases": {p: "not-started" for p in all_phases},
        }

    phase_map = {}
    for entry in manifest["phases"]:
        phase_map[entry["phase"]] = entry.get("status", "unknown")

    result_phases = {}
    for p in all_phases:
        result_phases[p] = phase_map.get(p, "not-started")

    return {
        "version": version,
        "manifest_exists": True,
        "phases": result_phases,
        "completed_count": sum(1 for v in result_phases.values() if v in ("completed", "success")),
        "total_phases": len(all_phases),
    }


def handle_workflow_run_phase(args: dict) -> dict:
    """Bridge MCP tool to workflow_runner.py phase execution."""
    phase = str(args.get("phase", "")).strip()
    if not phase:
        return {"error": "phase is required"}

    version = str(args.get("version") or get_active_version()).strip()
    if not version:
        return {"error": "version could not be resolved"}

    mode = str(args.get("mode") or "review").strip()
    assistant = str(args.get("assistant") or "codex").strip()
    force = bool(args.get("force", False))
    dry_run = bool(args.get("dry_run", True))

    runner = PROJECT_ROOT / "scripts" / "workflow_runner.py"
    if not runner.exists():
        return {"error": "workflow_runner.py not found"}

    command = [
        sys.executable,
        str(runner),
        "--phase",
        phase,
        "--target-version",
        version,
        "--mode",
        mode,
        "--assistant",
        assistant,
    ]
    if force:
        command.append("--force")
    if dry_run:
        command.append("--dry-run")

    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError) as exc:
        return {"error": f"workflow run failed: {exc}"}

    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "ok": result.returncode == 0,
    }


# --- MCP Protocol Handler ---

TOOL_HANDLERS = {
    "workflow_status": handle_workflow_status,
    "project_stats": handle_project_stats,
    "list_tasks": handle_list_tasks,
    "workflow_tasks": handle_list_tasks,
    "validate_release": handle_validate_release,
    "workflow_validate": handle_validate_release,
    "workflow_run_phase": handle_workflow_run_phase,
    "bump_version": handle_bump_version,
    "phase_status": handle_phase_status,
}


def handle_initialize(_params: dict) -> dict:
    """Handle initialize request."""
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            "tools": {"listChanged": False},
        },
        "serverInfo": SERVER_INFO,
    }


def handle_tools_list(_params: dict) -> dict:
    """Handle tools/list request."""
    return {"tools": TOOLS}


def handle_resources_list(_params: dict) -> dict:
    """Handle resources/list request."""
    return {"resources": RESOURCES}


def handle_resources_read(params: dict) -> dict:
    """Handle resources/read request."""
    uri = str(params.get("uri", "")).strip()
    if not uri:
        return {
            "contents": [{
                "uri": "",
                "mimeType": "application/json",
                "text": json.dumps({"error": "Missing required parameter: uri"}),
            }],
            "isError": True,
        }

    try:
        resolved_uri, mime_type, text = _resolve_resource_content(uri)
        return {
            "contents": [{
                "uri": resolved_uri,
                "mimeType": mime_type,
                "text": text,
            }],
            "isError": False,
        }
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError, FileNotFoundError) as e:
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps({"error": str(e)}),
            }],
            "isError": True,
        }


def handle_tools_call(params: dict) -> dict:
    """Handle tools/call request."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}],
            "isError": True,
        }

    try:
        result = handler(arguments)
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError": False,
        }
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "isError": True,
        }


METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "resources/list": handle_resources_list,
    "resources/read": handle_resources_read,
}


def process_message(msg: dict) -> dict | None:
    """Process a JSON-RPC 2.0 message, return response or None for notifications."""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    # Notifications (no id) — just acknowledge
    if msg_id is None:
        # Handle notifications/initialized silently
        return None

    handler = METHOD_HANDLERS.get(method)
    if handler:
        result = handler(params)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        }


def read_mcp_message() -> dict | None:
    """Read a single MCP message using Content-Length framing (LSP-style)."""
    headers: dict[str, str] = {}
    while True:
        line_bytes = sys.stdin.buffer.readline()
        if not line_bytes:
            return None
        line = line_bytes.decode("latin-1").rstrip("\r\n")
        if line == "":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    length_raw = headers.get("content-length")
    if not length_raw:
        raise ValueError("Missing Content-Length header")

    try:
        length = int(length_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid Content-Length: {length_raw}") from exc

    if length <= 0:
        raise ValueError(f"Invalid Content-Length value: {length}")

    body_bytes = sys.stdin.buffer.read(length)
    if len(body_bytes) < length:
        raise ValueError("Incomplete MCP message body")

    body = body_bytes.decode("utf-8")
    payload = json.loads(body)
    return payload if isinstance(payload, dict) else None


def write_mcp_message(msg: dict) -> None:
    """Write a single MCP message with Content-Length framing."""
    body_bytes = json.dumps(msg).encode("utf-8")
    header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header + body_bytes)
    sys.stdout.buffer.flush()


def main():
    """Main loop — read JSON-RPC messages from stdin, write responses to stdout."""
    # Use stderr for logging to avoid polluting the protocol stream
    def log(msg): return sys.stderr.write(f"[loofi-workflow] {msg}\n")  # noqa: E731
    log("MCP Workflow Server starting...")

    while True:
        try:
            msg = read_mcp_message()
        except (json.JSONDecodeError, ValueError) as e:
            log(f"Invalid message: {e}")
            continue

        if msg is None:
            break

        response = process_message(msg)
        if response is not None:
            write_mcp_message(response)

    log("MCP Workflow Server shutting down.")


if __name__ == "__main__":
    main()
