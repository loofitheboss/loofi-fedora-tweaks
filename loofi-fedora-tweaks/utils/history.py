import json
import logging
import os
import shutil
import subprocess
from datetime import datetime

from utils.containers import Result

logger = logging.getLogger(__name__)


class HistoryManager:
    HISTORY_FILE = os.path.expanduser("~/.config/loofi-fedora-tweaks/history.json")
    
    def __init__(self):
        os.makedirs(os.path.dirname(self.HISTORY_FILE), exist_ok=True)
    
    def log_change(self, description, undo_command):
        """
        Logs a change with a command to undo it.
        undo_command: A list of arguments for subprocess.run (e.g., ["gsettings", "set", ...])
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "undo_command": undo_command
        }
        
        history = self._load_history()
        history.append(entry)
        
        # Keep history manageable (last 50 items)
        if len(history) > 50:
            history = history[-50:]
            
        self._save_history(history)
        
    def get_last_action(self):
        """Returns the description of the last action, or None."""
        history = self._load_history()
        if not history:
            return None
        return history[-1]
        
    def undo_last_action(self):
        """
        Executes the undo command for the last action and removes it from history.
        Returns Result.
        """
        history = self._load_history()
        if not history:
            return Result(False, "No actions to undo.")

        last_action = history.pop()
        cmd = last_action["undo_command"]

        try:
            # Determine if we need pkexec (simple heuristic or explicitness in command)
            # ideally, the command stored should be complete.
            subprocess.run(cmd, check=True)
            self._save_history(history)
            return Result(True, f"Undid: {last_action['description']}")
        except subprocess.CalledProcessError as e:
            # Don't pop if failed? Or pop and log error?
            # Standard undo: if it fails, we might still want to keep it?
            # For now, let's keep it in history so user can retry manual fix
            return Result(False, f"Undo failed: {e}")
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to undo action: %s", e)
            return Result(False, f"Error: {e}")

    def _load_history(self):
        if not os.path.exists(self.HISTORY_FILE):
            return []
        try:
            with open(self.HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_history(self, history):
        with open(self.HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
