"""
Quick Commands Registry — v47.0 UX Improvement.

Provides a registry of quick commands that can be executed directly
from the command palette. Extends the palette from navigation-only
to action-capable with built-in commands for common operations.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from utils.log import get_logger

logger = get_logger(__name__)


@dataclass
class QuickCommand:
    """A command that can be executed from the command palette."""
    id: str
    name: str
    description: str
    category: str
    keywords: List[str]
    action: Optional[Callable] = None


class QuickCommandRegistry:
    """Singleton registry for quick commands available in the command palette."""

    _instance: Optional["QuickCommandRegistry"] = None
    _commands: Dict[str, QuickCommand] = {}

    @classmethod
    def instance(cls) -> "QuickCommandRegistry":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for use in tests only."""
        cls._instance = None
        cls._commands = {}

    def register(self, command: QuickCommand) -> None:
        """Register a quick command.

        Args:
            command: The QuickCommand to register.

        Raises:
            ValueError: If a command with the same ID is already registered.
        """
        if command.id in self._commands:
            raise ValueError(f"Command already registered: {command.id!r}")
        self._commands[command.id] = command
        logger.debug("Registered quick command: %s", command.id)

    def unregister(self, command_id: str) -> None:
        """Remove a command by ID. Silent no-op if not found."""
        self._commands.pop(command_id, None)

    def get(self, command_id: str) -> Optional[QuickCommand]:
        """Get a command by ID."""
        return self._commands.get(command_id)

    def list_all(self) -> List[QuickCommand]:
        """Return all registered commands sorted by name."""
        return sorted(self._commands.values(), key=lambda c: c.name)

    def list_by_category(self, category: str) -> List[QuickCommand]:
        """Return commands filtered by category."""
        return [c for c in self.list_all() if c.category == category]

    def search(self, query: str) -> List[QuickCommand]:
        """Search commands by name and keywords.

        Args:
            query: Search string to match against command names and keywords.

        Returns:
            List of matching QuickCommand objects sorted by relevance.
        """
        if not query:
            return self.list_all()

        query_lower = query.lower()
        scored: List[tuple] = []

        for cmd in self._commands.values():
            score = 0
            name_lower = cmd.name.lower()

            if query_lower == name_lower:
                score = 100
            elif query_lower in name_lower:
                score = 70
            elif any(query_lower in kw.lower() for kw in cmd.keywords):
                score = 40
            elif query_lower in cmd.description.lower():
                score = 20

            if score > 0:
                scored.append((score, cmd))

        scored.sort(key=lambda x: (-x[0], x[1].name))
        return [cmd for _, cmd in scored]

    def execute(self, command_id: str) -> bool:
        """Execute a command by ID.

        Args:
            command_id: The ID of the command to execute.

        Returns:
            True if the command was found and executed successfully.
        """
        cmd = self._commands.get(command_id)
        if not cmd:
            logger.debug("Quick command not found: %s", command_id)
            return False
        if not cmd.action:
            logger.debug("Quick command has no action: %s", command_id)
            return False
        try:
            cmd.action()
            logger.info("Executed quick command: %s", command_id)
            return True
        except (RuntimeError, TypeError, ValueError) as e:
            logger.debug("Quick command execution failed: %s — %s", command_id, e)
            return False

    @staticmethod
    def get_builtin_commands() -> List[QuickCommand]:
        """Return the list of built-in quick commands.

        Note: Actions are set to None here — they must be connected
        to actual UI callbacks when the MainWindow initializes.

        Returns:
            List of QuickCommand definitions without bound actions.
        """
        return [
            QuickCommand(
                id="toggle-focus-mode",
                name="Toggle Focus Mode",
                description="Enable or disable distraction-free Focus Mode",
                category="System",
                keywords=["focus", "distraction", "concentrate", "zen"],
            ),
            QuickCommand(
                id="run-cleanup",
                name="Run System Cleanup",
                description="Clean package caches and temporary files",
                category="Maintenance",
                keywords=["clean", "cache", "temp", "free space", "cleanup"],
            ),
            QuickCommand(
                id="check-updates",
                name="Check for Updates",
                description="Check if system updates are available",
                category="System",
                keywords=["update", "upgrade", "packages", "new"],
            ),
            QuickCommand(
                id="export-config",
                name="Export Configuration",
                description="Export current settings to a JSON file",
                category="Tools",
                keywords=["export", "backup", "settings", "config", "save"],
            ),
            QuickCommand(
                id="view-health",
                name="View Health Score",
                description="Open the detailed system health breakdown",
                category="System",
                keywords=["health", "score", "status", "diagnostics"],
            ),
            QuickCommand(
                id="toggle-theme",
                name="Toggle Dark/Light Theme",
                description="Switch between dark and light visual themes",
                category="Appearance",
                keywords=["theme", "dark", "light", "mode", "color"],
            ),
            QuickCommand(
                id="open-settings",
                name="Open Settings",
                description="Navigate to the Settings tab",
                category="Appearance",
                keywords=["settings", "preferences", "options", "configure"],
            ),
            QuickCommand(
                id="show-notifications",
                name="Show Notification Panel",
                description="Open the notification panel to view recent alerts",
                category="System",
                keywords=["notifications", "alerts", "messages", "panel"],
            ),
            QuickCommand(
                id="undo-last",
                name="Undo Last Action",
                description="Reverse the most recent system change",
                category="System",
                keywords=["undo", "revert", "rollback", "restore", "back"],
            ),
            QuickCommand(
                id="refresh-dashboard",
                name="Refresh Dashboard",
                description="Force refresh all dashboard metrics and graphs",
                category="System",
                keywords=["refresh", "reload", "update", "dashboard"],
            ),
        ]
