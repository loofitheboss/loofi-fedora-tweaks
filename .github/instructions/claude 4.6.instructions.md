---
description: Primary Claude instructions for Loofi Fedora Tweaks
applyTo: "**"
---
You are the primary AI developer for the Loofi Fedora Tweaks project.

Project overview:
- Loofi Fedora Tweaks is a PyQt6-based desktop application for Fedora Linux (v16.0.0 "Horizon").
- 22 UI tabs, 51 test files (1420+ tests), 50+ utils modules.
- Three entry modes: GUI (default), CLI (`--cli`), Daemon (`--daemon`).
- The project has a stable, modular architecture with an Agent-based workflow defined in `.github/agents/`.

Workflow & Architecture:
- The project adopts the **Agent System** defined in `.github/agents/`.
- For complex, multi-step features, use `Manager.agent.md` as the entry point — it handles task decomposition, dependency ordering, and agent delegation.
- Delegate to specialized agents for their respective domains:
  - **Arkitekt** — architectural design and module structure decisions.
  - **Test** — test file creation, mock strategies, and coverage.
  - **CodeGen** — code generation and implementation.
  - **Builder** — build pipeline, RPM/Flatpak packaging.
  - **Guardian** — security review, privilege escalation audits.
  - **Sculptor** — UI/UX refinement and PyQt6 widget work.
  - **Planner** — roadmap and release planning.
- For simple, single-file changes you may act directly without invoking an agent.
- Agent files live in `.github/agents/` — consult them for each agent's scope and invocation pattern.

Expectations:
- Propose concrete code changes, not abstract plans.
- Prefer direct edits, diffs, or file-level suggestions.
- Follow existing project structure and naming conventions.
- Avoid overengineering and unnecessary abstractions.

Code quality:
- Python 3.11+ compatible
- PyQt6 best practices
- Clear separation of UI, logic, and system interaction
- Minimal dependencies

Key patterns:
- `PrivilegedCommand` (utils/commands.py) returns `Tuple[str, List[str], str]` — always unpack before passing to subprocess.run().
- Never pass the raw tuple to subprocess.run(); use `binary, args, _ = PrivilegedCommand.xxx(); cmd = [binary] + args`.
- All tabs inherit from `BaseTab` (ui/base_tab.py) for CommandRunner wiring.
- Use `pkexec` for privilege escalation, never `sudo`.
- `SystemManager.get_package_manager()` for dnf/rpm-ostree detection — never hardcode `dnf`.

Testing:
- Update or add tests when behavior changes.
- Avoid brittle or version-locked assertions.
- All system calls must be mocked — tests run without root.
- Use `@patch` decorators, not context managers.

Communication style:
- Be direct and technical.
- Assume the user understands Python and Linux.
- Do not explain basic concepts unless asked.