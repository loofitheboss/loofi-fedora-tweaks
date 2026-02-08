# Loofi Fedora Tweaks v10.0 Implementation Plan
## "Zenith Update" - From Tool to Platform

**Planning Date:** February 7, 2026
**Current Version:** v9.3.0 "Clarity Update"
**Target:** v10.0 (Major Release)

---

## Executive Summary

Loofi Fedora Tweaks has grown to 82 Python modules, 25 UI tabs, 87+ features, and ~18,400 lines of code. Version 10.0 is a **consolidation and modernization** release that transforms the app from a feature collection into a cohesive platform. The plan is structured as 5 implementation phases, each with concrete file-level changes.

### Current State Inventory
| Metric | Value |
|--------|-------|
| Python modules | 82 |
| UI tabs | 25 (+ 1 conditional Overlays) |
| Utility modules | 45+ |
| Test files | 6 (~215 tests, ~35% coverage) |
| Lines of code | ~18,400 |
| UI framework | PyQt6 |
| Entry points | GUI, CLI (`--cli`), Daemon (`--daemon`) |
| Packaging | RPM (spec), Flatpak, install.sh |
| CI/CD | None (build_rpm.sh only) |

---

## Phase 0: Foundation (Do First)

**Goal:** Build the infrastructure that every other phase depends on.

### 0.1 CI/CD Pipeline
Create `.github/workflows/ci.yml`:

```yaml
triggers: push to master, PRs
jobs:
  - lint: flake8 + mypy type checking
  - test: pytest with coverage report (fail if <40%)
  - build: rpmbuild in Fedora container
  - release: auto-create RPM artifact on tag
```

**Files to create:**
- `.github/workflows/ci.yml` - Main CI pipeline
- `.github/workflows/release.yml` - Tag-triggered RPM build + GitHub Release
- `pyproject.toml` - Replace ad-hoc config with modern Python packaging
- `pytest.ini` - Test configuration with markers (unit, integration, slow)
- `tests/conftest.py` - Shared fixtures (mock_proc, temp_config_dir, etc.)
- `.flake8` or `ruff.toml` - Linter config

**Deliverables:**
- Every PR runs tests + lint automatically
- Coverage badge on README
- RPM artifacts attached to GitHub Releases

### 0.2 Base Tab Class (Kill Code Duplication)
The #1 architectural debt: 8+ tabs duplicate `run_command()`, `append_output()`, `command_finished()`, and share identical `QTextEdit` output areas.

**Create `ui/base_tab.py`:**
```python
class BaseTab(QWidget):
    """Common base for all tabs with command execution."""
    def __init__(self):
        self.output_area = QTextEdit(readOnly=True, maxHeight=200)
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.on_command_finished)
        self.runner.error_occurred.connect(self.on_error)

    def run_command(self, cmd, args, description): ...
    def append_output(self, text): ...
    def on_command_finished(self, exit_code): ...
    def on_error(self, error_msg): ...
    def add_section(self, title, widgets) -> QGroupBox: ...
```

**Files to modify:** All 15 command-executing tabs inherit from `BaseTab` instead of `QWidget`:
- `advanced_tab.py`, `apps_tab.py`, `cleanup_tab.py`, `containers_tab.py`
- `gaming_tab.py`, `network_tab.py`, `privacy_tab.py`, `repos_tab.py`
- `theming_tab.py`, `tweaks_tab.py`, `updates_tab.py`
- Plus new consolidated tabs

**Impact:** Removes ~40% duplicated code across UI layer (~800 lines eliminated)

### 0.3 Centralized Command Builder
Multiple files construct pkexec commands inconsistently. Some use shell strings (injection risk), others use argument arrays.

**Create `utils/commands.py`:**
```python
class PrivilegedCommand:
    """Safe builder for pkexec-wrapped commands."""
    @staticmethod
    def dnf(action, *packages, flags=None): ...
    @staticmethod
    def systemctl(action, service, user=False): ...
    @staticmethod
    def sysctl(key, value): ...
    @staticmethod
    def write_file(path, content): ...  # pkexec tee
```

