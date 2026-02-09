# Release Planner Memory

## Release Process Pattern

### Version Bump Locations (v21.0.0)
1. `/loofi-fedora-tweaks/version.py` — `__version__` and `__version_codename__`
2. `/loofi-fedora-tweaks.spec` — `Version:` and `Release:` fields
3. Spec file `%changelog` section — add new entry at top
4. `CHANGELOG.md` — add new section at top with Keep-a-Changelog format
5. `README.md` — update version badges, download URLs, build output paths
6. Create `RELEASE-NOTES-v{VERSION}.md` for GitHub release

### Packaging Scripts Validated (v23.0.0+)
- All scripts now in `scripts/` directory
- `scripts/build_rpm.sh` — dynamically reads version from version.py, no hardcoded version
- `scripts/build_flatpak.sh` — stub (planned for v23.1+)
- `scripts/build_appimage.sh` — stub (planned for v23.1+)
- `scripts/build_sdist.sh` — stub (planned for v23.1+)

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
**Theme**: Service layer refactor, executor abstraction, build consolidation

**Architecture Changes**:
1. BaseActionExecutor ABC with pkexec integration
2. ActionExecutor refactored to subclass BaseActionExecutor
3. BaseWorker QThread pattern in core/workers/
4. System services migrated to services/system/
5. Hardware services migrated to services/hardware/
6. Build scripts consolidated to scripts/
7. 34 import validation tests
8. Backward-compat shims with deprecation warnings

**Files Modified**: version.py (23.0.0, "Architecture Hardening"), loofi-fedora-tweaks.spec, CHANGELOG.md, README.md
**Files Created**: RELEASE-NOTES-v23.0.0.md
**Test Count**: 1715 passing

### v21.0.0 "UX Stabilization & Layout Integrity" (2026-02-09)
**Theme**: Layout fixes, HiDPI safety, theme consistency

**7 Tasks Documented**:
1. Baseline layout-integrity fixes (native title bar, border cleanup, documentMode)
2. Scoped QTabBar scroller styling
3. Min window size (800x500) + consistent margins
4. HiDPI safety (font-metrics-based sizing, pt units)
5. Frameless mode feature flag (stub)
6. Layout regression tests
7. Theme-aware inline styles (top-3 fixes)

**Files Modified**: version.py, loofi-fedora-tweaks.spec, CHANGELOG.md, README.md
**Files Created**: RELEASE-NOTES-v21.0.0.md
