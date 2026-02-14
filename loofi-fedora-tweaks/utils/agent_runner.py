"""
Agent Runner — Executes agents with safety constraints and scheduling.
Part of v19.0 "Vanguard".

Provides:
- AgentExecutor: Executes individual agent actions against system state
- AgentScheduler: Manages interval/event-based agent triggering
- AgentNotifier integration for desktop/webhook notifications (v19.0)
- Safety: rate limiting, dry-run mode, severity gating
"""

import logging
import os
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from services.system import SystemManager
from utils.agents import (
    ActionSeverity,
    AgentAction,
    AgentConfig,
    AgentRegistry,
    AgentResult,
    AgentState,
    AgentStatus,
    TriggerType,
)
from utils.action_executor import ActionExecutor as CentralExecutor
from utils.arbitrator import Arbitrator, AgentRequest, Priority

logger = logging.getLogger(__name__)

# Module constants
COMMAND_TIMEOUT_SECONDS = 60
SCHEDULER_POLL_SECONDS = 10


class AgentExecutor:
    """
    Executes agent actions against the real system.
    Maps operation strings to actual system checks and commands.
    """

    _arbitrator = Arbitrator()

    @staticmethod
    def execute_action(
        agent: AgentConfig,
        action: AgentAction,
        state: AgentState,
    ) -> AgentResult:
        """
        Execute a single agent action.

        Checks rate limits and severity before execution.
        In dry_run mode, logs but does not execute.
        """
        # Rate limit check
        if not state.can_act(agent.max_actions_per_hour):
            return AgentResult(
                success=False,
                message=f"Rate limit exceeded ({agent.max_actions_per_hour}/hr)",
                action_id=action.action_id,
            )

        # Dry run check
        if agent.dry_run:
            logger.info(
                "[DRY RUN] Agent %s would execute: %s",
                agent.name,
                action.name,
            )
            return AgentResult(
                success=True,
                message=f"[DRY RUN] {action.name}: {action.description}",
                action_id=action.action_id,
            )

        # Severity gate — block CRITICAL actions from automatic execution
        if action.severity == ActionSeverity.CRITICAL:
            return AgentResult(
                success=False,
                message=f"Action '{action.name}' requires manual confirmation (severity: critical)",
                action_id=action.action_id,
            )

        # Resource arbitration check
        request = AgentRequest(
            agent_name=agent.name,
            resource=AgentExecutor._infer_resource(action),
            priority=AgentExecutor._infer_priority(action),
        )
        if not AgentExecutor._arbitrator.can_proceed(request):
            return AgentResult(
                success=False,
                message=f"Action '{action.name}' deferred by arbitrator",
                action_id=action.action_id,
                data={"arbitrator_block": True},
            )

        # Route to appropriate handler
        try:
            if action.operation:
                result = AgentExecutor._execute_operation(
                    action.operation, agent.settings
                )
            elif action.command:
                result = AgentExecutor._execute_command(action.command, action.args)
            else:
                result = AgentResult(
                    success=False,
                    message=f"Action '{action.name}' has no operation or command",
                    action_id=action.action_id,
                )
            result.action_id = action.action_id
            return result

        except Exception as exc:
            logger.error(
                "Agent %s action %s failed: %s",
                agent.name,
                action.name,
                exc,
            )
            return AgentResult(
                success=False,
                message=f"Error executing '{action.name}': {exc}",
                action_id=action.action_id,
            )

    @staticmethod
    def _execute_command(cmd: str, args: List[str]) -> AgentResult:
        """Execute a raw command via centralized ActionExecutor."""
        ar = CentralExecutor.run(cmd, args, timeout=COMMAND_TIMEOUT_SECONDS)
        return AgentResult(
            success=ar.success,
            message=ar.message,
            data={"exit_code": ar.exit_code, "stdout": ar.stdout[:1000]},
        )

    @staticmethod
    def _execute_operation(operation: str, settings: Dict[str, Any]) -> AgentResult:
        """
        Execute a named operation.

        Operation format: "module.function" mapping to known system checks.
        """
        handlers = AgentExecutor._get_operation_handlers()
        handler = handlers.get(operation)
        if handler:
            result: AgentResult = handler(settings)
            return result
        return AgentResult(
            success=False,
            message=f"Unknown operation: {operation}",
        )

    @staticmethod
    def _infer_priority(action: AgentAction) -> Priority:
        if action.severity == ActionSeverity.CRITICAL:
            return Priority.CRITICAL
        if action.severity in (ActionSeverity.HIGH, ActionSeverity.MEDIUM):
            return Priority.USER_INTERACTION
        return Priority.BACKGROUND

    @staticmethod
    def _infer_resource(action: AgentAction) -> str:
        if action.operation:
            prefix = action.operation.split(".", 1)[0]
            if prefix in {"monitor", "tuner"}:
                return "cpu"
            if prefix in {"security", "updates"}:
                return "network"
            if prefix in {"cleanup"}:
                return "disk"
        return "background_process"

    @staticmethod
    def _get_operation_handlers() -> Dict[str, Callable]:
        """Return mapping of operation names to handler functions."""
        return {
            # System Monitor operations
            "monitor.check_cpu": AgentExecutor._op_check_cpu,
            "monitor.check_memory": AgentExecutor._op_check_memory,
            "monitor.check_disk": AgentExecutor._op_check_disk,
            "monitor.check_temperature": AgentExecutor._op_check_temperature,
            # Security operations
            "security.scan_ports": AgentExecutor._op_scan_ports,
            "security.check_failed_logins": AgentExecutor._op_check_failed_logins,
            "security.check_firewall": AgentExecutor._op_check_firewall,
            # Update operations
            "updates.check_dnf": AgentExecutor._op_check_dnf_updates,
            "updates.check_flatpak": AgentExecutor._op_check_flatpak_updates,
            # Cleanup operations
            "cleanup.dnf_cache": AgentExecutor._op_clean_dnf_cache,
            "cleanup.vacuum_journal": AgentExecutor._op_vacuum_journal,
            "cleanup.temp_files": AgentExecutor._op_clean_temp_files,
            # Performance operations
            "tuner.detect_workload": AgentExecutor._op_detect_workload,
            "tuner.apply_recommendation": AgentExecutor._op_apply_tuning,
        }

    # ==================== Monitor Operations ====================

    @staticmethod
    def _op_check_cpu(settings: Dict[str, Any]) -> AgentResult:
        """Check CPU usage against threshold."""
        threshold = settings.get("cpu_threshold", 90)
        try:
            with open("/proc/loadavg", "r") as fh:
                parts = fh.read().strip().split()
            load_1 = float(parts[0])
            cores = os.cpu_count() or 1
            percent = (load_1 / cores) * 100

            if percent > threshold:
                return AgentResult(
                    success=True,
                    message=f"⚠️ CPU load high: {percent:.1f}% (threshold: {threshold}%)",
                    data={"cpu_percent": percent, "alert": True},
                )
            return AgentResult(
                success=True,
                message=f"CPU load normal: {percent:.1f}%",
                data={"cpu_percent": percent, "alert": False},
            )
        except OSError as exc:
            return AgentResult(success=False, message=f"Cannot read CPU: {exc}")

    @staticmethod
    def _op_check_memory(settings: Dict[str, Any]) -> AgentResult:
        """Check memory usage against threshold."""
        threshold = settings.get("memory_threshold", 85)
        try:
            with open("/proc/meminfo", "r") as fh:
                lines = fh.readlines()
            mem_info = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem_info[key] = int(val)

            total = mem_info.get("MemTotal", 1)
            available = mem_info.get("MemAvailable", total)
            used_pct = ((total - available) / total) * 100

            if used_pct > threshold:
                return AgentResult(
                    success=True,
                    message=f"⚠️ Memory high: {used_pct:.1f}% (threshold: {threshold}%)",
                    data={"memory_percent": used_pct, "alert": True},
                )
            return AgentResult(
                success=True,
                message=f"Memory normal: {used_pct:.1f}%",
                data={"memory_percent": used_pct, "alert": False},
            )
        except OSError as exc:
            return AgentResult(success=False, message=f"Cannot read memory: {exc}")

    @staticmethod
    def _op_check_disk(settings: Dict[str, Any]) -> AgentResult:
        """Check root disk usage against threshold."""
        threshold = settings.get("disk_threshold", 90)
        try:
            st = os.statvfs("/")
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used_pct = ((total - free) / total) * 100 if total > 0 else 0

            if used_pct > threshold:
                return AgentResult(
                    success=True,
                    message=f"⚠️ Disk usage high: {used_pct:.1f}% (threshold: {threshold}%)",
                    data={"disk_percent": used_pct, "alert": True},
                )
            return AgentResult(
                success=True,
                message=f"Disk usage normal: {used_pct:.1f}%",
                data={"disk_percent": used_pct, "alert": False},
            )
        except OSError as exc:
            return AgentResult(success=False, message=f"Cannot read disk: {exc}")

    @staticmethod
    def _op_check_temperature(settings: Dict[str, Any]) -> AgentResult:
        """Check CPU temperature against threshold."""
        threshold = settings.get("temp_threshold", 80)
        thermal_zones = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/thermal/thermal_zone1/temp",
        ]
        temp_c = None
        for zone in thermal_zones:
            try:
                with open(zone, "r") as fh:
                    temp_c = int(fh.read().strip()) / 1000.0
                break
            except (OSError, ValueError):
                continue

        if temp_c is None:
            return AgentResult(
                success=True,
                message="No temperature sensors found",
                data={"alert": False},
            )

        if temp_c > threshold:
            return AgentResult(
                success=True,
                message=f"⚠️ Temperature high: {temp_c:.1f}°C (threshold: {threshold}°C)",
                data={"temperature_c": temp_c, "alert": True},
            )
        return AgentResult(
            success=True,
            message=f"Temperature normal: {temp_c:.1f}°C",
            data={"temperature_c": temp_c, "alert": False},
        )

    # ==================== Security Operations ====================

    @staticmethod
    def _op_scan_ports(settings: Dict[str, Any]) -> AgentResult:
        """Scan for open listening ports."""
        try:
            result = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return AgentResult(success=False, message="Failed to scan ports")

            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            ports = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    addr = parts[3]
                    ports.append(addr)

            return AgentResult(
                success=True,
                message=f"Found {len(ports)} listening port(s)",
                data={"port_count": len(ports), "ports": ports[:20], "alert": False},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"Port scan failed: {exc}")

    @staticmethod
    def _op_check_failed_logins(settings: Dict[str, Any]) -> AgentResult:
        """Check for recent failed login attempts via journalctl."""
        max_allowed = settings.get("max_failed_logins", 5)
        try:
            result = subprocess.run(
                [
                    "journalctl",
                    "--no-pager",
                    "-q",
                    "--since",
                    "1 hour ago",
                    "-g",
                    "authentication failure|Failed password",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
            count = len(lines)

            if count > max_allowed:
                return AgentResult(
                    success=True,
                    message=f"⚠️ {count} failed login attempts in last hour (threshold: {max_allowed})",
                    data={"failed_logins": count, "alert": True},
                )
            return AgentResult(
                success=True,
                message=f"{count} failed login attempt(s) in last hour",
                data={"failed_logins": count, "alert": False},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"Login check failed: {exc}")

    @staticmethod
    def _op_check_firewall(settings: Dict[str, Any]) -> AgentResult:
        """Check if firewalld is running."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "firewalld"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_active = result.stdout.strip() == "active"
            if is_active:
                return AgentResult(
                    success=True,
                    message="Firewall is active",
                    data={"firewall_active": True, "alert": False},
                )
            return AgentResult(
                success=True,
                message="⚠️ Firewall is not active",
                data={"firewall_active": False, "alert": True},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"Firewall check failed: {exc}")

    # ==================== Update Operations ====================

    @staticmethod
    def _op_check_dnf_updates(settings: Dict[str, Any]) -> AgentResult:
        """Check for available package updates."""
        try:
            if SystemManager.is_atomic():
                result = subprocess.run(
                    ["rpm-ostree", "upgrade", "--check"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0 and "AvailableUpdate" in result.stdout:
                    lines = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if line.strip()
                    ]
                    count = len(lines)
                    return AgentResult(
                        success=True,
                        message=f"{count} rpm-ostree update(s) available",
                        data={"dnf_updates": count, "alert": count > 0},
                    )
                return AgentResult(
                    success=True,
                    message="System is up to date (rpm-ostree)",
                    data={"dnf_updates": 0, "alert": False},
                )
            else:
                result = subprocess.run(
                    ["dnf", "check-update", "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                # Exit code 100 = updates available, 0 = no updates
                if result.returncode == 100:
                    lines = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if line.strip() and not line.startswith("Last")
                    ]
                    count = len(lines)
                    return AgentResult(
                        success=True,
                        message=f"{count} DNF update(s) available",
                        data={"dnf_updates": count, "alert": count > 0},
                    )
                return AgentResult(
                    success=True,
                    message="System is up to date (DNF)",
                    data={"dnf_updates": 0, "alert": False},
                )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"DNF check failed: {exc}")

    @staticmethod
    def _op_check_flatpak_updates(settings: Dict[str, Any]) -> AgentResult:
        """Check for available Flatpak updates."""
        try:
            result = subprocess.run(
                ["flatpak", "remote-ls", "--updates"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                lines = [
                    line for line in result.stdout.strip().split("\n") if line.strip()
                ]
                count = len(lines)
                return AgentResult(
                    success=True,
                    message=f"{count} Flatpak update(s) available",
                    data={"flatpak_updates": count, "alert": count > 0},
                )
            return AgentResult(
                success=True,
                message="Flatpak updates check complete",
                data={"flatpak_updates": 0, "alert": False},
            )
        except FileNotFoundError:
            return AgentResult(
                success=True,
                message="Flatpak not installed",
                data={"flatpak_updates": 0, "alert": False},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"Flatpak check failed: {exc}")

    # ==================== Cleanup Operations ====================

    @staticmethod
    def _op_clean_dnf_cache(settings: Dict[str, Any]) -> AgentResult:
        """Report DNF cache size (actual cleanup requires pkexec)."""
        try:
            result = subprocess.run(
                ["du", "-sh", "/var/cache/dnf"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            size = (
                result.stdout.strip().split("\t")[0]
                if result.returncode == 0
                else "unknown"
            )
            return AgentResult(
                success=True,
                message=f"DNF cache size: {size} (use Maintenance tab to clean)",
                data={"cache_size": size, "alert": False},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"Cache check failed: {exc}")

    @staticmethod
    def _op_vacuum_journal(settings: Dict[str, Any]) -> AgentResult:
        """Report journal disk usage."""
        try:
            result = subprocess.run(
                ["journalctl", "--disk-usage"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            msg = result.stdout.strip() if result.returncode == 0 else "Unknown"
            return AgentResult(
                success=True,
                message=f"Journal usage: {msg}",
                data={"journal_info": msg, "alert": False},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return AgentResult(success=False, message=f"Journal check failed: {exc}")

    @staticmethod
    def _op_clean_temp_files(settings: Dict[str, Any]) -> AgentResult:
        """Report temp directory sizes."""
        sizes = {}
        for path in ["/tmp", os.path.expanduser("~/.cache")]:
            try:
                result = subprocess.run(
                    ["du", "-sh", path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    sizes[path] = result.stdout.strip().split("\t")[0]
            except (OSError, subprocess.SubprocessError):
                sizes[path] = "unknown"

        msg = ", ".join(f"{p}: {s}" for p, s in sizes.items())
        return AgentResult(
            success=True,
            message=f"Temp sizes: {msg}",
            data={"sizes": sizes, "alert": False},
        )

    # ==================== Performance Operations ====================

    @staticmethod
    def _op_detect_workload(settings: Dict[str, Any]) -> AgentResult:
        """Detect current workload type."""
        try:
            with open("/proc/loadavg", "r") as fh:
                parts = fh.read().strip().split()
            load_1 = float(parts[0])
            cores = os.cpu_count() or 1
            cpu_pct = (load_1 / cores) * 100

            with open("/proc/meminfo", "r") as fh:
                lines = fh.readlines()
            mem_info = {}
            for line in lines:
                parts_m = line.split(":")
                if len(parts_m) == 2:
                    mem_info[parts_m[0].strip()] = int(parts_m[1].strip().split()[0])

            total = mem_info.get("MemTotal", 1)
            available = mem_info.get("MemAvailable", total)
            mem_pct = ((total - available) / total) * 100

            if cpu_pct < 10 and mem_pct < 30:
                workload = "idle"
            elif cpu_pct < 30:
                workload = "light"
            elif cpu_pct < 70:
                workload = "moderate"
            elif cpu_pct < 90:
                workload = "heavy"
            else:
                workload = "extreme"

            return AgentResult(
                success=True,
                message=f"Workload: {workload} (CPU: {cpu_pct:.1f}%, RAM: {mem_pct:.1f}%)",
                data={
                    "workload": workload,
                    "cpu_percent": cpu_pct,
                    "memory_percent": mem_pct,
                    "alert": False,
                },
            )
        except OSError as exc:
            return AgentResult(
                success=False, message=f"Workload detection failed: {exc}"
            )

    @staticmethod
    def _op_apply_tuning(settings: Dict[str, Any]) -> AgentResult:
        """Report tuning recommendation (actual apply requires pkexec)."""
        auto_apply = settings.get("auto_apply", False)
        if not auto_apply:
            return AgentResult(
                success=True,
                message="Auto-apply disabled. Use Performance tab to apply tuning.",
                data={"alert": False},
            )
        return AgentResult(
            success=True,
            message="Tuning would require privilege escalation — use Performance tab",
            data={"alert": False},
        )


class AgentScheduler:
    """
    Manages background scheduling and execution of enabled agents.
    Runs agents on their configured interval triggers in a background thread.
    """

    def __init__(self):
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_result: Optional[Callable[[str, AgentResult], None]] = None

    def set_result_callback(self, callback: Callable[[str, AgentResult], None]):
        """Set a callback for when an agent produces a result."""
        self._on_result = callback

    def start(self):
        """Start the agent scheduler in a background thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="AgentScheduler"
        )
        self._thread.start()
        logger.info("Agent scheduler started")

    def stop(self):
        """Stop the agent scheduler."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Agent scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def _run_loop(self):
        """Main scheduler loop."""
        registry = AgentRegistry.instance()

        while not self._stop_event.is_set():
            now = time.time()
            enabled_agents = registry.get_enabled_agents()

            for agent in enabled_agents:
                state = registry.get_state(agent.agent_id)

                # Skip agents that aren't idle
                if state.status not in (AgentStatus.IDLE, AgentStatus.RUNNING):
                    continue

                # Check interval triggers
                for trigger in agent.triggers:
                    if trigger.trigger_type == TriggerType.INTERVAL:
                        interval = trigger.config.get("seconds", 300)
                        if now - state.last_run >= interval:
                            self._execute_agent(agent, state, registry)
                            break

            # Save state periodically
            registry.save()

            # Sleep between checks
            self._stop_event.wait(timeout=SCHEDULER_POLL_SECONDS)

    def _execute_agent(
        self,
        agent: AgentConfig,
        state: AgentState,
        registry: AgentRegistry,
    ):
        """Execute all actions for an agent."""
        state.status = AgentStatus.RUNNING

        for action in agent.actions:
            if self._stop_event.is_set():
                break

            result = AgentExecutor.execute_action(agent, action, state)
            state.record_action(result)

            if self._on_result:
                try:
                    self._on_result(agent.agent_id, result)
                except Exception as exc:
                    logger.error("Result callback error: %s", exc)

            # Send notifications
            self._notify_result(agent, result)

            # Log alerts
            if result.data and result.data.get("alert"):
                logger.warning("Agent %s alert: %s", agent.name, result.message)

        state.status = AgentStatus.IDLE

    def run_agent_now(self, agent_id: str) -> List[AgentResult]:
        """Manually trigger an agent immediately. Returns results."""
        registry = AgentRegistry.instance()
        agent = registry.get_agent(agent_id)
        if not agent:
            return [AgentResult(success=False, message=f"Agent '{agent_id}' not found")]

        state = registry.get_state(agent_id)
        results = []

        state.status = AgentStatus.RUNNING
        for action in agent.actions:
            result = AgentExecutor.execute_action(agent, action, state)
            state.record_action(result)
            results.append(result)

            if self._on_result:
                try:
                    self._on_result(agent_id, result)
                except Exception as exc:
                    logger.error("Result callback error in run_agent_now: %s", exc)

            # Send notifications
            self._notify_result(agent, result)

        state.status = AgentStatus.IDLE
        registry.save()
        return results

    def _notify_result(self, agent: AgentConfig, result: AgentResult):
        """Send notifications for an agent result if configured."""
        try:
            from utils.agent_notifications import AgentNotifier, AgentNotificationConfig

            if not hasattr(self, "_notifier"):
                self._notifier = AgentNotifier()
            notif_config = AgentNotificationConfig.from_dict(agent.notification_config)
            self._notifier.notify(agent.agent_id, agent.name, result, notif_config)
        except Exception as exc:
            logger.debug("Notification skipped: %s", exc)
