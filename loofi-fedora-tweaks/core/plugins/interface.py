from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget
from core.plugins.metadata import PluginMetadata, CompatStatus

if TYPE_CHECKING:
    from core.plugins.compat import CompatibilityDetector


class PluginInterface(ABC):
    """
    Abstract base class for all Loofi tab plugins.

    Every built-in tab and future external plugin must subclass this.
    Core never imports ui/; tabs import from core.
    """

    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return immutable plugin metadata. Must not perform I/O."""
        ...

    @abstractmethod
    def create_widget(self) -> QWidget:
        """
        Instantiate and return the tab's QWidget.
        Called lazily by PluginLoader inside a LazyWidget wrapper.
        Must not be called more than once per plugin instance.
        """
        ...

    def on_activate(self) -> None:
        """Called when this tab becomes the active page. Optional."""

    def on_deactivate(self) -> None:
        """Called when this tab is navigated away from. Optional."""

    def check_compat(self, detector: "CompatibilityDetector") -> CompatStatus:
        """
        Check whether this plugin is compatible with the current system.
        Default implementation: always compatible.
        Tabs override this to gate on Fedora version, DE, hardware, etc.
        """
        from core.plugins.metadata import CompatStatus
        return CompatStatus(compatible=True)

    def set_context(self, context: dict) -> None:
        """
        Inject shared application context (replaces direct MainWindow ref).
        Called by PluginLoader after registration.
        context keys: "main_window", "config_manager", "executor"
        """
