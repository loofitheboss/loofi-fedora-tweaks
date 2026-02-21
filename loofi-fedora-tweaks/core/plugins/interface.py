from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.plugins.metadata import CompatStatus, PluginMetadata

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from core.plugins.compat import CompatibilityDetector
else:
    QWidget = Any


class PluginInterface:
    """
    Abstract base class for all Loofi tab plugins.

    Every built-in tab and future external plugin must subclass this.
    Core never imports ui/; tabs import from core.
    """

    def metadata(self) -> PluginMetadata:
        """Return immutable plugin metadata. Must not perform I/O."""
        raise NotImplementedError

    def create_widget(self) -> QWidget:
        """
        Instantiate and return the tab's QWidget.
        Called lazily by PluginLoader inside a LazyWidget wrapper.
        Must not be called more than once per plugin instance.
        """
        raise NotImplementedError

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
