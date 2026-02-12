"""
Daemon - Background service for scheduled task execution.
Runs as a systemd user service.
"""

import time
import signal
import subprocess
from pathlib import Path

from utils.config_manager import ConfigManager
from utils.plugin_base import PluginLoader
from utils.plugin_installer import PluginInstaller


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
        print(f"[Daemon] Received signal {signum}, shutting down...")
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
                capture_output=True, text=True, check=False
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
        except Exception:
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
            print(f"[Daemon] Power state changed: {cls._last_power_state} -> {current_state}")

            on_battery = current_state == "battery"
            tasks = TaskScheduler.get_power_trigger_tasks(on_battery)

            for task in tasks:
                print(f"[Daemon] Running power-triggered task: {task.name}")
                TaskScheduler.execute_task(task)

            cls._last_power_state = current_state

    @classmethod
    def run_boot_tasks(cls):
        """Run all on_boot tasks."""
        from utils.scheduler import TaskScheduler

        print("[Daemon] Running boot tasks...")

        for task in TaskScheduler.get_boot_tasks():
            print(f"[Daemon] Running boot task: {task.name}")
            TaskScheduler.execute_task(task)

    @classmethod
    def run_due_tasks(cls):
        """Check and run any due scheduled tasks."""
        from utils.scheduler import TaskScheduler

        due_tasks = TaskScheduler.get_due_tasks()

        if due_tasks:
            print(f"[Daemon] Found {len(due_tasks)} due tasks")

            for task in due_tasks:
                print(f"[Daemon] Running scheduled task: {task.name}")
                success, message = TaskScheduler.execute_task(task)
                print(f"[Daemon] Task '{task.name}': {'Success' if success else 'Failed'} - {message}")

    @classmethod
    def check_plugin_updates(cls):
        """Check for plugin updates and auto-update if enabled."""
        # Check if auto-update is enabled in config
        config = ConfigManager.load_config()
        if not config.get("plugin_auto_update", True):
            return

        print("[Daemon] Checking for plugin updates...")

        try:
            loader = PluginLoader()
            installer = PluginInstaller()
            plugins = loader.list_plugins()

            for plugin in plugins:
                if not plugin.get("enabled", True):
                    continue  # Skip disabled plugins

                plugin_name = plugin["name"]
                print(f"[Daemon] Checking updates for plugin: {plugin_name}")

                result = installer.check_update(plugin_name)

                if result.success and result.data and result.data.get("update_available"):
                    new_version = result.data.get("new_version")
                    print(f"[Daemon] Update available for {plugin_name}: {new_version}")

                    # Auto-update the plugin
                    update_result = installer.update(plugin_name)

                    if update_result.success:
                        print(f"[Daemon] Successfully updated {plugin_name} to {new_version}")
                    else:
                        print(f"[Daemon] Failed to update {plugin_name}: {update_result.error}")

        except Exception as e:
            print(f"[Daemon] Error checking plugin updates: {e}")

    @classmethod
    def run(cls):
        """Main daemon loop."""
        print("[Daemon] Loofi Fedora Tweaks daemon starting...")

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

            except Exception as e:
                print(f"[Daemon] Error in main loop: {e}")
                time.sleep(60)  # Back off on error

        print("[Daemon] Daemon stopped.")


def main():
    """Entry point for daemon mode."""
    Daemon.run()


if __name__ == "__main__":
    main()
