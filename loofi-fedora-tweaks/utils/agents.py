"""
Agent Framework — Autonomous system management agents.
Part of v19.0 "Vanguard".

Provides:
- Agent dataclasses (AgentConfig, AgentState, AgentAction, AgentResult)
- Built-in agent types (SystemMonitor, SecurityGuard, UpdateWatcher, CleanupBot, PerformanceOptimizer)
- AgentRegistry for managing agent definitions
- Agent persistence (JSON-based state)
- Notification config per agent (v19.0)
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Module constants
HISTORY_MAX_ENTRIES = 100
DEFAULT_MAX_ACTIONS_PER_HOUR = 10
AGENT_ID_LENGTH = 8


class AgentType(Enum):
    """Types of system agents."""
    SYSTEM_MONITOR = "system_monitor"
    SECURITY_GUARD = "security_guard"
    UPDATE_WATCHER = "update_watcher"
    CLEANUP_BOT = "cleanup_bot"
    PERFORMANCE_OPTIMIZER = "performance_optimizer"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Current status of an agent."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class TriggerType(Enum):
    """What triggers an agent to act."""
    SCHEDULE = "schedule"          # Cron-like schedule
    EVENT = "event"                # System event (power, network, etc.)
    THRESHOLD = "threshold"        # Metric crosses a threshold
    MANUAL = "manual"              # User-initiated only
    INTERVAL = "interval"          # Every N seconds


class ActionSeverity(Enum):
    """How impactful an action is."""
    INFO = "info"                  # Logging/notification only
    LOW = "low"                    # Safe automatic action
    MEDIUM = "medium"              # Needs confirmation in strict mode
    HIGH = "high"                  # Always needs confirmation
    CRITICAL = "critical"          # Privileged operation


@dataclass
class AgentTrigger:
    """Defines when an agent should activate."""
    trigger_type: TriggerType
    config: Dict[str, Any] = field(default_factory=dict)
    # For INTERVAL: {"seconds": 300}
    # For THRESHOLD: {"metric": "cpu_percent", "operator": ">", "value": 90}
    # For EVENT: {"event_type": "battery_low"}
    # For SCHEDULE: {"cron": "0 */6 * * *"}

    def to_dict(self) -> dict:
        return {
            "trigger_type": self.trigger_type.value,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentTrigger":
        return cls(
            trigger_type=TriggerType(data["trigger_type"]),
            config=data.get("config", {}),
        )


@dataclass
class AgentAction:
    """An action that an agent can perform."""
    action_id: str
    name: str
    description: str
    severity: ActionSeverity
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    operation: Optional[str] = None  # Reference to an operations.py function

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "command": self.command,
            "args": self.args,
            "operation": self.operation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentAction":
        return cls(
            action_id=data["action_id"],
            name=data["name"],
            description=data["description"],
            severity=ActionSeverity(data.get("severity", "info")),
            command=data.get("command"),
            args=data.get("args", []),
            operation=data.get("operation"),
        )


@dataclass
class AgentResult:
    """Result of an agent action execution."""
    success: bool
    message: str
    action_id: str = ""
    timestamp: float = 0.0
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }


@dataclass
class AgentConfig:
    """Configuration for a single agent instance."""
    agent_id: str
    name: str
    agent_type: AgentType
    description: str
    enabled: bool = True
    triggers: List[AgentTrigger] = field(default_factory=list)
    actions: List[AgentAction] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    # Safety settings
    require_confirmation: bool = False
    max_actions_per_hour: int = DEFAULT_MAX_ACTIONS_PER_HOUR
    dry_run: bool = False
    created_at: float = 0.0
    notification_config: Dict[str, Any] = field(default_factory=dict)
    # Event subscriptions (v19.0 Phase 2)
    subscriptions: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if not self.agent_id:
            self.agent_id = str(uuid.uuid4())[:AGENT_ID_LENGTH]

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "agent_type": self.agent_type.value,
            "description": self.description,
            "enabled": self.enabled,
            "triggers": [t.to_dict() for t in self.triggers],
            "actions": [a.to_dict() for a in self.actions],
            "settings": self.settings,
            "require_confirmation": self.require_confirmation,
            "max_actions_per_hour": self.max_actions_per_hour,
            "dry_run": self.dry_run,
            "created_at": self.created_at,
            "notification_config": self.notification_config,
            "subscriptions": self.subscriptions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        return cls(
            agent_id=data.get("agent_id", ""),
            name=data["name"],
            agent_type=AgentType(data.get("agent_type", "custom")),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            triggers=[AgentTrigger.from_dict(t) for t in data.get("triggers", [])],
            actions=[AgentAction.from_dict(a) for a in data.get("actions", [])],
            settings=data.get("settings", {}),
            require_confirmation=data.get("require_confirmation", False),
            max_actions_per_hour=data.get("max_actions_per_hour", DEFAULT_MAX_ACTIONS_PER_HOUR),
            dry_run=data.get("dry_run", False),
            created_at=data.get("created_at", 0.0),
            notification_config=data.get("notification_config", {}),
            subscriptions=data.get("subscriptions", []),
        )


@dataclass
class AgentState:
    """Runtime state of an agent."""
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    last_run: float = 0.0
    last_result: Optional[AgentResult] = None
    run_count: int = 0
    error_count: int = 0
    actions_this_hour: int = 0
    hour_window_start: float = 0.0
    history: List[AgentResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "last_run": self.last_run,
            "last_result": self.last_result.to_dict() if self.last_result else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "actions_this_hour": self.actions_this_hour,
            "hour_window_start": self.hour_window_start,
            "history": [h.to_dict() for h in self.history[-HISTORY_MAX_ENTRIES:]],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentState":
        last_result = None
        if data.get("last_result"):
            lr = data["last_result"]
            last_result = AgentResult(
                success=lr["success"],
                message=lr["message"],
                action_id=lr.get("action_id", ""),
                timestamp=lr.get("timestamp", 0.0),
                data=lr.get("data"),
            )
        history = []
        for h in data.get("history", []):
            history.append(AgentResult(
                success=h["success"],
                message=h["message"],
                action_id=h.get("action_id", ""),
                timestamp=h.get("timestamp", 0.0),
                data=h.get("data"),
            ))
        return cls(
            agent_id=data["agent_id"],
            status=AgentStatus(data.get("status", "idle")),
            last_run=data.get("last_run", 0.0),
            last_result=last_result,
            run_count=data.get("run_count", 0),
            error_count=data.get("error_count", 0),
            actions_this_hour=data.get("actions_this_hour", 0),
            hour_window_start=data.get("hour_window_start", 0.0),
            history=history,
        )

    def can_act(self, max_per_hour: int) -> bool:
        """Check if the agent is within its rate limit."""
        now = time.time()
        if now - self.hour_window_start > 3600:
            self.actions_this_hour = 0
            self.hour_window_start = now
        return self.actions_this_hour < max_per_hour

    def record_action(self, result: AgentResult):
        """Record an action result in the agent's history."""
        self.last_result = result
        self.last_run = result.timestamp
        self.run_count += 1
        self.actions_this_hour += 1
        if not result.success:
            self.error_count += 1
        self.history.append(result)
        # Keep history bounded
        if len(self.history) > HISTORY_MAX_ENTRIES:
            self.history = self.history[-HISTORY_MAX_ENTRIES:]


