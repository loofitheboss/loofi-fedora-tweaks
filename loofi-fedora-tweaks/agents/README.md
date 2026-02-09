# Agent Definitions

This directory contains declarative agent definitions in JSON format for the v20.0 Agent Hive Mind system.

## Overview

Agents are autonomous system management components that respond to events published on the EventBus. Each agent:
- Subscribes to specific event topics
- Executes predefined actions when events occur
- Respects rate limiting to prevent excessive actions
- Publishes completion events for inter-agent communication

## Agent Files

### cleanup.json - Storage Cleanup Agent
**Subscriptions:** `system.storage.low`

Automatically cleans system when storage is low by:
- Clearing DNF package cache
- Removing old journald logs (7 days)
- Cleaning temporary files (3 days)
- Notifying user of space recovered

**Rate Limit:** 3 actions/hour

### security.json - Network Security Agent
**Subscriptions:** `network.connection.public`, `network.connection.trusted`

Adjusts firewall profile based on network connection:
- Enables strict firewall on public Wi-Fi
- Restores normal firewall on trusted networks
- Notifies user of security posture changes

**Rate Limit:** 10 actions/hour

### thermal.json - Thermal Management Agent
**Subscriptions:** `system.thermal.throttling`, `system.thermal.normal`

Responds to thermal events by:
- Setting CPU governor to powersave when throttling
- Reducing screen brightness to reduce heat
- Restoring performance settings when temperature normalizes

**Rate Limit:** 5 actions/hour

## JSON Schema

Agent definition files must match the `AgentConfig` dataclass structure:

```json
{
  "agent_id": "unique-identifier",
  "name": "Human-Readable Name",
  "agent_type": "cleanup_bot|security_guard|performance_optimizer|custom",
  "description": "What this agent does",
  "enabled": true,
  "subscriptions": ["event.topic.1", "event.topic.2"],
  "triggers": [
    {
      "trigger_type": "event",
      "config": {"event_types": ["..."]}
    }
  ],
  "actions": [
    {
      "action_id": "unique_action_id",
      "name": "Action Name",
      "description": "What this action does",
      "severity": "info|low|medium|high|critical",
      "command": "executable",
      "args": ["arg1", "arg2"],
      "operation": "optional.operation.reference"
    }
  ],
  "settings": {},
  "require_confirmation": false,
  "max_actions_per_hour": 10,
  "dry_run": false,
  "notification_config": {
    "enabled": true,
    "urgency": "normal",
    "title": "Notification Title"
  }
}
```

## Loading Agents

Agents are automatically loaded from this directory by calling:

```python
from utils.agents import AgentRegistry

registry = AgentRegistry.instance()
loaded_count = registry.load_from_directory("/path/to/agents")
```

## Command Execution

Agent actions are executed through the centralized `ActionExecutor`:
- Commands with `severity` of `medium`, `high`, or `critical` use `pkexec` for privilege escalation
- All execution is logged for diagnostics
- Commands can be previewed before execution
- Rate limiting prevents excessive system modifications

## Testing

Test agents using the `EventSimulator` utility:

```python
from utils.event_simulator import EventSimulator

simulator = EventSimulator()
simulator.simulate_low_storage(available_mb=500)
simulator.simulate_public_wifi(ssid="CoffeeShop")
simulator.simulate_thermal_throttling(temperature=95)
```

See `/workspaces/loofi-fedora-tweaks/tests/test_agent_implementations.py` for comprehensive examples.

## Creating Custom Agents

To create a new agent:

1. Create a JSON file in this directory following the schema above
2. Define event subscriptions in the `subscriptions` array
3. Specify actions with commands or operation references
4. Set appropriate rate limits and severity levels
5. Agent will be loaded automatically on next application start

Example minimal agent:

```json
{
  "agent_id": "custom-monitor",
  "name": "Custom Monitor",
  "agent_type": "custom",
  "description": "Monitors custom metrics",
  "enabled": true,
  "subscriptions": ["system.custom.event"],
  "actions": [
    {
      "action_id": "log_event",
      "name": "Log Event",
      "description": "Log the custom event",
      "severity": "info",
      "operation": "custom.log_event"
    }
  ],
  "max_actions_per_hour": 20
}
```

## Safety Considerations

- **Rate Limiting**: Always set `max_actions_per_hour` to prevent runaway agents
- **Severity Levels**: Use appropriate severity for privilege escalation control
- **Dry Run Mode**: Test agents with `"dry_run": true` before production use
- **Confirmation**: Set `"require_confirmation": true` for destructive operations
- **Testing**: All agents should have corresponding integration tests

## Documentation

- Agent Framework: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/agents.py`
- Event Scheduler: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/agent_scheduler.py`
- Event Bus: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/event_bus.py`
- Action Executor: `/workspaces/loofi-fedora-tweaks/loofi-fedora-tweaks/utils/action_executor.py`
