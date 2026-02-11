# Release Planner Memory

## Workflow System (v23.0+)

### My Pipeline Phases
- P5 DOCUMENT: CHANGELOG, README, release notes, version strings
- P6 PACKAGE: Validate build scripts, version alignment
- P7 RELEASE: Branch, tag, push, GitHub Release

### Prompts
- `.github/workflow/prompts/document.md`
- `.github/workflow/prompts/package.md`
- `.github/workflow/prompts/release.md`

### Cost Model
- I run on haiku (cheapest tier)
- Docs, version bumps, packaging = all haiku-level work
- Never need opus/sonnet for my phases

## Release Process Pattern

### Version Bump Locations
1. `/loofi-fedora-tweaks/version.py` — `__version__` and `__version_codename__`
2. `/loofi-fedora-tweaks.spec` — `Version:` and `Release:` fields
3. Spec file `%changelog` section — add new entry at top
4. `CHANGELOG.md` — add new section at top with Keep-a-Changelog format
5. `README.md` — update version badges, download URLs, build output paths
6. Create `RELEASE-NOTES-v{VERSION}.md` for GitHub release

### Packaging Scripts (v23.0.0+)
- All scripts in `scripts/` directory
- `scripts/build_rpm.sh` — dynamically reads version from version.py
- `scripts/build_flatpak.sh` — stub (planned for v23.1+)
- `scripts/build_appimage.sh` — stub
- `scripts/build_sdist.sh` — stub
- `scripts/workflow-runner.sh` — CLI for pipeline execution

### GitHub Workflows
- `.github/workflows/ci.yml` — lint + typecheck + security + test + build
- `.github/workflows/release.yml` — Tag-triggered release (legacy)
- `.github/workflows/auto-release.yml` — Enhanced: validate + lint + test + security + build + release

### CHANGELOG.md Format (Keep-a-Changelog)
```markdown
## [VERSION] - YYYY-MM-DD "Codename"

### Changed / Added / Fixed / Security

- **Feature Name**: Description with technical details
```

### Release Notes Format (Max 8 Bullets)
- Title: "v{VERSION} {Codename}"
- Highlights section with 3-8 bullet points
- Installation instructions
- Testing info
- Link to full CHANGELOG.md

## Completed Releases

### v23.0.0 "Architecture Hardening" (2026-02-09)
**Files Modified**: version.py (23.0.0), loofi-fedora-tweaks.spec, CHANGELOG.md, README.md
**Files Created**: RELEASE-NOTES-v23.0.0.md
**Test Count**: 1715 passing

### v21.0.0 "UX Stabilization & Layout Integrity" (2026-02-09)
**Files Modified**: version.py, loofi-fedora-tweaks.spec, CHANGELOG.md, README.md
**Files Created**: RELEASE-NOTES-v21.0.0.md
