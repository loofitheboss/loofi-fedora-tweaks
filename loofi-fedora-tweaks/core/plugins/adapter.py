"""
core.plugins.adapter — Adapter for legacy LoofiPlugin to PluginInterface.

Enables external plugins (v13.0 LoofiPlugin) to work with the v25.0+
unified plugin system (PluginInterface + PluginRegistry).

Usage:
    from utils.plugin_base import LoofiPlugin
    from core.plugins.adapter import PluginAdapter

    legacy_plugin = MyLegacyPlugin()  # LoofiPlugin instance
    adapter = PluginAdapter(legacy_plugin)
    registry.register(adapter)  # Now works with PluginRegistry
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable
import re

from PyQt6.QtWidgets import QWidget
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata, CompatStatus
from utils.plugin_base import LoofiPlugin
from utils.log import get_logger

if TYPE_CHECKING:
    from core.plugins.compat import CompatibilityDetector

logger = get_logger(__name__)


class PluginAdapter(PluginInterface):
    """
    Adapter that wraps a legacy LoofiPlugin as a PluginInterface.

    This allows external plugins using the v13.0 LoofiPlugin ABC to be
    registered in the v25.0+ PluginRegistry without modification.

    Attributes:
        _wrapped: The legacy LoofiPlugin instance being adapted
        _metadata_cache: Cached PluginMetadata (computed once)
    """

    def __init__(self, wrapped_plugin: LoofiPlugin):
        """
        Initialize the adapter with a legacy plugin.

        Args:
            wrapped_plugin: The LoofiPlugin instance to wrap
        """
        self._wrapped = wrapped_plugin
        self._metadata_cache: PluginMetadata | None = None
        logger.debug("PluginAdapter wrapping %s", wrapped_plugin.info.name)

    def metadata(self) -> PluginMetadata:
        """
        Convert legacy PluginInfo to PluginMetadata.

        Maps fields as follows:
        - id: Slugified plugin name (e.g., "My Plugin" → "my-plugin")
        - name: Original plugin name
        - description: Original plugin description
        - category: "Community" (all external plugins)
        - icon: Original plugin icon or default 🔌
        - badge: "community"
        - version: Original plugin version
        - requires: Empty tuple (legacy plugins don't declare dependencies)
        - compat: Empty dict (handled in check_compat())
        - order: 500 (after built-in plugins which use 0-400)
        - enabled: True (user can disable via UI)

        Returns:
            PluginMetadata instance
        """
        if self._metadata_cache is not None:
            return self._metadata_cache

        info = self._wrapped.info

        # Generate unique ID from plugin name (slugify)
        plugin_id = self._slugify(info.name)

        # Build metadata
        self._metadata_cache = PluginMetadata(
            id=plugin_id,
            name=info.name,
            description=info.description,
            category="Community",
            icon=info.icon or "🔌",
            badge="community",
            version=info.version,
            requires=(),
            compat={},
            order=500,
            enabled=True,
        )

        return self._metadata_cache

    def create_widget(self) -> QWidget:
        """
        Delegate widget creation to the wrapped plugin.

        Returns:
            QWidget created by the legacy plugin

        Raises:
            RuntimeError: If widget creation fails
        """
        try:
            widget = self._wrapped.create_widget()
            if not isinstance(widget, QWidget):
                raise TypeError(
                    f"Plugin {self._wrapped.info.name} create_widget() must "
                    f"return QWidget, got {type(widget).__name__}"
                )
            logger.debug("Created widget for %s", self._wrapped.info.name)
            return widget
        except (TypeError, AttributeError, RuntimeError, ValueError) as e:
            logger.error(
                "Failed to create widget for %s: %s", self._wrapped.info.name, e
            )
            raise RuntimeError(
                f"Plugin {self._wrapped.info.name} failed to create widget: {e}"
            ) from e

    def on_activate(self) -> None:
        """
        Called when tab becomes active.

        Delegates to wrapped plugin if it implements on_load().
        Note: LoofiPlugin uses on_load() for initialization, we repurpose
        it for activation since external plugins may use it.
        """
        if hasattr(self._wrapped, "on_load") and callable(self._wrapped.on_load):
            try:
                self._wrapped.on_load()
            except (TypeError, AttributeError, RuntimeError, ValueError) as e:
                logger.warning(
                    "Plugin %s on_load() failed: %s", self._wrapped.info.name, e
                )

    def on_deactivate(self) -> None:
        """
        Called when navigating away from this tab.

        Note: No-op for legacy plugins. LoofiPlugin.on_unload() is for
        complete shutdown, not tab deactivation.
        """

    def check_compat(self, detector: "CompatibilityDetector") -> CompatStatus:
        """
        Check system compatibility for the wrapped plugin.

        Legacy plugins don't have structured compatibility data, but they
        may have requirements in their PluginManifest (if loaded from
        .loofi-plugin archive). For now, we assume compatibility unless
        the plugin explicitly fails during widget creation.

        Future: Could inspect getattr(self._wrapped, "manifest", None) for
        min_app_version or permissions checks.

        Args:
            detector: CompatibilityDetector instance (unused for now)

        Returns:
            CompatStatus indicating compatibility
        """
        # Check if plugin has a manifest with min_app_version
        manifest = getattr(self._wrapped, "manifest", None)

        if manifest and hasattr(manifest, "min_app_version"):
            min_version = manifest.min_app_version
            if min_version:
                from version import __version__ as APP_VERSION

                if not self._version_compat(APP_VERSION, min_version):
                    return CompatStatus(
                        compatible=False,
                        reason=f"Requires app version >= {min_version} "
                        f"(current: {APP_VERSION})",
                    )

        # Check permissions (warn but don't block)
        warnings = []
        if manifest and hasattr(manifest, "permissions"):
            perms = manifest.permissions
            if "sudo" in perms:
                warnings.append("Plugin requests 'sudo' permission — use with caution")
            if "network" in perms:
                warnings.append("Plugin requires network access")

        return CompatStatus(compatible=True, warnings=warnings)

    def set_context(self, context: dict[str, Any]) -> None:
        """
        Inject application context.

        Legacy plugins may not expect this, so we store it as an attribute
        but don't enforce usage. Future external plugins can access via
        self._context if needed.

        Args:
            context: Dict with "main_window", "config_manager", "executor"
        """
        self._context = context
        logger.debug(
            "Injected context for %s: %s",
            self._wrapped.info.name,
            ", ".join(context.keys()),
        )

    @staticmethod
    def _slugify(text: str) -> str:
        """
        Convert plugin name to slug ID.

        Examples:
            "My Plugin" → "my-plugin"
            "AI Enhanced" → "ai-enhanced"
            "Test_Plugin 2.0" → "test-plugin-20"

        Args:
            text: Plugin name

        Returns:
            Lowercase slug with hyphens
        """
        # Lowercase, replace non-alphanumeric with hyphen, strip leading/trailing
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
        return slug.strip("-")

    @staticmethod
    def _version_compat(current: str, minimum: str) -> bool:
        """
        Check if current version meets minimum requirement.

        Simple numeric comparison (e.g., "25.0.0" >= "24.0.0").

        Args:
            current: Current app version (e.g., "25.0.0")
            minimum: Minimum required version (e.g., "24.0.0")

        Returns:
            True if current >= minimum
        """
        try:
            # Extract numeric parts (handle "25.0.0" or "25.0")
            current_parts = [int(x) for x in current.split(".")[:3]]
            minimum_parts = [int(x) for x in minimum.split(".")[:3]]

            # Pad to 3 elements
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(minimum_parts) < 3:
                minimum_parts.append(0)

            return tuple(current_parts) >= tuple(minimum_parts)
        except (ValueError, AttributeError):
            # Unparseable versions — assume compatible
            logger.warning(
                "Could not parse versions: %s vs %s, assuming compatible",
                current,
                minimum,
            )
            return True

    def get_cli_commands(self) -> dict[str, Callable]:  # type: ignore[type-arg]
        """
        Expose CLI commands from wrapped plugin.

        Returns:
            Dict mapping command names to handler functions
        """
        return self._wrapped.get_cli_commands()

    @property
    def wrapped_plugin(self) -> LoofiPlugin:
        """Access the underlying legacy plugin (for advanced use cases)."""
        return self._wrapped
