from __future__ import annotations
import importlib
import logging
from core.plugins.registry import PluginRegistry
from core.plugins.interface import PluginInterface
from core.plugins.compat import CompatibilityDetector

log = logging.getLogger(__name__)

# Ordered list of (module_path, class_name) for all 26 built-in tabs.
# Order here determines initial registration order; PluginMetadata.order refines within category.
_BUILTIN_PLUGINS: list[tuple[str, str]] = [
    ("ui.dashboard_tab", "DashboardTab"),
    ("ui.agents_tab", "AgentsTab"),
    ("ui.automation_tab", "AutomationTab"),
    ("ui.system_info_tab", "SystemInfoTab"),
    ("ui.monitor_tab", "MonitorTab"),
    ("ui.health_timeline_tab", "HealthTimelineTab"),
    ("ui.logs_tab", "LogsTab"),
    ("ui.hardware_tab", "HardwareTab"),
    ("ui.performance_tab", "PerformanceTab"),
    ("ui.storage_tab", "StorageTab"),
    ("ui.software_tab", "SoftwareTab"),
    ("ui.maintenance_tab", "MaintenanceTab"),
    ("ui.snapshot_tab", "SnapshotTab"),
    ("ui.virtualization_tab", "VirtualizationTab"),
    ("ui.development_tab", "DevelopmentTab"),
    ("ui.network_tab", "NetworkTab"),
    ("ui.mesh_tab", "MeshTab"),
    ("ui.security_tab", "SecurityTab"),
    ("ui.desktop_tab", "DesktopTab"),
    ("ui.profiles_tab", "ProfilesTab"),
    ("ui.gaming_tab", "GamingTab"),
    ("ui.ai_enhanced_tab", "AIEnhancedTab"),
    ("ui.teleport_tab", "TeleportTab"),
    ("ui.diagnostics_tab", "DiagnosticsTab"),
    ("ui.community_tab", "CommunityTab"),
    ("ui.settings_tab", "SettingsTab"),
]


class PluginLoader:
    """
    Discovers and loads plugins into PluginRegistry.

    v25.0: built-in plugins only.
    v26.0: add load_external() for filesystem scan.
    """

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        detector: CompatibilityDetector | None = None,
    ) -> None:
        self._registry = registry or PluginRegistry.instance()
        self._detector = detector or CompatibilityDetector()

    def load_builtins(self, context: dict | None = None) -> list[str]:
        """
        Import all built-in plugin modules, instantiate, validate, and register.
        Returns list of successfully loaded plugin IDs.
        """
        loaded: list[str] = []
        for module_path, class_name in _BUILTIN_PLUGINS:
            try:
                plugin = self._import_plugin(module_path, class_name)
                if context:
                    plugin.set_context(context)
                self._registry.register(plugin)
                loaded.append(plugin.metadata().id)
                log.debug("Loaded plugin: %s", plugin.metadata().id)
            except Exception as exc:
                log.warning("Failed to load plugin %s.%s: %s", module_path, class_name, exc)
        return loaded

    def _import_plugin(self, module_path: str, class_name: str) -> PluginInterface:
        """Import module, instantiate class, validate it implements PluginInterface."""
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        if not (isinstance(cls, type) and issubclass(cls, PluginInterface)):
            raise TypeError(f"{class_name} does not subclass PluginInterface")
        return cls()

    def load_external(self, directory: str) -> list[str]:
        """
        Future: scan directory for external plugins.
        v26.0 scope — not implemented in v25.0.
        """
        raise NotImplementedError(
            "External plugin loading is scheduled for v26.0. "
            "See ROADMAP.md for details."
        )
