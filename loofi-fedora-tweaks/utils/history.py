"""Action history tracking with JSON persistence and undo capability."""
import json
import logging
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List

from utils.containers import Result

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """A single action history entry with undo capability."""
    id: str
    timestamp: str
    description: str
    undo_command: list

    @staticmethod
    def from_dict(data: dict) -> "HistoryEntry":
        """Create a HistoryEntry from a dict (loaded from JSON)."""
        return HistoryEntry(
            id=data.get("id", str(uuid.uuid4())[:8]),
            timestamp=data.get("timestamp", ""),
            description=data.get("description", ""),
            undo_command=data.get("undo_command", []),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "description": self.description,
            "undo_command": self.undo_command,
        }


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
            "id": str(uuid.uuid4())[:8],
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

    def get_recent(self, count: int = 3) -> List[HistoryEntry]:
        """Return the most recent history entries.

        Args:
            count: Number of recent entries to return.

        Returns:
            List of HistoryEntry objects, most recent first.
        """
        history = self._load_history()
        recent = history[-count:] if len(history) >= count else history
        entries = [HistoryEntry.from_dict(h) for h in reversed(recent)]
        return entries

    def can_undo(self) -> bool:
        """Check if there are any actions that can be undone.

        Returns:
            True if history contains at least one entry with an undo command.
        """
        history = self._load_history()
        return any(h.get("undo_command") for h in history)

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
            subprocess.run(cmd, check=True, timeout=60)
            self._save_history(history)
            return Result(True, f"Undid: {last_action['description']}")
        except subprocess.CalledProcessError as e:
            return Result(False, f"Undo failed: {e}")
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to undo action: %s", e)
            return Result(False, f"Error: {e}")

    def undo_action(self, action_id: str):
        """Undo a specific action by its ID.

        Args:
            action_id: The unique ID of the action to undo.

        Returns:
            Result indicating success or failure.
        """
        history = self._load_history()
        target_idx = None
        for idx, entry in enumerate(history):
            if entry.get("id") == action_id:
                target_idx = idx
                break

        if target_idx is None:
            return Result(False, f"Action not found: {action_id}")

        target = history[target_idx]
        cmd = target.get("undo_command", [])
        if not cmd:
            return Result(False, "No undo command available for this action.")

        try:
            subprocess.run(cmd, check=True, timeout=60)
            history.pop(target_idx)
            self._save_history(history)
            return Result(True, f"Undid: {target['description']}")
        except subprocess.CalledProcessError as e:
            return Result(False, f"Undo failed: {e}")
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to undo action '%s': %s", action_id, e)
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
