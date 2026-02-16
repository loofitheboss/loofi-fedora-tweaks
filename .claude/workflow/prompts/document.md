# Prompt: P5 DOC Phase (State-File)

> Agent: release-planner | Model: GPT-4o-mini | Cost: LABOR-LIGHT

ROLE: Technical Writer
INPUT: `.workflow/specs/tasks-vXX.md` + `.workflow/specs/release-notes-draft-vXX.md` + git diff + AGENTS.md (conventions)
GOAL: Finalize release documentation to match actual code changes.

INSTRUCTIONS:
1. Reconcile task artifact + draft notes against implemented diff.
2. Read AGENTS.md for documentation conventions.
3. Update `CHANGELOG.md` (Keep-a-Changelog format):
   - Categories: Added, Changed, Fixed, Deprecated, Removed, Security
   - Imperative mood entries
   - Link to issue/PR if applicable
4. Update `README.md` only where behavior/commands changed.
5. Create or update `docs/releases/RELEASE-NOTES-vXX.md`:
   - Max 8 bullets in highlights
   - Include upgrade notes if breaking changes
   - Reference critical rules from AGENTS.md if new patterns introduced
6. Keep entries concise and non-duplicative.

CHANGELOG FORMAT:
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description
```

RULES:
- Imperative changelog entries ("Add feature", not "Added feature").
- Max 8 bullets in release notes highlights.
- Do not invent unimplemented features.
- Document any new critical rules or patterns from AGENTS.md.

EXIT CRITERIA:
- [ ] CHANGELOG updated with version entry
- [ ] RELEASE-NOTES updated or created
- [ ] README aligned with current behavior (if applicable)
- [ ] All docs follow project conventions
