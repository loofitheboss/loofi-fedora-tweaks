#!/usr/bin/env python3
"""Smoke test for scripts/mcp_workflow_server.py MCP protocol endpoints.

Validates minimal MCP roundtrip behavior:
1. initialize
2. resources/list
3. resources/read for workflow://race-lock
4. resources/read for workflow://stats
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "scripts" / "mcp_workflow_server.py"
TIMEOUT_SECONDS = 10


def _write_message(stdin: Any, payload: dict[str, Any]) -> None:
    body = json.dumps(payload)
    header = f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n"
    stdin.write(header)
    stdin.write(body)
    stdin.flush()


def _read_message(stdout: Any) -> dict[str, Any]:
    headers: dict[str, str] = {}
    while True:
        line = stdout.readline()
        if not line:
            raise RuntimeError("EOF while reading MCP headers")
        line = line.rstrip("\r\n")
        if not line:
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    content_length = int(headers.get("Content-Length", "0"))
    if content_length <= 0:
        raise RuntimeError("Invalid Content-Length in MCP response")

    body = stdout.read(content_length)
    if not body:
        raise RuntimeError("Empty MCP response body")

    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise RuntimeError("MCP response payload is not a JSON object")
    return payload


def _assert_response(response: dict[str, Any], expected_id: int, name: str) -> None:
    if response.get("id") != expected_id:
        raise RuntimeError(f"{name}: response id mismatch")
    if "error" in response:
        raise RuntimeError(f"{name}: server error: {response['error']}")


def main() -> int:
    if not SERVER.exists():
        print(f"ERROR: missing server script: {SERVER}")
        return 1

    process = subprocess.Popen(
        [sys.executable, str(SERVER)],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert process.stdin is not None
        assert process.stdout is not None

        # 1) initialize
        _write_message(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            },
        )
        response = _read_message(process.stdout)
        _assert_response(response, 1, "initialize")

        # 2) resources/list
        _write_message(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/list",
                "params": {},
            },
        )
        response = _read_message(process.stdout)
        _assert_response(response, 2, "resources/list")

        resources = response.get("result", {}).get("resources", [])
        if not isinstance(resources, list):
            raise RuntimeError("resources/list: invalid resources payload")

        expected = {
            "workflow://race-lock",
            "workflow://tasks/{version}",
            "workflow://arch/{version}",
            "workflow://stats",
        }
        found = {item.get("uri") for item in resources if isinstance(item, dict)}
        missing = sorted(expected - found)
        if missing:
            raise RuntimeError(f"resources/list: missing resources: {', '.join(missing)}")

        # 3) resources/read workflow://race-lock
        _write_message(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/read",
                "params": {"uri": "workflow://race-lock"},
            },
        )
        response = _read_message(process.stdout)
        _assert_response(response, 3, "resources/read race-lock")

        contents = response.get("result", {}).get("contents", [])
        if not isinstance(contents, list) or not contents:
            raise RuntimeError("resources/read race-lock: empty contents")

        # 4) resources/read workflow://stats
        _write_message(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "resources/read",
                "params": {"uri": "workflow://stats"},
            },
        )
        response = _read_message(process.stdout)
        _assert_response(response, 4, "resources/read stats")

        contents = response.get("result", {}).get("contents", [])
        if not isinstance(contents, list) or not contents:
            raise RuntimeError("resources/read stats: empty contents")

        print("MCP workflow smoke test passed")
        return 0
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"MCP workflow smoke test failed: {exc}")
        return 1
    finally:
        try:
            process.terminate()
            process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=TIMEOUT_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