# ==================== Built-in Agent Templates ====================

BUILTIN_AGENTS: Dict[str, AgentConfig] = {
    "system_monitor": AgentConfig(
        agent_id="builtin-sysmon",
        name="System Monitor Agent",
        agent_type=AgentType.SYSTEM_MONITOR,
        description="Monitors CPU, RAM, disk, and temperature. Alerts on anomalies.",
        enabled=False,
        triggers=[
            AgentTrigger(TriggerType.INTERVAL, {"seconds": 60}),
        ],
        actions=[
            AgentAction(
                action_id="check_cpu",
                name="Check CPU Usage",
                description="Alert if CPU usage exceeds threshold",
                severity=ActionSeverity.INFO,
                operation="monitor.check_cpu",
            ),
            AgentAction(
                action_id="check_memory",
                name="Check Memory Usage",
                description="Alert if memory usage exceeds threshold",
                severity=ActionSeverity.INFO,
                operation="monitor.check_memory",
            ),
            AgentAction(
                action_id="check_disk",
                name="Check Disk Space",
                description="Alert if disk usage exceeds threshold",
                severity=ActionSeverity.INFO,
                operation="monitor.check_disk",
            ),
            AgentAction(
                action_id="check_temp",
                name="Check Temperature",
                description="Alert if CPU temperature exceeds safe limits",
                severity=ActionSeverity.INFO,
                operation="monitor.check_temperature",
            ),
        ],
        settings={
            "cpu_threshold": 90,
            "memory_threshold": 85,
            "disk_threshold": 90,
            "temp_threshold": 80,
        },
    ),
    "security_guard": AgentConfig(
        agent_id="builtin-secguard",
        name="Security Guard Agent",
        agent_type=AgentType.SECURITY_GUARD,
        description="Watches for security issues: open ports, failed logins, firewall changes.",
        enabled=False,
        triggers=[
            AgentTrigger(TriggerType.INTERVAL, {"seconds": 300}),
        ],
        actions=[
            AgentAction(
                action_id="scan_ports",
                name="Scan Open Ports",
                description="Check for unexpected open ports",
                severity=ActionSeverity.INFO,
                operation="security.scan_ports",
            ),
            AgentAction(
                action_id="check_failed_logins",
                name="Check Failed Logins",
                description="Look for failed authentication attempts",
                severity=ActionSeverity.INFO,
                operation="security.check_failed_logins",
            ),
            AgentAction(
                action_id="firewall_status",
                name="Verify Firewall",
                description="Ensure firewalld is running",
                severity=ActionSeverity.LOW,
                operation="security.check_firewall",
            ),
        ],
        settings={
            "max_failed_logins": 5,
            "alert_on_new_port": True,
        },
    ),
    "update_watcher": AgentConfig(
        agent_id="builtin-updates",
        name="Update Watcher Agent",
        agent_type=AgentType.UPDATE_WATCHER,
        description="Checks for system and application updates periodically.",
        enabled=False,
        triggers=[
            AgentTrigger(TriggerType.INTERVAL, {"seconds": 3600}),
        ],
        actions=[
            AgentAction(
                action_id="check_dnf_updates",
                name="Check DNF Updates",
                description="Query dnf for available updates",
                severity=ActionSeverity.INFO,
                operation="updates.check_dnf",
            ),
            AgentAction(
                action_id="check_flatpak_updates",
                name="Check Flatpak Updates",
                description="Query flatpak for available updates",
                severity=ActionSeverity.INFO,
                operation="updates.check_flatpak",
            ),
        ],
        settings={
            "notify_on_security_updates": True,
            "auto_download": False,
        },
    ),
    "cleanup_bot": AgentConfig(
        agent_id="builtin-cleanup",
        name="Cleanup Bot Agent",
        agent_type=AgentType.CLEANUP_BOT,
        description="Automatically cleans caches, old journals, and temporary files.",
        enabled=False,
        triggers=[
            AgentTrigger(TriggerType.INTERVAL, {"seconds": 86400}),  # Daily
        ],
        actions=[
            AgentAction(
                action_id="clean_dnf_cache",
                name="Clean DNF Cache",
                description="Remove cached package data",
                severity=ActionSeverity.LOW,
                operation="cleanup.dnf_cache",
            ),
            AgentAction(
                action_id="vacuum_journal",
                name="Vacuum Journal",
                description="Clean old systemd journal entries",
                severity=ActionSeverity.LOW,
                operation="cleanup.vacuum_journal",
            ),
            AgentAction(
                action_id="clean_tmp",
                name="Clean Temp Files",
                description="Remove old files from /tmp and ~/.cache",
                severity=ActionSeverity.LOW,
                operation="cleanup.temp_files",
            ),
        ],
        settings={
            "journal_retain_days": 14,
            "cache_max_age_days": 30,
        },
    ),
    "performance_optimizer": AgentConfig(
        agent_id="builtin-perfopt",
        name="Performance Optimizer Agent",
        agent_type=AgentType.PERFORMANCE_OPTIMIZER,
        description="Monitors workload and auto-tunes CPU governor, swappiness, and I/O scheduler.",
        enabled=False,
        triggers=[
            AgentTrigger(TriggerType.INTERVAL, {"seconds": 120}),
            AgentTrigger(TriggerType.EVENT, {"event_type": "power_change"}),
        ],
        actions=[
            AgentAction(
                action_id="detect_workload",
                name="Detect Workload",
                description="Classify current system workload",
                severity=ActionSeverity.INFO,
                operation="tuner.detect_workload",
            ),
            AgentAction(
                action_id="apply_tuning",
                name="Apply Tuning",
                description="Apply recommended CPU governor and swappiness",
                severity=ActionSeverity.MEDIUM,
                operation="tuner.apply_recommendation",
            ),
        ],
        settings={
            "auto_apply": False,
            "min_change_interval": 300,
        },
    ),
}