**Files to modify:** `operations.py`, `battery.py`, `hardware.py`, `services.py`

### 0.4 Remove Dead Code
- Delete `utils/process.py` (deprecated shim, replaced by `command_runner.py`)
- Remove hardcoded version "5.5.0" in `config_manager.py`, use `version.__version__`
- Consolidate duplicate `bytes_to_human()` (found in 4+ files) into `utils/formatting.py`

---

## Phase 1: Tab Consolidation (25 -> 15)

**Goal:** Reduce cognitive overload. Every tab passes the "3-click test" for critical actions.

### Merge Map

| New Tab | Old Tabs Merged | New File | Old Files |
|---------|----------------|----------|-----------|
| **Home** | Dashboard | `dashboard_tab.py` | (keep as-is, enhance) |
| **System Info** | System Info | `system_info_tab.py` | (keep as-is) |
| **System Monitor** | Performance + Processes | `monitor_tab.py` | `performance_tab.py` + `processes_tab.py` |
| **Maintenance** | Updates + Cleanup + Overlays | `maintenance_tab.py` | `updates_tab.py` + `cleanup_tab.py` + `overlays_tab.py` |
| **Hardware** | Hardware + HP Tweaks | `hardware_tab.py` | `hardware_tab.py` + `tweaks_tab.py` |
| **Software** | Apps + Repos | `software_tab.py` | `apps_tab.py` + `repos_tab.py` |
| **Security & Privacy** | Security + Privacy | `security_tab.py` | `security_tab.py` + `privacy_tab.py` |
| **Desktop** | Director + Theming | `desktop_tab.py` | `director_tab.py` + `theming_tab.py` |
| **Development** | Containers + Developer | `development_tab.py` | `containers_tab.py` + `developer_tab.py` |
| **Community** | Presets + Marketplace | `community_tab.py` | `presets_tab.py` + `marketplace_tab.py` |
| **Diagnostics** | Watchtower + Boot | `diagnostics_tab.py` | `watchtower_tab.py` + `boot_tab.py` |
| **Network** | Network | `network_tab.py` | (keep, expand) |
| **Gaming** | Gaming | `gaming_tab.py` | (keep, expand) |
| **AI Lab** | AI Lab | `ai_tab.py` | (keep, expand) |
| **Automation** | Scheduler + Replicator | `automation_tab.py` | `scheduler_tab.py` + `replicator_tab.py` |

### Implementation Strategy per Merged Tab

Each consolidated tab uses **sub-navigation** (QTabWidget inside the page) to preserve feature access:

```python
class MaintenanceTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(UpdatesSection(), "Updates")
        self.sub_tabs.addTab(CleanupSection(), "Cleanup")
        if SystemManager.is_atomic():
            self.sub_tabs.addTab(OverlaysSection(), "Overlays")
```

This preserves all existing features while reducing the sidebar from 25 to 15 entries.

### main_window.py Rewrite

```python
# v10.0 Consolidated sidebar (15 tabs)
self.add_page("Home",              "🏠", DashboardTab(self))
self.add_page("System Info",       "ℹ️",  SystemInfoTab())
self.add_page("System Monitor",    "📊", self._lazy("monitor"))
self.add_page("Maintenance",       "🔧", self._lazy("maintenance"))
self.add_page("Hardware",          "⚡", self._lazy("hardware"))
self.add_page("Software",          "📦", self._lazy("software"))
self.add_page("Security & Privacy","🛡️", self._lazy("security"))
self.add_page("Network",           "🌐", self._lazy("network"))
self.add_page("Gaming",            "🎮", self._lazy("gaming"))
self.add_page("Desktop",           "🎨", self._lazy("desktop"))
self.add_page("Development",       "🛠️", self._lazy("development"))
self.add_page("AI Lab",            "🧠", self._lazy("ai"))
self.add_page("Automation",        "⏰", self._lazy("automation"))
self.add_page("Community",         "🌐", self._lazy("community"))
self.add_page("Diagnostics",       "🔭", self._lazy("diagnostics"))
```

