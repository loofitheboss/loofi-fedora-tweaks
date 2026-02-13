````skill
---
name: doc
description: Update documentation (CHANGELOG, README, release notes) for the current version.
---

# Document Phase (P5)

## Steps
1. Read `.workflow/specs/tasks-v{VERSION}.md` — gather all completed tasks
2. Read `loofi-fedora-tweaks/version.py` for version and codename
3. Update `CHANGELOG.md`:
   - Keep-a-Changelog format (`## [{VERSION}] - YYYY-MM-DD "{Codename}"`)
   - Sections: Added, Changed, Fixed, Removed
   - Imperative mood, max 8 bullets per section
4. Update `README.md`:
   - Version references
   - Feature list (if new tabs/capabilities)
   - Badge versions
5. Create `docs/releases/RELEASE-NOTES-v{VERSION}.md`:
   - 3-5 sentence overview
   - Highlight list (max 8 items)
   - Upgrade notes if breaking changes
6. Verify version alignment:
   - `loofi-fedora-tweaks/version.py`: `__version__`
   - `loofi-fedora-tweaks.spec`: `Version:`

## CHANGELOG Format
```markdown
## [{VERSION}] - YYYY-MM-DD "{Codename}"

### Added
- Feature description (imperative mood)

### Changed
- Change description

### Fixed
- Fix description
```

## Rules
- Must complete P4 (Test) before starting P5
- No undocumented changes — every task maps to a CHANGELOG entry
- Reference `.github/workflow/prompts/document.md` for full prompt

````
