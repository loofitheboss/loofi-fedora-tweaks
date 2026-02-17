# Universal Roadmap / UX / Quality Audit & Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Comprehensive codebase audit and multi-release roadmap for Loofi Fedora Tweaks, covering features, UX, bugs, quality, compliance, and documentation.

**Architecture:** PyQt6 desktop app, 29 feature tabs, 107 utils modules, CLI + daemon modes, plugin marketplace, 82% test coverage, Fedora Linux target.

**Tech Stack:** Python 3.12+, PyQt6, subprocess/pkexec, RPM/Flatpak/AppImage packaging, GitHub Actions CI.

---

# 1. Current State Summary

**What the product does:** Loofi Fedora Tweaks is a comprehensive Fedora Linux system management tool providing GUI, CLI, and daemon interfaces for system configuration, maintenance, monitoring, security, networking, gaming, development, virtualization, and automation tasks. It uses pkexec for privilege escalation and supports both traditional Fedora (dnf) and Atomic Fedora (rpm-ostree).

**Key user journeys:**
- Post-install system setup via first-run wizard (detect hardware, choose use case, run health checks, apply recommended actions)
- System maintenance (updates, cleanup, overlays) via Maintenance tab or `loofi --cli maintenance`
- Hardware configuration (Bluetooth, HP tweaks, boot config, Wayland display)
- Security & privacy hardening (firewall, USBGuard, SecureBoot)
- Performance tuning (auto-tuner, zram, kernel tweaks)
- Snapshot/backup management (Timeshift/Snapper integration, state teleport)
- Plugin ecosystem (marketplace, install, rate, review third-party plugins)

**Architecture overview:** Three entry modes (GUI, CLI `--cli`, daemon `--daemon`). Strict layer separation: UI (PyQt6 widgets) -> utils (business logic, @staticmethod, subprocess) -> core/executor (ActionResult abstraction). CLI calls utils/ directly. Daemon validates against TaskAction enum. Plugin system with marketplace, sandboxing, and hot-reload.

**Build/run/test:**
- `./run.sh` for dev, `bash scripts/build_rpm.sh` for packaging
- 202 test files, ~5900 tests, 82% coverage (14 files silently excluded)
- CI: lint (flake8), typecheck (mypy), security (bandit), test + coverage gate (80%), stabilization rules checker, Fedora review gate, RPM build

**Current version:** v44.0.0 "Review Gate" (packaging/workflow hardening release)

---

# 2. Key Problems & Opportunities

## Crashers / Data Loss / Rule Violations
- **CRITICAL: `bash -c` shell in DNS test** — `network_tab.py:687` calls `self.run_command("bash", ["-c", ...])` which is `shell=True`-equivalent. Violates Critical Rule #6 (Never `shell=True`).
- **CRITICAL: Direct `systemctl reboot` without `pkexec`** — `maintenance_tab.py:639` calls `self.reboot_runner.run_command("systemctl", ["reboot"])` without privilege escalation via pkexec. Violates Critical Rule #1 (Never sudo/direct privileged commands).
- **CRITICAL: Wizard step label contradiction** — `wizard.py:394` says "Step 3: Review & Apply" but `wizard.py:437` says "Step 5 of 5: Apply". Method is named `_build_step3` but is the 5th page in the stack.

## High-Friction UX Blockers
- **Accessibility gaps:** `extensions_tab.py` and `backup_tab.py` have ZERO `setAccessibleName`/`setAccessibleDescription` calls. Only 15 of 29 feature tabs have `setToolTip` calls. Wizard objectNames are absent from all QSS files.
- **CLI discoverability:** 9 CLI arguments in `smart-updates` subcommand lack `help=` strings. CLI module docstring says `v18.0.0` (stale).
- **Empty states:** Inconsistent across tabs. Some tabs show placeholder text, others show nothing when data is unavailable.

