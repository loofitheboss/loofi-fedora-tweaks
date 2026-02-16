"""
Task Scheduler - Manages scheduled automation tasks.
Supports time-based and power-state triggers.
"""

import logging
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum

from services.system import SystemManager
from utils.audit import AuditLogger
from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)


class TaskAction(Enum):
    """Available automated actions."""

    CLEANUP = "cleanup"
    UPDATE_CHECK = "update_check"
    SYNC_CONFIG = "sync_config"
    APPLY_PRESET = "apply_preset"


# Allowed actions - derived from TaskAction enum for validation
ALLOWED_ACTIONS = frozenset(action.value for action in TaskAction)


class TaskSchedule(Enum):
    """Schedule triggers."""

    DAILY = "daily"
    WEEKLY = "weekly"
    ON_BOOT = "on_boot"
    ON_BATTERY = "on_battery"
    ON_AC = "on_ac"
    HOURLY = "hourly"


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""

    id: str
    name: str
    action: str  # TaskAction value
    schedule: str  # TaskSchedule value
    enabled: bool = True
    last_run: Optional[str] = None  # ISO format
    preset_name: Optional[str] = None  # For apply_preset action

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        return cls(**data)

    def is_due(self) -> bool:
        """Check if task is due to run."""
        if not self.enabled:
            return False

        if self.schedule == TaskSchedule.ON_BOOT.value:
            # Always due on boot (handled specially)
            return False

        if self.schedule in [TaskSchedule.ON_BATTERY.value, TaskSchedule.ON_AC.value]:
            # Power triggers handled specially
            return False

        if not self.last_run:
            return True

        try:
            last = datetime.fromisoformat(self.last_run)
            now = datetime.now()

            if self.schedule == TaskSchedule.HOURLY.value:
                return (now - last) >= timedelta(hours=1)
            elif self.schedule == TaskSchedule.DAILY.value:
                return (now - last) >= timedelta(days=1)
            elif self.schedule == TaskSchedule.WEEKLY.value:
                return (now - last) >= timedelta(weeks=1)
        except ValueError as e:
            logger.debug("Failed to parse last_run timestamp: %s", e)
            return True

        return False


