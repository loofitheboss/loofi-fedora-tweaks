"""
Notification Center - In-app notification system.
Part of v13.5 UX Polish.
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
NOTIFICATIONS_FILE = CONFIG_DIR / "notifications.json"
MAX_NOTIFICATIONS = 100


@dataclass
class Notification:
    """A single notification entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    message: str = ""
    category: str = "general"  # general, health, profile, security, system
    timestamp: float = field(default_factory=time.time)
    read: bool = False


class NotificationCenter:
    """Singleton notification center with JSON persistence."""

    _instance: Optional['NotificationCenter'] = None
    _notifications: List[Notification] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._notifications = []
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load notifications from disk."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if NOTIFICATIONS_FILE.exists():
                with open(NOTIFICATIONS_FILE, "r") as f:
                    data = json.load(f)
                self._notifications = [Notification(**n) for n in data]
        except (OSError, json.JSONDecodeError, TypeError) as e:
            logger.debug("Failed to load notifications: %s", e)
            self._notifications = []

    def _save(self):
        """Save notifications to disk."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = [asdict(n) for n in self._notifications]
            with open(NOTIFICATIONS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.debug("Failed to save notifications: %s", e)

    def add(self, title: str, message: str, category: str = "general") -> Notification:
        """Add a new notification."""
        notif = Notification(title=title, message=message, category=category)
        self._notifications.insert(0, notif)
        # FIFO eviction
        if len(self._notifications) > MAX_NOTIFICATIONS:
            self._notifications = self._notifications[:MAX_NOTIFICATIONS]
        self._save()
        return notif

    def get_unread_count(self) -> int:
        """Get number of unread notifications."""
        return sum(1 for n in self._notifications if not n.read)

    def mark_all_read(self):
        """Mark all notifications as read."""
        for n in self._notifications:
            n.read = True
        self._save()

    def mark_read(self, notification_id: str):
        """Mark a specific notification as read."""
        for n in self._notifications:
            if n.id == notification_id:
                n.read = True
                break
        self._save()

    def dismiss(self, notification_id: str):
        """Remove a notification."""
        self._notifications = [n for n in self._notifications if n.id != notification_id]
        self._save()

    def get_recent(self, limit: int = 20) -> List[Notification]:
        """Get recent notifications."""
        return self._notifications[:limit]

    def clear_all(self):
        """Clear all notifications."""
        self._notifications = []
        self._save()

    @classmethod
    def reset_singleton(cls):
        """Reset singleton for testing."""
        cls._instance = None
        cls._notifications = None
