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

## Test Patterns

**Import convention**: Tests use direct imports from utils (e.g., `from utils.event_bus import ...`)
**Mock strategy**: No system execution in tests — all subprocess calls mocked
**Concurrency tests**: Use threading primitives, counters with locks, and sleep delays for async assertions

**Singleton testing pitfall**: When testing singletons with executors, don't call `shutdown()` in fixtures. The singleton persists across tests and shutdown makes the executor unusable.

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
