"""
Plugin installer engine with download, verify, extract, and install capabilities.
Part of v26.0 Phase 1 (T5).
"""
import json
import logging
import shutil
import tarfile
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from core.plugins.integrity import IntegrityVerifier
from core.plugins.package import PluginManifest
from core.plugins.resolver import DependencyResolver
from utils.plugin_marketplace import PluginMarketplace

logger = logging.getLogger(__name__)


@dataclass
class InstallerResult:
    """Result of plugin installation operation."""
    success: bool
    plugin_id: str
    version: Optional[str] = None
    error: Optional[str] = None
    installed_path: Optional[Path] = None
    backup_path: Optional[Path] = None
    data: Optional[Dict] = None  # Additional data for specific operations


class PluginInstaller:
    """Install, uninstall, update, and rollback plugins."""

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize plugin installer.

        Args:
            plugins_dir: Directory for installed plugins (default: ~/.config/loofi-fedora-tweaks/plugins/)
        """
        if plugins_dir is None:
            config_home = Path.home() / ".config" / "loofi-fedora-tweaks"
            plugins_dir = config_home / "plugins"

        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.plugins_dir / "state.json"
        self.backups_dir = self.plugins_dir / ".backups"
        self.backups_dir.mkdir(exist_ok=True)

        self.marketplace = PluginMarketplace()
        self.verifier = IntegrityVerifier()

    def _load_state(self) -> Dict[str, Dict]:
        """Load plugin state from state.json."""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to load state: %s", exc)
            return {}

    def _save_state(self, state: Dict[str, Dict]) -> bool:
        """Save plugin state to state.json."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as exc:
            logger.error("Failed to save state: %s", exc)
            return False

    def _extract_archive(self, archive_path: Path, destination: Path) -> bool:
        """
        Extract .loofi-plugin archive (tar.gz) to destination.

        Args:
            archive_path: Path to archive file
            destination: Directory to extract to

        Returns:
            True on success
        """
        try:
            logger.info("Extracting %s to %s", archive_path, destination)

            destination.mkdir(parents=True, exist_ok=True)

            with tarfile.open(archive_path, 'r:gz') as tar:
                # Security check: prevent path traversal
                for member in tar.getmembers():
                    if member.name.startswith('/') or '..' in member.name:
                        logger.error("Security: Invalid path in archive: %s", member.name)
                        return False

                tar.extractall(destination)

            logger.info("Extraction complete")
            return True

        except tarfile.TarError as exc:
            logger.error("Failed to extract archive: %s", exc)
            return False
        except OSError as exc:
            logger.error("Failed to write extracted files: %s", exc)
            return False

    def validate_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """
        Validate plugin manifest.json (public method).

        Args:
            plugin_dir: Plugin directory

        Returns:
            PluginManifest or None if invalid
        """
        return self._validate_manifest(plugin_dir)

    def _validate_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """
        Validate plugin manifest.json.

        Args:
            plugin_dir: Plugin directory

        Returns:
            PluginManifest or None if invalid
        """
        manifest_path = plugin_dir / "manifest.json"

        if not manifest_path.exists():
            logger.error("Missing manifest.json in plugin directory")
            return None

        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)

            # Required fields
            required = ["id", "name", "version", "description", "author"]
            for field in required:
                if field not in data:
                    logger.error("Missing required field '%s' in manifest", field)
                    return None
            if "entrypoint" not in data and "entry_point" not in data:
                logger.error("Missing required field 'entrypoint'/'entry_point' in manifest")
                return None

            manifest = PluginManifest(
                id=data["id"],
                name=data["name"],
                version=data["version"],
                description=data["description"],
                author=data["author"],
                entry_point=data.get("entrypoint", data.get("entry_point", "plugin.py")),
                icon=data.get("icon", "🔌"),
                category=data.get("category", "Other"),
                requires=data.get("requires", []),
                permissions=data.get("permissions", []),
                homepage=data.get("homepage"),
                license=data.get("license")
            )

            logger.debug("Validated manifest for %s v%s", manifest.id, manifest.version)
            return manifest

        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in manifest: %s", exc)
            return None
        except Exception as exc:
            logger.error("Failed to parse manifest: %s", exc)
            return None

    def install(self, plugin_id_or_meta, version: Optional[str] = None, skip_deps: bool = False) -> InstallerResult:
        """
        Download and install plugin from marketplace.

        Args:
            plugin_id_or_meta: Plugin ID string or PluginMetadata object
            version: Optional specific version (defaults to latest)
            skip_deps: If True, don't install dependencies

        Returns:
            InstallerResult with installation status
        """
        try:
            # Handle both plugin ID and metadata
            if isinstance(plugin_id_or_meta, str):
                plugin_id = plugin_id_or_meta
                plugin_meta = None
            else:
                # PluginMetadata object
                plugin_meta = plugin_id_or_meta
                plugin_id = plugin_meta.id

            logger.info("Installing plugin: %s (version: %s)", plugin_id, version or "latest")

            # Check if already installed
            plugin_dir = self.plugins_dir / plugin_id
            if plugin_dir.exists():
                logger.warning("Plugin already installed: %s", plugin_id)
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="Plugin already installed (use update to upgrade)"
                )

            # Get plugin metadata from marketplace if not provided
            if not plugin_meta:
                plugin_meta = self.marketplace.get_plugin_info(plugin_id)
                if not plugin_meta:
                    return InstallerResult(
                        success=False,
                        plugin_id=plugin_id,
                        error="Plugin not found in marketplace"
                    )

            # Check dependencies
            if not skip_deps and plugin_meta.requires:
                logger.info("Checking dependencies: %s", plugin_meta.requires)
                state = self._load_state()
                installed = {pid: pdata["version"] for pid, pdata in state.items()}

                resolver = DependencyResolver(installed)
                missing = resolver.get_missing(plugin_id, plugin_meta.requires)

                if missing:
                    logger.error("Missing dependencies: %s", missing)
                    return InstallerResult(
                        success=False,
                        plugin_id=plugin_id,
                        error=f"Missing dependencies: {', '.join(missing)}"
                    )

            # Download plugin archive
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / f"{plugin_id}.loofi-plugin"

                if plugin_meta:
                    # Metadata object provided by caller: download directly without marketplace re-query.
                    req = urllib.request.Request(
                        plugin_meta.download_url,
                        headers={'User-Agent': 'Loofi-Fedora-Tweaks'}
                    )
                    with urllib.request.urlopen(req, timeout=60) as response:
                        archive_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(archive_path, 'wb') as f:
                            f.write(response.read())
                else:
                    download_result = self.marketplace.download_plugin(plugin_id, archive_path, version)

                    if not download_result.success:
                        return InstallerResult(
                            success=False,
                            plugin_id=plugin_id,
                            error=download_result.error
                        )

                # Verify checksum
                logger.info("Verifying archive integrity")
                verify_result = self.verifier.verify_checksum(archive_path, plugin_meta.checksum_sha256)

                if not verify_result.success:
                    return InstallerResult(
                        success=False,
                        plugin_id=plugin_id,
                        error=f"Integrity verification failed: {verify_result.error}"
                    )

                # Extract to temp location
                extract_dir = Path(temp_dir) / "extracted"
                if not self._extract_archive(archive_path, extract_dir):
                    return InstallerResult(
                        success=False,
                        plugin_id=plugin_id,
                        error="Failed to extract plugin archive"
                    )

                # Validate manifest (support archives with root directory)
                install_source = extract_dir
                manifest = self._validate_manifest(install_source)
                if not manifest:
                    subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
                    if len(subdirs) == 1:
                        install_source = subdirs[0]
                        manifest = self._validate_manifest(install_source)
                if not manifest:
                    return InstallerResult(
                        success=False,
                        plugin_id=plugin_id,
                        error="Invalid or missing plugin manifest"
                    )

                # Verify plugin ID matches
                if manifest.id != plugin_id:
                    logger.error("Plugin ID mismatch: expected %s, got %s", plugin_id, manifest.id)
                    return InstallerResult(
                        success=False,
                        plugin_id=plugin_id,
                        error=f"Plugin ID mismatch in manifest: {manifest.id}"
                    )

                # Move to final location
                logger.info("Installing to %s", plugin_dir)
                shutil.move(str(install_source), str(plugin_dir))

            # Update state
            state = self._load_state()
            state[plugin_id] = {
                "version": manifest.version,
                "enabled": True,
                "installed_at": str(Path(plugin_dir))
            }
            self._save_state(state)

            logger.info("Successfully installed %s v%s", plugin_id, manifest.version)

            return InstallerResult(
                success=True,
                plugin_id=plugin_id,
                version=manifest.version,
                installed_path=plugin_dir
            )

        except Exception as exc:
            logger.error("Installation failed: %s", exc)
            return InstallerResult(
                success=False,
                plugin_id=plugin_id,
                error=f"Installation error: {exc}"
            )

    def uninstall(self, plugin_id: str, create_backup: bool = False) -> InstallerResult:
        """
        Uninstall plugin and remove its directory.

        Args:
            plugin_id: Plugin ID to uninstall
            create_backup: If True, create backup before removal

        Returns:
            InstallerResult with uninstall status
        """
        try:
            logger.info("Uninstalling plugin: %s", plugin_id)

            plugin_dir = self.plugins_dir / plugin_id

            if not plugin_dir.exists():
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="Plugin not found or not installed"
                )

            backup_path = None

            # Create backup if requested
            if create_backup:
                manifest = self._validate_manifest(plugin_dir)
                version = manifest.version if manifest else "unknown"
                backup_path = self.backups_dir / f"{plugin_id}-{version}"

                logger.info("Creating backup at %s", backup_path)
                if backup_path.exists():
                    shutil.rmtree(backup_path)

                shutil.copytree(plugin_dir, backup_path)

            # Remove directory
            shutil.rmtree(plugin_dir)
            logger.info("Removed plugin directory: %s", plugin_dir)

            # Update state
            state = self._load_state()
            if plugin_id in state:
                del state[plugin_id]
                self._save_state(state)

            logger.info("Successfully uninstalled %s", plugin_id)

            return InstallerResult(
                success=True,
                plugin_id=plugin_id,
                backup_path=backup_path
            )

        except Exception as exc:
            logger.error("Uninstall failed: %s", exc)
            return InstallerResult(
                success=False,
                plugin_id=plugin_id,
                error=f"Uninstall error: {exc}"
            )

    def update(self, plugin_id: str, version: Optional[str] = None) -> InstallerResult:
        """
        Update plugin to newer version (backup old version first).

        Args:
            plugin_id: Plugin ID to update
            version: Optional specific version (defaults to latest)

        Returns:
            InstallerResult with update status
        """
        try:
            logger.info("Updating plugin: %s", plugin_id)

            plugin_dir = self.plugins_dir / plugin_id

            if not plugin_dir.exists():
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="Plugin not installed (use install instead)"
                )

            # Get current version
            manifest = self._validate_manifest(plugin_dir)
            if not manifest:
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="Invalid plugin manifest (cannot update)"
                )

            old_version = manifest.version

            # Create backup
            backup_path = self.backups_dir / f"{plugin_id}-{old_version}"
            logger.info("Creating backup at %s", backup_path)

            if backup_path.exists():
                shutil.rmtree(backup_path)

            shutil.copytree(plugin_dir, backup_path)

            # Remove old installation
            shutil.rmtree(plugin_dir)

            # Install new version
            result = self.install(plugin_id, version, skip_deps=True)

            if not result.success:
                # Restore backup on failure
                logger.warning("Update failed, restoring backup")
                shutil.copytree(backup_path, plugin_dir)
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error=f"Update failed: {result.error}",
                    backup_path=backup_path
                )

            logger.info("Successfully updated %s from %s to %s", plugin_id, old_version, result.version)

            return InstallerResult(
                success=True,
                plugin_id=plugin_id,
                version=result.version,
                installed_path=plugin_dir,
                backup_path=backup_path
            )

        except Exception as exc:
            logger.error("Update failed: %s", exc)
            return InstallerResult(
                success=False,
                plugin_id=plugin_id,
                error=f"Update error: {exc}"
            )

    def rollback(self, plugin_id: str) -> InstallerResult:
        """
        Rollback to previous version from backup.

        Args:
            plugin_id: Plugin ID to rollback

        Returns:
            InstallerResult with rollback status
        """
        try:
            logger.info("Rolling back plugin: %s", plugin_id)

            plugin_dir = self.plugins_dir / plugin_id

            # Find most recent backup
            backups = sorted(self.backups_dir.glob(f"{plugin_id}-*"))

            if not backups:
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="No backup found for this plugin"
                )

            backup_path = backups[-1]  # Most recent
            logger.info("Restoring from backup: %s", backup_path)

            # Remove current installation if exists
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)

            # Restore backup
            shutil.copytree(backup_path, plugin_dir)

            # Update state
            manifest = self._validate_manifest(plugin_dir)
            if manifest:
                state = self._load_state()
                state[plugin_id] = {
                    "version": manifest.version,
                    "enabled": True,
                    "installed_at": str(plugin_dir)
                }
                self._save_state(state)

            logger.info("Successfully rolled back %s", plugin_id)

            return InstallerResult(
                success=True,
                plugin_id=plugin_id,
                version=manifest.version if manifest else None,
                installed_path=plugin_dir,
                backup_path=backup_path
            )

        except Exception as exc:
            logger.error("Rollback failed: %s", exc)
            return InstallerResult(
                success=False,
                plugin_id=plugin_id,
                error=f"Rollback error: {exc}"
            )

    def check_update(self, plugin_id: str) -> InstallerResult:
        """
        Check if an update is available for a plugin.

        Args:
            plugin_id: Plugin ID to check

        Returns:
            InstallerResult with update_available in data field
        """
        try:
            logger.info("Checking for updates: %s", plugin_id)

            # Get current version
            state = self._load_state()
            if plugin_id not in state:
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="Plugin not installed"
                )

            current_version = state[plugin_id]["version"]

            # Get latest version from marketplace
            plugin_meta = self.marketplace.get_plugin_info(plugin_id)
            if not plugin_meta:
                return InstallerResult(
                    success=False,
                    plugin_id=plugin_id,
                    error="Plugin not found in marketplace"
                )

            update_available = plugin_meta.version != current_version

            return InstallerResult(
                success=True,
                plugin_id=plugin_id,
                version=current_version,
                data={
                    "update_available": update_available,
                    "current_version": current_version,
                    "new_version": plugin_meta.version if update_available else current_version
                }
            )

        except Exception as exc:
            logger.error("Check update failed: %s", exc)
            return InstallerResult(
                success=False,
                plugin_id=plugin_id,
                error=f"Check update error: {exc}"
            )

    def list_installed(self) -> InstallerResult:
        """
        List all installed plugins.

        Returns:
            InstallerResult with list of installed plugin manifests in .data
        """
        try:
            logger.debug("Listing installed plugins")

            if not self.plugins_dir.exists():
                return InstallerResult(
                    success=True,
                    plugin_id="",
                    data=[]
                )

            installed = []

            for plugin_dir in self.plugins_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue

                # Skip backups directory
                if plugin_dir.name.startswith("."):
                    continue

                # Try to read manifest
                manifest = self._validate_manifest(plugin_dir)
                if manifest:
                    installed.append(manifest)
                    logger.debug("Found installed plugin: %s v%s", manifest.id, manifest.version)

            logger.info("Found %d installed plugin(s)", len(installed))

            return InstallerResult(
                success=True,
                plugin_id="",
                data=installed
            )

        except Exception as exc:
            logger.error("Failed to list installed plugins: %s", exc)
            return InstallerResult(
                success=False,
                plugin_id="",
                error=f"List error: {exc}",
                data=[]
            )
