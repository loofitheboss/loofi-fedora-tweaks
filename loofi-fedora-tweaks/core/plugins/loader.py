from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from utils.plugin_base import LoofiPlugin
from version import __version__ as APP_VERSION

from core.plugins.adapter import PluginAdapter
from core.plugins.compat import CompatibilityDetector
from core.plugins.interface import PluginInterface
from core.plugins.registry import PluginRegistry
from core.plugins.sandbox import create_sandbox
from core.plugins.scanner import PluginScanner

log = logging.getLogger(__name__)

# NOTE: List order below does NOT affect sidebar order.
# Final sidebar order is determined by (CATEGORY_ORDER rank, PluginMetadata.order).
# See core/plugins/registry.py for CATEGORY_ORDER.
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
    ("ui.extensions_tab", "ExtensionsTab"),
    ("ui.backup_tab", "BackupTab"),
    ("ui.settings_tab", "SettingsTab"),
]


@dataclass(frozen=True)
class HotReloadRequest:
    """Contract describing a plugin hot-reload trigger and changed files."""
    plugin_id: str
    changed_files: tuple[str, ...] = ()
    reason: str = "filesystem"


@dataclass(frozen=True)
class HotReloadResult:
    """Contract describing hot-reload execution outcome."""
    plugin_id: str
    reloaded: bool
    message: str = ""
    rolled_back: bool = False