### Files to Delete After Migration
Once consolidated tabs are working:
- `tweaks_tab.py` -> merged into `hardware_tab.py`
- `processes_tab.py` -> merged into `monitor_tab.py`
- `overlays_tab.py` -> merged into `maintenance_tab.py`
- `repos_tab.py` -> merged into `software_tab.py`
- `privacy_tab.py` -> merged into `security_tab.py`
- `director_tab.py` -> merged into `desktop_tab.py`
- `marketplace_tab.py` -> merged into `community_tab.py`
- `replicator_tab.py` -> merged into `automation_tab.py`
- `watchtower_tab.py` -> merged into `diagnostics_tab.py`
- `boot_tab.py` -> merged into `diagnostics_tab.py`

---

## Phase 2: Architecture Modernization

**Goal:** Separate business logic from UI so CLI, TUI, and future API share the same engine.

### 2.1 Services Layer Extraction

Create `services/` directory as the authoritative business logic layer:

```
loofi-fedora-tweaks/
  services/
    __init__.py
    system_service.py      # System info, health checks, resource monitoring
    package_service.py     # DNF, rpm-ostree, Flatpak operations
    security_service.py    # Firewall, ports, USB guard, privacy
    hardware_service.py    # CPU, GPU, fans, battery, power profiles
    network_service.py     # DNS, MAC randomization, monitoring
    gaming_service.py      # GameMode, MangoHud, Proton, shader cache
    ai_service.py          # Ollama lifecycle, model management
    container_service.py   # Distrobox, Podman operations
    preset_service.py      # Preset CRUD, community sync
    config_service.py      # App config, export/import, drift detection
    automation_service.py  # Scheduler, scripts, systemd units
    desktop_service.py     # Themes, icons, window management
```

Each service:
- Takes no Qt dependencies (pure Python + stdlib)
- Returns dataclasses or typed dicts (not Qt signals)
- Handles errors with custom exceptions (`LoofiError`, `PrivilegeError`, `CommandFailedError`)
- Is independently testable

**Migration pattern:**
```python
# BEFORE (in ui/gaming_tab.py):
def install_gamemode(self):
    self.runner.run_command("pkexec", ["dnf", "install", "-y", "gamemode"])

# AFTER:
# services/gaming_service.py
class GamingService:
    def install_gamemode(self) -> CommandResult:
        return PrivilegedCommand.dnf("install", "gamemode")

# ui/gaming_tab.py
def install_gamemode(self):
    result = self.gaming_service.install_gamemode()
    self.runner.run_command(result.cmd, result.args)
```

### 2.2 Error Handling Framework

**Create `utils/errors.py`:**
```python
class LoofiError(Exception):
    """Base exception with error code and recovery hint."""
    code: str        # e.g., "DNF_LOCKED", "PERMISSION_DENIED"
    hint: str        # e.g., "Wait for other package manager to finish"
    recoverable: bool

class DnfLockedError(LoofiError): ...
class PrivilegeError(LoofiError): ...
class HardwareNotFoundError(LoofiError): ...
class NetworkError(LoofiError): ...
```

### 2.3 Configuration Validation

**Create `utils/schema.py`:**
- JSON Schema definitions for presets, configs, plugin manifests
- `validate_preset(data)` before applying
- `dry_run(operations)` to preview changes without executing

### 2.4 CLI Enhancement

Upgrade `cli/main.py` to use the services layer:

```python
# New subcommands:
loofi --cli monitor          # Live system monitor (curses-based)
loofi --cli suggest          # AI-powered suggestions
loofi --cli doctor           # Full system diagnostic
loofi --cli preset apply X   # Apply preset from CLI
loofi --cli search "dns"     # Search all features
```

Add `--json` flag to all commands for scripting:
```bash
loofi --cli health --json | jq '.cpu_usage'
```

---

## Phase 3: New Features

### 3.1 First-Run Wizard
**File:** `ui/wizard.py`

Guided 3-step setup on first launch:
1. **System Detection** - Auto-detect hardware (laptop/desktop, GPU vendor, battery)
2. **Use Case** - Ask: Gaming / Development / Daily Driver / Server
3. **Apply** - Auto-apply optimal preset based on answers

