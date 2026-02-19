#!/usr/bin/env python3
"""
Loofi Fedora Tweaks — MCP Agent Sync Server

Bridges AI agent definitions, memory, and git state for cross-tool synchronization.
Exposes tools for reading/updating agent memory, checking adapter drift,
and syncing agent definitions between VS Code and Claude formats.

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / ".github" / "agents"
CLAUDE_AGENTS_DIR = PROJECT_ROOT / ".github" / "claude-agents"
AGENT_MEMORY_DIR = PROJECT_ROOT / ".github" / "agent-memory"
INSTRUCTIONS_DIR = PROJECT_ROOT / ".github" / "instructions"

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "loofi-agent-sync", "version": "1.0.0"}

TOOLS = [
    {
        "name": "list_agents",
        "description": "List all AI agent definitions across VS Code and Claude platforms with sync status.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "read_agent_memory",
        "description": "Read an agent's persistent memory (MEMORY.md and topic files).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Agent name (e.g. 'architecture-advisor', 'backend-builder').",
                },
            },
            "required": ["agent"],
        },
    },
    {
        "name": "update_agent_memory",
        "description": "Append or update content in an agent's MEMORY.md file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Agent name.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to append to MEMORY.md.",
                },
                "replace": {
                    "type": "boolean",
                    "description": "If true, replace entire MEMORY.md. Default: false (append).",
                },
            },
            "required": ["agent", "content"],
        },
    },
    {
        "name": "check_adapter_drift",
        "description": "Check if Claude agent adapters are in sync with VS Code canonical definitions.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "sync_adapters",
        "description": "Run the adapter sync script to update Claude agents from VS Code definitions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, only check without modifying. Default: true.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "agent_git_status",
        "description": "Show git status for agent-related files (definitions, memory, instructions).",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "list_instructions",
        "description": "List all AI instruction files with their scope and description.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def handle_list_agents(_args: dict) -> dict:
    """List all agents across both platforms with sync status."""
    vscode_agents = {}
    claude_agents = {}

    # VS Code agents
    if AGENTS_DIR.exists():
        for f in sorted(AGENTS_DIR.glob("*.agent.md")):
            name = f.stem.replace(".agent", "")
            text = f.read_text(encoding="utf-8")
            desc = ""
            for line in text.splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
            vscode_agents[name] = {
                "file": str(f.relative_to(PROJECT_ROOT)),
                "description": desc[:100],
            }

    # Claude agents
    if CLAUDE_AGENTS_DIR.exists():
        for f in sorted(CLAUDE_AGENTS_DIR.glob("*.md")):
            name = f.stem
            text = f.read_text(encoding="utf-8")
            desc = ""
            for line in text.splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip('"')[:100]
                    break
            has_memory = (AGENT_MEMORY_DIR / name / "MEMORY.md").exists()
            memory_files = []
            mem_dir = AGENT_MEMORY_DIR / name
            if mem_dir.exists():
                memory_files = [
                    str(mf.relative_to(mem_dir))
                    for mf in mem_dir.iterdir()
                    if mf.is_file()
                ]
            claude_agents[name] = {
                "file": str(f.relative_to(PROJECT_ROOT)),
                "description": desc[:100],
                "has_memory": has_memory,
                "memory_files": memory_files,
            }

    # Mapping
    agent_map = {
        "Arkitekt": "architecture-advisor",
        "Builder": "backend-builder",
        "CodeGen": "code-implementer",
        "Guardian": None,
        "Manager": "project-coordinator",
        "Planner": "release-planner",
        "Sculptor": "frontend-integration-builder",
        "Test": "test-writer",
    }

    return {
        "vscode_agents": vscode_agents,
        "claude_agents": claude_agents,
        "mapping": agent_map,
        "vscode_count": len(vscode_agents),
        "claude_count": len(claude_agents),
    }


def handle_read_agent_memory(args: dict) -> dict:
    """Read an agent's memory files."""
    agent = args.get("agent", "")
    mem_dir = AGENT_MEMORY_DIR / agent

    if not mem_dir.exists():
        return {"error": f"No memory directory for agent: {agent}"}

    files = {}
    for f in sorted(mem_dir.iterdir()):
        if f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
                files[f.name] = {
                    "content": content,
                    "lines": len(content.splitlines()),
                    "size_bytes": len(content.encode("utf-8")),
                }
            except Exception as e:
                files[f.name] = {"error": str(e)}

    return {
        "agent": agent,
        "memory_dir": str(mem_dir.relative_to(PROJECT_ROOT)),
        "file_count": len(files),
        "files": files,
    }


