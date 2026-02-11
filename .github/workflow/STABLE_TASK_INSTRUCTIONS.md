# Stable Task Instructions (Codex + Claude Code + Copilot)

## Goal
- Keep all tools aligned to one workflow from roadmap -> plan -> build -> test -> doc -> package -> release.
- Always use `.workflow/specs/` artifacts as the source of truth, never chat memory.

## Non-Negotiable Rules
1. Read `AGENTS.md` and obey scope rules before editing files.
2. Make minimal diffs and preserve existing architecture patterns.
3. Update docs first-class: README, changelog/release notes, and workflow artifacts.
4. Every change must include at least one validation command.
5. Use the same target version tag across all phases (race lock discipline).

## Phase Contract
- **Plan**: update `tasks-vXX.md` from `ROADMAP.md`.
- **Design**: produce/refresh `arch-vXX.md` and release-notes draft.
- **Build**: implement only what tasks + architecture specify.
- **Test**: run relevant tests and summarize failures with actionable fixes.
- **Doc**: sync README/release notes/changelog with implemented scope.
- **Package**: verify `version.py` and `.spec` alignment.
- **Release**: finalize release checklist and GitHub-ready notes.

## Cross-Tool Handoff Format
When switching tools, pass only:
- `.workflow/context/vXX/context.md`
- `.workflow/context/vXX/handoff.json`
- Changed file list (`git status --short`)

## Token & Cost Controls
- One phase = one fresh chat/session.
- Load excerpts, not whole files, unless actively editing them.
- Prefer artifact references and diffs over narrative recaps.
- Escalate to high-reasoning models only for plan/design blockers.

## VS Code Daily Loop
1. Run `Workflow: Sync AI Context` task.
2. Run one phase task (plan/design/build/test/doc/package/release).
3. Commit phase result with phase-prefixed message (`workflow(plan): ...`).
4. Open PR when release/doc artifacts are coherent.
