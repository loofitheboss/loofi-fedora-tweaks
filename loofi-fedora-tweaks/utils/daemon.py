"""
Daemon - Background service for scheduled task execution.

SECURITY CONTRACT
-----------------
This daemon runs as a systemd user service and performs ONLY these operations:

1. Scheduled Task Execution (via TaskScheduler.execute_task):
   - CLEANUP: dnf/rpm-ostree cache cleaning and autoremove
   - UPDATE_CHECK: Check for system updates (read-only, no installation)
   - SYNC_CONFIG: Sync configuration to GitHub Gist (requires auth token)
   - APPLY_PRESET: Apply saved system presets

   All task actions are validated against ALLOWED_ACTIONS in scheduler.py.
   Unknown/disallowed actions are rejected and audit logged.

2. Power State Monitoring:
   - Reads /sys/class/power_supply/* (read-only)
   - Uses upower command (read-only query)
   - Triggers tasks on battery/AC transitions

3. Plugin Update Checking:
   - Checks plugin repositories for updates (if auto-update enabled)
   - Downloads and installs plugin updates
   - Respects plugin_auto_update config flag (default: False)

SAFETY GUARANTEES
-----------------
- No arbitrary command execution: All actions validated via ALLOWED_ACTIONS
- No direct subprocess calls with user-controlled input
- All privileged operations go through PrivilegedCommand
- Audit logging for all task executions (successful and failed)
- Graceful shutdown on SIGTERM/SIGINT

DATA ACCESS
-----------
- Reads: ~/.config/loofi-fedora-tweaks/scheduler.json
- Writes: Task last_run timestamps
- Audit: All executions logged via AuditLogger

See utils/scheduler.py for task action definitions.
"""

import signal
import subprocess
import time
from pathlib import Path

from utils.config_manager import ConfigManager
from utils.log import get_logger
from utils.plugin_base import PluginLoader
from utils.plugin_installer import PluginInstaller

logger = get_logger(__name__)


class Daemon:
    """Background daemon for automated task execution."""

    CHECK_INTERVAL = 300  # Check every 5 minutes
    POWER_CHECK_INTERVAL = 30  # Check power state every 30 seconds
    PLUGIN_UPDATE_INTERVAL = 86400  # Check for plugin updates every 24 hours

    _running = True
    _last_power_state = None
    _last_plugin_check = 0

    @classmethod
    def signal_handler(cls, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received signal %s, shutting down...", signum)
        cls._running = False

    @classmethod
    def get_power_state(cls) -> str:
        """
        Get current power state.

        Returns:
            'battery' or 'ac'
        """
        try:
            # Check using upower
            result = subprocess.run(
                ["upower", "-i", "/org/freedesktop/UPower/devices/line_power_AC0"],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

            if "online: yes" in result.stdout.lower():
                return "ac"

            # Fallback: check /sys
            ac_path = Path("/sys/class/power_supply/AC0/online")
            if ac_path.exists():
                with open(ac_path, "r") as f:
                    return "ac" if f.read().strip() == "1" else "battery"

            # Another fallback for different hardware
            for ac in Path("/sys/class/power_supply").glob("AC*"):
                online_file = ac / "online"
                if online_file.exists():
                    with open(online_file, "r") as f:
                        return "ac" if f.read().strip() == "1" else "battery"

            return "ac"  # Default to AC if unknown
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to detect power state: %s", e)
            return "ac"

    @classmethod
    def check_power_triggers(cls):
        """Check for power state changes and trigger tasks."""
        from utils.scheduler import TaskScheduler

        current_state = cls.get_power_state()

        if cls._last_power_state is None:
            cls._last_power_state = current_state
            return

        if current_state != cls._last_power_state:
            logger.info(
                "Power state changed: %s -> %s", cls._last_power_state, current_state
            )

            on_battery = current_state == "battery"
            tasks = TaskScheduler.get_power_trigger_tasks(on_battery)

            for task in tasks:
                logger.info("Running power-triggered task: %s", task.name)
                TaskScheduler.execute_task(task)

            cls._last_power_state = current_state

    @classmethod
    def run_boot_tasks(cls):
        """Run all on_boot tasks."""
        from utils.scheduler import TaskScheduler

        logger.info("Running boot tasks...")

        for task in TaskScheduler.get_boot_tasks():
            logger.info("Running boot task: %s", task.name)
            TaskScheduler.execute_task(task)

    @classmethod
    def run_due_tasks(cls):
        """Check and run any due scheduled tasks."""
        from utils.scheduler import TaskScheduler

        due_tasks = TaskScheduler.get_due_tasks()

        if due_tasks:
            logger.info("Found %d due tasks", len(due_tasks))

            for task in due_tasks:
                logger.info("Running scheduled task: %s", task.name)
                success, message = TaskScheduler.execute_task(task)
                logger.info(
                    "Task '%s': %s - %s",
                    task.name,
                    "Success" if success else "Failed",
                    message,
                )

    @classmethod
    def check_plugin_updates(cls):
        """Check for plugin updates and auto-update if enabled."""
        # Check if auto-update is enabled in config
        config = ConfigManager.load_config()
        if not config.get("plugin_auto_update", False):
            return

        logger.info("Checking for plugin updates...")

        try:
            loader = PluginLoader()
            installer = PluginInstaller()
            plugins = loader.list_plugins()

            for plugin in plugins:
                if not plugin.get("enabled", True):
                    continue  # Skip disabled plugins

                plugin_name = plugin["name"]
                logger.debug("Checking updates for plugin: %s", plugin_name)

                result = installer.check_update(plugin_name)

                if (
                    result.success
                    and result.data
                    and result.data.get("update_available")
                ):
                    new_version = result.data.get("new_version")
                    logger.info("Update available for %s: %s", plugin_name, new_version)

                    # Auto-update the plugin
                    update_result = installer.update(plugin_name)

                    if update_result.success:
                        logger.info(
                            "Successfully updated %s to %s", plugin_name, new_version
                        )
                    else:
                        logger.warning(
                            "Failed to update %s: %s", plugin_name, update_result.error
                        )

        except (ImportError, AttributeError, OSError) as e:
            logger.error("Error checking plugin updates: %s", e, exc_info=True)

    @classmethod
    def run(cls):
        """Main daemon loop."""
        logger.info("Loofi Fedora Tweaks daemon starting...")

        # Set up signal handlers
        signal.signal(signal.SIGTERM, cls.signal_handler)
        signal.signal(signal.SIGINT, cls.signal_handler)

        # Run boot tasks on startup
        cls.run_boot_tasks()

        last_task_check = 0
        last_power_check = 0
        last_plugin_update_check = 0

        while cls._running:
            try:
                now = time.time()

                # Check for due tasks
                if now - last_task_check >= cls.CHECK_INTERVAL:
                    cls.run_due_tasks()
                    last_task_check = now

                # Check power state
                if now - last_power_check >= cls.POWER_CHECK_INTERVAL:
                    cls.check_power_triggers()
                    last_power_check = now

                # Check for plugin updates (daily)
                if now - last_plugin_update_check >= cls.PLUGIN_UPDATE_INTERVAL:
                    cls.check_plugin_updates()
                    last_plugin_update_check = now

                # Sleep briefly
                time.sleep(10)

            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as e:
                logger.error("Error in main loop: %s", e, exc_info=True)
                time.sleep(60)  # Back off on error

        logger.info("Daemon stopped.")


def main():
    """Entry point for daemon mode."""
    Daemon.run()


if __name__ == "__main__":
    main()
