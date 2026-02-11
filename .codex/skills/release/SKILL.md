---
name: release
description: Execute documentation, packaging, and release phases (P5-P7) for a version.
---

# Release Phases (P5 + P6 + P7)

## P5: Document
1. Update `CHANGELOG.md` — Keep-a-Changelog format
2. Update `README.md` — version references, features
3. Create `RELEASE-NOTES-v{VERSION}.md`
4. Verify version strings aligned:
   - `loofi-fedora-tweaks/version.py`: `__version__`
   - `loofi-fedora-tweaks.spec`: `Version:`

## P6: Package
1. Verify version alignment
2. Validate `scripts/build_rpm.sh` is executable
3. Check other build scripts exist

## P7: Release
1. Commit all changes
2. Create tag: `v{VERSION}`
3. Push tag (triggers `.github/workflows/auto-release.yml`)
4. Update `ROADMAP.md`: version status → DONE

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
- No undocumented changes
- Max 8 bullets in release notes
- Reference `.github/workflow/prompts/document.md`, `package.md`, `release.md`
