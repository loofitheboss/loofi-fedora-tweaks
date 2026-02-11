# v23.0 Architecture Refactor Plan

## ANALYSIS

**Current State:**
- 40+ UI tab files in flat `ui/` directory
- 130+ utility modules (~27K LOC) in flat `utils/` directory
- No separation: system services, business logic, execution layer, UI helpers all mixed
- Plugin system exists but isolated
- API routes exist under `api/routes/`
- Agents config in `agents/` directory

**Key Constraints:**
- Must maintain import compatibility (or provide migration aliases)
- Packaging scripts reference current structure
- Testing requires all system calls mockable via ActionExecutor
- No root access required for tests
- v23.0 goal: introduce `ui/`, `core/`, `services/`, `utils/` structure

**Critical Insight:**
The "utils" directory is a dumping ground. It contains:
- Core execution layer (action_executor, action_result)
- System service abstractions (services, systemd, daemon)
- Business logic (automation_profiles, presets, profiles)
- Agent infrastructure (agent_*, agents)
- API server infrastructure (api_server, auth)
- Hardware/system queries (hardware, battery, temperature, disk)
- UI helpers (formatting, tooltips via ui/tooltips.py)

## DESIGN

### Proposed Structure

```
loofi-fedora-tweaks/
├── main.py                    # Entry point (unchanged)
├── version.py                 # Version (unchanged)
│
├── ui/                        # UI Layer
│   ├── windows/              # Main window, dialogs
│   ├── tabs/                 # Feature tabs (40+ files)
│   ├── widgets/              # Reusable widgets, command palette, lazy_widget
│   ├── base_tab.py           # Base classes
│   └── __init__.py
│
├── core/                      # NEW: Business Logic
│   ├── executor/             # Action execution layer
│   │   ├── action_executor.py
│   │   ├── action_result.py
│   │   └── operations.py
│   ├── profiles/             # User profiles, presets, automation
│   │   ├── automation_profiles.py
│   │   ├── profiles.py
│   │   ├── presets.py
│   │   └── hardware_profiles.py
│   ├── agents/               # Agent orchestration logic
│   │   ├── agent_runner.py
│   │   ├── agent_scheduler.py
│   │   ├── agent_planner.py
│   │   ├── agent_notifications.py
│   │   ├── agents.py
│   │   └── arbitrator.py
│   ├── export/               # Export/import logic
│   │   ├── ansible_export.py
│   │   ├── kickstart.py
│   │   └── cloud_sync.py
│   ├── diagnostics/          # Health, boot analysis, logs
│   │   ├── boot_analyzer.py
│   │   ├── health_timeline.py
│   │   ├── journal.py
│   │   ├── smart_logs.py
│   │   └── monitor.py
│   ├── ai/                   # AI/ML features
│   │   ├── ai.py
│   │   ├── ai_models.py
│   │   ├── context_rag.py
│   │   ├── voice.py
│   │   └── auto_tuner.py
│   ├── history.py
│   ├── config_manager.py
│   ├── settings.py
│   ├── safety.py
│   ├── drift.py
│   └── __init__.py
│
├── services/                  # NEW: System Service Abstraction
│   ├── system/               # Core system services
│   │   ├── services.py       # systemd service management
│   │   ├── process.py / processes.py  # Process management
│   │   ├── command_runner.py
│   │   ├── commands.py
│   │   └── system.py
│   ├── hardware/             # Hardware abstraction
│   │   ├── hardware.py
│   │   ├── battery.py
│   │   ├── temperature.py
│   │   ├── disk.py
│   │   ├── bluetooth.py
│   │   ├── pulse.py          # Audio
│   │   └── fingerprint.py
│   ├── network/              # Network services
│   │   ├── network_monitor.py
│   │   ├── firewall_manager.py
│   │   ├── ports.py
│   │   ├── mesh_discovery.py
│   │   └── clipboard_sync.py
│   ├── desktop/              # Desktop environment
│   │   ├── kwin_tiling.py
│   │   ├── tiling.py
│   │   └── focus_mode.py
│   ├── virtualization/       # VM/container services
│   │   ├── virtualization.py
│   │   ├── vm_manager.py
│   │   ├── containers.py
│   │   ├── disposable_vm.py
│   │   └── vfio.py
│   ├── security/             # Security services
│   │   ├── secureboot.py
│   │   ├── usbguard.py
│   │   ├── sandbox.py
│   │   └── factory_reset.py
│   ├── storage/              # Storage services
│   │   ├── storage.py
│   │   ├── snapshot_manager.py
│   │   └── zram.py
│   ├── software/             # Software management
│   │   ├── package_manager.py
│   │   ├── package_explorer.py
│   │   ├── service_explorer.py
│   │   └── update_checker.py
│   ├── kernel.py
│   ├── daemon.py             # Background daemon service
│   ├── performance.py
│   └── __init__.py
│
├── utils/                     # REDUCED: Pure utilities only
│   ├── formatting.py
│   ├── errors.py
│   ├── log.py
│   ├── notifications.py
│   ├── notification_center.py
│   ├── file_drop.py
│   ├── event_bus.py
│   ├── event_simulator.py
│   ├── rate_limiter.py
│   ├── scheduler.py
│   ├── plugin_base.py         # Keep here, plugins/ uses it
│   ├── devtools.py
│   ├── vscode.py
│   ├── state_teleport.py
│   ├── marketplace.py
│   ├── remote_config.py
│   └── __init__.py
│
├── api/                       # REST API (unchanged structure)
│   ├── routes/
│   │   ├── executor.py
│   │   └── system.py
│   └── __init__.py
│
├── web/                       # Web interface (unchanged)
│   └── ...
│
├── cli/                       # CLI interface (unchanged)
│   ├── main.py
│   └── __init__.py
│
├── plugins/                   # Plugin system (unchanged)
│   ├── ai_lab/
│   ├── hello_world/
│   ├── virtualization/
│   └── __init__.py
│
├── agents/                    # Agent config files (unchanged)
│   ├── cleanup.json
│   ├── security.json
│   └── thermal.json
│
├── config/                    # Configuration (unchanged)
├── assets/                    # Assets (unchanged)
└── resources/                 # Resources (unchanged)
```

