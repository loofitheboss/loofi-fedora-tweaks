# loofi-fedora-tweaks — Vibe Coding Autopilot (low-cost)

## Prime directive
- I (Cline) do the coding. User does not write code.
- Optimize for minimal cost: smallest context, smallest diffs, shortest messages.
- Never scan the entire repo. Never open folders recursively.

## Workflow: Plan → Act → Verify → Summarize
1) PLAN (always first, max 8 bullets)
   - State goal in 1 line.
   - List EXACT files to open (max 3).
   - List actions + success criteria.
   - Ask ONE yes/no question: "Proceed?"
2) ACT
   - Make the smallest possible patch to achieve success criteria.
   - Prefer editing existing code; avoid refactors unless required.
3) VERIFY
   - Run the minimum tests/commands needed to validate.
   - If commands are unknown, open relevant scripts/docs first (do not guess).
4) SUMMARIZE (max 10 lines)
   - What changed + where.
   - How to run/verify.
   - Write a short note to memory-bank/DEV_NOTES.md and stop.

## Context discipline (token control)
- Open at most 3 files per cycle.
- If more context is needed: ask to open next 1–2 files, not more.
- Do not paste large file contents into chat; rely on opened files.
- If logs are long: ask user for ONLY the last ~60 lines or the error block.
- If conversation grows: write status to memory-bank and start a new task.

## Automation defaults
- Make a branch name suggestion: vibe/<short-topic>
- After successful verify:
  - Provide a commit message (Conventional Commits style).
  - Provide PR title + 5-line PR description.
- Always propose next smallest task as an option.

## Coding standards
- Python: explicit errors, no bare `except:`.
- Keep UI separate from system actions where possible.
- Avoid adding new dependencies unless essential.
- Prefer deterministic behavior and clear user-facing messages.

## Safety
- Treat system tweaks as potentially destructive.
- Before any command that changes system state (install/remove packages, write to /etc, permissions, services):
  - Ask for explicit confirmation.
- For read-only commands/tests, proceed.

## Repo-specific hints
- Prefer existing scripts if present: run.sh, install.sh, build_rpm.sh, build_flatpak.sh.
- Tests live under ./tests (update if behavior changes).
- Flatpak/RPM assets exist; do not modify packaging unless asked.

## Output formatting (strict)
- PLAN: bullets only.
- ACT: patch summary only.
- VERIFY: commands + result only.
- SUMMARIZE: max 10 lines.
- No long explanations unless user asks.
