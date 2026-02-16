# Prompt: P2 DESIGN Phase (State-File)

> Agent: architecture-advisor | Model: GPT-5.3 Codex | Cost: BRAIN

ROLE: Architecture Advisor
INPUT: `.workflow/specs/tasks-vXX.md`, AGENTS.md (conventions)
GOAL: Create implementation blueprint + pre-doc draft artifact.

INSTRUCTIONS:
1. Review tasks for architecture risks and pattern violations.
2. Verify alignment with AGENTS.md critical rules and ARCHITECTURE.md patterns.
3. Define exact signatures/structures needed for implementation.
4. Write architecture blueprint to `.workflow/specs/arch-vXX.md`.
5. Write pre-documentation draft to `.workflow/specs/release-notes-draft-vXX.md`.
6. Do not emit conversational output.

CRITICAL PATTERNS TO ENFORCE (from AGENTS.md):
- PrivilegedCommand: Always unpack tuple — `binary, args, desc = PrivilegedCommand.dnf(...)`
- Never `sudo` — only `pkexec` via PrivilegedCommand
- Never hardcode `dnf` — use `SystemManager.get_package_manager()`
- Always branch on `SystemManager.is_atomic()` for Atomic vs Traditional Fedora
- Always `timeout=N` on every subprocess call
- UI tabs: inherit BaseTab, use CommandRunner (never subprocess in UI)
- Utils modules: @staticmethod only, return operations tuples
- Audit log privileged actions (timestamp, action, params, exit code)

CHECKS:
- Fedora patterns respected (BaseTab, PrivilegedCommand unpacking, SystemManager PM detection).
- Dependencies are acyclic and implementable.
- Risky changes include mitigation notes.
- No shell=True in subprocess calls.

EXIT CRITERIA:
- [ ] `arch-vXX.md` exists and is implementation-ready
- [ ] `release-notes-draft-vXX.md` exists
- [ ] No unresolved blocking concerns
- [ ] All designs follow AGENTS.md critical rules
