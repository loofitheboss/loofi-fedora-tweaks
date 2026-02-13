# GitHub MCP (Workspace) — Quick Guide

## Fast setup (recommended)

1. Open this workspace in VS Code.
2. Create token file:
	- `cp .vscode/mcp.env.example .vscode/mcp.env`
3. Edit `.vscode/mcp.env` and set:
	- `GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_NEW_PAT`
4. Restart the GitHub MCP server in VS Code.

This workspace reads the token from `.vscode/mcp.env` via Docker `--env-file` in `.vscode/mcp.json`.

## Requirements

- Docker installed and running.
- A GitHub PAT with the scopes you need (usually `repo`, optionally `read:org`).

## If server does not start

- Verify Docker: `docker --version` and `docker info`.
- Restart VS Code, then restart the GitHub MCP server.
- Confirm `.vscode/mcp.env` exists and contains `GITHUB_PERSONAL_ACCESS_TOKEN=...`.

## Security

- Never commit a PAT to files.
- If a token is ever pasted in chat/history, revoke it and create a new one.
