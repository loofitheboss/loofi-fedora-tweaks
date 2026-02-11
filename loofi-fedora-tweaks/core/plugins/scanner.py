"""
core.plugins.scanner — External plugin discovery and validation.

Scans user plugin directory (~/.config/loofi-fedora-tweaks/plugins/) for
valid plugin packages and returns discovered manifests.

Directory Structure:
    ~/.config/loofi-fedora-tweaks/plugins/
    ├── my-plugin/
    │   ├── plugin.json          # Manifest (required)
    │   ├── plugin.py            # Entry point (required)
    │   └── requirements.txt     # Python deps (optional)
    └── another-plugin/
        └── ...

Usage:
    from core.plugins.scanner import PluginScanner
    
    scanner = PluginScanner()
    plugins = scanner.scan()
    
    for plugin_path, manifest in plugins:
        print(f"Found: {manifest.name} v{manifest.version}")
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional
import json
import logging

from core.plugins.package import PluginManifest
from version import __version__ as APP_VERSION

logger = logging.getLogger(__name__)


class PluginScanner:
    """
    Discovers and validates external plugins in user directory.
    
    Scans ~/.config/loofi-fedora-tweaks/plugins/ for plugin directories,
    validates structure, parses manifests, and returns valid plugins.
    
    Attributes:
        plugins_dir: Path to user plugin directory
        state_file: Path to plugin state file (enabled/disabled tracking)
    """
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize scanner with plugin directory.
        
        Args:
            plugins_dir: Override default plugin directory path
        """
        config_base = Path.home() / ".config" / "loofi-fedora-tweaks"
        self.plugins_dir = plugins_dir or (config_base / "plugins")
        self.state_file = config_base / "plugins.json"
        
        # Ensure directories exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("PluginScanner initialized: %s", self.plugins_dir)
    
    def scan(self) -> List[Tuple[Path, PluginManifest]]:
        """
        Scan plugin directory and return list of valid plugins.
        
        Returns:
            List of (plugin_dir_path, manifest) tuples for valid plugins
        """
        if not self.plugins_dir.exists():
            logger.info("Plugin directory does not exist: %s", self.plugins_dir)
            return []
        
        discovered: List[Tuple[Path, PluginManifest]] = []
        state = self._load_state()
        
        # Scan all subdirectories
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            plugin_id = plugin_dir.name
            
            # Skip disabled plugins
            if not self._is_enabled(plugin_id, state):
                logger.debug("Skipping disabled plugin: %s", plugin_id)
                continue
            
            # Validate plugin structure
            try:
                manifest = self._validate_plugin(plugin_dir)
                if manifest:
                    discovered.append((plugin_dir, manifest))
                    logger.debug(
                        "Discovered plugin: %s v%s",
                        manifest.name, manifest.version
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to validate plugin '%s': %s",
                    plugin_id, exc
                )
                continue
        
        logger.info("Discovered %d external plugin(s)", len(discovered))
        return discovered
    
    def _validate_plugin(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """
        Validate plugin directory structure and parse manifest.
        
        Args:
            plugin_dir: Path to plugin directory
            
        Returns:
            PluginManifest if valid, None otherwise
        """
        manifest_path = plugin_dir / "plugin.json"
        
        # Check for required manifest
        if not manifest_path.exists():
            logger.warning(
                "Plugin '%s' missing plugin.json manifest",
                plugin_dir.name
            )
            return None
        
        # Parse manifest
        try:
            manifest = self._parse_manifest(manifest_path)
            if not manifest:
                return None
        except Exception as exc:
            logger.warning(
                "Failed to parse manifest for '%s': %s",
                plugin_dir.name, exc
            )
            return None
        
        # Check for entry point
        entry_point = manifest.entry_point or "plugin.py"
        entry_file = plugin_dir / entry_point
        
        if not entry_file.exists():
            logger.warning(
                "Plugin '%s' missing entry point: %s",
                plugin_dir.name, entry_point
            )
            return None
        
        # Check app version compatibility
        if manifest.min_app_version:
            if not self._is_version_compatible(manifest.min_app_version):
                logger.warning(
                    "Plugin '%s' requires app version >= %s (current: %s)",
                    manifest.id, manifest.min_app_version, APP_VERSION
                )
                return None
        
        return manifest
    
    def _parse_manifest(self, manifest_path: Path) -> Optional[PluginManifest]:
        """
        Parse plugin.json manifest file.
        
        Args:
            manifest_path: Path to plugin.json file
            
        Returns:
            PluginManifest instance or None if invalid
        """
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to read/parse manifest: %s", exc)
            return None
        
        # Validate required fields
        required_fields = ["id", "name", "version", "description", "author"]
        missing = [f for f in required_fields if f not in raw]
        
        if missing:
            logger.error(
                "Manifest missing required fields: %s",
                ", ".join(missing)
            )
            return None
        
        # Create manifest instance
        try:
            manifest = PluginManifest(
                id=raw["id"],
                name=raw["name"],
                version=raw["version"],
                description=raw["description"],
                author=raw["author"],
                author_email=raw.get("author_email"),
                license=raw.get("license"),
                homepage=raw.get("homepage"),
                permissions=raw.get("permissions", []),
                requires=raw.get("requires", []),
                min_app_version=raw.get("min_app_version"),
                entry_point=raw.get("entry_point", "plugin.py"),
                icon=raw.get("icon", "🔌"),
                category=raw.get("category"),
                order=raw.get("order"),
            )
            return manifest
        except (TypeError, KeyError) as exc:
            logger.error("Invalid manifest data: %s", exc)
            return None
    
    def _load_state(self) -> dict:
        """
        Load plugin state from JSON file.
        
        Returns:
            State dict with 'enabled' mapping
        """
        if not self.state_file.exists():
            return {"enabled": {}}
        
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load plugin state: %s", exc)
            return {"enabled": {}}
    
    def _is_enabled(self, plugin_id: str, state: dict) -> bool:
        """
        Check if plugin is enabled in state file.
        
        Args:
            plugin_id: Plugin identifier
            state: Loaded state dict
            
        Returns:
            True if enabled (or not in state = default enabled), False if disabled
        """
        enabled_map = state.get("enabled", {})
        
        # Default is enabled if not in state
        if plugin_id not in enabled_map:
            return True
        
        return bool(enabled_map[plugin_id])
    
    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """
        Parse semantic version string to tuple of ints.
        
        Args:
            version_str: Version string like "1.2.3"
            
        Returns:
            Tuple of version components like (1, 2, 3)
        """
        parts = []
        for token in version_str.split("."):
            try:
                parts.append(int(token))
            except ValueError:
                parts.append(0)
        return tuple(parts)
    
    def _is_version_compatible(self, min_version: str) -> bool:
        """
        Check if current app version meets minimum requirement.
        
        Args:
            min_version: Required minimum version string
            
        Returns:
            True if current version >= min_version
        """
        try:
            current = self._parse_version(APP_VERSION)
            required = self._parse_version(min_version)
            return current >= required
        except Exception as exc:
            logger.warning("Version comparison failed: %s", exc)
            return False
