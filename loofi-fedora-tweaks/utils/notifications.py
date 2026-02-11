"""
Notification Manager - Desktop notifications for background tasks.
Uses notify-send for maximum compatibility.
"""

import logging
import subprocess
import shutil

logger = logging.getLogger(__name__)


class NotificationManager:
    """Handles desktop notifications for task completion and alerts."""

    APP_NAME = "Loofi Fedora Tweaks"
    APP_ICON = "preferences-system"  # Standard system icon

    @classmethod
    def is_available(cls) -> bool:
        """Check if notifications can be sent."""
        return shutil.which("notify-send") is not None

    @classmethod
    def send(
        cls,
        title: str,
        body: str,
        icon: str = "dialog-information",
        urgency: str = "normal",
        timeout: int = 5000
    ) -> bool:
        """
        Send a desktop notification.

        Args:
            title: Notification title.
            body: Notification body text.
            icon: Icon name (freedesktop icon name or path).
            urgency: low, normal, or critical.
            timeout: Display time in milliseconds (0 = no timeout).

        Returns:
            True if notification was sent successfully.
        """
        if not cls.is_available():
            return False

        try:
            cmd = [
                "notify-send",
                "--app-name", cls.APP_NAME,
                "--icon", icon,
                "--urgency", urgency,
                "--expire-time", str(timeout),
                title,
                body
            ]

            subprocess.run(cmd, check=False, capture_output=True)
            return True
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to send notification: %s", e)
            return False

    @classmethod
    def notify_task_complete(cls, task_name: str, success: bool = True):
        """Shortcut for task completion notifications."""
        if success:
            cls.send(
                f"✅ {task_name} Complete",
                f"The scheduled task '{task_name}' has completed successfully.",
                icon="emblem-ok-symbolic"
            )
        else:
            cls.send(
                f"❌ {task_name} Failed",
                f"The scheduled task '{task_name}' encountered an error.",
                icon="dialog-error",
                urgency="critical"
            )

    @classmethod
    def notify_updates_available(cls, count: int):
        """Notify user of available system updates."""
        cls.send(
            f"📦 {count} Updates Available",
            "System updates are ready to install.",
            icon="software-update-available"
        )

    @classmethod
    def notify_cleanup_complete(cls, freed_mb: float):
        """Notify user of cleanup completion."""
        cls.send(
            "🧹 Cleanup Complete",
            f"Freed {freed_mb:.1f} MB of disk space.",
            icon="user-trash-symbolic"
        )

    @classmethod
    def notify_sync_complete(cls):
        """Notify user of config sync completion."""
        cls.send(
            "☁️ Config Synced",
            "Your configuration has been synced to GitHub Gist.",
            icon="emblem-synchronizing-symbolic"
        )

    @classmethod
    def notify_preset_applied(cls, preset_name: str):
        """Notify user of preset application."""
        cls.send(
            "💾 Preset Applied",
            f"'{preset_name}' preset has been applied.",
            icon="emblem-default-symbolic"
        )
