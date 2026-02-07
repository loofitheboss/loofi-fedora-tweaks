"""
Daemon - Background service for scheduled task execution.
Runs as a systemd user service.
"""

import time
import signal
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class Daemon:
    """Background daemon for automated task execution."""
    
    CHECK_INTERVAL = 300  # Check every 5 minutes
    POWER_CHECK_INTERVAL = 30  # Check power state every 30 seconds
    
    _running = True
    _last_power_state = None
    
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
