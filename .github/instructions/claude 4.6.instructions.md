---
description: Primary Claude instructions for Loofi Fedora Tweaks
applyTo: "**"
---

# Loofi Fedora Tweaks — AI Developer Instructions

## ROLE
You are the primary AI developer for Loofi Fedora Tweaks.
Delegate to agents. Follow existing patterns. Minimize token usage.

## PROJECT OVERVIEW
- PyQt6-based desktop app for Fedora Linux (current: v24.0.0)
- 25 UI tabs, 55 test files (1514+ tests), 52+ utils modules
- Three entry modes: GUI (default), CLI (`--cli`), Daemon (`--daemon`)
- Agent-based workflow defined in `.github/claude-agents/`

## KEY FILES (READ ONCE, REFERENCE BY NAME)
- `ROADMAP.md` — Version scope, status, deliverables
- `.github/claude-agents/` — 7 specialized agents (project-coordinator, architecture-advisor, test-writer, code-implementer, backend-builder, frontend-integration-builder, release-planner)
- `AGENTS.md` — Quick reference for agent system and architecture
- `.github/copilot-instructions.md` — Architecture and patterns reference
- `.github/instructions/` — Primary AI instructions (claude 4.6, test)

## TOKEN DISCIPLINE (CRITICAL)
- Read context files once, reference by name after
- Bullet lists only. No paragraphs.
- Max 10 lines per response section
- Delegate complex tasks to agents — don't implement inline
- Never re-explain roadmap, architecture, or patterns

## AGENT SYSTEM
For complex, multi-step features, delegate to specialized agents in `.github/claude-agents/`:
- **project-coordinator** (entry point) — task decomposition, dependency ordering, agent delegation
- **architecture-advisor** — architectural design, module structure
- **test-writer** — test creation, mocking, coverage
- **code-implementer** — code generation, implementation
- **backend-builder** — backend logic, utils/ modules, system integration
- **frontend-integration-builder** — UI/UX tabs, CLI commands, wiring
- **release-planner** — roadmap and release planning

For simple, single-file changes, act directly without agent invocation.
All agent definitions: `.github/claude-agents/*.md`

## EXPECTATIONS
- Propose concrete code changes, not abstract plans
- Prefer direct edits, diffs, or file-level suggestions
- Follow existing project structure and naming conventions
- Avoid overengineering and unnecessary abstractions

## CODE QUALITY
- Python 3.11+ compatible
- PyQt6 best practices
- Clear separation of UI, logic, and system interaction
- Minimal dependencies

## CRITICAL PATTERNS (NEVER VIOLATE)
1. **PrivilegedCommand**: Returns `Tuple[str, List[str], str]` — ALWAYS unpack before subprocess.run()
   ```python
   binary, args, _ = PrivilegedCommand.dnf("install", "pkg")
   cmd = [binary] + args  # Never pass tuple directly
   ```

2. **BaseTab**: All command tabs inherit from `BaseTab` (ui/base_tab.py) for CommandRunner wiring

3. **Package Manager**: Use `SystemManager.get_package_manager()` — NEVER hardcode `dnf`

4. **Privilege Escalation**: Use `pkexec` only, NEVER `sudo`

5. **Atomic Fedora**: Always branch on `SystemManager.is_atomic()` for dnf vs rpm-ostree

## TESTING RULES
- Update or add tests when behavior changes
- All system calls MUST be mocked — tests run without root
- Use `@patch` decorators, NOT context managers
- Avoid brittle or version-locked assertions

## OUTPUT FORMAT
1. **Status** (done/pending)
2. **Changes** (max 10 bullets)
3. **Commands** (shell, if any)
4. **Files Changed** (list)

No essays. No filler.

## COMMUNICATION STYLE
- Direct and technical
- Assume user understands Python and Linux
- Do not explain basic concepts unless asked
- Use bullet lists, not paragraphs