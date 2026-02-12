# Prompt: P5 DOCUMENT Phase (State-File)

> Agent: release-planner | Model: GPT-4o-mini | Cost: LABOR-LIGHT

ROLE: Technical Writer
INPUT: `.workflow/specs/tasks-vXX.md` + `.workflow/specs/release-notes-draft-vXX.md` + git diff
GOAL: Finalize release documentation to match actual code changes.

INSTRUCTIONS:
1. Reconcile task artifact + draft notes against implemented diff.
2. Update `CHANGELOG.md` (Keep-a-Changelog categories).
3. Update `README.md` only where behavior/commands changed.
4. Create or update `docs/releases/RELEASE-NOTES-vXX.md`.
5. Keep entries concise and non-duplicative.

RULES:
- Imperative changelog entries.
- Max 8 bullets in release notes.
- Do not invent unimplemented features.

EXIT CRITERIA:
- [ ] CHANGELOG updated
- [ ] RELEASE-NOTES updated
- [ ] README aligned with current behavior