Detection triggers: Check `~/.config/loofi-fedora-tweaks/first_run_complete`

### 3.2 Command Palette (Ctrl+K)
**File:** `ui/command_palette.py`

Global search overlay that fuzzy-matches across all features:
```
> dns          -> "Network > Change DNS Provider"
> gamemode     -> "Gaming > Install GameMode"
> cleanup      -> "Maintenance > Clean DNF Cache"
```

Implementation: Build feature registry at startup, QLineEdit with QCompleter + popup

### 3.3 Smart Profiles Engine
**File:** `services/profiles_service.py`

Context-aware automation:
- **Gaming Profile**: Detect Steam/game launch -> enable performance mode, disable compositing
- **Battery Profile**: Below 20% charge -> reduce brightness, disable bluetooth, set power-saver
- **Dev Profile**: Detect IDE launch -> start containers, adjust power

Uses D-Bus monitoring for app launch detection. Profiles stored as JSON in `~/.config/loofi-fedora-tweaks/profiles/`.

### 3.4 Hardware Profiles (Beyond HP Elitebook)
**File:** `utils/hardware_profiles.py`

```python
PROFILES = {
    "hp-elitebook": { "battery": True, "nbfc": True, "fingerprint": True },
    "thinkpad":     { "battery": True, "tlp": True, "fingerprint": True },
    "dell-xps":     { "battery": True, "thermal": True },
    "framework":    { "battery": True, "ectool": True },
    "generic":      { "battery": False, "power_profiles": True },
}
```

Auto-detect via DMI data (`/sys/class/dmi/id/product_name`). The "HP Tweaks" tab becomes a generic "Hardware Tweaks" section that adapts its UI based on detected hardware.

### 3.5 Loofi Suggest (AI-Powered Hints)
**File:** `services/suggest_service.py`

When Ollama is installed, provide contextual suggestions:
- Dashboard shows "AI Suggestions" card when issues detected
- User can ask: `loofi --cli chat "why is my laptop hot?"`
- Suggestions link directly to the action that fixes the issue

### 3.6 Enhanced Plugin System
**Upgrade `utils/plugin_base.py`:**
- Plugin manifest validation (JSON Schema)
- Version compatibility checking (semver)
- Hot-reload: `inotify` watch on plugins directory
- Plugin settings UI (auto-generated from manifest)
- Plugin CLI commands auto-registered

---

## Phase 4: Quality & Testing

### 4.1 Test Coverage Expansion

**Target: 60% by v10.0-alpha, 80% by v10.0-stable**

Priority test areas (by risk):
1. **Services layer** (new) - 90% coverage required, all business logic
2. **utils/operations.py** - Every operation tested with mocked commands
3. **utils/safety.py** - Snapshot, lock detection, rollback
4. **utils/battery.py** - Charge limiting with mocked sysfs
5. **utils/hardware.py** - CPU/GPU/fan control with mocked sysfs
6. **CLI commands** - All subcommands tested end-to-end
7. **Plugin system** - Load, unload, hot-reload, malformed manifests
8. **Preset system** - Save, load, apply, community sync

**New test files to create:**
- `tests/test_services.py` - Services layer unit tests
- `tests/test_commands.py` - PrivilegedCommand builder tests
- `tests/test_wizard.py` - First-run wizard flow tests
- `tests/test_profiles.py` - Smart profiles engine tests
- `tests/test_plugins.py` - Plugin lifecycle tests
- `tests/test_cli_json.py` - CLI JSON output format tests
- `tests/test_hardware_profiles.py` - Hardware detection tests
- `tests/test_schema.py` - Config validation tests

### 4.2 Integration Tests
- Full preset save -> load -> apply cycle
- CLI command -> verify system state changed
- Plugin install -> load -> create widget -> unload

### 4.3 Safety Regression Suite
Every bug fix gets a permanent regression test. Tests in `test_bugfixes.py` must never be removed.

---

## Phase 5: Polish & Release

### 5.1 Version & Branding
```python
# version.py
__version__ = "10.0.0"
__version_codename__ = "Zenith Update"
```

