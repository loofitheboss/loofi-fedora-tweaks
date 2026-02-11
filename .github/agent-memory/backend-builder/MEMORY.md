# Backend Builder Memory — loofi-fedora-tweaks

## Dataclass Patterns

**Location**: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/action_result.py`

Standard pattern for v19+ structured results:
```python
from dataclasses import dataclass, field
import time

@dataclass
class ActionResult:
    success: bool
    message: str
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def ok(cls, message: str, **kwargs) -> "ActionResult":
        return cls(success=True, message=message, **kwargs)

    @classmethod
    def fail(cls, message: str, **kwargs) -> "ActionResult":
        return cls(success=False, message=message, **kwargs)
```

Use `frozen=True` for immutable value objects. Include `__post_init__` for validation.

## Threading & Concurrency

**EventBus Pattern** (v20 Agent Hive Mind):
- Use `ThreadPoolExecutor` for async callback execution
- Use `threading.Lock` for protecting shared state
- Singleton instances need careful executor lifecycle management in tests
- Don't shutdown executors in test fixtures when using singletons — reinitialize instead

**API Server Pattern**: Background thread with daemon=True (see `/utils/api_server.py`)

**BaseWorker Pattern (v23.0)**: `/core/workers/base_worker.py`
- Standardized QThread worker with `started`, `progress(str, int)`, `finished(object)`, `error(str)` signals
- Subclass and implement `do_work() -> Any` abstract method
- Metaclass resolution: `_BaseWorkerMeta` combines `wrappertype` (Qt) and `ABCMeta`
- Built-in cancellation via `cancel()` / `is_cancelled()`
- Progress reporting via `report_progress(message, percentage)`
- Result retrieval via `get_result()`

## Test Patterns

**Import convention**: Tests use direct imports from utils (e.g., `from utils.event_bus import ...`)
**Mock strategy**: No system execution in tests — all subprocess calls mocked
**Concurrency tests**: Use threading primitives, counters with locks, and sleep delays for async assertions

**Singleton testing pitfall**: When testing singletons with executors, don't call `shutdown()` in fixtures. The singleton persists across tests and shutdown makes the executor unusable.

**QThread testing pitfall**: Qt signals require event loop. For simple tests, test worker completion/results directly via `wait()` and `get_result()`. Avoid signal-based assertions without proper event loop. See `tests/test_base_worker_simple.py`.

## v23.0 Architecture Migration

**System utilities migration** (v23.0 Architecture Hardening):
- Moved `utils/system.py` → `services/system/system.py`
- Moved `utils/services.py` → `services/system/services.py`
- Moved `utils/processes.py` → `services/system/processes.py`
- Moved `utils/process.py` → `services/system/process.py`

**Hardware utilities migration** (v23.0 Architecture Hardening):
- Moved `utils/hardware.py` → `services/hardware/hardware.py`
- Moved `utils/battery.py` → `services/hardware/battery.py`
- Moved `utils/disk.py` → `services/hardware/disk.py`
- Moved `utils/temperature.py` → `services/hardware/temperature.py`
- Moved `utils/bluetooth.py` → `services/hardware/bluetooth.py`
- Moved `utils/hardware_profiles.py` → `services/hardware/hardware_profiles.py`

**Backward-compat shims**:
- Shims in `utils/` re-export from `services/system/`
- Must include `subprocess`, `os` imports for test mock compatibility
- Tests patch `utils.services.subprocess.run` — shim must have subprocess in namespace
- Use deprecation warnings with `stacklevel=2` for proper caller context

**services/system/__init__.py** exports:
- SystemManager
- ServiceManager, ServiceUnit, UnitScope, UnitState, Result
- ProcessManager, ProcessInfo
- CommandRunner (backward compat)

**services/hardware/__init__.py** exports:
- HardwareManager
- BatteryManager
- DiskManager, DiskUsage, LargeDirectory
- TemperatureManager, TemperatureSensor
- BluetoothManager, BluetoothDevice, BluetoothDeviceType, BluetoothResult, BluetoothStatus
- PROFILES, detect_hardware_profile, get_profile_label, get_all_profiles

## Module Structure

Standard module header:
```python
"""One-line module purpose.

Extended description if needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
```

All public functions: type hints + docstrings.
All dataclass fields: type annotations.

## Executor Architecture (v19.0 Phase 1)

**BaseActionExecutor ABC** (`core/executor/base_executor.py`):
- Abstract interface: `execute()`, `preview()`, `set_global_dry_run()`
- All executors return `ActionResult`
- `privileged` parameter for pkexec/sudo escalation
- No Qt/UI dependencies in base or sync implementations

**ActionExecutor** (`core/executor/action_executor.py`):
- Concrete sync subprocess implementation extending BaseActionExecutor
- Instance methods: `execute()`, `preview()`
- Legacy classmethod API: `run()` for backward compat (maps pkexec→privileged)
- pkexec integration via `privileged=True` parameter
- Flatpak-aware: auto-wraps with `flatpak-spawn --host`
- JSON-lines action log at `~/.local/share/loofi-fedora-tweaks/action_log.jsonl`

**Backward Compatibility**:
- `utils/action_executor.py` shim re-exports from `core/executor/`
- Legacy `ActionExecutor.run(pkexec=True)` → maps to `privileged=True`
- Internal methods changed from classmethod to instance methods (_build_command, _trim_log, etc.)
- Tests must instantiate executor to call internal methods

## v20 EventBus Topics

Standard topics from roadmap:
- `system.power.battery` (level, status)
- `system.thermal.throttling` (temp, sensor)
- `system.thermal.normal` (temp, sensor)
- `security.firewall.panic` (source)
- `agent.{agent_id}.success` (action_result)
- `agent.{agent_id}.failure` (error_log)
- `system.storage.low` (path, available_mb)
- `network.connection.public` (ssid, security)
- `network.connection.trusted` (ssid, security)

## Agent Framework Integration (v19.0 Phase 2)

### AgentConfig Subscriptions
- Added `subscriptions: List[str] = field(default_factory=list)` to AgentConfig
- Must be included in `to_dict()` and `from_dict()` serialization methods
- Subscriptions are event topics the agent listens to

### AgentScheduler Module
**Location**: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/agent_scheduler.py`

- Integrates AgentRegistry with EventBus
- Auto-subscribes enabled agents on initialization
- Respects rate limiting via `AgentState.can_act(max_actions_per_hour)`
- Publishes agent completion events: `agent.{agent_id}.success` or `agent.{agent_id}.failure`
- Thread-safe execution with status tracking (IDLE → RUNNING → IDLE/ERROR)
- `_execute_action()` integrates with ActionExecutor for real command execution
- Determines pkexec need based on action.severity (medium/high/critical require privileges)
- **Rate limit caveat**: Counts individual actions, not executions. Agent with 4 actions running once increments `actions_this_hour` by 4

### Agent Definition Files (v20.0)
**Location**: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/agents/*.json`

JSON files defining agents matching AgentConfig schema. Example structure:
```json
{
  "agent_id": "event-cleanup",
  "name": "Storage Cleanup Agent",
  "agent_type": "cleanup_bot",
  "subscriptions": ["system.storage.low"],
  "actions": [{"action_id": "...", "command": "dnf", "args": ["clean", "all"], ...}],
  "max_actions_per_hour": 3,
  "enabled": true
}
```

### AgentRegistry Dynamic Loading
Added `load_from_directory(directory: str) -> int` method to AgentRegistry:
- Loads agent JSON files from specified directory
- Returns count of successfully loaded agents
- Creates AgentState for new agents automatically
- Saves registry after loading complete

## v25.0 Plugin Architecture
See `plugin-architecture.md` for full details. Key points:
- Source root: `loofi-fedora-tweaks/loofi-fedora-tweaks/` (nested dir)
- `core/plugins/` package: interface, metadata, registry, loader, compat
- `BaseTab(QWidget, PluginInterface)` — QWidget first in MRO
- `TYPE_CHECKING` guard in interface.py for CompatibilityDetector import
- Tasks 1-4, 8 complete. Tests and migration (Tasks 5-13) pending.

### EventSimulator Utility (v20.0)

**Location**: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/event_simulator.py`

Testing utility for triggering events without system changes:

- `simulate_low_storage(path, available_mb, threshold_mb)`
- `simulate_public_wifi(ssid, security, interface)`
- `simulate_trusted_network(ssid, security, interface)`
- `simulate_thermal_throttling(temperature, sensor, threshold)`
- `simulate_thermal_normal(temperature, sensor, threshold)`
- `simulate_battery_low(level, status, threshold)`
- `simulate_firewall_panic(source, reason)`
- `simulate_custom_event(topic, data, source)`

Use in tests to trigger agent reactions without real system state changes

### Test Setup for Agent Events
**Location**: `/workspaces/loofi-fedora-tweaks/tests/test_agent_events.py`

Critical setup steps:
```python
def setUp(self):
    AgentRegistry.reset()
    EventBus._instance = None
    registry = AgentRegistry.instance()
    registry._agents.clear()  # Remove built-in agents
    registry._states.clear()
    event_bus = EventBus()
    event_bus.clear()  # Clear subscriptions
```

- Tests require `time.sleep(0.1-0.2)` after publishing events (async execution)
- Patch paths for action execution: `@patch('utils.action_executor.ActionExecutor.run')`
- Built-in agents from `BUILTIN_AGENTS` dict are auto-loaded, must be cleared for clean tests

### Practical Agent Implementations (v20.0)
**Location**: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/agents/`

Three production agents demonstrating inter-agent communication:
1. **cleanup.json** - Storage Cleanup Agent: Responds to `system.storage.low`, cleans DNF cache, journals, tmp files
2. **security.json** - Network Security Agent: Adjusts firewall on `network.connection.public/trusted`
3. **thermal.json** - Thermal Management Agent: Reduces load on `system.thermal.throttling`, restores on `system.thermal.normal`

All agents use ActionExecutor for system commands (dnf, journalctl, firewall-cmd, cpupower, brightnessctl)

## ConfigManager Integration

**Location**: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/config_manager.py`

Persistent JSON config at `~/.config/loofi-fedora-tweaks/config.json`:
- `ConfigManager.load_config() -> Optional[dict]` - Load saved config
- `ConfigManager.save_config(config: dict) -> bool` - Save runtime config
- Config structure is flexible (any keys allowed)
- Use for app-level settings that need persistence between sessions

**UI Feature Flag Pattern**: For UI-specific feature flags:
1. Check config file first: `config.get("ui", {}).get("feature_name")`
2. Fallback to environment variable: `os.environ.get("FEATURE_VAR") == "1"`
3. Default to False/safe behavior if neither is set

Example: Frameless mode flag in MainWindow.__init__ checks `ui.frameless_mode` then `LOOFI_FRAMELESS=1`