def handle_update_agent_memory(args: dict) -> dict:
    """Append or replace content in an agent's MEMORY.md."""
    agent = args.get("agent", "")
    content = args.get("content", "")
    replace = args.get("replace", False)

    mem_dir = AGENT_MEMORY_DIR / agent
    mem_dir.mkdir(parents=True, exist_ok=True)
    mem_file = mem_dir / "MEMORY.md"

    if replace:
        mem_file.write_text(content, encoding="utf-8")
        action = "replaced"
    else:
        existing = ""
        if mem_file.exists():
            existing = mem_file.read_text(encoding="utf-8")
        separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
        mem_file.write_text(existing + separator + content + "\n", encoding="utf-8")
        action = "appended"

    return {
        "agent": agent,
        "action": action,
        "file": str(mem_file.relative_to(PROJECT_ROOT)),
        "total_lines": len(mem_file.read_text(encoding="utf-8").splitlines()),
    }


def handle_check_adapter_drift(_args: dict) -> dict:
    """Check sync status between VS Code and Claude agent definitions."""
    sync_script = PROJECT_ROOT / "scripts" / "sync_ai_adapters.py"
    if not sync_script.exists():
        return {"error": "sync_ai_adapters.py not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(sync_script), "--check"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "in_sync": result.returncode == 0,
            "output": result.stdout.strip(),
            "errors": result.stderr.strip() if result.returncode != 0 else "",
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        return {"error": str(e)}


def handle_sync_adapters(args: dict) -> dict:
    """Run adapter sync (dry-run by default)."""
    dry_run = args.get("dry_run", True)
    sync_script = PROJECT_ROOT / "scripts" / "sync_ai_adapters.py"

    if not sync_script.exists():
        return {"error": "sync_ai_adapters.py not found"}

    cmd = [sys.executable, str(sync_script)]
    if dry_run:
        cmd.append("--check")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "dry_run": dry_run,
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "errors": result.stderr.strip() if result.stderr else "",
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        return {"error": str(e)}


def handle_agent_git_status(_args: dict) -> dict:
    """Show git status for agent-related files."""
    paths = [
        ".github/agents/",
        ".github/claude-agents/",
        ".github/agent-memory/",
        ".github/instructions/",
    ]

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--"] + paths,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        changes = []
        for line in result.stdout.strip().splitlines():
            if line.strip():
                status = line[:2].strip()
                path = line[3:].strip()
                changes.append({"status": status, "path": path})

        # Also check last commit touching these paths
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-3", "--"] + paths,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        recent_commits = log_result.stdout.strip().splitlines()

        return {
            "uncommitted_changes": changes,
            "change_count": len(changes),
            "recent_commits": recent_commits,
            "clean": len(changes) == 0,
        }
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return {"error": str(e)}


def handle_list_instructions(_args: dict) -> dict:
    """List all instruction files with metadata."""
    instructions = []

    if INSTRUCTIONS_DIR.exists():
        for f in sorted(INSTRUCTIONS_DIR.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            desc = ""
            apply_to = ""
            for line in text.splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                elif line.startswith("applyTo:"):
                    apply_to = line.split(":", 1)[1].strip().strip('"')
            instructions.append(
                {
                    "file": f.name,
                    "path": str(f.relative_to(PROJECT_ROOT)),
                    "description": desc,
                    "apply_to": apply_to,
                    "lines": len(text.splitlines()),
                }
            )

    # Also check root-level instruction files
    for name in ["AGENTS.md", "ARCHITECTURE.md", "ROADMAP.md", "CLAUDE.md"]:
        root_file = PROJECT_ROOT / name
        if root_file.exists():
            instructions.append(
                {
                    "file": name,
                    "path": name,
                    "description": f"Root-level {name}",
                    "apply_to": "all",
                    "lines": len(root_file.read_text(encoding="utf-8").splitlines()),
                }
            )

    return {
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


# --- MCP Protocol ---

TOOL_HANDLERS = {
    "list_agents": handle_list_agents,
    "read_agent_memory": handle_read_agent_memory,
    "update_agent_memory": handle_update_agent_memory,
    "check_adapter_drift": handle_check_adapter_drift,
    "sync_adapters": handle_sync_adapters,
    "agent_git_status": handle_agent_git_status,
    "list_instructions": handle_list_instructions,
}


def handle_initialize(_params: dict) -> dict:
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": SERVER_INFO,
    }


def handle_tools_list(_params: dict) -> dict:
    return {"tools": TOOLS}


def handle_tools_call(params: dict) -> dict:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                }
            ],
            "isError": True,
        }

    try:
        result = handler(arguments)
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError": False,
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
            "isError": True,
        }


METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def process_message(msg: dict) -> dict | None:
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if msg_id is None:
        return None

    handler = METHOD_HANDLERS.get(method)
    if handler:
        return {"jsonrpc": "2.0", "id": msg_id, "result": handler(params)}
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def read_mcp_message() -> dict | None:
    """Read a single MCP message (newline-delimited JSON over stdio)."""
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    payload = json.loads(line)
    return payload if isinstance(payload, dict) else None


def write_mcp_message(msg: dict) -> None:
    """Write a single MCP message (newline-delimited JSON over stdio)."""
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main():
    def log(msg: str) -> None:
        sys.stderr.write(f"[loofi-agent-sync] {msg}\n")

    log("MCP Agent Sync Server starting...")

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

    log("MCP Agent Sync Server shutting down.")


if __name__ == "__main__":
    main()