## Medium Annoyances
- **ROADMAP.md inconsistency:** v37.0 "Pinnacle" marked DONE but all 10 deliverables still show `[ ]` (they ARE implemented). v33.0 has 3 unchecked items delivered in later versions.
- **SECURITY.md stale:** Supported versions table shows v41.x as Active — 3 major versions behind.
- **pyproject.toml incomplete:** `packages = []`, no `dependencies`, no `classifiers`, no `[project.urls]`, no `[project.scripts]` entry points. Functionally broken for `pip install`.
- **CONTRIBUTING.md not at repo root:** GitHub won't auto-link it.
- **14 test files silently excluded** via `conftest.py` `collect_ignore` — inflates coverage metrics.
- **API server has no rate limiting** on endpoints (grep for rate_limit/Limiter returned empty).

## Security Concerns
- **cloud_sync.py** stores GitHub gist token as plaintext file (0o600 permissions) — should use system keyring.
- **ActionExecutor** accepts any command string — no command allowlist validation at executor level (daemon has ALLOWED_ACTIONS, but executor doesn't).
- **API server** missing rate limiting, request size limits.

## Tech Debt
- CLI module is 3600+ lines in a single file — should be split into subcommand modules.
- All CLI imports are eager at module level — slows startup for simple commands.
- `utils/event_simulator.py` is orphaned (no production imports, only self-references).
- `agent_scheduler.py` has stub code for `action.operation` dispatch path.

---

# 3. Roadmap (Release by Release)

## v45.0 "Housekeeping" — Documentation & Quality Debt

**Theme:** Fix all documentation inconsistencies, stale metadata, and test infrastructure gaps. No feature changes.

### Feature Additions
- None (documentation/quality release)

### UI/UX Improvements
- Fix accessibility gaps in `extensions_tab.py` and `backup_tab.py` (add `setAccessibleName` calls)
- Add wizard objectNames to all 3 QSS files (modern, light, highcontrast)
- Add missing `help=` strings to 9 CLI arguments in `smart-updates` subcommand

### Bug/Error Fix Plan
- **CRITICAL:** Fix `bash -c` shell injection in `network_tab.py:687` DNS test — extract to utils/
- **CRITICAL:** Fix `maintenance_tab.py:639` direct `systemctl reboot` — must use `pkexec` via `PrivilegedCommand`
- **CRITICAL:** Fix wizard step label contradiction (`_build_step3` is actually step 5)
- **High-friction:** Fix stale CLI docstring version (v18.0.0 -> dynamic)
- **High:** Fix wizard Skip button — no confirmation, silently discards first-run
- **High:** Fix `main_window.py:86` f-string in `self.tr()` — breaks Qt Linguist extraction
- **Medium:** Fix ROADMAP.md v37.0/v33.0 unchecked items, update SECURITY.md versions
- **Medium:** Fix highcontrast.qss `bcDesc` color `#999999` — fails WCAG AA on black background

### Engineering Tasks
- Update `pyproject.toml`: add `dependencies`, `classifiers`, `[project.urls]`, `[project.scripts]`, fix `packages`
- Move `docs/CONTRIBUTING.md` to repo root (or `.github/CONTRIBUTING.md`)
- Align CONTRIBUTING.md commands with CLAUDE.md (flake8 ignore list, test flags)
- Un-exclude or delete the 14 silently-excluded test files in conftest.py
- Remove orphaned `utils/event_simulator.py` if confirmed unused
- Fix `agent_scheduler.py` stub code (implement or remove operation dispatch)

### Acceptance Criteria
- [ ] ROADMAP.md v37.0 all deliverables show `[x]`
- [ ] SECURITY.md shows v44.x as Active
- [ ] `pyproject.toml` has complete metadata and valid packages list
- [ ] `CONTRIBUTING.md` exists at repo root
- [ ] Zero silently-excluded test files (either fixed or deleted)
- [ ] All CLI subcommands pass `--help` with no missing descriptions
- [ ] Accessibility: all 29 tabs have `setAccessibleName` calls

### Docs Updates
- ROADMAP.md, SECURITY.md, CONTRIBUTING.md, pyproject.toml, CHANGELOG.md

---

## v46.0 "Shield" — Security Hardening & API Stabilization

**Theme:** Close remaining security gaps from stabilization guide. Harden API server. Improve credential handling.

### Feature Additions
- System keyring integration for token storage (replace plaintext `.gist_token`)
- API rate limiting middleware
- Command allowlist validation in ActionExecutor

### UI/UX Improvements
- API health dashboard card showing rate limit status
- Token management UI in Settings tab (store/clear/rotate)

### Bug/Error Fix Plan
- **Security:** cloud_sync.py plaintext token -> keyring
- **Security:** ActionExecutor command validation
- **Security:** API rate limiting and request size limits

### Engineering Tasks
- `utils/cloud_sync.py`: Replace `TOKEN_FILE` plaintext with `secretstorage`/`keyring` library
- `core/executor/action_executor.py`: Add ALLOWED_COMMANDS frozenset, validate before execution
- `utils/api_server.py`: Add rate limiting middleware, request body size limits
- `utils/api_server.py`: Add API threat model documentation
- Split Polkit policies (if not already done per v35.0 deliverable verification)

### Acceptance Criteria
- [ ] No plaintext tokens on filesystem
- [ ] ActionExecutor rejects commands not in allowlist
- [ ] API endpoints have rate limits (configurable)
- [ ] API request body size capped
- [ ] All changes tested with mocks

### Docs Updates
- SECURITY.md (threat model), CHANGELOG.md, API documentation

---

## v47.0 "Modular" — CLI Refactor & Performance

**Theme:** Break up monolithic CLI, optimize startup, clean up dead code.

### Feature Additions
- Lazy CLI subcommand loading (only import modules needed for the invoked command)
- CLI shell completions refresh (bash/zsh/fish)

### UI/UX Improvements
- CLI command groups with better `--help` organization
- Startup time improvement target: cold CLI `--version` < 0.5s

### Engineering Tasks
- Split `cli/main.py` (3600+ lines) into `cli/commands/{info,maintenance,network,plugins,...}.py`
- Convert eager imports to lazy per-subcommand imports
- Profile and optimize GUI startup time (target < 2s cold)
- Remove orphaned modules: `event_simulator.py`, stub code in `agent_scheduler.py`
- Implement or remove the unfinished `action.operation` dispatch in scheduler

### Acceptance Criteria
- [ ] `cli/main.py` < 500 lines (dispatches to submodules)
- [ ] `loofi --cli --version` runs in < 0.5s
- [ ] GUI cold start < 2s
- [ ] Zero orphaned modules
- [ ] Shell completions cover all subcommands

### Docs Updates
- CLI reference documentation, ARCHITECTURE.md (CLI structure), CHANGELOG.md

---

## v48.0 "Forge" — Real Feature Delivery

**Theme:** With housekeeping, security, and performance complete, deliver the promised v37.0 features that were implemented but never polished.

### Feature Additions
- Smart Update Manager polish: conflict preview UI, scheduling UI, rollback on failure
- Extension Manager polish: ratings, screenshots, one-click install
- Flatpak Manager polish: size treemap visualization, permission audit report
- Boot config polish: GRUB theme preview, kernel comparison view

### UI/UX Improvements
- Consistent empty states across all 29 tabs
- Loading indicators for all async operations
- Keyboard shortcut cheat sheet (Ctrl+?)
- Improved onboarding: "What's New" dialog for version upgrades

### Engineering Tasks
- Polish and test all v37.0 features (currently implemented but untested in CI due to collect_ignore)
- Add integration test coverage for update_manager, boot_config, wayland_display
- Improve error recovery messages with actionable hints

### Acceptance Criteria
- [ ] All v37.0 features have passing tests (not excluded)
- [ ] All tabs have consistent empty state handling
- [ ] Keyboard shortcuts documented and functional
- [ ] 85%+ test coverage

### Docs Updates
- User guide updates, CHANGELOG.md, feature documentation

---

## v49.0 "Constellation" — Ecosystem & Community

**Theme:** Expand plugin ecosystem, improve community features, prepare for broader adoption.

### Feature Additions
- Plugin development wizard (generate boilerplate, test template, manifest)
- Plugin ratings/reviews backend improvements (local caching, offline access)
- Community presets: curated system configurations for common use cases (gaming, development, server)
- System migration assistant: export/import system configuration across machines

### UI/UX Improvements
- Plugin search improvements (fuzzy matching, category filters)
- Dashboard customization (drag-and-drop card arrangement)
- Multi-language support (complete i18n for Swedish, prepare for community translations)

### Engineering Tasks
- Plugin SDK documentation and examples
- Translation workflow automation (extract -> translate -> compile)
- Community preset format specification and validation

### Acceptance Criteria
- [ ] Plugin development wizard generates working plugin skeleton
- [ ] At least 2 languages fully translated (English + Swedish)
- [ ] Community presets can be imported/exported
- [ ] 85%+ test coverage maintained

### Docs Updates
- Plugin SDK guide, translation guide, community preset format spec

---

## v50.0 "Apex" — Production Readiness

**Theme:** Final polish for broad distribution. Copr repository, signed releases, reproducible builds.

### Feature Additions
- Signed RPM distribution via Copr with GPG verification
- Automatic crash reporting (opt-in, privacy-preserving)
- System health trend analysis (week-over-week comparisons)

### UI/UX Improvements
- Onboarding flow improvements based on user feedback
- Performance budget enforcement (no tab > 200ms to render)
- Full WCAG 2.1 AA accessibility compliance

### Engineering Tasks
- Reproducible builds via mock/container
- SHA256 checksums for all release artifacts
- End-to-end integration test suite
- Performance regression test suite
- Accessibility audit with automated tooling

### Acceptance Criteria
- [ ] Copr repository live with signed packages
- [ ] Reproducible builds verified
- [ ] 90%+ test coverage
- [ ] WCAG 2.1 AA compliance verified
- [ ] Performance budgets enforced in CI

### Docs Updates
- Installation guide (Copr primary), SECURITY.md (signing verification), accessibility statement

---

# 4. Prioritized Backlog Table

| # | Item | Type | Impact | Effort | Risk | Dependencies | Notes |
|---|------|------|--------|--------|------|--------------|-------|
| 1 | Fix ROADMAP.md unchecked v37.0/v33.0 items | TechDebt | 2 | 1 | 1 | None | Documentation-only fix |
| 2 | Update SECURITY.md supported versions | Compliance | 4 | 1 | 1 | None | 3 versions stale |
| 3 | Fix CLI docstring version (v18.0.0) | Bug | 2 | 1 | 1 | None | One-line fix |
| 4 | Add missing CLI help= strings (9 args) | UX | 3 | 1 | 1 | None | smart-updates subcommand |
| 5 | Add accessibility to extensions_tab, backup_tab | UX | 4 | 2 | 1 | None | Zero a11y calls currently |
| 6 | Complete pyproject.toml metadata | TechDebt | 4 | 2 | 1 | None | Broken for pip install |
| 7 | Move CONTRIBUTING.md to repo root | TechDebt | 2 | 1 | 1 | None | GitHub auto-link |
| 8 | Fix/remove 14 excluded test files | TechDebt | 5 | 4 | 2 | None | Inflates coverage metrics |
| 9 | Add wizard objectNames to QSS files | UX | 3 | 2 | 1 | None | Wizard unstyled in themes |
| 10 | Replace plaintext token with keyring | Security | 5 | 3 | 2 | secretstorage lib | cloud_sync.py |
| 11 | Add ActionExecutor command allowlist | Security | 5 | 3 | 2 | None | No validation currently |
| 12 | Add API rate limiting | Security | 4 | 3 | 2 | None | Zero rate limiting |
| 13 | Split CLI into subcommand modules | TechDebt | 3 | 4 | 2 | None | 3600+ lines single file |
| 14 | Lazy CLI imports | Feature | 3 | 3 | 2 | #13 | Startup time optimization |
| 15 | Remove orphaned event_simulator.py | TechDebt | 1 | 1 | 1 | None | No production imports |
| 16 | Fix agent_scheduler stub code | Bug | 2 | 2 | 1 | None | Stub in production path |
| 17 | Consistent empty states across tabs | UX | 3 | 3 | 1 | None | Inconsistent currently |
| 18 | Plugin development wizard | Feature | 3 | 4 | 2 | None | v49.0 scope |
| 19 | Signed RPM via Copr | Compliance | 5 | 4 | 3 | GPG key setup | v50.0 scope |
| 20 | Reproducible builds | Compliance | 4 | 4 | 3 | Mock/container | v50.0 scope |

*Scoring: Impact 1-5 (5=highest), Effort 1-5 (5=most work), Risk 1-5 (5=highest risk)*

**Assumptions:**
- Effort scores assume a single developer familiar with the codebase
- Risk accounts for potential regressions and dependency on external systems
- Impact weighted toward user-facing improvements and security

---

# 5. Sprint 1 Plan (Top 10 Tasks)

## Task 1: Fix ROADMAP.md unchecked items
- **Goal:** Mark v37.0 and v33.0 deliverables as checked where delivered
- **Steps:** Edit ROADMAP.md, change `[ ]` to `[x]` for implemented items
- **Files:** `ROADMAP.md` lines 404-413 (v37.0), lines 488-491 (v33.0)
- **Acceptance:** All implemented deliverables show `[x]`
- **Test:** Visual review

## Task 2: Update SECURITY.md supported versions
- **Goal:** Update supported versions table to reflect v44.x as Active
- **Steps:** Edit SECURITY.md lines 5-9, update version table
- **Files:** `SECURITY.md`
- **Acceptance:** Current version shown as Active, previous 2 as security-fixes-only
- **Test:** Visual review

## Task 3: Fix CLI module docstring version
- **Goal:** Remove stale v18.0.0 version reference
- **Steps:** Edit `cli/main.py` line 4, remove hardcoded version or make dynamic
- **Files:** `loofi-fedora-tweaks/cli/main.py:4`
- **Acceptance:** Docstring doesn't contain hardcoded version
- **Test:** `grep -n "v18" loofi-fedora-tweaks/cli/main.py` returns empty

## Task 4: Add missing CLI help= strings
- **Goal:** All smart-updates arguments have help text
- **Steps:** Add `help=` to 8 arguments at cli/main.py lines 3541-3554
- **Files:** `loofi-fedora-tweaks/cli/main.py:3541-3554`
- **Acceptance:** `loofi --cli smart-updates --help` shows all argument descriptions
- **Test:** Run help command, verify no undocumented arguments

## Task 5: Add accessibility to extensions_tab.py
- **Goal:** Add setAccessibleName/Description to all interactive widgets
- **Steps:** Identify buttons, inputs, lists in extensions_tab.py; add accessibility calls
- **Files:** `loofi-fedora-tweaks/ui/extensions_tab.py`
- **Acceptance:** grep for setAccessibleName returns 5+ matches
- **Test:** Existing tab smoke tests pass

## Task 6: Add accessibility to backup_tab.py
- **Goal:** Add setAccessibleName/Description to all interactive widgets
- **Steps:** Same as Task 5 for backup_tab.py
- **Files:** `loofi-fedora-tweaks/ui/backup_tab.py`
- **Acceptance:** grep for setAccessibleName returns 5+ matches
- **Test:** Existing tab smoke tests pass

## Task 7: Complete pyproject.toml metadata
- **Goal:** Make pyproject.toml PEP 621 compliant with full metadata
- **Steps:** Add dependencies, classifiers, urls, scripts, fix packages
- **Files:** `pyproject.toml`
- **Acceptance:** `python -m build --sdist` succeeds, metadata complete
- **Test:** `pip install -e .` works in clean venv

## Task 8: Move CONTRIBUTING.md to repo root
- **Goal:** GitHub auto-links CONTRIBUTING.md for new contributors
- **Steps:** Move or symlink `docs/CONTRIBUTING.md` to repo root, align commands with CLAUDE.md
- **Files:** `docs/CONTRIBUTING.md` -> `CONTRIBUTING.md`
- **Acceptance:** File exists at repo root, commands match CLAUDE.md
- **Test:** File exists check

## Task 9: Add wizard objectNames to QSS files
- **Goal:** Wizard components styled consistently across all themes
- **Steps:** Identify wizard objectNames in wizard.py, add QSS rules to all 3 files
- **Files:** `assets/modern.qss`, `assets/light.qss`, `assets/highcontrast.qss`
- **Acceptance:** Wizard objectNames present in all 3 QSS files
- **Test:** grep for wizardBtn returns matches in all 3 files

## Task 10: Remove orphaned event_simulator.py
- **Goal:** Remove dead code that has no production imports
- **Steps:** Verify no imports, delete file, remove any test references
- **Files:** `loofi-fedora-tweaks/utils/event_simulator.py`, any test file referencing it
- **Acceptance:** File deleted, all tests pass
- **Test:** Full test suite passes

---

# 6. Quality & Compliance Plan

## Security
- [x] No secrets in repo (verified: .gitignore excludes .env, tokens)
- [x] pkexec-only privilege escalation (no sudo)
- [x] Subprocess timeout enforcement (stabilization checker in CI)
- [ ] Dependency scanning: add `pip-audit` or `safety` to CI
- [ ] Token storage: migrate from plaintext to system keyring
- [ ] ActionExecutor: add command allowlist validation
- [ ] API: add rate limiting and request size limits

## Privacy
- [x] Plugin analytics opt-in (default off)
- [x] No telemetry in core application
- [ ] Audit all network calls for data minimization
- [ ] Document data practices in PRIVACY.md

## Accessibility
- [x] setAccessibleName across most tabs (314 calls per v34.0)
- [ ] Gap: extensions_tab.py and backup_tab.py have zero a11y calls
- [ ] Gap: Wizard has no QSS objectNames
- [ ] Target: WCAG 2.1 AA compliance audit
- [ ] Keyboard navigation: verify all tabs reachable via keyboard

## Reliability & Observability
- [x] Structured error handling with LoofiError hierarchy
- [x] Structured audit logging (utils/audit.py)
- [x] Action log (core/executor action_log.jsonl)
- [ ] Crash reporting (opt-in, future)
- [ ] Performance monitoring (startup time, tab render time)

## Testing & CI
- [x] 82% line coverage (80% threshold)
- [x] flake8 lint gate
- [x] mypy typecheck gate
- [x] bandit security gate
- [x] Stabilization rules checker
- [x] Fedora review gate
- [ ] Fix 14 silently-excluded test files
- [ ] Add pip-audit dependency scanning
- [ ] Add performance regression tests
- [ ] Target: 90% coverage by v50.0

---

# 7. Documentation Plan

## Existing (update needed)
- `ROADMAP.md` — Fix unchecked items, add v45-v50 plan
- `CHANGELOG.md` — Continue per-release format
- `SECURITY.md` — Update supported versions, add threat model for API
- `CONTRIBUTING.md` — Move to root, align with CLAUDE.md
- `ARCHITECTURE.md` — Update version reference (says v42.0), add API/daemon architecture
- `README.md` — Add v42.0 to "What's New" section, fix coverage badge to be dynamic

## New (propose)
- `PRIVACY.md` — Data practices, telemetry policy, network calls inventory
- `docs/CLI_REFERENCE.md` — Full CLI command reference (generated from --help)
- `docs/API_REFERENCE.md` — REST API endpoint documentation
- `docs/ACCESSIBILITY.md` — Accessibility statement and compliance status

## Not needed
- `RUNBOOK.md` — Not a service (daemon is simple scheduler)
- `UX_GUIDE.md` — Covered by ARCHITECTURE.md tab layout section

---

# 8. Open Questions / Assumptions

1. **Assumption:** v37.0 features are implemented but untested in CI (14 excluded test files). Need verification that these features work correctly before v48.0 polish.

2. **Assumption:** `packages = []` in pyproject.toml is intentional for RPM-only distribution. If pip/PyPI distribution is desired, this needs a proper package structure.

3. **Question:** Is the REST API (`utils/api_server.py`) actively used? If not, should it be deprecated or hardened?

4. **Question:** Is `utils/event_simulator.py` truly orphaned, or is it loaded dynamically (e.g., via plugin system)?

5. **Assumption:** The 14 excluded test files in conftest.py are due to import errors that accumulated over time, not intentional permanent exclusions.

6. **Question:** Should the project support `pip install` from PyPI, or is RPM/Copr the only distribution channel? This affects pyproject.toml scope.

7. **Assumption:** The stabilization directive (no new major features until Phase 1-2 complete) has been satisfied by v35-v44. New feature work can proceed.
