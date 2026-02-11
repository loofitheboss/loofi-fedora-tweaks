# Prompt: P3 IMPLEMENT Phase (State-File)

> Agent: code-implementer (+ layer specialists) | Model: GPT-4o | Cost: LABOR

ROLE: Code Implementer
INPUT: `.workflow/specs/arch-vXX.md` + `.workflow/specs/tasks-vXX.md`
GOAL: Implement the defined architecture exactly.

INSTRUCTIONS:
1. Read architecture and tasks artifacts only (need-to-know basis).
2. Execute tasks in dependency order with minimal diffs.
3. Follow project rules: no subprocess in UI, no sudo, no hardcoded dnf.
4. Add/update tests for changed behavior.
5. Verify syntax/imports/tests before finishing.

OUTPUT:
- Apply code changes in-place.
- Update task status in `.workflow/specs/tasks-vXX.md`.
- Emit concise completion summary.

RULES:
- Do not invent extra features.
- If blocked, document blocker in the task artifact and continue with unblocked work.
