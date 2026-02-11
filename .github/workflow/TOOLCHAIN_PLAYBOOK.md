# VS Code Toolchain Playbook (Copilot + Claude Code + Codex)

## What This Solves
- One shared workflow from roadmap to GitHub release.
- Stable instruction pack for every task.
- Fast handoff between tools without re-explaining context.

## Single Sources of Truth
- `ROADMAP.md` for feature scope.
- `.workflow/specs/` for phase outputs.
- `.github/workflow/STABLE_TASK_INSTRUCTIONS.md` for shared rules.
- `.workflow/context/vXX/` for compact handoff bundles.

## Daily Workflow
1. Run VS Code task: **Workflow: Sync AI Context**.
2. Pick one phase task (Plan/Design/Build/Test/Doc/Package/Release).
3. Use generated `.workflow/context/vXX/context.md` in any assistant.
4. Commit after each phase.
5. Push and open PR after doc + package + release checks are consistent.

## Which Tool to Use
- **Codex / GPT Codex**: plan/design and complex architecture decisions.
- **Claude Code (Opus/Sonnet)**: implementation + refactor + test iteration.
- **GitHub Copilot Chat**: inline edits, quick fixes, and editor-native follow-ups.

## Handoff Protocol (Cost-Effective)
When switching tools, share only:
- `.workflow/context/vXX/context.md`
- `.workflow/context/vXX/handoff.json`
- Current `git diff` / changed file list

This avoids replaying full conversation history and keeps tokens predictable.

## GitHub Plan -> Release Mapping
- Plan/Design update `.workflow/specs/*` artifacts.
- Build/Test update code and tests.
- Doc update release notes, changelog, README.
- Package validates version alignment.
- Release phase prepares GitHub release checklist and PR narrative.