### 5.2 Startup Performance
- Current: ~5s startup
- Target: <2s
- Lazy-load services (not just tabs)
- Defer D-Bus connections until needed
- Profile with `cProfile` and eliminate bottlenecks

### 5.3 Accessibility
- Keyboard navigation for all tabs (Tab/Shift+Tab)
- Screen reader hints (`setAccessibleName()`, `setAccessibleDescription()`)
- High-contrast mode support

### 5.4 Documentation Update
- Update `docs/USER_GUIDE.md` for 15-tab layout
- Update `README.md` with v10 features and screenshots
- Update `CHANGELOG.md` with full v10 changelog
- Plugin SDK documentation in `docs/PLUGIN_SDK.md`

### 5.5 Packaging
- Update `loofi-fedora-tweaks.spec` to v10.0.0
- Update `build_rpm.sh` version
- Ensure all new files included in RPM
- Test Flatpak build with new structure
- Submit to Fedora COPR repository

---

## Implementation Order (Critical Path)

```
Phase 0: Foundation
  0.1 CI/CD Pipeline ................... [CRITICAL - unblocks everything]
  0.2 BaseTab class .................... [HIGH - unblocks Phase 1]
  0.3 Centralized commands ............. [HIGH - unblocks Phase 2]
  0.4 Dead code removal ................ [LOW - cleanup]
      |
Phase 1: Tab Consolidation
  1.1 Create consolidated tab shells ... [merge UI files]
  1.2 Rewrite main_window.py .......... [wire 15 tabs]
  1.3 Delete old tab files ............. [cleanup]
  1.4 Update lazy_widget loaders ....... [wire lazy loading]
      |
Phase 2: Architecture
  2.1 Services layer ................... [extract from utils]
  2.2 Error handling framework ......... [new module]
  2.3 Config validation ................ [new module]
  2.4 CLI upgrade ...................... [refactor cli/main.py]
      |
Phase 3: New Features (can partially parallel with Phase 2)
  3.1 First-run wizard ................. [new UI]
  3.2 Command palette .................. [new UI]
  3.3 Smart profiles ................... [new service]
  3.4 Hardware profiles ................ [expand detection]
  3.5 Loofi suggest .................... [AI integration]
  3.6 Plugin system v2 ................. [upgrade existing]
      |
Phase 4: Quality (runs continuously alongside Phases 1-3)
  4.1 Test expansion ................... [ongoing]
  4.2 Integration tests ................ [after Phase 2]
  4.3 Safety regression suite .......... [ongoing]
      |
Phase 5: Polish
  5.1 Version bump ..................... [final]
  5.2 Startup optimization ............. [profiling]
  5.3 Accessibility .................... [UI audit]
  5.4 Documentation .................... [final]
  5.5 Packaging & release .............. [final]
```

---

## File Change Summary

### New Files (23)
```
.github/workflows/ci.yml
.github/workflows/release.yml
pyproject.toml
pytest.ini
.flake8
tests/conftest.py
tests/test_services.py
tests/test_commands.py
tests/test_wizard.py
tests/test_profiles.py
tests/test_plugins.py
tests/test_cli_json.py
tests/test_hardware_profiles.py
tests/test_schema.py
loofi-fedora-tweaks/ui/base_tab.py
loofi-fedora-tweaks/ui/wizard.py
loofi-fedora-tweaks/ui/command_palette.py
loofi-fedora-tweaks/utils/commands.py
loofi-fedora-tweaks/utils/errors.py
loofi-fedora-tweaks/utils/schema.py
loofi-fedora-tweaks/utils/formatting.py
loofi-fedora-tweaks/utils/hardware_profiles.py
loofi-fedora-tweaks/services/ (12 service modules)
```

