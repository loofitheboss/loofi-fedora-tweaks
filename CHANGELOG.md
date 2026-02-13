# Changelog

<!-- markdownlint-configure-file {"MD024": {"siblings_only": true}} -->

All notable changes to this project will be documented in this file.

## [31.0.2] - 2026-02-13 "Smart UX" (Hotfix)

### Fixed

- **Table Data Row Visibility**: Added `configure_table()` helper to `BaseTab` — forces bright text color via QPalette, sets alternating row colors, proper 36px row height, and hides vertical header row numbers. Applied to all 17 tables across 10 tab files.
- **QSS Table Item Styling**: Added explicit `QTableWidget::item` color (`#e4e8f4`), min-height, border-bottom separator, and `:alternate` / `:selected` pseudo-state styling. Increased font size to 10.5pt.
- **Vertical Header Styling**: Added QSS for `QHeaderView:vertical` and `QHeaderView::section:vertical` to clean up row number columns.
- **Off-theme setForeground colors**: Replaced `Qt.GlobalColor.darkGray` (maintenance), `Qt.GlobalColor.gray` (automation), `Qt.GlobalColor.green/red` (agents), `#e74c3c` (security), `#27ae60/#c0392b` (doctor) with Catppuccin-compatible equivalents.

---

## [31.0.1] - 2026-02-13 "Smart UX" (Hotfix)

### Fixed

- **QSS Global Styles** (`assets/modern.qss`): Improved table readability — brighter headers with blue accent border, better alternating row contrast, sharper gridlines, white selection text, and item padding.
- **Group Boxes**: Added visible card borders and pill-shaped title backgrounds for clearer section separation.
- **Buttons**: Stronger border contrast, blue hover accent, bolder font weight, and minimum height for better touch targets.
- **Input Fields**: Blue focus ring and improved border visibility.
- **Output Area**: New terminal-style look with dark background, green monospace text, and rounded border.
- **Low-contrast text**: Replaced `#888` (26 instances across 12 tabs) with readable `#bac2de` (Catppuccin Subtext1).
- **Off-theme colors**: Replaced `color: red` (maintenance), `#e67e22` (security), `#82e0aa` (AI), `#28a745` (automation), `#9b59b6` (desktop), `#6c7086` (hardware, community) with proper Catppuccin theme equivalents.
- **Inconsistent headers**: Added missing `#a277ff` accent color to maintenance, security, software, and community tab headers.

---

## [31.0.0] - 2026-02-13 "Smart UX"

### Added

- **System Health Score** (`utils/health_score.py`): Weighted 0–100 health score aggregating CPU, RAM, disk, uptime, and pending updates. Dashboard displays a circular gauge with letter grade (A–F) and actionable recommendations.
- **i18n Scaffolding** (`utils/i18n.py`): Qt Linguist translation workflow with `I18nManager` — locale detection, `.qm` file loading, preference persistence. Ready for community translations.
- **Batch Operations** (`utils/batch_ops.py`): Batch install/remove/update for Software tab with package validation. Supports both `dnf` and `rpm-ostree` (Atomic Fedora).
- **System Report Export** (`utils/report_exporter.py`): Export system info as Markdown or styled HTML from the System Info tab. Reports include hostname, kernel, CPU, RAM, disk, battery, desktop, and uptime.
- **Favorite Tabs** (`utils/favorites.py`): Pin any sidebar tab as a favorite — persisted to `~/.config/loofi-fedora-tweaks/favorites.json`. Right-click sidebar context menu to add/remove.
- **Configurable Quick Actions** (`utils/quick_actions_config.py`): Dashboard quick actions grid now reads from user config. Default: Clean Cache, Update All, Power Profile, Gaming Mode.
- **Plugin Template Script** (`scripts/create_plugin.sh`): Scaffolds new plugin directories with `plugin.py`, `metadata.json`, `README.md`, and test stub. Usage: `bash scripts/create_plugin.sh my-plugin`.
- **Accessibility Level 2**: `setAccessibleName` / `setAccessibleDescription` on sidebar search, sidebar tree, dashboard reboot button, health score widget, export controls, and batch operation buttons.
- **95 new tests** across 6 test files: `test_health_score.py` (30), `test_i18n.py` (12), `test_batch_ops.py` (14), `test_report_exporter.py` (10), `test_favorites.py` (14), `test_quick_actions_config.py` (15).

### Changed

- **Dashboard tab** (`ui/dashboard_tab.py`): Added health score circular gauge widget and configurable quick actions grid replacing hardcoded buttons.
- **System Info tab** (`ui/system_info_tab.py`): Added export format selector (Markdown/HTML) and "Export Report" button.
- **Software tab** (`ui/software_tab.py`): Added checkboxes per app row and batch install/remove toolbar buttons.
- **Main Window** (`ui/main_window.py`): Added ⭐ Favorites sidebar category, right-click context menu for toggling favorites, and accessible names on navigation widgets.

### Validation

- **v31 test suite**: 95 passed, 0 failed across all 6 new test files.
- **Lint**: All 6 new modules pass flake8 (max-line-length=150).
- **Coverage target**: 80% (v31 goal).

## [30.0.0] - 2026-02-13 "Distribution & Reliability"

### Added

- **Packaging scripts**: Added `scripts/build_flatpak.sh`, `scripts/build_appimage.sh`, `scripts/build_sdist.sh`, plus root `build_flatpak.sh` wrapper and `pyproject.toml` metadata for source builds.
- **Release notes**: Added `docs/releases/RELEASE-NOTES-v30.0.0.md` for v30 distribution/reliability scope.
- **Targeted regression tests**: Added/expanded packaging and reliability tests in `tests/test_packaging_scripts.py`, `tests/test_rate_limiter.py`, `tests/test_update_checker.py`, `tests/test_plugin_marketplace.py`, and `tests/test_auto_tuner.py`.

### Changed

- **Update checker reliability** (`utils/update_checker.py`): Added structured update assets, download pipeline, and fail-closed checksum/signature verification with offline/cache-aware behavior.
- **Marketplace offline mode** (`utils/plugin_marketplace.py`): Added explicit `offline/source` result metadata and cache-first fallback on network failures.
- **Rate limiter concurrency** (`utils/rate_limiter.py`): Replaced polling-style waits with event-bounded waits to reduce busy-loop behavior.
- **Auto-tuner history thread safety** (`utils/auto_tuner.py`): Added lock-protected history read/write path for concurrent usage stability.
- **CI quality gates** (`.github/workflows/ci.yml`): Enforced blocking `mypy`/`bandit`, raised coverage gate to 75%, and added Flatpak/AppImage/sdist packaging jobs.

### Validation

- **Touched reliability/distribution suite**: One-pass targeted run succeeded (`156 passed, 0 failed`) across `tests/test_update_checker.py`, `tests/test_plugin_marketplace.py`, `tests/test_packaging_scripts.py`, `tests/test_rate_limiter.py`, and `tests/test_auto_tuner.py`.
- **Coverage gate contract**: Repository-wide verification command remains `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --cov=loofi-fedora-tweaks --cov-fail-under=75`.

## [29.0.0] - 2026-02-13 "Usability & Polish"

### Added

- **Centralized error handler** (`utils/error_handler.py`): Global `sys.excepthook` override that catches unhandled `LoofiError` subtypes, shows user-friendly dialogs with recovery hints, and logs to NotificationCenter.
- **Confirmation dialog** (`ui/confirm_dialog.py`): Rich `ConfirmActionDialog` for dangerous operations with action description, undo hints, optional snapshot checkbox, and "don't ask again" toggle. Integrates with `SettingsManager.confirm_dangerous_actions`.
- **Notification toast** (`ui/notification_toast.py`): Animated slide-in toast widget with category-based accent colors, auto-hide timer, and smooth slide animations. Wired to `MainWindow.show_toast()`.
- **Notification badge**: Unread count badge on the bell icon in the breadcrumb bar, auto-refreshed every 5 seconds.
- **Status indicators on tabs**: Live colored dots (🟢🟡🔴) on Maintenance and Storage sidebar items reflecting update availability and disk usage.
- **Settings reset per group**: "↩ Reset Appearance" and "↩ Reset Behavior" buttons in Settings tab. New `SettingsManager.reset_group()` method resets only specified keys.
- **95 new tests** across 5 test files: `test_error_handler.py` (24), `test_confirm_dialog.py` (10), `test_notification_toast.py` (16), `test_v29_features.py` (17), `test_settings_extended_v29.py` (14).
- **Comprehensive test coverage campaign**: 151 test files, 3846+ tests passing, 76.8% line coverage (up from ~57.8%). Added deep tests for CLI, plugins, hardware, focus mode, marketplace, command runner, UI tab initialization (16 tabs), and more.
- **Roadmap v29–v31**: Three-version roadmap added covering Usability, Distribution, and Smart UX.

### Changed

- **Sidebar search enhanced**: Now matches tab descriptions and badge data in addition to names. More discoverable for general users.
- **Sidebar keyboard focus restored**: Changed `FocusPolicy.NoFocus` to `StrongFocus` on sidebar `QTreeWidget`, enabling keyboard navigation with Tab/arrow keys.
- **Dashboard SparkLine theme-aware**: Replaced hardcoded `#1e1e2e` background with `palette().color(backgroundRole())` so sparklines render correctly in both dark and light themes.
- **Web API CORS locked down**: Restricted CORS origins from wildcard `["*"]` to `["http://localhost:8000", "http://127.0.0.1:8000"]`. Prevents cross-origin abuse in production.

### New Files (4)

