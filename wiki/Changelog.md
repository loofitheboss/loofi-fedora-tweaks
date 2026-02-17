# Changelog

Version history highlights for Loofi Fedora Tweaks.

For the complete changelog with all changes, see [CHANGELOG.md](https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/CHANGELOG.md) in the repository.

---

## Latest Release

### v46.0.0 "Navigator" (2026-02-17)

**Navigation clarity release** focused on taxonomy consistency and release packaging alignment.

**Key Changes:**
- Sidebar categories standardized to technical groups (`System`, `Packages`, `Hardware`, `Network`, `Security`, `Appearance`, `Tools`, `Maintenance`)
- Tab metadata categories/orders aligned with registry definitions
- Command palette category grouping aligned with sidebar taxonomy
- Release pipeline gate fixes (workflow specs + race-lock alignment)
- Release assets published: RPM, Flatpak, and source tarball

**Test Suite**: 5,936 collected (5,901 passed, 35 skipped)

---

## Recent Releases

### v41.0.0 "Coverage" (2026-02-15)

**Test coverage push release** with zero production code changes. Coverage raised from 74% to 80%+ and CI pipeline hardened.

**Key Changes:**
- Coverage raised from 74% to 80%+ (30,653 stmts, 6,125 missed)
- 23 test files created or expanded (~1,900 new tests, 5,894 total)
- `dorny/test-reporter` renders JUnit XML as GitHub check annotations
- RPM post-install smoke test gates every release build
- Coverage threshold bumped from 74 to 80 in ci.yml, auto-release.yml, coverage-gate.yml

**Test Suite**: 5,894 tests collected, 80% coverage

---

### v40.0.0 "Foundation" (2026-02-14)

**Security hardening release** with subprocess timeout enforcement, shell injection elimination, and privilege escalation cleanup.

**Key Changes:**
- Added explicit `timeout=` parameters to all subprocess calls
- Refactored all `pkexec sh -c` calls to atomic commands
- Replaced all `sudo dnf` messages with `pkexec dnf`
- Converted 21 f-string logger calls to `%s` formatting
- Fixed 141 silent exception blocks to log errors
- Hardcoded `dnf` references replaced with `SystemManager.get_package_manager()`

**Test Suite**: 4,329 tests passing (up from 4,326)

---

### v39.0.0 "Prism" (2026-02-14)

**Services layer migration release** with zero deprecated imports, zero inline styles, zero DeprecationWarnings.

**Highlights:**
- 27 production + 13 test file imports migrated from `utils.*` to `services.*`
- 175+ `setStyleSheet` calls replaced with `setObjectName` + QSS rules across 31 UI files
- 9 deprecated shim modules removed
- ~600 new QSS rules in both dark and light themes

**Test Suite**: 4,367 tests passing

### v38.0.0 "Clarity" (2025-07-22)

**UX polish release** with theme correctness, Doctor tab rewrite, and new UI features.

**Highlights:**
- Doctor Tab rewrite using modern patterns
- Dynamic username on Dashboard
- All 16 Quick Actions wired
- Theme correctness (14 inline styles → objectNames)
- Undo button in status bar
- Toast notification system
- Output toolbar (Copy/Save/Cancel)
- Risk badges (LOW/MEDIUM/HIGH)
- ~200 new QSS rules for both dark and light themes

**Test Suite**: 4349 tests passing

### v37.0.0 "Pinnacle" (2025-07-21)

**Feature expansion release** with smart updates, extension management, and backup wizard.

**New Features:**
- Smart Update Manager (schedule updates, rollback, preview)
- Extension Manager (GNOME/KDE extensions)
- Flatpak Manager (audit, orphans, cleanup)
- Boot Configuration Manager (GRUB, kernels)
- Wayland Display Manager (fractional scaling)
- Backup Wizard (Timeshift, Snapper, restic)
- Risk Registry (centralized risk assessment)

**New Tabs**: Extensions, Backup (26 → 28 tabs)

**Test Suite**: 76 new tests

### v35.0.0 "Fortress" (2025-07-19)

**Security hardening release** with timeout enforcement and structured audit logging.

**Security Features:**
- Subprocess timeout enforcement (all calls have mandatory timeouts)
- Structured audit logging (JSONL format, auto-rotation)
- Granular Polkit policies (7 purpose-scoped files)
- Parameter validation (`@validated_action` decorator)
- CLI `--dry-run` and `--timeout` flags

**Test Suite**: 54 new tests

### v34.0.0 "Citadel" (2025-07-18)

**Polish-only release** with light theme fix and stability hardening.

**Improvements:**
- Light theme completely rewritten (Catppuccin Latte palette)
- CommandRunner hardened (timeouts, terminate→kill escalation)
- Zero subprocess in UI (extracted to utils/)
- 21 silent exceptions fixed (all now log with `exc_info=True`)
- Accessibility (314 `setAccessibleName()` calls)