### Modified Files (15+)
```
loofi-fedora-tweaks/ui/main_window.py  (rewrite for 15 tabs)
loofi-fedora-tweaks/ui/hardware_tab.py (absorb tweaks_tab)
loofi-fedora-tweaks/ui/security_tab.py (absorb privacy_tab)
loofi-fedora-tweaks/ui/ai_tab.py       (add Suggest integration)
loofi-fedora-tweaks/ui/gaming_tab.py   (use services layer)
loofi-fedora-tweaks/ui/network_tab.py  (use services layer)
loofi-fedora-tweaks/cli/main.py        (add new subcommands + --json)
loofi-fedora-tweaks/main.py            (add wizard trigger)
loofi-fedora-tweaks/version.py         (bump to 10.0.0)
loofi-fedora-tweaks/utils/plugin_base.py (v2 plugin system)
loofi-fedora-tweaks/utils/operations.py  (use commands.py)
loofi-fedora-tweaks/utils/battery.py     (use commands.py)
loofi-fedora-tweaks/utils/config_manager.py (use version module)
build_rpm.sh                             (version bump)
loofi-fedora-tweaks.spec                 (version + new files)
```

### Deleted Files (10)
```
loofi-fedora-tweaks/utils/process.py      (deprecated shim)
loofi-fedora-tweaks/ui/tweaks_tab.py      (merged -> hardware_tab)
loofi-fedora-tweaks/ui/processes_tab.py   (merged -> monitor_tab)
loofi-fedora-tweaks/ui/overlays_tab.py    (merged -> maintenance_tab)
loofi-fedora-tweaks/ui/repos_tab.py       (merged -> software_tab)
loofi-fedora-tweaks/ui/privacy_tab.py     (merged -> security_tab)
loofi-fedora-tweaks/ui/director_tab.py    (merged -> desktop_tab)
loofi-fedora-tweaks/ui/marketplace_tab.py (merged -> community_tab)
loofi-fedora-tweaks/ui/replicator_tab.py  (merged -> automation_tab)
loofi-fedora-tweaks/ui/watchtower_tab.py  (merged -> diagnostics_tab)
```

### New Consolidated Tab Files (7)
```
loofi-fedora-tweaks/ui/monitor_tab.py      (Performance + Processes)
loofi-fedora-tweaks/ui/maintenance_tab.py  (Updates + Cleanup + Overlays)
loofi-fedora-tweaks/ui/software_tab.py     (Apps + Repos)
loofi-fedora-tweaks/ui/desktop_tab.py      (Director + Theming)
loofi-fedora-tweaks/ui/development_tab.py  (Containers + Developer)
loofi-fedora-tweaks/ui/community_tab.py    (Presets + Marketplace)
loofi-fedora-tweaks/ui/diagnostics_tab.py  (Watchtower + Boot)
loofi-fedora-tweaks/ui/automation_tab.py   (Scheduler + Replicator)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Tab merging breaks features | Each merged tab keeps sub-tabs; feature parity verified by existing tests |
| Services extraction introduces regressions | Write service tests BEFORE migrating logic |
| CI/CD blocks development | Set up CI first (Phase 0.1) so all subsequent work is tested |
| Plugin system v2 breaks existing plugins | Version field in manifest; v1 plugins still load with compat shim |
| Scope creep | This plan is the scope. Features not listed here go to v10.1+ |

---

## What is NOT in v10.0

These are explicitly deferred to v10.1+ or v11.0:

- Web UI (Vue.js/React) - deferred to v10.2
- TUI (Textual) - deferred to v10.1
- REST API (FastAPI) - deferred to v10.1
- gRPC IPC - deferred to v11.0
- Multi-user support - deferred to v10.1
- eBPF monitoring - deferred to v11.0
- Prometheus/Grafana - deferred to v11.0
- QR code provisioning - deferred to v10.2
- Monetization / Pro tier - not planned

**v10.0 is about consolidation, quality, and platform foundation. Not new frontends.**

---

## Success Criteria for v10.0

- [ ] 15 tabs (down from 25), all features preserved
- [ ] Services layer with 0 Qt dependencies
- [ ] CI/CD running on every PR
- [ ] 60%+ test coverage
- [ ] First-run wizard functional
- [ ] Command palette (Ctrl+K) functional
- [ ] Hardware profiles detect 4+ laptop families
- [ ] Startup time <3s (measured)
- [ ] All existing tests still pass
- [ ] RPM builds and installs cleanly

---

**Document Version:** 2.0
**Last Updated:** February 7, 2026
**Author:** Automated analysis from 4 parallel codebase agents
