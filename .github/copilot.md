# GitHub Copilot Instructions

This file serves as an additional entry point for GitHub Copilot instructions. The comprehensive instructions are located at [.github/copilot-instructions.md](.github/copilot-instructions.md).

## Quick Reference

**Primary Instructions**: `.github/copilot-instructions.md` (211 lines)
- Architecture overview (PyQt6 app, 28 tabs, utils/ layer separation)
- Critical patterns (BaseTab, PrivilegedCommand, error framework)
- Testing conventions (unittest + mock, no root required)
- Version management

**Path-Specific Instructions**: `.github/instructions/`
- `copilot.instructions.md` - Comprehensive coding guidelines (applies to all files)
- `test.instructions.md` - Testing guidelines (applies to `**/{tests,test_}*`)
- `workflow.instructions.md` - Workflow pipeline rules
- `primary.instructions.md` - AI developer instructions
- `system_hardening_and_stabilization_guide.md` - Security and hardening rules

**Agent Instructions**: Root level
- `AGENTS.md` - Quick reference for all agents
- `CLAUDE.md` - Claude-specific instructions
- `ARCHITECTURE.md` - Canonical architecture documentation
- `ROADMAP.md` - Version scope and deliverables

**VS Code Copilot Agents**: `.github/agents/`
- 8 specialized agents: Arkitekt, Builder, CodeGen, Guardian, Manager, Planner, Sculptor, Test

## Build, Test, and Run Commands

```bash
# Development run (requires .venv with PyQt6)
./run.sh

# Run full test suite (5894+ tests)
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_commands.py -v

# Run with coverage
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=term-missing

# Lint
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203

# Type check
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary

# Build RPM
bash scripts/build_rpm.sh
```

## Key Architecture Rules

1. **Never use `sudo`** - Only `pkexec` via `PrivilegedCommand`
2. **Never hardcode `dnf`** - Use `SystemManager.get_package_manager()`
3. **Never put subprocess in UI** - Extract to `utils/`, call via `CommandRunner`
4. **Always unpack PrivilegedCommand** - `binary, args, desc = PrivilegedCommand.dnf(...)`
5. **Always set timeout** on subprocess calls
6. **Always branch on `SystemManager.is_atomic()`** for dnf vs rpm-ostree
7. **Always audit log** privileged actions

## MCP Configuration

MCP (Model Context Protocol) servers are configured in `.copilot/mcp-config.json`:
- GitHub MCP server for PR/issue management
- Loofi workflow server for workflow automation

See `docs/mcp-setup.md` for detailed setup instructions.

## Setup Steps for CI/CD

See `.github/workflows/copilot-setup-steps.yml` for the complete environment setup:
- Python 3.12
- System dependencies (libegl1)
- PyQt6 with offscreen rendering
- Dev tools (pytest, flake8, mypy, bandit)

---

For complete instructions, see [.github/copilot-instructions.md](.github/copilot-instructions.md)
