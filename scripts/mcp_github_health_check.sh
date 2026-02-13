#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .vscode/mcp.env ]; then
  echo "ERROR: .vscode/mcp.env not found (copy .vscode/mcp.env.example)"
  exit 1
fi

if grep -q ghp_replace_with_new_token .vscode/mcp.env; then
  echo "ERROR: placeholder token still present in .vscode/mcp.env"
  exit 1
fi

if ! grep -q "^GITHUB_PERSONAL_ACCESS_TOKEN=" .vscode/mcp.env; then
  echo "ERROR: GITHUB_PERSONAL_ACCESS_TOKEN missing in .vscode/mcp.env"
  exit 1
fi

docker run --rm --env-file .vscode/mcp.env ghcr.io/github/github-mcp-server:0.30.3 stdio --help >/tmp/mcp_help.out 2>/tmp/mcp_help.err

echo "OK: GitHub MCP token wiring looks valid"