- `utils/error_handler.py` — Centralized error handler
- `ui/confirm_dialog.py` — Confirmation dialog widget
- `ui/notification_toast.py` — Animated toast notifications
- `tests/test_error_handler.py`, `tests/test_confirm_dialog.py`, `tests/test_notification_toast.py`, `tests/test_v29_features.py`, `tests/test_settings_extended_v29.py`

## [28.0.0] - 2026-02-12 "Workflow Contract Reset"

### Changed

- Reset workflow race lock and run manifest to v28.0.0 clean-slate baseline.
- Align all planning artifacts with workflow runner task contract validation (v26+ rules).
- Bump version strings to 28.0.0 in `version.py` and `.spec`.
- Update README.md and release documentation for v28.0.0.

### Added

- Architecture blueprint (`arch-v28.0.0.md`) documenting artifact structure and validation rules.
- Release notes draft and final release notes for v28.0.0 meta-version.
- Planning checkpoint entry in run manifest for phase traceability.

### Fixed

- Clear residual v27 workflow state that could interfere with phase execution.

---

## [27.0.0] - 2026-02-12 "Marketplace Enhancement"

### Added

- Add CDN-first marketplace index provider with cache and fallback behavior.
- Add marketplace ratings/reviews APIs and CLI operations (`reviews`, `review-submit`, `rating`).
- Add verified publisher verification state and badge exposure in marketplace listing/detail outputs.
- Add opt-in plugin analytics pipeline (default off) with batched anonymized event sending.
- Add plugin hot-reload request/rollback contracts and stronger isolation policy enforcement hooks.

### Changed

- Update Plugin SDK marketplace documentation to reflect CDN-first behavior and v27 command flows.
- Update release documentation set (`README.md`, release notes, roadmap) for v27.0.0 alignment.

---

## [26.0.2] - 2026-02-12 "Status Bar UI Hotfix"

### Fixed

- Fix bottom status bar rendering artifacts where labels drew opaque blocks behind shortcut hints and version text.
- Force transparent label backgrounds for status bar labels in both `modern.qss` and `light.qss`.

---

## [26.0.1] - 2026-02-12 "Breadcrumb Bar UI Hotfix"

### Fixed

- Fix breadcrumb bar text rendering artifacts where each label drew an opaque block behind `Category > Page > Description`.
- Force transparent label backgrounds for breadcrumb labels in both `modern.qss` and `light.qss`.

---

## [26.0.0] - 2026-02-12 "Plugin Marketplace"

### Added

- Add Plugin Marketplace system for external plugin discovery, installation, and management
- Add `PluginAdapter` to bridge `LoofiPlugin` (old API) with `PluginInterface` (v25+ core API)
- Add `PluginPackage` dataclass for `.loofi-plugin` archive format specification
- Add `PluginSandbox` for runtime permission enforcement (filesystem, network, sudo, clipboard, notifications)
- Add external plugin scanner and loader in `core/plugins/scanner.py`
- Add `PluginInstaller` engine with download, verify, extract, and register workflow
- Add `PluginIntegrityVerifier` with SHA256 hash and GPG signature verification
- Add `PluginMarketplaceAPI` with GitHub-based plugin index fetching
- Add `PluginDependencyResolver` for automatic dependency installation and version constraints
- Add CLI marketplace commands: `search`, `install`, `uninstall`, `update`, `info`
- Add Marketplace UI in Community tab (browse, search, install with permission dialog)
- Add plugin auto-update service for daemon mode
- Add 195 new tests across 8 test modules (adapter, sandbox, loader, installer, marketplace, resolver, integrity, CLI)

### Changed

- Update `PluginLoader` to support both built-in and external plugin sources
- Extend `plugin.json` manifest format with `dependencies`, `checksum`, `signature` fields
- Update `PLUGIN_SDK.md` with comprehensive marketplace usage guide and API reference
- Refactor permission system to enforce grants at runtime via `PluginSandbox`

### Fixed

- Fix plugin installation race conditions with atomic file operations
- Fix permission dialog to properly handle user cancellation
- Fix dependency resolution to respect version constraints (>=, >, <, <=, ==)

---

## [25.0.3] - 2026-02-11 "Maintenance Update Crash Hotfix"

### Fixed

- Fix crash when pressing `Update System` and `Update All` in Maintenance by routing system updates through the stable `CommandRunner` execution path.
- Fix update queue behavior to always start `Update All` with the system package-manager step before Flatpak and firmware updates.
- Add regression tests for maintenance update command selection and update-all startup sequencing.

## [25.0.2] - 2026-02-11 "Plugin Architecture Testability Hotfix"

### Fixed

- Fix plugin/core import behavior to avoid hard Qt runtime dependency during non-UI module loading.
- Fix `BaseTab` inheritance fallback to prevent metaclass/MRO import failures in mocked headless test contexts.
- Fix frameless-mode tests to skip cleanly when PyQt6 system libraries are unavailable.
- Fix stale architecture/version assertions in legacy tests to match current plugin-based app structure and `25.0.1+` metadata.

## [25.0.1] - 2026-02-11 "Plugin Architecture Hotfix"

### Fixed

- Fix plugin startup regression on newer PyQt6 builds by removing `ABC` metaclass coupling from `PluginInterface`.
- Fix tab base class compatibility by removing `pyqtWrapperType` dependency from `BaseTab`.
- Fix noisy startup logs in restricted environments by downgrading expected DBus access failures to info-level fallback messages.

---

## [25.0.0] - 2026-02-11 "Plugin Architecture"

### Added

- Add `PluginInterface` ABC and `PluginMetadata` dataclass in `core/plugins/` for modular tab system.
- Add `PluginRegistry` singleton for plugin registration, lookup, and category-based filtering.
- Add `PluginLoader` for built-in tab discovery and validation via entrypoint import.
- Add `CompatibilityDetector` to check Fedora version, desktop environment, Wayland/X11, and required packages.
- Add 86 comprehensive tests for plugin registry, loader, compatibility checks, and integration.
- Add `check_plugin_compat()` API for declarative compatibility specifications in plugin metadata.

### Changed

- Refactor all 26 built-in tabs to implement `PluginInterface` with self-describing metadata.
- Replace hardcoded tab loading in `MainWindow` with dynamic `PluginLoader.load_builtins()`.
- Refactor sidebar navigation to render categories, icons, and badges from `PluginRegistry`.
- Convert `BaseTab` to implement `PluginInterface` with default metadata stub for backward compatibility.
- Move tab instantiation from `MainWindow._lazy_tab()` to `PluginLoader.create_widget()`.

### Removed