class HotReloadManager(Protocol):
    """Interface contract for plugin hot-reload integrations (v27)."""

    def request_reload(self, request: HotReloadRequest) -> HotReloadResult:
        """Evaluate and execute a plugin reload request."""


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
        self._external_plugin_dirs: dict[str, Path] = {}
        self._external_registry_ids: dict[str, str] = {}
        self._external_snapshots: dict[str, str] = {}
        self._external_context: dict = {}

    @staticmethod
    def _parse_version(ver_str: str) -> tuple[int, ...]:
        """Parse semantic version string to tuple for comparison."""
        if not ver_str or not isinstance(ver_str, str):
            return (0,)
        try:
            clean_ver = ver_str.strip().lstrip("v")
            parts = clean_ver.split(".")
            return tuple(int(p) for p in parts if p.isdigit())
        except (ValueError, AttributeError):
            return (0,)

    def _check_version_compatibility(
        self, plugin_id: str, min_version: str, max_version: str
    ) -> tuple[bool, str]:
        """Check if plugin version requirements match current app version."""
        if not min_version and not max_version:
            return (True, "")
        try:
            app_ver = self._parse_version(APP_VERSION)
            if min_version:
                min_ver = self._parse_version(min_version)
                if app_ver < min_ver:
                    reason = "Plugin requires app version >= %s, current: %s" % (
                        min_version, APP_VERSION,
                    )
                    log.warning("Plugin '%s' version incompatible: %s", plugin_id, reason)
                    return (False, reason)
            if max_version:
                max_ver = self._parse_version(max_version)
                if app_ver > max_ver:
                    reason = "Plugin supports app version <= %s, current: %s" % (
                        max_version, APP_VERSION,
                    )
                    log.warning("Plugin '%s' version incompatible: %s", plugin_id, reason)
                    return (False, reason)
            return (True, "")
        except (ValueError, TypeError, AttributeError) as exc:
            log.error("Version comparison failed for plugin '%s': %s", plugin_id, exc)
            return (False, "Version comparison error: %s" % exc)

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
            except (ImportError, AttributeError, TypeError, ValueError) as exc:
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
        self._external_context = dict(context or {})
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
                if not sandbox.enforce_isolation():
                    log.warning(
                        "Skipping plugin '%s': isolation policy could not be enforced",
                        plugin_id,
                    )
                    continue

                # Load plugin module
                plugin_instance = self._load_external_plugin(
                    plugin_dir, manifest, sandbox
                )

                if not plugin_instance:
                    continue

                # Attach manifest to plugin instance (PluginAdapter expects this)
                plugin_instance.manifest = manifest  # type: ignore[attr-defined]

                # Wrap legacy plugin with adapter
                adapter = PluginAdapter(plugin_instance)

                # Set context if provided
                if context:
                    adapter.set_context(context)

                # Check app version compatibility
                metadata = adapter.metadata()
                min_ver = getattr(metadata, "min_app_version", "")
                max_ver = getattr(metadata, "max_app_version", "")
                if min_ver or max_ver:
                    ver_ok, ver_reason = self._check_version_compatibility(
                        plugin_id, min_ver, max_ver,
                    )
                    if not ver_ok:
                        log.warning(
                            "Plugin '%s' version incompatible: %s",
                            plugin_id, ver_reason,
                        )
                        continue

                # Check compatibility
                compat_result = self._detector.check_plugin_compat(adapter.metadata().compat)

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
                self._external_plugin_dirs[plugin_id] = plugin_dir
                self._external_registry_ids[plugin_id] = adapter.metadata().id
                self._external_snapshots[plugin_id] = scanner.build_plugin_fingerprint(
                    plugin_dir, manifest.entry_point or "plugin.py"
                )

                log.info(
                    "Loaded external plugin: %s v%s",
                    manifest.name, manifest.version
                )

            except (ImportError, AttributeError, OSError, RuntimeError) as exc:
                log.error(
                    "Failed to load plugin '%s': %s",
                    plugin_id, exc, exc_info=True
                )
                continue

        log.info("Loaded %d external plugin(s)", len(loaded))
        return loaded

    def request_reload(self, request: HotReloadRequest) -> HotReloadResult:
        """
        Reload an already loaded external plugin if file changes are detected.

        Reload strategy:
        1. Validate plugin is known and currently registered.
        2. Detect content change (explicit changed_files or fingerprint delta).
        3. Unregister old plugin and attempt full reload.
        4. On failure, rollback old plugin registration.
        """
        plugin_id = str(request.plugin_id or "").strip()
        if not plugin_id:
            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=False,
                message="Plugin ID is required",
            )

        plugin_dir = self._external_plugin_dirs.get(plugin_id)
        if not plugin_dir:
            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=False,
                message=f"Plugin '{plugin_id}' is not loaded as external plugin",
            )

        registry_id = self._external_registry_ids.get(plugin_id, plugin_id)
        previous_plugin = self._registry.get(registry_id)
        if previous_plugin is None:
            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=False,
                message=f"Plugin '{plugin_id}' is not present in registry",
            )

        scanner = PluginScanner(plugin_dir.parent)
        manifest = scanner._validate_plugin(plugin_dir)
        if manifest is None:
            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=False,
                message=f"Plugin '{plugin_id}' manifest/entry validation failed",
            )

        current_fingerprint = scanner.build_plugin_fingerprint(
            plugin_dir, manifest.entry_point or "plugin.py"
        )
        previous_fingerprint = self._external_snapshots.get(plugin_id, "")
        changed = bool(request.changed_files) or (previous_fingerprint != current_fingerprint)
        if not changed:
            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=False,
                message=f"No changes detected for plugin '{plugin_id}'",
            )

        return self._reload_external_plugin(
            plugin_id=plugin_id,
            plugin_dir=plugin_dir,
            manifest=manifest,
            previous_plugin=previous_plugin,
            previous_registry_id=registry_id,
            new_fingerprint=current_fingerprint,
            reason=request.reason,
        )

    def _reload_external_plugin(
        self,
        plugin_id: str,
        plugin_dir: Path,
        manifest,
        previous_plugin: PluginInterface,
        previous_registry_id: str,
        new_fingerprint: str,
        reason: str = "manual",
    ) -> HotReloadResult:
        """Reload one external plugin and rollback on any failure."""
        self._registry.unregister(previous_registry_id)

        try:
            sandbox = create_sandbox(plugin_id, manifest.permissions)
            if not sandbox.enforce_isolation():
                raise RuntimeError("Isolation policy could not be enforced")

            plugin_instance = self._load_external_plugin(plugin_dir, manifest, sandbox)
            if not plugin_instance:
                raise RuntimeError("Plugin import failed")

            setattr(plugin_instance, 'manifest', manifest)
            adapter = PluginAdapter(plugin_instance)

            if self._external_context:
                adapter.set_context(self._external_context)

            compat_result = self._detector.check_plugin_compat(adapter.metadata().compat)
            if not compat_result.compatible:
                raise RuntimeError(f"Incompatible plugin: {compat_result.reason}")

            self._registry.register(adapter)
            self._external_registry_ids[plugin_id] = adapter.metadata().id
            self._external_snapshots[plugin_id] = new_fingerprint

            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=True,
                message=f"Plugin reloaded ({reason})",
                rolled_back=False,
            )

        except (ImportError, AttributeError, OSError, RuntimeError) as exc:
            restored = self._restore_previous_plugin(previous_registry_id, previous_plugin)
            return HotReloadResult(
                plugin_id=plugin_id,
                reloaded=False,
                message=f"Hot reload failed: {exc}",
                rolled_back=restored,
            )

    def _restore_previous_plugin(self, previous_registry_id: str, previous_plugin: PluginInterface) -> bool:
        """Best-effort rollback of prior plugin registration."""
        try:
            if self._registry.get(previous_registry_id) is None:
                self._registry.register(previous_plugin)
            return True
        except (RuntimeError, TypeError) as exc:
            log.error(
                "Rollback failed for plugin '%s': %s",
                previous_registry_id,
                exc,
                exc_info=True,
            )
            return False

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
                plugin_instance: LoofiPlugin = plugin_class()

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

        except (TypeError, AttributeError, RuntimeError) as exc:
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
