from __future__ import annotations
import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Optional

from core.plugins.registry import PluginRegistry
from core.plugins.interface import PluginInterface
from core.plugins.compat import CompatibilityDetector
from core.plugins.scanner import PluginScanner
from core.plugins.adapter import PluginAdapter
from core.plugins.sandbox import create_sandbox
from utils.plugin_base import LoofiPlugin

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

    def load_external(self, context: dict | None = None, directory: str | None = None) -> list[str]:
        """
        Scan directory for external plugins and load them into registry.
        
        Discovery flow:
        1. Scanner discovers plugin directories
        2. Parse plugin.json → PluginManifest
        3. Validate manifest schema and version compatibility
        4. Create sandbox with manifest.permissions
        5. Import plugin module dynamically
        6. Find LoofiPlugin subclass in module
        7. Instantiate plugin
        8. Wrap with PluginAdapter(plugin, manifest)
        9. Check compatibility
        10. Register in PluginRegistry if compatible
        
        Args:
            context: Context dict passed to plugins (main_window, config_manager, etc.)
            directory: Override default plugin directory (for testing)
        
        Returns:
            List of successfully loaded plugin IDs
        """
        scanner = PluginScanner(Path(directory) if directory else None)
        discovered = scanner.scan()
        
        if not discovered:
            log.info("No external plugins found")
            return []
        
        loaded: list[str] = []
        
        for plugin_dir, manifest in discovered:
            plugin_id = manifest.id
            
            try:
                # Create sandbox with declared permissions
                sandbox = create_sandbox(plugin_id, manifest.permissions)
                
                # Load plugin module
                plugin_instance = self._load_external_plugin(
                    plugin_dir, manifest, sandbox
                )
                
                if not plugin_instance:
                    continue
                
                # Attach manifest to plugin instance (PluginAdapter expects this)
                plugin_instance.manifest = manifest
                
                # Wrap legacy plugin with adapter
                adapter = PluginAdapter(plugin_instance)
                
                # Set context if provided
                if context:
                    adapter.set_context(context)
                
                # Check compatibility
                compat_result = self._detector.check(adapter.metadata())
                
                if not compat_result.compatible:
                    log.warning(
                        "Plugin '%s' incompatible: %s",
                        plugin_id, compat_result.reason
                    )
                    # Register as disabled (like v25.0 pattern)
                    # Future: Add disabled plugins to registry with metadata
                    continue
                
                # Register in registry
                self._registry.register(adapter)
                loaded.append(plugin_id)
                
                log.info(
                    "Loaded external plugin: %s v%s",
                    manifest.name, manifest.version
                )
                
            except Exception as exc:
                log.error(
                    "Failed to load plugin '%s': %s",
                    plugin_id, exc, exc_info=True
                )
                continue
        
        log.info("Loaded %d external plugin(s)", len(loaded))
        return loaded
    
    def _load_external_plugin(
        self,
        plugin_dir: Path,
        manifest,
        sandbox
    ) -> Optional[LoofiPlugin]:
        """
        Dynamically import and instantiate external plugin.
        
        Args:
            plugin_dir: Path to plugin directory
            manifest: PluginManifest with entry_point
            sandbox: PluginSandbox for permission enforcement
        
        Returns:
            Instantiated LoofiPlugin or None if failed
        """
        entry_point = manifest.entry_point or "plugin.py"
        entry_file = plugin_dir / entry_point
        
        if not entry_file.exists():
            log.error("Entry point not found: %s", entry_file)
            return None
        
        # Prepare module name (replace hyphens for valid Python identifier)
        module_name = f"external_plugin_{manifest.id.replace('-', '_')}"
        
        # Install sandbox import hooks
        sandbox.install()
        
        try:
            # Add plugin dir to sys.path temporarily
            plugin_dir_str = str(plugin_dir)
            if plugin_dir_str not in sys.path:
                sys.path.insert(0, plugin_dir_str)
            
            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(
                    module_name, entry_file
                )
                
                if not spec or not spec.loader:
                    log.error("Failed to create module spec for %s", entry_file)
                    return None
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Find LoofiPlugin subclass in module
                plugin_class = self._find_plugin_class(module)
                
                if not plugin_class:
                    log.error(
                        "No LoofiPlugin subclass found in %s",
                        entry_file
                    )
                    return None
                
                # Instantiate plugin
                plugin_instance = plugin_class()
                
                log.debug(
                    "Instantiated plugin class: %s from %s",
                    plugin_class.__name__, entry_file
                )
                
                return plugin_instance
                
            finally:
                # Clean up sys.path
                if plugin_dir_str in sys.path:
                    sys.path.remove(plugin_dir_str)
                
        except ImportError as exc:
            log.error(
                "Failed to import plugin module '%s': %s",
                manifest.id, exc, exc_info=True
            )
            return None
        
        except Exception as exc:
            log.error(
                "Error instantiating plugin '%s': %s",
                manifest.id, exc, exc_info=True
            )
            return None
        
        finally:
            # Uninstall sandbox hooks
            sandbox.uninstall()
    
    def _find_plugin_class(self, module) -> Optional[type]:
        """
        Find LoofiPlugin subclass in module.
        
        Args:
            module: Imported module object
        
        Returns:
            Plugin class or None if not found
        """
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Must be defined in this module (not imported)
            if obj.__module__ != module.__name__:
                continue
            
            # Must subclass LoofiPlugin but not be LoofiPlugin itself
            if issubclass(obj, LoofiPlugin) and obj is not LoofiPlugin:
                return obj
        
        return None