- Remove `_TAB_META` dict from `MainWindow` (metadata now lives in each tab's `PluginMetadata`).
- Remove `_lazy_tab()` private method from `MainWindow` (loader handles instantiation).

---

## [24.0.0] - 2026-02-10 "Power Features"

### Added

- Add `core/profiles/models.py` with `ProfileRecord` and `ProfileBundle` schema types.
- Add `core/profiles/storage.py` with profile CRUD and single/bundle JSON import/export support.
- Add profile API routes in `api/routes/profiles.py` for list/apply/import/export (single and bundle).
- Add live incremental polling API `SmartLogViewer.get_logs_incremental()`.
- Add test coverage for profile storage, profile CLI/API/UI workflows, and live log polling.

### Changed

- Refactor `utils/profiles.py` to use `ProfileStore` while keeping backward-compatible `ProfileManager` methods.
- Extend `ProfileManager.apply_profile()` with snapshot-before-apply hook and graceful fallback warnings.
- Extend CLI `profile` command with `export`, `import`, `export-all`, `import-all`, `--overwrite`, `--no-snapshot`, and `--include-builtins`.
- Update `ui/profiles_tab.py` with import/export bundle controls and per-profile export.
- Update `ui/logs_tab.py` with live log panel controls (start/stop, interval, bounded buffer).

### Fixed

- Fix log export action in `LogsTab` to pass fetched entries into `SmartLogViewer.export_logs()`.

---

## [23.0.0] - 2026-02-10 "Architecture Hardening"

### Added

- Add `BaseActionExecutor` abstract base class with `privileged=True` execution support.
- Add `pkexec` privilege elevation integration through executor base abstractions.
- Add centralized `BaseWorker` QThread pattern in `core/workers/` for non-blocking operations.
- Add comprehensive import validation coverage with 34 tests.
- Add GitHub Actions CI workflow for automated validation.

### Changed

- Move system services to `services/system/` (system.py, services.py, processes.py, process.py).
- Move hardware services to `services/hardware/` (hardware.py, battery.py, disk.py, temperature.py, bluetooth.py, hardware_profiles.py).
- Consolidate packaging scripts under `scripts/` (`build_rpm.sh`, `build_flatpak.sh`, `build_appimage.sh`, `build_sdist.sh`).
- Refactor `ActionExecutor` to subclass `BaseActionExecutor` for improved abstraction and testability.

### Fixed

- Keep backward-compatible import shims in `utils/` to preserve legacy import paths.

### Removed

- Remove direct legacy import usage by migrating service and worker code to new core/service modules.

---

## [21.0.1] - 2026-02-09

### Fixed

- **Packaging**: Removed python-jose test dependency that blocked RPM installation on Fedora
- **Tests**: Use PyJWT's `ExpiredSignatureError` instead of importing from python-jose
- Runtime code already correctly uses PyJWT; this fix aligns test dependencies

---

## [21.0.0] - 2026-02-09 "UX Stabilization & Layout Integrity"

### Changed

- **Baseline Layout Integrity**: Fixed window chrome overlay issues on KDE Plasma by enforcing native title bar rendering, removing custom window hints, and setting `documentMode()` on all QTabWidget instances.
- **QTabBar Scroller Styling**: Scoped scroller button styles to prevent theme conflicts, ensuring clean scroll navigation for sub-tabs.
- **Minimum Window Dimensions**: Enforced 800x500 minimum window size with consistent 16px margins for proper content layout.
- **HiDPI Rendering Safety**: Switched to font-metrics-based sizing and `pt` units for DPI-independent layouts across all themes.
- **Frameless Mode Feature Flag**: Added stubbed-out feature flag for frameless window mode (future implementation).
- **Layout Regression Tests**: Added test suite for main window geometry, title bar visibility, and client area placement.
- **Theme-Aware Inline Styles**: Top-3 critical inline style fixes for theme compatibility (tabs, scrollers, margins).

---

## [20.0.2] - 2026-02-09 "Synapse"

### Changed

- UI: Fixed top sub-tab overflow by enabling scroll buttons, eliding long labels, and styling scrollers.
- Dependencies: Pinned Python dependencies to the latest versions (PyQt6, requests, fastapi, uvicorn, PyJWT, bcrypt, httpx, python-multipart).

---

## [20.0.1] - 2026-02-09 "Synapse"

### Changed

- Packaging: switch JWT dependency to PyJWT to align with Fedora `python3-jwt` package.

---

## [20.0.0] - 2026-02-09 "Synapse" (Phase 1: Remote Management)

### Added

- **Loofi Web API**: Headless FastAPI server for remote system management (`utils/api_server.py`).
  - `--web` flag to run headless: `loofi-fedora-tweaks --web`
  - Endpoints: `GET /api/health`, `GET /api/info`, `GET /api/agents`, `POST /api/execute`
  - JWT authentication with bcrypt-hashed API key storage
  - Mandatory preview mode: `/api/execute` always previews first, real execution is opt-in
  - CORS middleware for cross-origin access
  - Static file serving for web dashboard

- **JWT Authentication System**: Secure token-based auth (`utils/auth.py`).
  - `POST /api/key` generates API key (bcrypt-hashed storage)
  - `POST /api/token` exchanges API key for JWT (1-hour expiry)
  - Bearer token verification via FastAPI dependency injection
  - `~/.config/loofi-fedora-tweaks/api_keys.json` storage

- **Web Dashboard**: Mobile-responsive dark-theme UI (`loofi-fedora-tweaks/web/`).
  - Login screen with API key authentication
  - System health panel (CPU, memory, uptime, hostname)
  - Agent status list with enabled/disabled states
  - Command executor interface with preview/execute toggle
  - Auto-refresh system stats every 10 seconds
  - Vanilla JavaScript (no framework dependencies)

- **EventBus (Hive Mind)**: Thread-safe pub/sub system for inter-agent communication (`utils/event_bus.py`).
  - Singleton EventBus with topic-based subscriptions
  - Async callback execution via ThreadPoolExecutor
  - Error isolation: one failing subscriber doesn't crash others
  - Event types: `system.storage.low`, `network.connection.public`, `system.thermal.throttling`, etc.
  - `get_events()` returns last 100 events for debugging

- **AgentScheduler**: Event-driven agent execution system (`utils/agent_scheduler.py`).
  - Agents subscribe to event topics via `subscriptions: ["topic.name"]`
  - Automatic execution when subscribed events are published
  - Rate limiting via `max_actions_per_hour` enforcement
  - Publishes `agent.{id}.success` and `agent.{id}.failure` events
  - ActionExecutor integration for real command execution
  - Notification support via `notify.cleanup_complete` operations

- **Agent Implementations**: Three real-world agents demonstrating EventBus (`loofi-fedora-tweaks/agents/`).
  - **cleanup.json**: Storage cleanup on `system.storage.low` (DNF cache, journal vacuum, /tmp cleanup)
  - **security.json**: Firewall profile adjustment on `network.connection.public` / `network.connection.trusted`
  - **thermal.json**: CPU governor and brightness adjustment on `system.thermal.throttling` / `system.thermal.normal`

- **Event Simulator**: Testing utility for triggering events without system changes (`utils/event_simulator.py`).
  - `simulate_low_storage()`, `simulate_public_wifi()`, `simulate_thermal_throttling()`
  - Dry-run demonstrations and integration testing

- **API Routes**: Modular FastAPI route structure (`loofi-fedora-tweaks/api/routes/`).
  - `system.py`: Health, info, agent listing endpoints
  - `executor.py`: ActionExecutor execution endpoint with auth

### Changed

- **AgentConfig**: Added `subscriptions: List[str]` field for event-based triggers.
- **AgentRegistry**: Added `load_from_directory()` for dynamic agent loading from JSON files.
- **main.py**: Added `--web` CLI flag for headless API server mode.
- **requirements.txt**: Added fastapi, uvicorn, python-jose, bcrypt, httpx, python-multipart.
- **loofi-fedora-tweaks.spec**: Added Python dependencies for web API.

### Tests

- **28 API security tests** in `test_api_server.py`:
  - Authentication: bearer token, invalid tokens, expired tokens, malformed headers
  - Input validation: command injection, path traversal, malformed JSON, extremely long inputs
  - Authorization: pkexec enforcement, preview mode auth, read-only endpoints
  - Error handling: invalid commands, executor exceptions, ActionResult serialization
- **18 EventBus tests** in `test_event_bus.py`:
  - Thread safety, singleton pattern, pub/sub flow, error isolation, callback execution
- **10 agent integration tests** in `test_agent_events.py`:
  - Event subscription, agent triggering, scheduler execution, notification publishing
- **10 agent implementation tests** in `test_agent_implementations.py`:
  - cleanup.json, security.json, thermal.json behavior
  - Rate limiting, event triggers, command execution, dry-run mode

#### Total: 66 new tests passing

### New Files

- `loofi-fedora-tweaks/utils/api_server.py` — FastAPI server
- `loofi-fedora-tweaks/utils/auth.py` — JWT authentication
- `loofi-fedora-tweaks/utils/event_bus.py` — EventBus pub/sub system
- `loofi-fedora-tweaks/utils/agent_scheduler.py` — Event-driven agent scheduler
- `loofi-fedora-tweaks/utils/event_simulator.py` — Event testing utility
- `loofi-fedora-tweaks/api/routes/system.py` — System endpoints
- `loofi-fedora-tweaks/api/routes/executor.py` — Executor endpoints
- `loofi-fedora-tweaks/web/index.html` — Web dashboard UI
- `loofi-fedora-tweaks/web/assets/app.js` — Dashboard JavaScript
- `loofi-fedora-tweaks/web/assets/style.css` — Dark theme styles
- `loofi-fedora-tweaks/agents/cleanup.json` — Storage cleanup agent
- `loofi-fedora-tweaks/agents/security.json` — Network security agent
- `loofi-fedora-tweaks/agents/thermal.json` — Thermal management agent
- `examples/loofi_api_demo.py` — API usage demonstration
- `examples/simulate_events.py` — Event simulator demo
- `tests/test_api_server.py` — API security test suite
- `tests/test_event_bus.py` — EventBus test suite
- `tests/test_agent_events.py` — Agent integration tests
- `tests/test_agent_implementations.py` — Agent behavior tests

### Documentation

- Updated README.md with v20.0 preview section and API usage examples
- Updated USER_GUIDE.md with `--web` mode documentation

---

## [19.0.0] - 2026-02-09 "Vanguard"

### Added

- **Unified ActionResult Schema**: Single structured result type for all system actions (`utils/action_result.py`).
  - `ActionResult` dataclass with success, message, exit_code, stdout, stderr, data, preview flag, needs_reboot, timestamp, action_id.
  - Convenience constructors: `ok()`, `fail()`, `previewed()`.
  - Full serialization with `to_dict()` / `from_dict()` and output truncation safety.

- **Centralized ActionExecutor**: Single entry point for all system command execution (`utils/action_executor.py`).
  - Preview mode: inspect what any action _would_ do without executing.
  - Global dry-run toggle: disable all real execution for testing.
  - Flatpak-aware: auto-wraps commands with `flatpak-spawn --host` inside sandbox.
  - pkexec support: privilege escalation via `pkexec=True` parameter.
  - Structured JSONL action log with auto-trimming (max 500 entries).
  - `get_action_log()` and `export_diagnostics()` for diagnostics export.

- **Agent Arbitrator**: Resource-aware agent scheduling (`utils/arbitrator.py`).
  - Blocks background agents when CPU temperature exceeds thermal limit.
  - Blocks background work on battery power.
  - Priority-aware: CRITICAL actions bypass thermal/power constraints.

- **Operations Bridge**: `execute_operation()` function bridges existing operation tuples to ActionExecutor for CLI/headless paths.

### Changed

- **Agent Runner**: `_execute_command()` now routes through centralized ActionExecutor instead of direct subprocess calls.
- **Agent Runner**: Added arbitrator integration for resource-aware action gating.
- **Version**: Bumped to 19.0.0 "Vanguard".

### Tests

- 24 new tests in `test_action_executor.py` covering:
  - ActionResult schema, convenience constructors, serialization roundtrips, truncation.
  - ActionExecutor preview mode, global dry-run, execution, timeouts, command-not-found.
  - Flatpak wrapping, pkexec prepend, action_id propagation.
  - JSONL action logging, log trimming, diagnostics export, logging failure resilience.
  - Operations bridge preview and pkexec extraction.
- 4 new tests in `test_agents.py` for arbitrator integration (thermal block, battery block, critical bypass).

### New Files

- `utils/action_result.py` — Unified ActionResult schema
- `utils/action_executor.py` — Centralized executor with preview, dry-run, logging
- `utils/arbitrator.py` — Agent resource arbitrator
- `tests/test_action_executor.py` — ActionExecutor + ActionResult test suite

## [18.0.0] - 2026-02-09 "Sentinel"

### Added

- **Autonomous Agent Framework**: Full agent system for proactive system management (`utils/agents.py`).
  - `AgentConfig` declarative agent definition with type, triggers, actions, settings.
  - `AgentState` runtime state with bounded history, rate limiting, status tracking.
  - `AgentRegistry` singleton for agent CRUD, JSON persistence, and querying.
  - `AgentResult`, `AgentTrigger`, `AgentAction` dataclasses with full serialization.
  - 5 built-in agents: System Monitor, Security Guard, Update Watcher, Cleanup Bot, Performance Optimizer.
  - 8 agent types: `system_monitor`, `security_guard`, `update_watcher`, `cleanup_bot`, `performance_optimizer`, `custom`, `composite`, `scheduled_task`.

- **Agent Runner & Executor**: Background execution engine (`utils/agent_runner.py`).
  - `AgentExecutor` maps 14 built-in operations to real system checks (CPU, memory, disk, temperature, ports, failed logins, firewall, DNF/Flatpak updates, cache cleanup, journal vacuum, temp files, workload detection, tuning).
  - `AgentScheduler` background thread-based scheduling with interval triggers, result callbacks.
  - Safety: rate limiting (configurable max actions/hour), dry-run mode, severity gating (CRITICAL blocked from automation).

- **AI-Powered Agent Planner**: Natural language goal → agent configuration (`utils/agent_planner.py`).
  - Template matching for 5 common goals (health, security, updates, cleanup, performance).
  - Ollama LLM fallback for custom goal interpretation with JSON response parsing.
  - Operation catalog with 14 entries and severity metadata.
  - `AgentPlan` dataclass with confidence scoring and `to_agent_config()` conversion.

- **Agents Tab**: New GUI tab (#26) for agent management (`ui/agents_tab.py`).
  - Dashboard: 5 stat cards (total, enabled, running, errors, total runs), scheduler start/stop, recent activity.
  - My Agents: Table with enable/disable/run controls per agent.
  - Create Agent: Goal input with 5 template buttons, AI plan generation, dry-run/rate-limit config.
  - Activity Log: Timestamped history of all agent actions.

- **CLI Agent Commands**: `loofi agent` subcommand with 9 actions.
  - `list`, `status`, `enable`, `disable`, `run`, `create --goal "…"`, `remove`, `logs`, `templates`.
  - Full `--json` support for scripting.

### Changed

- **Main Window**: Updated to v18.0 "Sentinel", reorganized 26 tabs into logical categories (System, Hardware, Software, Network, Desktop, Automation, Security, Tools, Settings) with a collapsible sidebar.
- **CLI**: Updated header to v18.0.0, added `agent` subparser and command handler.

### Tests

- 60+ new tests in `test_agents.py` covering:
  - Agent dataclass serialization/deserialization roundtrips
  - AgentRegistry CRUD, persistence, enable/disable, settings update
  - AgentExecutor dry-run, rate limiting, severity gating, operation execution
  - Built-in operations (CPU, memory, disk, temperature, workload detection)
  - AgentPlanner template matching, fallback, plan-to-config conversion
  - AgentScheduler start/stop, run-now, result callbacks
  - CLI agent commands (list, status, templates, create, enable/disable, logs)

### New Files

- `utils/agents.py` — Agent framework, registry, and built-in agent definitions
- `utils/agent_runner.py` — Agent executor and background scheduler
- `utils/agent_planner.py` — AI-powered natural language agent planning
- `ui/agents_tab.py` — Agents management GUI tab
- `tests/test_agents.py` — Agent framework test suite
- `docs/ROADMAP_V18.md` — v18.0 "Sentinel" roadmap and architecture

## [17.0.0] - 2026-02-09 "Atlas"

### Added

- **Performance Tab**: GUI for the v15 AutoTuner (`ui/performance_tab.py`).
  - Workload detection card with real-time CPU/memory classification.
  - Kernel settings display (governor, swappiness, I/O scheduler, THP).
  - One-click "Apply Recommendations" with pkexec privilege escalation.
  - Tuning history table with timestamps.
  - 30-second auto-refresh timer.

- **Snapshots Tab**: GUI for the v15 SnapshotManager (`ui/snapshot_tab.py`).
  - Create, restore, and delete snapshots across Timeshift/Snapper/BTRFS.
  - Backend auto-detection, snapshot timeline table, retention policies.

- **Smart Logs Tab**: GUI for the v15 SmartLogViewer (`ui/logs_tab.py`).
  - Color-coded journal viewer with 10 built-in error patterns.
  - Pattern analysis table, unit/priority/time filters, log export.

- **Storage & Disks Tab**: Full disk management (`ui/storage_tab.py`, `utils/storage.py`).
  - `StorageManager` with `list_block_devices()`, `list_disks()`, `list_partitions()`.
  - `get_smart_health()` — SMART health status and temperature via smartctl.
  - `list_mounts()` — mount points with usage stats from `df`.
  - `check_filesystem()` — fsck via pkexec, `trim_ssd()` — fstrim SSD optimization.
  - `get_usage_summary()` — aggregate disk usage overview.
  - CLI: `loofi storage disks`, `loofi storage mounts`, `loofi storage smart <device>`, `loofi storage trim`, `loofi storage usage`.

- **Bluetooth Manager**: Full bluetoothctl wrapper in Hardware tab (`utils/bluetooth.py`).
  - `BluetoothManager` classmethods: `get_adapter_status()`, `list_devices()`, `scan()`.
  - `pair()`, `unpair()`, `connect()`, `disconnect()`, `trust()`, `block()`, `unblock()`.
  - `power_on()`, `power_off()` — adapter power control.
  - `BluetoothDevice` dataclass with battery level, device type, paired/connected/trusted/blocked state.
  - `BluetoothDeviceType` enum (audio, computer, input, phone, network, imaging, other).
  - CLI: `loofi bluetooth status`, `loofi bluetooth devices`, `loofi bluetooth scan`, `loofi bluetooth pair/connect/disconnect/trust <address>`, `loofi bluetooth power-on/power-off`.

- **Network Tab Overhaul**: Rewritten from 155 lines to full multi-sub-tab layout (`ui/network_tab.py`).
  - Connections sub-tab: WiFi scanning, VPN status via nmcli.
  - DNS sub-tab: One-click DNS switching (Cloudflare, Google, Quad9, AdGuard, DHCP default).
  - Privacy sub-tab: Per-connection MAC address randomization.
  - Monitoring sub-tab: Interface stats table + active connections with auto-refresh.

### Changed

- **Gaming Tab**: Normalized to inherit `BaseTab` with `PrivilegedCommand.dnf()` instead of hardcoded `pkexec dnf`.
- **Hardware Tab**: Added Bluetooth card at grid position (3,1) with scan, pair, connect, trust, block UI.
- **Main Window**: Updated to v17.0 "Atlas", 25-tab count, 4 new `add_page()` calls and lazy loaders.

### Tests

- 94 new tests across `test_bluetooth.py`, `test_storage.py`, `test_v17_atlas.py`, `test_v17_cli.py`.
- Full suite: **1514 passed**, 22 skipped.

### New Files

- `utils/bluetooth.py` — Bluetooth device management via bluetoothctl
- `utils/storage.py` — Disk info, SMART health, mounts via lsblk/smartctl/df
- `ui/performance_tab.py` — Performance Auto-Tuner GUI
- `ui/snapshot_tab.py` — Snapshot Timeline GUI
- `ui/logs_tab.py` — Smart Log Viewer GUI
- `ui/storage_tab.py` — Storage & Disks GUI
- `tests/test_bluetooth.py` — Bluetooth manager unit tests
- `tests/test_storage.py` — Storage manager unit tests
- `tests/test_v17_atlas.py` — GUI tab instantiation tests
- `tests/test_v17_cli.py` — CLI bluetooth/storage command tests

## [16.0.0] - 2025-07-23 "Horizon"

### Added

- **Service Explorer**: Full systemd service browser and controller (`utils/service_explorer.py`).
  - `list_services()` — browse all system/user services with state, enabled, and description.
  - `get_service_details()` — rich info via `systemctl show` (memory, PID, timestamps, unit path).
  - `get_service_logs()` — journal logs per service with configurable line count.
  - `start/stop/restart/enable/disable/mask/unmask_service()` — full lifecycle control.
  - `get_summary()` — quick active/failed/inactive counts.
  - System scope uses pkexec via PrivilegedCommand; user scope runs unprivileged.
  - CLI: `loofi service list`, `loofi service start/stop/restart/enable/disable <name>`, `loofi service logs <name>`, `loofi service status <name>`.

- **Package Explorer**: Unified package search and management across DNF, rpm-ostree, and Flatpak (`utils/package_explorer.py`).
  - `search()` — combined search across DNF and Flatpak remotes with installed status.
  - `install()/remove()` — auto-detects package source (DNF/rpm-ostree/Flatpak) or accepts explicit source.
  - `list_installed()` — unified listing of RPM and Flatpak packages with search filter.
  - `recently_installed()` — packages installed in the last N days via DNF history.
  - `get_package_info()` — detailed info via `dnf info`.
  - `get_counts()` — quick summary of RPM and Flatpak package counts.
  - CLI: `loofi package search --query <term>`, `loofi package install/remove <name>`, `loofi package list`, `loofi package recent`.

- **Firewall Manager**: Full firewalld GUI backend (`utils/firewall_manager.py`).
  - `get_status()` — comprehensive snapshot (running, zones, ports, services, rich rules).
  - `get_zones()/get_active_zones()/set_default_zone()` — zone management.
  - `list_ports()/open_port()/close_port()` — port management with permanent/runtime modes.
  - `list_services()/add_service()/remove_service()` — service allowlist management.
  - `list_rich_rules()/add_rich_rule()/remove_rich_rule()` — rich rule management.
  - `start_firewall()/stop_firewall()` — toggle firewalld via pkexec.
  - CLI: `loofi firewall status`, `loofi firewall ports`, `loofi firewall open-port/close-port <spec>`, `loofi firewall services`, `loofi firewall zones`.

- **Dashboard v2**: Complete dashboard overhaul with live metrics.
  - Real-time CPU and RAM sparkline graphs (30-point area charts, 2s refresh).
  - Network speed indicator (↓/↑ bytes/sec from `/proc/net/dev`).
  - Per-mount-point storage breakdown with color-coded progress bars.
  - Top 5 processes by CPU usage.
  - Recent actions feed from HistoryManager.
  - Quick Actions grid with correct tab navigation.

### Tests

- 148 new tests across `test_service_explorer.py`, `test_package_explorer.py`, and `test_firewall_manager.py`.
- Full suite: **1420 passed**, 22 skipped.

## [15.0.0] - 2026-02-08 "Nebula"

### Added

- **Performance Auto-Tuner**: Intelligent workload detection and system optimization (`utils/auto_tuner.py`).
  - `detect_workload()` — classifies CPU/memory into 6 workload profiles (idle, light, compilation, gaming, server, heavy).
  - `recommend()` — suggests governor, swappiness, I/O scheduler, and THP settings per workload.
  - `apply_recommendation()` / `apply_swappiness()` / `apply_io_scheduler()` / `apply_thp()` — operation tuples for pkexec.
  - Tuning history with JSON persistence (max 50 entries).
  - CLI: `loofi tuner analyze`, `loofi tuner apply`, `loofi tuner history`.
- **System Snapshot Timeline**: Unified snapshot management for Timeshift, Snapper, and BTRFS (`utils/snapshot_manager.py`).
  - `detect_backends()` — auto-detect available snapshot tools.
  - `list_snapshots()` — chronological timeline with backend-agnostic parsing.
  - `create_snapshot()` / `delete_snapshot()` — operation tuples per backend.
  - `apply_retention()` — automated cleanup of old snapshots.
  - CLI: `loofi snapshot list`, `loofi snapshot create`, `loofi snapshot delete`, `loofi snapshot backends`.
- **Smart Log Viewer**: Intelligent journal viewer with pattern detection (`utils/smart_logs.py`).
  - 10 built-in log patterns: OOM, segfault, disk full, auth failure, service failed, kernel panic, etc.
  - `get_logs()` — structured journal parsing with severity color-coding and pattern matching.
  - `get_error_summary()` — aggregated error analysis with top units and detected patterns.
  - `export_logs()` — text and JSON export.
  - CLI: `loofi logs show`, `loofi logs errors`, `loofi logs export`.
- **Quick Actions Bar**: Searchable floating action palette (`ui/quick_actions.py`).
  - `Ctrl+Shift+K` shortcut opens searchable action bar.
  - `QuickActionRegistry` singleton with fuzzy search, category filtering, recent actions.
  - 15+ default actions across Maintenance, Security, Hardware, Network, System categories.
  - Plugin-extensible: plugins can register custom quick actions.
- **4 New Development Agents**: Planner, Builder, Sculptor, Guardian for v15.0+ workflow.
- **166 New Tests**: `test_auto_tuner.py` (53), `test_snapshot_manager.py` (41), `test_smart_logs.py` (45), `test_quick_actions.py` (27).

### Changed

- **MainWindow**: Added Quick Actions shortcut (`Ctrl+Shift+K`), updated shortcut help dialog.
- **CLI**: 3 new subcommands (`tuner`, `snapshot`, `logs`) with `--json` support.
- **Test coverage**: 1290+ tests (up from 1130).

### New Files

- `utils/auto_tuner.py` — Performance auto-tuner with workload detection
- `utils/snapshot_manager.py` — Unified snapshot management (Timeshift/Snapper/BTRFS)
- `utils/smart_logs.py` — Smart log viewer with pattern detection
- `ui/quick_actions.py` — Quick Actions Bar with registry and fuzzy search
- `.github/agents/Planner.agent.md` — Release planning agent
- `.github/agents/Builder.agent.md` — Backend implementation agent
- `.github/agents/Sculptor.agent.md` — Frontend/integration agent
- `.github/agents/Guardian.agent.md` — Quality assurance agent
- `tests/test_auto_tuner.py` — Auto-tuner tests (53)
- `tests/test_snapshot_manager.py` — Snapshot manager tests (41)
- `tests/test_smart_logs.py` — Smart log viewer tests (45)
- `tests/test_quick_actions.py` — Quick actions tests (27)
- `ROADMAP_V15.md` — v15.0 feature roadmap

## [14.0.0] - 2026-02-08 "Quantum Leap"

### Added

- **Update Checker**: Automatic update notifications from GitHub releases API (`utils/update_checker.py`).
  - `UpdateChecker.check_for_updates()` fetches latest release via GitHub API.
  - `UpdateInfo` dataclass with version comparison and download URL.
- **What's New Dialog**: Post-upgrade dialog showing release highlights (`ui/whats_new_dialog.py`).
  - Remembers last-seen version via `SettingsManager`.
  - Shows current + previous version notes in a scrollable view.
- **Factory Reset**: Full backup/restore/reset management (`utils/factory_reset.py`).
  - `create_backup()` — snapshot all JSON config files with manifest.
  - `list_backups()` — enumerate available backups with metadata.
  - `restore_backup()` — restore config from a named backup.
  - `delete_backup()` — remove old backups.
  - `reset_config()` — factory reset with auto-backup before deletion.
- **Plugin Lifecycle Events**: Added `on_app_start`, `on_app_quit`, `on_tab_switch`, `on_settings_changed`, `get_settings_schema` hooks to `LoofiPlugin` ABC.
- **Version Tracking**: `last_seen_version` field in `AppSettings` for What's New dialog tracking.
- **72 New Tests**: `test_factory_reset.py` (22), `test_update_checker.py` (8) — plus existing test base.

### Changed

- **Test coverage**: 1130+ tests (up from 1060).
- **Spec file**: Updated to v14.0.0 with expanded description.
- **Agent instructions**: Enhanced test and architecture agent docs.

### New Files

- `utils/update_checker.py` — GitHub releases API update checker
- `utils/factory_reset.py` — Backup/restore/reset management
- `ui/whats_new_dialog.py` — Post-upgrade What's New dialog
- `tests/test_factory_reset.py` — Factory reset unit tests
- `tests/test_update_checker.py` — Update checker unit tests

## [13.5.0] - 2026-02-08 "Nexus Update" (UX Polish)

### Added

- **Settings Tab**: New tab (#21) with Appearance, Behavior, and Advanced sub-tabs.
  - `SettingsManager` singleton with JSON persistence and atomic writes (`utils/settings.py`).
  - `AppSettings` dataclass with 9 configurable preferences.
  - Theme ComboBox (dark/light), Follow System Theme checkbox.
  - Start Minimized, Show Notifications, Confirm Dangerous Actions toggles.
  - Log Level selector and Factory Reset button in Advanced.
- **Light Theme**: Catppuccin Latte light theme (`assets/light.qss`) with full selector coverage mirroring `modern.qss`.
- **Sidebar Search**: Filter tabs by name with `QLineEdit` search box above sidebar.
- **Keyboard Shortcuts**: `Ctrl+1-9` tab switch, `Ctrl+Tab`/`Ctrl+Shift+Tab` cycling, `Ctrl+Q` quit, `F1` help dialog.
- **Notification Center**: Slide-out panel with FIFO eviction (max 100), JSON persistence, unread badge, mark-all-read.
  - `utils/notification_center.py` - Notification dataclass + singleton center.
  - `ui/notification_panel.py` - NotificationCard + NotificationPanel widgets.
- **Tooltip Constants**: Centralised `ui/tooltips.py` module with 28 tooltip strings for consistent UI text.
- **82 New Tests**: `test_settings.py` (26), `test_notification_center.py` (20), `test_tooltips.py` (5), `test_settings_extended.py` (13), `test_notification_extended.py` (18).

### Changed

- **Main Window**: Sidebar container with search, notification bell, keyboard shortcuts, theme management methods (`load_theme()`, `detect_system_theme()`).
- **i18n**: Wrapped 6 hardcoded English strings in `hardware_tab.py` with `self.tr()`.
- **Test coverage**: 1060+ tests (up from 988).

### New Files

- `utils/settings.py` - Settings manager with AppSettings dataclass
- `ui/settings_tab.py` - Settings UI with 3 sub-tabs
- `assets/light.qss` - Catppuccin Latte light theme
- `utils/notification_center.py` - Notification center singleton
- `ui/notification_panel.py` - Slide-out notification panel
- `ui/tooltips.py` - Centralised tooltip constants
- `tests/test_settings.py` - Settings unit tests
- `tests/test_notification_center.py` - Notification center unit tests
- `tests/test_tooltips.py` - Tooltip constants tests
- `tests/test_settings_extended.py` - Extended settings tests
- `tests/test_notification_extended.py` - Extended notification tests

## [13.1.0] - 2026-02-08 "Nexus Update" (Stability)

### Changed

- **Exception Cleanup**: Replaced ~50 bare/broad `except Exception:` blocks with specific exception types (`OSError`, `json.JSONDecodeError`, `subprocess.SubprocessError`, `sqlite3.Error`, etc.) across 20 files.
- **Structured Logging**: Added `logging.getLogger(__name__)` to all utils modules for consistent debug logging.
- **Error Return Standardization**: `config_manager.py` and `history.py` now return `Result` dataclass instead of `(bool, str)` tuples.

### Security

- **Removed `shell=True`**: Eliminated all 4 instances of `shell=True` in subprocess calls (`automation_profiles.py`, `hardware.py`, `apps_tab.py`, `software_tab.py`), replacing with `shlex.split()` or argument lists.
- **Localhost Binding**: Clipboard sync server and file drop server now bind to `127.0.0.1` by default instead of `0.0.0.0`, with configurable `bind_address` parameter.
- **Rate Limiting**: New `utils/rate_limiter.py` token bucket rate limiter integrated into clipboard sync server (10 conn/sec) and file drop server.

### Added

- **188 New Tests**: 11 new test files covering previously untested utils modules.
  - `test_config_manager.py` (20), `test_history.py` (11), `test_notifications_util.py` (10)
  - `test_kernel.py` (21), `test_services.py` (19), `test_sandbox.py` (18)
  - `test_ports.py` (16), `test_fingerprint.py` (9), `test_package_manager.py` (18)
  - `test_zram.py` (16), `test_clipboard_unit.py` (30)
- **Test coverage**: 988+ tests passing (up from 839).

### New Files

- `utils/rate_limiter.py` - Token bucket rate limiter for network services
- `tests/test_config_manager.py` - Config manager tests
- `tests/test_history.py` - History/undo system tests
- `tests/test_notifications_util.py` - Notification utility tests
- `tests/test_kernel.py` - Kernel parameter management tests
- `tests/test_services.py` - Systemd service manager tests
- `tests/test_sandbox.py` - Firejail/Bubblewrap sandbox tests
- `tests/test_ports.py` - Port auditor and firewall tests
- `tests/test_fingerprint.py` - Fingerprint enrollment tests
- `tests/test_package_manager.py` - DNF/rpm-ostree/Flatpak tests
- `tests/test_zram.py` - ZRAM configuration tests
- `tests/test_clipboard_unit.py` - Clipboard sync unit tests

## [13.0.0] - 2026-02-08 "Nexus Update"

### Added

- **System Profiles (v13.0)**: Quick-switch system configurations with 5 built-in profiles via `utils/profiles.py`.
  - Gaming: Performance governor, compositor disabled, DND notifications, gamemode
  - Development: Schedutil governor, docker/podman services enabled
  - Battery Saver: Powersave governor, reduced compositor, critical notifications only
  - Presentation: Performance governor, screen timeout disabled, DND mode
  - Server: Performance governor, headless optimization
- **Custom Profiles**: Create, save, and manage user-defined profiles with custom settings.
- **Profile Capture**: Capture current system state (governor, swappiness) as a new profile.
- **Health Timeline (v13.0)**: SQLite-based metrics tracking via `utils/health_timeline.py`.
  - CPU temperature, RAM usage, disk usage, load average monitoring
  - Anomaly detection (2+ standard deviations from mean)
  - Export to JSON or CSV format
  - Configurable data retention and pruning
- **Profiles Tab (v13.0)**: New UI tab for profile management via `ui/profiles_tab.py`.
- **Health Tab (v13.0)**: New UI tab for health timeline via `ui/health_timeline_tab.py`.
- **Plugin SDK v2**: Enhanced plugin system with permissions model and update checking.
  - Plugins declare required permissions (network, filesystem, system)
  - Plugins can check for updates via remote manifest URL
  - Dependency validation before plugin load
- **Mesh Networking Enhancements**: Improved peer discovery and clipboard sync reliability.
- **Shell Completions**: Bash, Zsh, and Fish completion scripts in `completions/`.
- **CLI Commands**:
  - `profile list|apply|create|delete`: Manage system profiles from CLI
  - `health-history show|record|export|prune`: View and manage health metrics
  - `preset list|apply|export`: Manage system presets
  - `focus-mode on|off|status`: Control focus mode
  - `security-audit`: Run security audit and show score

### Changed

- **Tab count**: 18 tabs expanded to 20 with Profiles and Health tabs.
- **Test coverage**: 839+ tests passing (up from 564).

### New Files

- `utils/profiles.py` - System profile manager with built-in and custom profiles
- `utils/health_timeline.py` - SQLite-based health metrics tracking
- `ui/profiles_tab.py` - System profiles management UI
- `ui/health_timeline_tab.py` - Health timeline visualization UI
- `completions/loofi.bash` - Bash completion script
- `completions/loofi.zsh` - Zsh completion script
- `completions/loofi.fish` - Fish completion script
- `docs/PLUGIN_SDK.md` - Expanded plugin SDK documentation
- `docs/TROUBLESHOOTING.md` - Troubleshooting guide
- `tests/test_profiles.py` - 53 profile tests
- `tests/test_health_timeline.py` - 46 health timeline tests
- `tests/test_ui_smoke.py` - 37 UI smoke tests

## [12.0.0] - 2026-02-08 "Sovereign Update"

### Added

- **VM Quick-Create Wizard**: One-click VMs with preset flavors (Windows 11, Fedora, Ubuntu, Kali, Arch) via `utils/vm_manager.py`.
- **VFIO GPU Passthrough Assistant**: Step-by-step IOMMU group analysis, kernel cmdline generation, dracut/modprobe config via `utils/vfio.py`.
- **Disposable VMs**: QCOW2 overlay-based throwaway VMs for untrusted software via `utils/disposable_vm.py`.
- **Loofi Link Mesh**: mDNS LAN device discovery via Avahi (`utils/mesh_discovery.py`).
- **Clipboard Sync**: Encrypted clipboard content sharing between paired devices (`utils/clipboard_sync.py`).
- **File Drop**: Local HTTP file transfer with checksum verification and filename sanitization (`utils/file_drop.py`).
- **State Teleport**: Capture and restore VS Code, git, and terminal workspace state across devices (`utils/state_teleport.py`).
- **AI Lite Model Library**: Curated GGUF models with RAM-based recommendations (`utils/ai_models.py`).
- **Voice Mode**: whisper.cpp integration for voice commands (`utils/voice.py`).
- **Context RAG**: TF-IDF local file indexing for AI-assisted system help (`utils/context_rag.py`).
- **Virtualization Tab**: VM management, VFIO checklist, and disposable VM UI (`ui/virtualization_tab.py`).
- **Loofi Link Tab**: Device discovery, clipboard sync, and file drop UI (`ui/mesh_tab.py`).
- **State Teleport Tab**: Workspace capture, saved states, and restore UI (`ui/teleport_tab.py`).
- **Enhanced AI Lab Tab**: Three sub-tabs for models, voice, and knowledge (`ui/ai_enhanced_tab.py`).
- **Plugin Refactor**: Virtualization and AI Lab as first-party plugins with JSON manifests.
- **CLI Commands**: `vm`, `vfio`, `mesh`, `teleport`, `ai-models` subcommands with `--json` support.

### Changed

- **Tab count**: 15 tabs expanded to 18 with Virtualization, Loofi Link, and State Teleport.
- **AI Lab tab**: Now uses `AIEnhancedTab` with lite models, voice mode, and context RAG sub-tabs.
- **Test coverage**: 564 tests passing (up from 225).

### New Files

- `utils/vm_manager.py` - VM creation, lifecycle management with libvirt
- `utils/vfio.py` - VFIO GPU passthrough assistant
- `utils/disposable_vm.py` - QCOW2 overlay disposable VMs
- `utils/mesh_discovery.py` - mDNS LAN device discovery
- `utils/clipboard_sync.py` - Encrypted clipboard sharing
- `utils/file_drop.py` - Local HTTP file transfer
- `utils/state_teleport.py` - Workspace state capture/restore
- `utils/ai_models.py` - AI lite model library
- `utils/voice.py` - whisper.cpp voice mode
- `utils/context_rag.py` - TF-IDF local file indexing
- `ui/virtualization_tab.py` - Virtualization management UI
- `ui/mesh_tab.py` - Loofi Link mesh networking UI
- `ui/teleport_tab.py` - State Teleport UI
- `ui/ai_enhanced_tab.py` - Enhanced AI Lab UI
- `plugins/virtualization/` - First-party virtualization plugin
- `plugins/ai_lab/` - First-party AI Lab plugin
- `tests/test_virtualization.py` - 32 virtualization tests
- `tests/test_hypervisor.py` - 76 hypervisor tests
- `tests/test_ai_polish.py` - 62 AI polish tests
- `tests/test_sovereign_network.py` - Mesh networking tests
- `tests/test_teleport.py` - 35 teleport tests
- `tests/test_plugins_v2.py` - 31 plugin v2 tests

## [11.0.0] - 2026-02-08 "Aurora Update"

### Added

- **Plugin Manifests**: `plugin.json` metadata with version gating and enable/disable state.
- **Plugin Manager UI**: Manage plugins from the Community tab.
- **Support Bundle Export**: ZIP with logs and system info (Diagnostics + CLI).
- **Automation Validation**: Rule validation and dry-run simulation.
- **Release Checklist**: New `docs/RELEASE_CHECKLIST.md`.

### Changed

- **Theme Loading**: Unified stylesheet loading via `modern.qss`.
- **Logging**: Structured error logging for Pulse, remote config, and command runner.
- **CI**: Added CLI smoke checks to CI workflow.

## [10.0.0] - 2026-02-07 "Zenith Update"

### Major Changes

- **Tab Consolidation**: 25 tabs reduced to 15 with sub-navigation via QTabWidget.
- **BaseTab Class**: New `ui/base_tab.py` eliminates code duplication across all command-executing tabs.
- **PrivilegedCommand Builder**: Centralized `utils/commands.py` for safe pkexec operations (argument arrays, not shell strings).
- **Error Framework**: `utils/errors.py` with typed exceptions (DnfLockedError, PrivilegeError, etc.) and recovery hints.
- **Hardware Profiles**: Auto-detect HP EliteBook, ThinkPad, Dell XPS, Framework, ASUS via DMI sysfs data.

### New Features

- **First-Run Wizard**: Hardware auto-detection, use-case selection, and profile persistence on first launch.
- **Command Palette**: Ctrl+K opens a fuzzy-search palette with 60+ feature entries and keyboard navigation.
- **Shared Formatting**: `utils/formatting.py` with bytes_to_human(), seconds_to_human(), percent_bar().
- **CI/CD Pipeline**: GitHub Actions workflows for lint (flake8), test (pytest), build (Fedora 43 rpmbuild), and tag-triggered releases.

### Consolidated Tabs

- **Maintenance**: Merges Updates + Cleanup + Overlays (Atomic overlay conditionally shown).
- **Software**: Merges Apps + Repos into Applications and Repositories sub-tabs.
- **System Monitor**: Merges Performance + Processes with live graphs and process management.
- **Hardware**: Absorbs HP Tweaks (now hardware-agnostic) with audio, battery limit, and fingerprint cards.
- **Security & Privacy**: Merges Security Center + Privacy tab with firewall, telemetry, and security updates sections.
- **Desktop**: Merges Director + Theming into Window Manager and Theming sub-tabs.
- **Development**: Merges Containers + Developer Tools with Distrobox GUI and toolchain installers.
- **Community**: Merges Presets + Marketplace with community preset browsing.
- **Automation**: Merges Scheduler + Replicator + Pulse for task scheduling, IaC exports, and event-driven automation.
- **Diagnostics**: Merges Watchtower + Boot with services, journal viewer, boot analyzer.

### CLI Enhancements

- **`--json` Flag**: Machine-readable JSON output for all CLI commands.
- **`doctor` Command**: Checks critical and optional tool dependencies.
- **`hardware` Command**: Shows detected hardware profile.
- **Version Sync**: CLI version now imports from centralized `version.py`.

### New Files

- `ui/base_tab.py` - Common base class for command-executing tabs
- `ui/maintenance_tab.py` - Consolidated maintenance tab (Updates + Cleanup + Overlays)
- `ui/software_tab.py` - Consolidated software tab (Apps + Repos)
- `ui/monitor_tab.py` - Consolidated system monitor (Performance + Processes)
- `ui/diagnostics_tab.py` - Consolidated diagnostics (Watchtower + Boot)
- `ui/desktop_tab.py` - Consolidated desktop tab (Director + Theming)
- `ui/development_tab.py` - Consolidated development tab (Containers + Developer)
- `ui/community_tab.py` - Consolidated community tab (Presets + Marketplace)
- `ui/automation_tab.py` - Consolidated automation tab (Scheduler + Replicator)
- `ui/wizard.py` - First-run wizard with hardware detection
- `ui/command_palette.py` - Ctrl+K fuzzy-search command palette
- `utils/errors.py` - Centralized error hierarchy
- `utils/commands.py` - PrivilegedCommand builder
- `utils/formatting.py` - Shared formatting utilities
- `utils/hardware_profiles.py` - Hardware profile auto-detection
- `tests/conftest.py` - Shared test fixtures
- `tests/test_v10_features.py` - 57 tests for v10 foundation modules
- `tests/test_cli_enhanced.py` - 30 tests for enhanced CLI
- `.github/workflows/ci.yml` - CI pipeline (lint, test, build)
- `.github/workflows/release.yml` - Tag-triggered release pipeline

### Tests

- 87+ new unit tests covering errors, commands, formatting, hardware profiles, and CLI.
- Shared test fixtures in `conftest.py` for mock_subprocess, temp_config_dir, mock_which.

---

## [9.1.0] - 2026-02-07 "Pulse Update"

### Added

- **Event-Driven Automation**: React to hardware changes, network status, and system events in real-time.
- **SystemPulse Engine**: DBus-based event listener for power, network, and monitor changes with polling fallback.
- **Focus Mode**: Distraction blocking with domain blocking, Do Not Disturb, and process killing.
- **Automation Profiles**: Create rules that trigger actions based on system events.
- **Automation Tab**: New UI for managing automation rules, focus mode profiles, and system status.
- **System Tray Focus Toggle**: Quick Focus Mode toggle from the system tray.
- **Power Event Triggers**: React immediately to AC/Battery transitions.
- **Network Event Triggers**: Detect public Wi-Fi, home network, and VPN connections.
- **Monitor Event Triggers**: React to ultrawide monitor connections, laptop-only mode.

### Automation Actions

- Set Power Profile (power-saver, balanced, performance)
- Set CPU Governor (powersave, schedutil, performance)
- Enable/Disable VPN
- Enable/Disable KWin Tiling
- Set Theme (light/dark)
- Enable/Disable Focus Mode
- Run Custom Command

### New Preset Rules

- **Battery Saver**: Auto-switch to power-saver profile on battery
- **Ultrawide Tiling**: Enable tiling when ultrawide monitor connected

### New Files

- `utils/pulse.py` - DBus event listener with power, network, and monitor detection
- `utils/focus_mode.py` - Focus Mode with domain blocking and process management
- `utils/automation_profiles.py` - Event-triggered automation rules engine
- `ui/pulse_tab.py` - Automation and Focus Mode UI
- `tests/test_pulse_system.py` - Unit tests for v9.1 features

---

## [9.0.0] - 2026-02-07 "Director Update"

### Added

- **Disk Space Monitoring**: New `utils/disk.py` module with disk usage stats, health checks, and large directory finder.
- **System Resource Monitor**: New `utils/monitor.py` module with memory usage, CPU load, and uptime tracking.
- **Dashboard Health Indicators**: Disk usage and memory usage now displayed in the Dashboard health card with color-coded status.
- **CLI `health` Command**: Quick system health overview showing memory, CPU, disk, and power profile status.
- **CLI `disk` Command**: Disk usage analysis with optional `--details` flag for large directory listing.
- **CLI Mode from Main Entry**: New `--cli` / `-c` flag on main entry point to launch CLI mode directly.

### Fixed

- CLI version updated from 7.0.0 to 9.0.0 to match the application version.

### New Files

- `utils/disk.py` - Disk space monitoring and analysis
- `utils/monitor.py` - System resource monitoring (memory, CPU, uptime)
- `tests/test_new_features.py` - Tests for disk, monitor, and CLI features

---

## [9.0.0] - 2026-02-07 "Director Update (Window Management)"

### Added

- **Director Tab**: Window management for KDE, Hyprland, and Sway.
- **TilingManager**: Configuration helpers for Hyprland and Sway with workspace templates.
- **KWinManager**: KDE Plasma tiling scripts and keybinding presets.
- **DotfileManager**: Backup and sync configs to a git repository.
- **Workspace Templates**: Pre-configured layouts for development, gaming, creative work.

### New Files

- `utils/tiling.py` - Hyprland/Sway configuration management
- `utils/kwin_tiling.py` - KDE KWin scripts and window rules
- `ui/director_tab.py` - Window management UI

---

## [8.5.0] - 2026-02-07 "Sentinel Update"

### Added

- **Security Tab**: Complete security hardening center with scoring.
- **Port Auditor**: Scan open ports, identify risks, manage firewall rules.
- **USB Guard Integration**: Block unauthorized USB devices (BadUSB protection).
- **Sandbox Manager**: Launch applications in Firejail/Bubblewrap sandboxes.
- **Security Score**: Real-time 0-100 security health assessment.

### New Files

- `utils/sandbox.py` - Firejail and Bubblewrap wrappers
- `utils/usbguard.py` - USBGuard integration
- `utils/ports.py` - Port scanning and firewall management
- `ui/security_tab.py` - Security Center UI

---

## [8.1.0] - 2026-02-07 "Neural Update"

### Added

- **AI Lab Tab**: Local AI setup and model management interface.
- **AI Hardware Detection**: CUDA, ROCm, Intel NPU, AMD Ryzen AI detection.
- **Ollama Management**: Install Ollama, download and manage models.
- **Model Library**: Support for Llama3, Mistral, CodeLlama, Phi-3, Gemma.
- **Ansible Safety Disclaimer**: Added prominent warning header to exported playbooks.

### New Files

- `utils/ai.py` - Ollama manager and AI configuration
- `utils/hardware.py` - Extended with AI capabilities detection
- `ui/ai_tab.py` - AI Lab UI

---

## [8.0.0] - 2026-02-07 "Replicator Update"

### Added

- **Replicator Tab**: Export system configuration as Infrastructure as Code.
- **Ansible Playbook Export**: Generate playbooks with packages, Flatpaks, GNOME settings.
- **Kickstart Generator**: Create Anaconda-compatible .ks files for automated installs.
- **Watchtower Tab**: Combined diagnostics hub with services, boot analyzer, journal viewer.
- **Gaming-Focused Service Manager**: Filter and manage gaming-related systemd services.
- **Boot Time Analyzer**: Visualize boot time breakdown with optimization suggestions.
- **Panic Button Log Export**: One-click forum-ready diagnostic log export.
- **Containers Tab**: Distrobox GUI for managing development containers.
- **Developer Tab**: One-click install for PyEnv, NVM, Rustup + VS Code extension profiles.
- **Lazy Tab Loading**: Tabs load on-demand for faster application startup.

### New Files

- `utils/ansible_export.py` - Ansible playbook generator
- `utils/kickstart.py` - Kickstart file generator
- `utils/services.py` - Gaming-focused systemd service manager
- `utils/boot_analyzer.py` - Boot time analyzer
- `utils/journal.py` - Journal viewer with panic button
- `utils/containers.py` - Distrobox wrapper
- `utils/devtools.py` - PyEnv, NVM, Rustup installers
- `utils/vscode.py` - VS Code extension management
- `ui/replicator_tab.py` - IaC export UI
- `ui/watchtower_tab.py` - Diagnostics hub UI
- `ui/containers_tab.py` - Container management UI
- `ui/developer_tab.py` - Developer tools UI
- `ui/lazy_widget.py` - Lazy loading widget

---

## [7.0.0] - 2026-02-07 "Community Update"

### Added

- **Preset Marketplace**: Browse and download community presets from GitHub.
- **Configuration Drift Detection**: Track system changes from applied presets.
- **Marketplace Tab**: New UI for community preset discovery.

### New Files

- `utils/marketplace.py` - GitHub-based preset marketplace
- `utils/drift.py` - Configuration drift detection
- `ui/marketplace_tab.py` - Marketplace UI

---

## [6.5.0] - 2026-02-07 "Architect Update"

### Added

- **CLI Mode**: Headless `loofi` command for scripting and automation.
- **Operations Layer**: Extracted business logic from UI tabs (`utils/operations.py`).
- **Plugin System**: Modular architecture for third-party extensions (`utils/plugin_base.py`).
- **Plugins Directory**: `plugins/` folder for community extensions.

### CLI Commands

```bash
loofi info              # System information
loofi cleanup           # DNF clean + journal vacuum + SSD trim
loofi tweak power       # Set power profile
loofi advanced bbr      # Enable TCP BBR
loofi network dns       # Set DNS provider
```

### New Files

- `utils/operations.py` - CleanupOps, TweakOps, AdvancedOps, NetworkOps
- `utils/plugin_base.py` - LoofiPlugin ABC + PluginLoader
- `cli/main.py` - CLI entrypoint
- `plugins/__init__.py` - Plugins directory

---

## [6.2.0] - 2026-02-07 "Engine Room Update"\n\n### Added\n\n- **Boot Tab**: New comprehensive boot management interface.\n- **Kernel Parameter Editor**: GUI wrapper for `grubby` with common presets.\n- **ZRAM Tuner**: Adjust compressed swap size and compression algorithm.\n- **Secure Boot Helper**: MOK key generation and enrollment wizard.\n- **Backup/Restore**: Auto-backup GRUB config before changes.\n\n### New Files\n\n- `utils/kernel.py` - Kernel parameter management.\n- `utils/zram.py` - ZRAM configuration.\n- `utils/secureboot.py` - MOK key management.\n- `ui/boot_tab.py` - Boot management GUI.\n\n---\n\n## [6.1.0] - 2026-02-07 \"Polyglot Update\"

### Added

- **Internationalization (i18n)**: Full localization infrastructure.
- **Translation Files**: `.ts` files for English (`en.ts`) and Swedish (`sv.ts`).
- **414 Translatable Strings**: All UI text wrapped with `self.tr()`.
- **Auto Locale Detection**: `QTranslator` loads translations based on system language.

### Changed

- `main.py`: Added `QTranslator` and `QLocale` integration.
- All 17 UI tab files updated with `self.tr()` wrappers.

### New Files

- `resources/translations/en.ts` - English source strings.
- `resources/translations/sv.ts` - Swedish translation template.
- `resources/translations/README.md` - Translator documentation.

---

## [6.0.0] - 2026-02-07 "Autonomy Update"

### Added

- **Scheduler Tab**: New tab for managing scheduled automation tasks.
- **Background Service**: Systemd user service (`loofi-fedora-tweaks.service`) for running tasks automatically.
- **Notifications**: Desktop toast notifications via `notify-send` when tasks complete.
- **Power Triggers**: Execute tasks when switching to battery or AC power.
- **CLI Daemon Mode**: `--daemon` flag to run as background process.

### New Files

- `utils/scheduler.py` - Task scheduling engine with time and power triggers.
- `utils/notifications.py` - Desktop notification wrapper.
- `utils/daemon.py` - Background service daemon.
- `ui/scheduler_tab.py` - Scheduler management UI.
- `config/loofi-fedora-tweaks.service` - Systemd unit file.

---

## [5.5.0] - 2026-02-07 "Ecosystem Update"

### Added

- **Cloud Sync**: Sync configuration to GitHub Gist.
- **Config Export/Import**: Backup and restore all settings to JSON.
- **Community Presets**: Browse and download presets from GitHub.
- **Redesigned Presets Tab**: Three sub-tabs (My Presets, Community, Backup & Sync).

### New Files

- `utils/config_manager.py` - Full config export/import.
- `utils/cloud_sync.py` - GitHub Gist sync and community presets.

---

## [5.2.0] - 2026-02-07 "Silicon Update"

### Added

- **Hardware Tab**: New consolidated hardware control tab.
- **CPU Governor Switching**: Toggle powersave/schedutil/performance.
- **Power Profile Management**: Quick switch power-saver/balanced/performance.
- **GPU Mode Switching**: Integrated/Hybrid/Dedicated modes via envycontrol.
- **Fan Control**: Manual slider and auto mode via nbfc-linux.

### New Files

- `utils/hardware.py` - HardwareManager for CPU, GPU, Fan, Power controls.
- `ui/hardware_tab.py` - Consolidated hardware control UI.

---

## [5.1.0] - 2026-02-07 "Atomic Update"

### Added

- **Atomic/Silverblue Support**: Automatic detection of rpm-ostree systems.
- **System Overlays Tab**: Manage layered packages on Atomic variants.
- **Polkit Policy**: Professional authorization dialogs.
- **Unified Package Manager**: Abstracts dnf and rpm-ostree operations.

### New Files

- `utils/system.py` - SystemManager for system detection.
- `utils/package_manager.py` - Unified package management.
- `ui/overlays_tab.py` - Layered package management UI.
- `config/org.loofi.fedora-tweaks.policy` - Polkit policy file.

---

## [5.0.0] - 2026-02-07 "Visual Revolution"

### Added

- **Modern Sidebar Navigation**: Replaced top tabs with a sleek left-side menu.
- **Dashboard Tab**: New "Home" screen with system health checks and quick action buttons.
- **Dark Theme (modern.qss)**: Custom glassmorphism-inspired QSS theme with rounded corners.

### Changed

- `ui/main_window.py` now uses `QStackedWidget` + `QListWidget` instead of `QTabWidget`.
- Window resized to 1100x700 for better content display.

## [4.7.0] - 2026-02-07 "Safety Net"

### Added

- **Timeshift Snapshot Prompts**: Before risky operations, the app prompts for a Timeshift backup.
- **Undo System**: `utils/history.py` tracks changes; "Undo" button in Network tab reverts actions.
- **DNF Lock Detection**: `utils/safety.py` checks for running DNF/RPM processes to prevent hangs.

### Changed

- `ui/updates_tab.py` and `ui/cleanup_tab.py` now include safety checks before operations.

## [4.6.0] - 2026-02-07 "Hardware Mastery"

### Added

- **Persistent Battery Limits**: Battery charge limits (80%/100%) now persist via a Systemd oneshot service.
- **Fingerprint Enrollment Wizard**: GUI dialog wrapping `fprintd-enroll` with progress bar.
- **Fan Control Profiles**: Dropdown to switch NBFC profiles (Quiet/Balanced/Performance).

### Changed

- `utils/battery.py` now generates a Systemd service file.
- `ui/tweaks_tab.py` includes fan profile dropdown and fingerprint button.

## [4.5.0] - 2026-02-06 "Refinement"

### Added

- Unit tests for core utilities (`tests/`).
- Robustness improvements: checks for missing tools (`gsettings`, `powerprofilesctl`).

### Fixed

- System Tray initialization crashes on systems without tray support.

## [4.0.0] - 2026-02-05 "Gaming & Network"

### Added

- **Gaming Tab**: GameMode, MangoHud, ProtonUp-Qt, Steam Devices.
- **Network Tab**: DNS Switcher (Google, Cloudflare, Quad9), MAC Randomization.
- **Presets Tab**: Save and load system configurations.

### Changed

- Major UI reorganization into more logical categories.

## [3.0.0] - 2026-02-04 "Essential Apps"

### Added

- **Apps Tab**: One-click install for VS Code, Chrome, Discord, Spotify, etc.
- **Repos Tab**: Enable RPM Fusion, Flathub, Multimedia Codecs.
- **Privacy Tab**: Disable telemetry and trackers.

## [2.0.0] - 2026-02-03 "Updates & Cleanup"

### Added

- **Updates Tab**: Real-time progress bars for DNF and Flatpak updates.
- **Cleanup Tab**: Safe system cleaning with confirmation dialogs.
- **System Tray**: Minimize to tray, quick access menu.

## [1.0.0] - 2026-02-01 "Initial Release"

### Added

- **System Info Tab**: View CPU, RAM, Battery, Disk, Uptime.
- **HP Tweaks Tab**: Battery charge limits, audio fixes.
- Basic PyQt6 structure.