### Module Organization Rationale

**core/** — Business logic with NO system calls
- Contains logic that orchestrates services
- All system interaction delegated to `services/`
- Testable via mocking services layer
- Profiles, agents, AI, diagnostics, export all belong here

**services/** — System abstraction boundary
- All subprocess calls, file I/O, hardware queries go here
- Each service wraps system interaction with clean interface
- Mockable for testing
- Organized by domain: system, hardware, network, desktop, virtualization, security, storage, software

**utils/** — Pure utilities ONLY
- No system calls, no business logic
- Formatting, logging, error handling, events, notifications
- Helper functions used across layers

**ui/** — Presentation layer
- No business logic beyond presentation state
- Calls `core/` for operations
- Organized: windows, tabs, widgets

### Key Interfaces

**Execution Layer** (`core/executor/`)
```python
# core/executor/action_executor.py
class ActionExecutor:
    @staticmethod
    def run(cmd: str, args: List[str], preview=False, pkexec=False) -> ActionResult
```

**Service Layer Example** (`services/software/package_manager.py`)
```python
# services/software/package_manager.py
class PackageManager:
    @staticmethod
    def check_updates() -> ActionResult:
        return ActionExecutor.run("dnf", ["check-update"])

    @staticmethod
    def install(package: str) -> ActionResult:
        return ActionExecutor.run("dnf", ["install", "-y", package], pkexec=True)
```

**Business Logic Example** (`core/profiles/automation_profiles.py`)
```python
# core/profiles/automation_profiles.py
from services.software.package_manager import PackageManager
from services.system.services import SystemdService

class AutomationProfile:
    def apply(self) -> List[ActionResult]:
        results = []
        for pkg in self.packages:
            results.append(PackageManager.install(pkg))
        for svc in self.services:
            results.append(SystemdService.enable(svc))
        return results
```

## INTEGRATION

### Backward Compatibility Strategy

**Phase 1: Create new structure with symlinks**
```bash
# Create new directories
mkdir -p core/{executor,profiles,agents,export,diagnostics,ai}
mkdir -p services/{system,hardware,network,desktop,virtualization,security,storage,software}

# Move files (example)
mv utils/action_executor.py core/executor/
mv utils/action_result.py core/executor/

# Create compatibility aliases in utils/__init__.py
from core.executor.action_executor import ActionExecutor
from core.executor.action_result import ActionResult
__all__ = ['ActionExecutor', 'ActionResult', ...]
```

**Phase 2: Update imports incrementally**
- Start with `core/` modules (they import from `services/` and `utils/`)
- Then `ui/` modules (they import from `core/`)
- Finally remove aliases

**Phase 3: Update packaging**
- Update `setup.py` / `pyproject.toml` package discovery
- Update RPM spec file paths
- Update Flatpak manifest
- Verify all entry points still work

### Migration by File Category

**To core/executor/** (3 files)
- utils/action_executor.py → core/executor/action_executor.py
- utils/action_result.py → core/executor/action_result.py
- utils/operations.py → core/executor/operations.py

**To core/profiles/** (4 files)
- utils/automation_profiles.py → core/profiles/automation_profiles.py
- utils/profiles.py → core/profiles/profiles.py
- utils/presets.py → core/profiles/presets.py
- utils/hardware_profiles.py → core/profiles/hardware_profiles.py

**To core/agents/** (6 files)
- utils/agent_runner.py → core/agents/agent_runner.py
- utils/agent_scheduler.py → core/agents/agent_scheduler.py
- utils/agent_planner.py → core/agents/agent_planner.py
- utils/agent_notifications.py → core/agents/agent_notifications.py
- utils/agents.py → core/agents/agents.py
- utils/arbitrator.py → core/agents/arbitrator.py

**To core/export/** (3 files)
- utils/ansible_export.py → core/export/ansible_export.py
- utils/kickstart.py → core/export/kickstart.py
- utils/cloud_sync.py → core/export/cloud_sync.py

**To core/diagnostics/** (5 files)
- utils/boot_analyzer.py → core/diagnostics/boot_analyzer.py
- utils/health_timeline.py → core/diagnostics/health_timeline.py
- utils/journal.py → core/diagnostics/journal.py
- utils/smart_logs.py → core/diagnostics/smart_logs.py
- utils/monitor.py → core/diagnostics/monitor.py

**To core/ai/** (5 files)
- utils/ai.py → core/ai/ai.py
- utils/ai_models.py → core/ai/ai_models.py
- utils/context_rag.py → core/ai/context_rag.py
- utils/voice.py → core/ai/voice.py
- utils/auto_tuner.py → core/ai/auto_tuner.py

**To core/** (6 files, top-level)
- utils/history.py → core/history.py
- utils/config_manager.py → core/config_manager.py
- utils/settings.py → core/settings.py
- utils/safety.py → core/safety.py
- utils/drift.py → core/drift.py
- utils/auth.py → core/auth.py (API authentication logic)

**To services/system/** (6 files)
- utils/services.py → services/system/services.py
- utils/process.py → services/system/process.py
- utils/processes.py → services/system/processes.py (merge with process.py?)
- utils/command_runner.py → services/system/command_runner.py
- utils/commands.py → services/system/commands.py
- utils/system.py → services/system/system.py

**To services/hardware/** (7 files)
- utils/hardware.py → services/hardware/hardware.py
- utils/battery.py → services/hardware/battery.py
- utils/temperature.py → services/hardware/temperature.py
- utils/disk.py → services/hardware/disk.py
- utils/bluetooth.py → services/hardware/bluetooth.py
- utils/pulse.py → services/hardware/pulse.py
- utils/fingerprint.py → services/hardware/fingerprint.py

**To services/network/** (5 files)
- utils/network_monitor.py → services/network/network_monitor.py
- utils/firewall_manager.py → services/network/firewall_manager.py
- utils/ports.py → services/network/ports.py
- utils/mesh_discovery.py → services/network/mesh_discovery.py
- utils/clipboard_sync.py → services/network/clipboard_sync.py

**To services/desktop/** (3 files)
- utils/kwin_tiling.py → services/desktop/kwin_tiling.py
- utils/tiling.py → services/desktop/tiling.py
- utils/focus_mode.py → services/desktop/focus_mode.py

**To services/virtualization/** (5 files)
- utils/virtualization.py → services/virtualization/virtualization.py
- utils/vm_manager.py → services/virtualization/vm_manager.py
- utils/containers.py → services/virtualization/containers.py
- utils/disposable_vm.py → services/virtualization/disposable_vm.py
- utils/vfio.py → services/virtualization/vfio.py

**To services/security/** (4 files)
- utils/secureboot.py → services/security/secureboot.py
- utils/usbguard.py → services/security/usbguard.py
- utils/sandbox.py → services/security/sandbox.py
- utils/factory_reset.py → services/security/factory_reset.py

**To services/storage/** (3 files)
- utils/storage.py → services/storage/storage.py
- utils/snapshot_manager.py → services/storage/snapshot_manager.py
- utils/zram.py → services/storage/zram.py

**To services/software/** (4 files)
- utils/package_manager.py → services/software/package_manager.py
- utils/package_explorer.py → services/software/package_explorer.py
- utils/service_explorer.py → services/software/service_explorer.py
- utils/update_checker.py → services/software/update_checker.py

**To services/** (3 files, top-level)
- utils/kernel.py → services/kernel.py
- utils/daemon.py → services/daemon.py
- utils/performance.py → services/performance.py
- utils/api_server.py → services/api_server.py (web server infrastructure)

**To ui/windows/**
- ui/main_window.py → ui/windows/main_window.py
- ui/wizard.py → ui/windows/wizard.py
- ui/doctor.py → ui/windows/doctor.py
- ui/fingerprint_dialog.py → ui/windows/fingerprint_dialog.py
- ui/whats_new_dialog.py → ui/windows/whats_new_dialog.py

**To ui/tabs/** (all *_tab.py files)
- ui/agents_tab.py → ui/tabs/agents_tab.py
- ui/ai_enhanced_tab.py → ui/tabs/ai_enhanced_tab.py
- ... (30+ tab files)

**To ui/widgets/**
- ui/command_palette.py → ui/widgets/command_palette.py
- ui/lazy_widget.py → ui/widgets/lazy_widget.py
- ui/notification_panel.py → ui/widgets/notification_panel.py
- ui/quick_actions.py → ui/widgets/quick_actions.py
- ui/tab_utils.py → ui/widgets/tab_utils.py
- ui/tooltips.py → ui/widgets/tooltips.py

**Remain in utils/** (13 files)
- utils/formatting.py
- utils/errors.py
- utils/log.py
- utils/notifications.py
- utils/notification_center.py
- utils/file_drop.py
- utils/event_bus.py
- utils/event_simulator.py
- utils/rate_limiter.py
- utils/scheduler.py
- utils/plugin_base.py
- utils/devtools.py
- utils/vscode.py
- utils/state_teleport.py
- utils/marketplace.py
- utils/remote_config.py

**Total Migration:**
- 32 → core/
- 40 → services/
- 40 → ui/ (reorganize)
- 16 remain in utils/
- ~128 files moved/reorganized

## RISKS & MITIGATIONS

### Risk 1: Import breakage
**Mitigation:**
- Phase 1 creates compatibility aliases in old locations
- Run full test suite after each phase
- Update imports incrementally, not all at once

### Risk 2: Packaging breakage
**Mitigation:**
- Test RPM build after Phase 1 (before removing aliases)
- Update manifest files incrementally
- Validate entry points: `loofi-fedora-tweaks`, `loofi-fedora-tweaks --cli`, `--daemon`, `--web`

### Risk 3: Circular dependencies
**Mitigation:**
- Dependency graph: `ui/` → `core/` → `services/` → (no backward deps)
- Enforce via import linting
- Move shared base classes to appropriate layer

### Risk 4: Testing disruption
**Mitigation:**
- Keep ActionExecutor interface unchanged
- All tests mock ActionExecutor, should work transparently
- Add conftest.py fixtures for new service mocks

### Risk 5: Too much change at once
**Mitigation:**
- Incremental migration by subsystem:
  1. executor (3 files) — most critical
  2. services/system (6 files)
  3. services/software (4 files)
  4. core/profiles (4 files)
  5. Continue subsystem by subsystem
- Validate packaging after each subsystem
- Git commits per subsystem, easy to revert

## IMPLEMENTATION ORDER

### Phase 0: Preparation
1. Create architecture decision record (this document)
2. Run full test suite, establish baseline
3. Create feature branch: `refactor/v23-architecture`

### Phase 1: Create Structure + Executor Migration
1. Create directory structure:
   ```bash
   mkdir -p core/{executor,profiles,agents,export,diagnostics,ai}
   mkdir -p services/{system,hardware,network,desktop,virtualization,security,storage,software}
   mkdir -p ui/{windows,tabs,widgets}
   ```

2. Move executor layer (highest priority):
   ```bash
   git mv utils/action_executor.py core/executor/
   git mv utils/action_result.py core/executor/
   git mv utils/operations.py core/executor/
   ```

3. Create compatibility aliases in `utils/__init__.py`:
   ```python
   # Backward compatibility — remove in Phase 2
   from core.executor.action_executor import ActionExecutor
   from core.executor.action_result import ActionResult
   from core.executor.operations import Operation
   ```

4. Update imports in moved files to use `core.executor`
5. Run tests, validate packaging
6. Commit: "refactor(v23): migrate action executor to core/executor/"

### Phase 2: Migrate Services (Critical Path)
**Subsystem 1: services/system** (6 files)
- Move: services.py, process.py, command_runner.py, commands.py, system.py
- Update imports in moved files
- Create utils/ compatibility aliases
- Test, commit

**Subsystem 2: services/software** (4 files)
- Move: package_manager.py, package_explorer.py, service_explorer.py, update_checker.py
- Update imports
- Test, commit

**Subsystem 3: services/hardware** (7 files)
- Move hardware abstraction modules
- Test, commit

**Repeat for:** network (5), desktop (3), virtualization (5), security (4), storage (3), kernel/daemon/perf (4)

### Phase 3: Migrate Core Business Logic
**Subsystem 1: core/profiles** (4 files)
**Subsystem 2: core/agents** (6 files)
**Subsystem 3: core/diagnostics** (5 files)
**Subsystem 4: core/ai** (5 files)
**Subsystem 5: core/export** (3 files)
**Subsystem 6: core top-level** (6 files)

Each subsystem: move, update imports, test, commit

### Phase 4: Reorganize UI
1. Create ui/windows, ui/tabs, ui/widgets
2. Move files to appropriate subdirs
3. Update imports in ui/ modules and main.py
4. Test GUI launch
5. Commit

### Phase 5: Update Imports Across Codebase
1. Search and replace old imports with new paths:
   ```bash
   # Example: update all references to old utils imports
   rg "from utils.action_executor" -l | xargs sed -i 's/from utils.action_executor/from core.executor.action_executor/g'
   ```
2. Incremental approach: update by directory (ui/, api/, cli/, plugins/)
3. Run tests after each batch
4. Commit per directory

### Phase 6: Remove Compatibility Aliases
1. Remove all backward-compat imports from `utils/__init__.py`
2. Verify no remaining old-style imports:
   ```bash
   rg "from utils.(action_executor|agent_|automation_profiles)" --type py
   ```
3. Run full test suite
4. Commit: "refactor(v23): remove backward-compatibility aliases"

### Phase 7: Update Packaging
1. Update `setup.py` or `pyproject.toml`:
   - Update `packages` to include core, services
   - Update entry points if needed
2. Update RPM spec file:
   - Update `%files` section to include new directories
3. Update Flatpak manifest
4. Update AppImage build script
5. Build all packages, validate installation
6. Commit: "build(v23): update packaging for new structure"

### Phase 8: Documentation & Validation
1. Update CONTRIBUTING.md with new structure
2. Update README.md architecture section
3. Add docstrings to each new __init__.py explaining module purpose
4. Create architecture diagram (optional, text-based)
5. Run full test suite (pytest)
6. Run packaging build tests
7. Manual smoke test: GUI, CLI, daemon, web modes
8. Commit: "docs(v23): update for refactored architecture"

### Phase 9: Merge & Release
1. Create PR: `refactor/v23-architecture` → `master`
2. Code review with architecture checklist
3. Merge to master
4. Tag: `v23.0.0`
5. Build release packages
6. Update CHANGELOG.md

## Estimated Effort

- Phase 0: 1 hour (prep)
- Phase 1: 2 hours (executor migration + validation)
- Phase 2: 8 hours (services, ~40 files)
- Phase 3: 6 hours (core, ~32 files)
- Phase 4: 2 hours (UI reorganization)
- Phase 5: 4 hours (import updates)
- Phase 6: 1 hour (remove aliases)
- Phase 7: 3 hours (packaging)
- Phase 8: 2 hours (docs + validation)

**Total: ~29 hours** (3-4 full work days)

## Success Criteria

- All tests pass (pytest)
- All packaging formats build successfully (RPM, Flatpak, AppImage, sdist)
- GUI launches without errors
- CLI mode works
- Daemon mode works
- Web server mode works
- No import errors in any module
- `utils/` contains only pure utilities (no business logic or system calls)
- Clear separation: ui → core → services
- Architecture diagram updated
- CONTRIBUTING.md reflects new structure

## Future Enhancements (v24+)

Once v23.0 structure is stable:
- **v24.0:** Introduce service interfaces (ABC base classes) for easier mocking
- **v24.0:** Add dependency injection container for services
- **v25.0:** Plugin API uses new structure, plugins can extend services
- **v25.0:** Dynamic plugin loading from core/plugins/
- **v26.0:** GraphQL API layer on top of services/
- **v27.0:** gRPC service definitions for IPC with daemon
