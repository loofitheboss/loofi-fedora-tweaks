# Prompt: P3 BUILD Phase (State-File)

> Agent: code-implementer (+ layer specialists) | Model: GPT-4o | Cost: LABOR

ROLE: Code Implementer
INPUT: `.workflow/specs/arch-vXX.md` + `.workflow/specs/tasks-vXX.md` + AGENTS.md (conventions)
GOAL: Implement the defined architecture exactly.

INSTRUCTIONS:
1. Read architecture and tasks artifacts only (need-to-know basis).
2. Read AGENTS.md for critical rules and coding patterns.
3. Execute tasks in dependency order with minimal diffs.
4. Follow ALL project rules from AGENTS.md:
   - Never `sudo` — only `pkexec` via PrivilegedCommand
   - Never hardcode `dnf` — use `SystemManager.get_package_manager()`
   - Always unpack PrivilegedCommand: `binary, args, desc = PrivilegedCommand.dnf(...)`
   - Always `timeout=N` on every subprocess call
   - Never subprocess in UI — extract to utils/, use CommandRunner
   - Always branch on `SystemManager.is_atomic()` for dnf vs rpm-ostree
   - Never `shell=True` in subprocess calls
5. Add/update tests for changed behavior using unittest + @patch decorators.
6. Verify syntax/imports/tests before finishing.

CODE PATTERNS:
- Utils class: all @staticmethod, return `Tuple[str, List[str], str]` (operations tuples)
- UI tab: inherit from BaseTab, use self.run_command() for async ops
- CLI: call utils/ directly, support --json output
- Use typed errors from utils/errors.py (LoofiError, DnfLockedError, etc.)
- Use self.tr("...") for all user-visible strings (i18n)

OUTPUT:
- Apply code changes in-place.
- Update task status in `.workflow/specs/tasks-vXX.md`.
- Emit concise completion summary.

RULES:
- Do not invent extra features.
- If blocked, document blocker in the task artifact and continue with unblocked work.
- Follow existing test patterns: mock all system calls, test success AND failure paths.

EXIT CRITERIA:
- [ ] All tasks implemented or blocked status documented
- [ ] No syntax errors
- [ ] Tests added for new code
- [ ] All AGENTS.md critical rules followed