**Test Suite**: 4061 tests passing (85 new tests)

### v33.0.0 "Bastion" (2025-07-17)

**Type safety release** with full mypy compliance.

**Fixes:**
- 163 mypy type errors → 0
- All test failures resolved (3958 tests passing)
- Fixed SecurityTab static method calls
- Fixed pulse.py upower parsing

### v32.0.0 "Abyss" (2026-02-13)

**Visual redesign release** with new "Loofi Abyss" color palette.

**New:**
- Complete visual redesign (Abyss dark/light themes)
- Activity-based category navigation (10 → 8 categories)
- Category emoji icons
- Sidebar collapse toggle
- Explicit category sort order

**Changed:**
- QSS rewrite for both themes (~560 lines each)
- 26 tab locations reorganized
- All inline colors migrated to Abyss palette

---

## Version History (v25.0.0 - v31.0.0)

### v31.0.0 "Smart UX" (2026-02-13)

- Smart table visibility fixes
- Empty state rows for all tables
- Explicit item foreground coloring
- QSS table styling improvements

### v30.0.0 "Distribution & Reliability" (2026-02-13)

- Distribution improvements
- Reliability enhancements
- Stability fixes

### v29.0.0 "Usability & Polish" (2026-02-13)

- Usability improvements
- UI polish and refinements
- Error handling enhancements

### v28.0.0 "Workflow Contract Reset" (2026-02-12)

- Workflow system overhaul
- Contract marker implementation
- Pipeline improvements

### v27.0.0 "Marketplace Enhancement" (2026-02-12)

**Plugin Marketplace release**

**New:**
- Plugin marketplace with CDN-first signed index
- Plugin installer with integrity verification
- Plugin sandboxing and permission enforcement
- Plugin dependency resolution
- Auto-update service
- Ratings and reviews support

### v26.0.0 "Teleport" (2026-02-11)

**State capture and restore**

**New:**
- State Teleport tab (workspace capture/restore)
- Workspace snapshot management
- Export/import workspace profiles

### v25.0.0 "Mesh" (2026-02-10)

**Mesh networking release**

**New:**
- Loofi Link tab (mesh networking)
- mDNS discovery (Avahi)
- Clipboard sync across devices
- File drop between Loofi instances

---

## Development Milestones

| Version | Codename | Date | Milestone |
|---------|----------|------|-----------|
| v41.0.0 | Coverage | 2026-02-15 | 80% coverage, 5894 tests |
| v40.0.0 | Foundation | 2026-02-14 | Security hardening complete |
| v38.0.0 | Clarity | 2025-07-22 | UX polish, 4349 tests |
| v37.0.0 | Pinnacle | 2025-07-21 | 28 tabs, backup wizard |
| v35.0.0 | Fortress | 2025-07-19 | Audit logging, timeout enforcement |
| v34.0.0 | Citadel | 2025-07-18 | 4061 tests, 74% coverage |
| v33.0.0 | Bastion | 2025-07-17 | Zero mypy errors |
| v32.0.0 | Abyss | 2026-02-13 | Abyss theme, 8 categories |
| v27.0.0 | Marketplace | 2026-02-12 | Plugin marketplace |
| v25.0.0 | Mesh | 2026-02-10 | Loofi Link networking |

---

## Statistics

**Current (v41.0.0):**
- **Tests**: 5,894 collected
- **Coverage**: 80%
- **Test files**: 193
- **Tabs**: 28
- **Utils modules**: 106
- **CLI commands**: 40+
- **Lines of code**: ~55,000

---

## Release Naming

Each major/minor release has a thematic codename:

- **v41**: "Coverage" — Test coverage milestone
- **v40**: "Foundation" — Core stability
- **v39**: "Prism" — Services migration
- **v38**: "Clarity" — UX refinement
- **v37**: "Pinnacle" — Feature completeness
- **v35**: "Fortress" — Security hardening
- **v34**: "Citadel" — Quality gates
- **v33**: "Bastion" — Type safety
- **v32**: "Abyss" — Visual identity

---

## Future Roadmap

See [ROADMAP.md](https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/ROADMAP.md) for:
- Planned features
- Version targets
- Development phases
- Long-term vision

---

## Full Changelog

For detailed release notes and complete changelogs:

- **Repository**: [CHANGELOG.md](https://github.com/loofitheboss/loofi-fedora-tweaks/blob/master/CHANGELOG.md)
- **Release Notes**: [docs/releases/](https://github.com/loofitheboss/loofi-fedora-tweaks/tree/master/docs/releases)
- **GitHub Releases**: [Releases page](https://github.com/loofitheboss/loofi-fedora-tweaks/releases)

---

## Next Steps

- [Installation](Installation) — Install latest version
- [Getting Started](Getting-Started) — Learn what's new
- [Contributing](Contributing) — Contribute to next release