class AgentRegistry:
    """
    Manages agent configurations and state.
    Singleton pattern — use AgentRegistry.instance().
    """
    _instance: Optional["AgentRegistry"] = None
    _CONFIG_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks/agents")

    def __init__(self):
        self._agents: Dict[str, AgentConfig] = {}
        self._states: Dict[str, AgentState] = {}
        self._ensure_config_dir()
        self._load()

    @classmethod
    def instance(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (useful for tests)."""
        cls._instance = None

    def _ensure_config_dir(self):
        try:
            os.makedirs(self._CONFIG_DIR, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create agent config dir: %s", exc)

    def _agents_file(self) -> str:
        return os.path.join(self._CONFIG_DIR, "agents.json")

    def _states_file(self) -> str:
        return os.path.join(self._CONFIG_DIR, "states.json")

    def _load(self):
        """Load agents and states from disk."""
        # Load agent configs
        agents_path = self._agents_file()
        if os.path.exists(agents_path):
            try:
                with open(agents_path, "r") as fh:
                    data = json.load(fh)
                for agent_data in data:
                    config = AgentConfig.from_dict(agent_data)
                    self._agents[config.agent_id] = config
            except (json.JSONDecodeError, OSError, KeyError) as exc:
                logger.error("Failed to load agents: %s", exc)

        # Merge built-in agents (don't overwrite user modifications)
        for key, builtin in BUILTIN_AGENTS.items():
            if builtin.agent_id not in self._agents:
                self._agents[builtin.agent_id] = builtin

        # Load states
        states_path = self._states_file()
        if os.path.exists(states_path):
            try:
                with open(states_path, "r") as fh:
                    data = json.load(fh)
                for state_data in data:
                    state = AgentState.from_dict(state_data)
                    self._states[state.agent_id] = state
            except (json.JSONDecodeError, OSError, KeyError) as exc:
                logger.error("Failed to load agent states: %s", exc)

    def save(self):
        """Persist agents and states to disk."""
        try:
            with open(self._agents_file(), "w") as fh:
                json.dump([a.to_dict() for a in self._agents.values()], fh, indent=2)
        except OSError as exc:
            logger.error("Failed to save agents: %s", exc)

        try:
            with open(self._states_file(), "w") as fh:
                json.dump([s.to_dict() for s in self._states.values()], fh, indent=2)
        except OSError as exc:
            logger.error("Failed to save agent states: %s", exc)

    def list_agents(self) -> List[AgentConfig]:
        """List all registered agents."""
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent config by ID."""
        return self._agents.get(agent_id)

    def get_state(self, agent_id: str) -> AgentState:
        """Get or create agent state."""
        if agent_id not in self._states:
            self._states[agent_id] = AgentState(agent_id=agent_id)
        return self._states[agent_id]

    def register_agent(self, config: AgentConfig) -> AgentConfig:
        """Register a new agent."""
        if not config.agent_id:
            config.agent_id = str(uuid.uuid4())[:8]
        self._agents[config.agent_id] = config
        self._states[config.agent_id] = AgentState(agent_id=config.agent_id)
        self.save()
        logger.info("Registered agent: %s (%s)", config.name, config.agent_id)
        return config

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent (cannot remove built-in agents)."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        # Check if it's a built-in
        builtin_ids = {a.agent_id for a in BUILTIN_AGENTS.values()}
        if agent_id in builtin_ids:
            logger.warning("Cannot remove built-in agent: %s", agent_id)
            return False
        del self._agents[agent_id]
        self._states.pop(agent_id, None)
        self.save()
        logger.info("Removed agent: %s", agent_id)
        return True

    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.enabled = True
        state = self.get_state(agent_id)
        state.status = AgentStatus.IDLE
        self.save()
        return True

    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.enabled = False
        state = self.get_state(agent_id)
        state.status = AgentStatus.DISABLED
        self.save()
        return True

    def get_enabled_agents(self) -> List[AgentConfig]:
        """Get all enabled agents."""
        return [a for a in self._agents.values() if a.enabled]

    def get_agent_summary(self) -> Dict[str, Any]:
        """Get summary of all agents."""
        agents = self.list_agents()
        enabled = [a for a in agents if a.enabled]
        states = {a.agent_id: self.get_state(a.agent_id) for a in agents}

        running = sum(1 for s in states.values() if s.status == AgentStatus.RUNNING)
        errors = sum(1 for s in states.values() if s.status == AgentStatus.ERROR)
        total_runs = sum(s.run_count for s in states.values())

        return {
            "total_agents": len(agents),
            "enabled": len(enabled),
            "running": running,
            "errors": errors,
            "total_runs": total_runs,
        }

    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent activity across all agents."""
        activity: List[Dict[str, Any]] = []
        for agent in self._agents.values():
            state = self.get_state(agent.agent_id)
            for result in state.history:
                activity.append({
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "action_id": result.action_id,
                    "success": result.success,
                    "message": result.message,
                    "timestamp": result.timestamp,
                })
        # Sort by timestamp descending
        activity.sort(key=lambda x: float(x["timestamp"]), reverse=True)
        return activity[:limit]

    def update_agent_settings(self, agent_id: str, settings: Dict[str, Any]) -> bool:
        """Update an agent's settings."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.settings.update(settings)
        self.save()
        return True

    def create_custom_agent(
        self,
        name: str,
        description: str,
        triggers: Optional[List[AgentTrigger]] = None,
        actions: Optional[List[AgentAction]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> AgentConfig:
        """Create and register a custom agent."""
        config = AgentConfig(
            agent_id=str(uuid.uuid4())[:8],
            name=name,
            agent_type=AgentType.CUSTOM,
            description=description,
            enabled=False,
            triggers=triggers or [],
            actions=actions or [],
            settings=settings or {},
        )
        return self.register_agent(config)

    def load_from_directory(self, directory: str) -> int:
        """
        Load agent definitions from JSON files in a directory.

        Args:
            directory: Path to directory containing .json agent definition files

        Returns:
            Number of agents successfully loaded
        """
        loaded_count = 0

        if not os.path.isdir(directory):
            logger.warning("Agent directory not found: %s", directory)
            return loaded_count

        for filename in os.listdir(directory):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, "r") as fh:
                    agent_data = json.load(fh)

                # Load as AgentConfig
                agent_config = AgentConfig.from_dict(agent_data)

                # Register (or update if already exists)
                self._agents[agent_config.agent_id] = agent_config

                # Create state if doesn't exist
                if agent_config.agent_id not in self._states:
                    self._states[agent_config.agent_id] = AgentState(
                        agent_id=agent_config.agent_id
                    )

                loaded_count += 1
                logger.info(
                    "Loaded agent '%s' (%s) from %s",
                    agent_config.name,
                    agent_config.agent_id,
                    filename
                )

            except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
                logger.error("Failed to load agent from %s: %s", filepath, exc)

        if loaded_count > 0:
            self.save()
            logger.info("Loaded %d agents from %s", loaded_count, directory)

        return loaded_count