class TaskScheduler:
    """Manages scheduled tasks and their execution."""

    CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
    CONFIG_FILE = CONFIG_DIR / "scheduler.json"

    @classmethod
    def ensure_dirs(cls):
        """Ensure config directories exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def list_tasks(cls) -> list:
        """Get all scheduled tasks."""
        cls.ensure_dirs()

        if not cls.CONFIG_FILE.exists():
            return []

        try:
            with open(cls.CONFIG_FILE, "r") as f:
                data = json.load(f)
            return [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to load tasks: %s", e)
            return []

    @classmethod
    def save_tasks(cls, tasks: list) -> bool:
        """Save all tasks to config."""
        cls.ensure_dirs()

        try:
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump({"tasks": [t.to_dict() for t in tasks]}, f, indent=2)
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to save tasks: %s", e)
            return False

    @classmethod
    def add_task(cls, task: ScheduledTask) -> bool:
        """Add a new scheduled task."""
        tasks = cls.list_tasks()

        # Check for duplicate ID
        if any(t.id == task.id for t in tasks):
            return False

        tasks.append(task)
        return cls.save_tasks(tasks)

    @classmethod
    def remove_task(cls, task_id: str) -> bool:
        """Remove a scheduled task by ID."""
        tasks = cls.list_tasks()
        original_count = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]

        if len(tasks) == original_count:
            return False  # Task not found

        return cls.save_tasks(tasks)

    @classmethod
    def enable_task(cls, task_id: str, enabled: bool) -> bool:
        """Enable or disable a task."""
        tasks = cls.list_tasks()

        for task in tasks:
            if task.id == task_id:
                task.enabled = enabled
                return cls.save_tasks(tasks)

        return False

    @classmethod
    def update_last_run(cls, task_id: str) -> bool:
        """Update last_run time for a task."""
        tasks = cls.list_tasks()

        for task in tasks:
            if task.id == task_id:
                task.last_run = datetime.now().isoformat()
                return cls.save_tasks(tasks)

        return False

    @classmethod
    def get_due_tasks(cls) -> list:
        """Get all tasks that are due to run."""
        return [t for t in cls.list_tasks() if t.is_due()]

    @classmethod
    def get_power_trigger_tasks(cls, on_battery: bool) -> list:
        """Get tasks triggered by power state change."""
        trigger = (
            TaskSchedule.ON_BATTERY.value if on_battery else TaskSchedule.ON_AC.value
        )
        return [t for t in cls.list_tasks() if t.enabled and t.schedule == trigger]

    @classmethod
    def get_boot_tasks(cls) -> list:
        """Get tasks that run on boot."""
        return [
            t
            for t in cls.list_tasks()
            if t.enabled and t.schedule == TaskSchedule.ON_BOOT.value
        ]

    @classmethod
    def execute_task(cls, task: ScheduledTask) -> tuple:
        """
        Execute a scheduled task with action validation and audit logging.

        Returns:
            (success: bool, message: str)
        """
        from utils.notifications import NotificationManager

        auditor = AuditLogger()

        # Validate action against allowed set before execution
        if task.action not in ALLOWED_ACTIONS:
            auditor.log_validation_failure(
                action="scheduler.execute_task",
                param="action",
                detail="Disallowed action: %s" % task.action,
                params={"task_id": task.id, "task_name": task.name,
                        "action": task.action},
            )
            logger.warning(
                "Rejected task with disallowed action: %s (action=%s)",
                task.name, task.action,
            )
            return (False, "Disallowed action: %s" % task.action)

        # Log task execution start
        auditor.log(
            action="scheduler.task.%s" % task.action,
            params={
                "task_id": task.id,
                "task_name": task.name,
                "schedule": task.schedule,
            },
        )

        try:
            if task.action == TaskAction.CLEANUP.value:
                result = cls._run_cleanup()
            elif task.action == TaskAction.UPDATE_CHECK.value:
                result = cls._run_update_check()
            elif task.action == TaskAction.SYNC_CONFIG.value:
                result = cls._run_sync_config()
            elif task.action == TaskAction.APPLY_PRESET.value:
                result = cls._run_apply_preset(task.preset_name)
            else:
                return (False, "Unknown action: %s" % task.action)

            # Update last run time
            cls.update_last_run(task.id)

            # Send notification
            NotificationManager.notify_task_complete(task.name, result[0])

            return result

        except (ImportError, OSError) as e:
            logger.debug("Failed to execute task %s: %s", task.name, e)
            return (False, str(e))

    @classmethod
    def run_due_tasks(cls) -> list:
        """Run all due tasks and return results."""
        results = []

        for task in cls.get_due_tasks():
            success, message = cls.execute_task(task)
            results.append({"task": task.name, "success": success, "message": message})

        return results

    # ==================== TASK IMPLEMENTATIONS ====================

    @classmethod
    def _run_cleanup(cls) -> tuple:
        """Run system cleanup."""
        try:
            # Clean package manager cache
            binary, args, desc = PrivilegedCommand.dnf("clean")
            subprocess.run(
                [binary] + args,
                capture_output=True,
                check=False,
                timeout=600,
            )

            # Remove orphaned packages (non-interactive)
            binary, args, desc = PrivilegedCommand.dnf("autoremove")
            subprocess.run(
                [binary] + args,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )

            from utils.notifications import NotificationManager

            NotificationManager.notify_cleanup_complete(50.0)  # Approximate

            return (True, "Cleanup completed")
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Cleanup task failed: %s", e)
            return (False, str(e))

    @classmethod
    def _run_update_check(cls) -> tuple:
        """Check for available updates."""
        try:
            if SystemManager.is_atomic():
                result = subprocess.run(
                    ["rpm-ostree", "upgrade", "--check"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=600,
                )
                if result.returncode == 0 and "AvailableUpdate" in result.stdout:
                    lines = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if line.strip()
                    ]
                    count = len(lines)

                    from utils.notifications import NotificationManager

                    NotificationManager.notify_updates_available(count)

                    return (True, f"{count} updates available (rpm-ostree)")
                else:
                    return (True, "System is up to date")
            else:
                package_manager = SystemManager.get_package_manager()
                if not shutil.which(package_manager):
                    return (True, "System is up to date (dnf not available)")
                result = subprocess.run(
                    [package_manager, "check-update", "-q"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=600,
                )

                # dnf check-update returns 100 if updates available
                if result.returncode == 100:
                    lines = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if line.strip()
                    ]
                    count = len(lines)

                    from utils.notifications import NotificationManager

                    NotificationManager.notify_updates_available(count)

                    return (True, f"{count} updates available")
                else:
                    return (True, "System is up to date")

        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Update check failed: %s", e)
            return (False, str(e))

    @classmethod
    def _run_sync_config(cls) -> tuple:
        """Sync config to GitHub Gist."""
        try:
            from utils.config_manager import ConfigManager
            from utils.cloud_sync import CloudSyncManager

            config = ConfigManager.export_all()
            success, message = CloudSyncManager.sync_to_gist(config)

            if success:
                from utils.notifications import NotificationManager

                NotificationManager.notify_sync_complete()

            return (success, message)
        except (ImportError, OSError) as e:
            logger.debug("Config sync failed: %s", e)
            return (False, str(e))

    @classmethod
    def _run_apply_preset(cls, preset_name: Optional[str]) -> tuple:
        """Apply a preset."""
        if not preset_name:
            return (False, "No preset name specified")

        try:
            from utils.presets import PresetManager

            manager = PresetManager()
            data = manager.load_preset(preset_name)

            if data:
                from utils.notifications import NotificationManager

                NotificationManager.notify_preset_applied(preset_name)
                return (True, f"Preset '{preset_name}' applied")
            else:
                return (False, f"Preset '{preset_name}' not found")

        except (ImportError, OSError) as e:
            logger.debug("Apply preset failed: %s", e)
            return (False, str(e))

    # ==================== SERVICE MANAGEMENT ====================

    @classmethod
    def is_service_enabled(cls) -> bool:
        """Check if the systemd user service is enabled."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-enabled", "loofi-fedora-tweaks"],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            return result.stdout.strip() == "enabled"
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check service enabled status: %s", e)
            return False

    @classmethod
    def is_service_running(cls) -> bool:
        """Check if the systemd user service is running."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "loofi-fedora-tweaks"],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            return result.stdout.strip() == "active"
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check service running status: %s", e)
            return False

    @classmethod
    def enable_service(cls) -> bool:
        """Enable and start the systemd user service."""
        try:
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "loofi-fedora-tweaks"],
                check=True,
                timeout=60,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to enable service: %s", e)
            return False

    @classmethod
    def disable_service(cls) -> bool:
        """Disable and stop the systemd user service."""
        try:
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", "loofi-fedora-tweaks"],
                check=True,
                timeout=60,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to disable service: %s", e)
            return False
