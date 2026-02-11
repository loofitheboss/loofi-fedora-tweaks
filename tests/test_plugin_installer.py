"""Tests for utils.plugin_installer — PluginInstaller install/uninstall engine."""
import os
import sys
import json
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.plugin_installer import PluginInstaller, InstallerResult
from core.plugins.package import PluginManifest
from core.plugins.integrity import VerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_archive(tmpdir: Path, plugin_id: str) -> Path:
    """Create a minimal .loofi-plugin archive."""
    archive_path = tmpdir / f"{plugin_id}.loofi-plugin"
    plugin_dir = tmpdir / plugin_id
    plugin_dir.mkdir()
    
    manifest = {
        "id": plugin_id,
        "name": plugin_id.title(),
        "version": "1.0.0",
        "description": "Test plugin",
        "author": "Test Author",
        "entrypoint": "plugin.py"
    }
    
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
    (plugin_dir / "plugin.py").write_text("# Plugin code")
    
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(plugin_dir, arcname=plugin_id)
    
    return archive_path


def _make_plugin_metadata(plugin_id: str = "test-plugin"):
    """Create mock PluginMetadata."""
    from utils.plugin_marketplace import PluginMetadata
    return PluginMetadata(
        id=plugin_id,
        name=plugin_id.title(),
        description="Test plugin",
        version="1.0.0",
        author="Test",
        category="Utility",
        icon="🔌",
        download_url=f"https://example.com/{plugin_id}.tar.gz",
        checksum_sha256="a" * 64,
        featured=False,
        tags=[],
        requires=[]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginInstallerInitialization:
    """Tests for PluginInstaller construction."""

    def test_installer_uses_default_plugins_dir(self):
        """Installer uses default plugins directory."""
        installer = PluginInstaller()
        expected = Path.home() / ".config" / "loofi-fedora-tweaks" / "plugins"
        assert installer.plugins_dir == expected

    def test_installer_accepts_custom_plugins_dir(self):
        """Installer accepts custom plugins directory."""
        custom_dir = Path("/tmp/custom-plugins")
        installer = PluginInstaller(plugins_dir=custom_dir)
        assert installer.plugins_dir == custom_dir

    def test_installer_creates_plugins_dir(self):
        """Installer creates plugins directory on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            installer = PluginInstaller(plugins_dir=plugins_dir)
            assert plugins_dir.exists()

    def test_installer_creates_backups_dir(self):
        """Installer creates backups directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            installer = PluginInstaller(plugins_dir=plugins_dir)
            backups_dir = plugins_dir / ".backups"
            assert backups_dir.exists()

    def test_installer_sets_state_file_path(self):
        """Installer sets correct state file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            installer = PluginInstaller(plugins_dir=plugins_dir)
            expected = plugins_dir / "state.json"
            assert installer.state_file == expected


class TestPluginInstallerExtractArchive:
    """Tests for archive extraction."""

    def test_extract_valid_archive(self):
        """Extract valid .loofi-plugin archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            archive = _create_test_archive(tmpdir, "test-plugin")
            dest = tmpdir / "extracted"
            
            installer = PluginInstaller()
            result = installer._extract_archive(archive, dest)
            
            assert result is True
            assert (dest / "test-plugin" / "manifest.json").exists()
            assert (dest / "test-plugin" / "plugin.py").exists()

    def test_extract_creates_destination_dir(self):
        """Extract creates destination directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            archive = _create_test_archive(tmpdir, "test-plugin")
            dest = tmpdir / "does-not-exist"
            
            installer = PluginInstaller()
            result = installer._extract_archive(archive, dest)
            
            assert result is True
            assert dest.exists()

    def test_extract_rejects_path_traversal(self):
        """Extract rejects archives with path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            archive_path = tmpdir / "malicious.tar.gz"
            
            # Create malicious archive with ../
            with tarfile.open(archive_path, "w:gz") as tar:
                info = tarfile.TarInfo(name="../etc/passwd")
                info.size = 0
                tar.addfile(info)
            
            dest = tmpdir / "dest"
            installer = PluginInstaller()
            result = installer._extract_archive(archive_path, dest)
            
            assert result is False

    def test_extract_handles_corrupted_archive(self):
        """Extract handles corrupted archive gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            corrupted = tmpdir / "corrupted.tar.gz"
            corrupted.write_text("not a valid archive")
            
            dest = tmpdir / "dest"
            installer = PluginInstaller()
            result = installer._extract_archive(corrupted, dest)
            
            assert result is False


class TestPluginInstallerValidateManifest:
    """Tests for manifest validation."""

    def test_validate_complete_manifest(self):
        """Validate accepts complete manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()
            
            manifest_data = {
                "id": "test-plugin",
                "name": "Test Plugin",
                "version": "1.0.0",
                "description": "Description",
                "author": "Author",
                "entrypoint": "plugin.py"
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(manifest_data))
            
            installer = PluginInstaller()
            manifest = installer._validate_manifest(plugin_dir)
            
            assert manifest is not None
            assert manifest.id == "test-plugin"

    def test_validate_rejects_missing_manifest(self):
        """Validate rejects directory without manifest.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "no-manifest"
            plugin_dir.mkdir()
            
            installer = PluginInstaller()
            manifest = installer._validate_manifest(plugin_dir)
            
            assert manifest is None

    def test_validate_rejects_incomplete_manifest(self):
        """Validate rejects manifest missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "incomplete"
            plugin_dir.mkdir()
            
            incomplete = {
                "id": "incomplete",
                "name": "Name"
                # Missing version, description, author, entrypoint
            }
            (plugin_dir / "manifest.json").write_text(json.dumps(incomplete))
            
            installer = PluginInstaller()
            manifest = installer._validate_manifest(plugin_dir)
            
            assert manifest is None

    def test_validate_handles_malformed_json(self):
        """Validate handles malformed JSON gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "bad-json"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.json").write_text("{ invalid json ")
            
            installer = PluginInstaller()
            manifest = installer._validate_manifest(plugin_dir)
            
            assert manifest is None


class TestPluginInstallerStateManagement:
    """Tests for plugin state persistence."""

    def test_load_state_returns_empty_dict_if_missing(self):
        """load_state() returns empty dict when state file missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PluginInstaller(plugins_dir=Path(tmpdir))
            state = installer._load_state()
            assert state == {}

    def test_load_state_parses_valid_json(self):
        """load_state() parses valid state JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir)
            state_file = plugins_dir / "state.json"
            state_data = {"plugin-1": {"enabled": True, "version": "1.0"}}
            state_file.write_text(json.dumps(state_data))
            
            installer = PluginInstaller(plugins_dir=plugins_dir)
            state = installer._load_state()
            
            assert state == state_data

    def test_save_state_writes_json(self):
        """save_state() writes state to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PluginInstaller(plugins_dir=Path(tmpdir))
            state = {"plugin-1": {"enabled": True}}
            
            result = installer._save_state(state)
            
            assert result is True
            assert installer.state_file.exists()
            
            saved = json.loads(installer.state_file.read_text())
            assert saved == state


class TestPluginInstallerInstall:
    """Tests for plugin installation."""

    @patch('utils.plugin_installer.PluginMarketplace')
    @patch('urllib.request.urlopen')
    def test_install_downloads_and_extracts_plugin(self, mock_urlopen, mock_marketplace_class):
        """install() downloads, verifies, and extracts plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test archive
            archive = _create_test_archive(tmpdir, "test-plugin")
            archive_bytes = archive.read_bytes()
            
            # Mock download
            mock_response = MagicMock()
            mock_response.read.return_value = archive_bytes
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            
            # Mock marketplace
            mock_marketplace = MagicMock()
            mock_marketplace_class.return_value = mock_marketplace
            
            # Mock verifier
            installer = PluginInstaller(plugins_dir=tmpdir / "plugins")
            installer.verifier = MagicMock()
            installer.verifier.verify_checksum.return_value = VerificationResult(success=True)
            
            metadata = _make_plugin_metadata("test-plugin")
            result = installer.install(metadata)
            
            assert result.success is True
            assert result.plugin_id == "test-plugin"

    def test_install_returns_error_on_verification_failure(self):
        """install() returns error when checksum verification fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PluginInstaller(plugins_dir=Path(tmpdir) / "plugins")
            installer.verifier = MagicMock()
            installer.verifier.verify_checksum.return_value = VerificationResult(
                success=False,
                error="Checksum mismatch"
            )
            
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.return_value = b"fake archive data"
                mock_response.__enter__.return_value = mock_response
                mock_urlopen.return_value = mock_response
                
                metadata = _make_plugin_metadata()
                result = installer.install(metadata)
                
                assert result.success is False
                assert "Checksum" in result.error or "verify" in result.error.lower()


class TestPluginInstallerUninstall:
    """Tests for plugin uninstallation."""

    def test_uninstall_removes_plugin_directory(self):
        """uninstall() removes plugin directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            plugins_dir.mkdir()
            
            plugin_dir = plugins_dir / "test-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.json").write_text("{}")
            
            installer = PluginInstaller(plugins_dir=plugins_dir)
            result = installer.uninstall("test-plugin")
            
            assert result.success is True
            assert not plugin_dir.exists()

    def test_uninstall_creates_backup_before_removal(self):
        """uninstall() creates backup before removing plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            plugins_dir.mkdir()
            
            plugin_dir = plugins_dir / "test-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "test.txt").write_text("data")
            
            installer = PluginInstaller(plugins_dir=plugins_dir)
            result = installer.uninstall("test-plugin", create_backup=True)
            
            assert result.success is True
            assert result.backup_path is not None
            assert result.backup_path.exists()

    def test_uninstall_returns_error_for_nonexistent_plugin(self):
        """uninstall() returns error when plugin doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PluginInstaller(plugins_dir=Path(tmpdir))
            result = installer.uninstall("nonexistent-plugin")
            
            assert result.success is False
            assert "not found" in result.error.lower() or "exist" in result.error.lower()


class TestPluginInstallerListInstalled:
    """Tests for listing installed plugins."""

    def test_list_installed_returns_empty_list_when_none(self):
        """list_installed() returns empty list when no plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PluginInstaller(plugins_dir=Path(tmpdir))
            result = installer.list_installed()
            
            assert result.success is True
            assert result.data == []

    def test_list_installed_finds_all_plugins(self):
        """list_installed() finds all installed plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir)
            
            for i in range(3):
                plugin_dir = plugins_dir / f"plugin-{i}"
                plugin_dir.mkdir()
                manifest = {
                    "id": f"plugin-{i}",
                    "name": f"Plugin {i}",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "Test",
                    "entrypoint": "plugin.py"
                }
                (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
            
            installer = PluginInstaller(plugins_dir=plugins_dir)
            result = installer.list_installed()
            
            assert result.success is True
            assert len(result.data) == 3


class TestPluginInstallerIntegration:
    """Integration tests for installer workflow."""

    @patch('urllib.request.urlopen')
    def test_full_install_lifecycle(self, mock_urlopen):
        """Test complete install -> list -> uninstall workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            plugins_dir = tmpdir / "plugins"
            
            # Create archive
            archive = _create_test_archive(tmpdir, "lifecycle-plugin")
            
            # Mock download
            mock_response = MagicMock()
            mock_response.read.return_value = archive.read_bytes()
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            
            installer = PluginInstaller(plugins_dir=plugins_dir)
            installer.verifier = MagicMock()
            installer.verifier.verify_checksum.return_value = VerificationResult(success=True)
            
            # Install
            metadata = _make_plugin_metadata("lifecycle-plugin")
            install_result = installer.install(metadata)
            assert install_result.success is True
            
            # List
            list_result = installer.list_installed()
            assert len(list_result.data) == 1
            
            # Uninstall
            uninstall_result = installer.uninstall("lifecycle-plugin")
            assert uninstall_result.success is True
