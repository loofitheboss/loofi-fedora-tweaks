"""
Tests for v26.0 Phase 2: Plugin Marketplace UI, CLI, and Auto-Update.
Tests T9-T14 functionality.
"""
import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from utils.plugin_installer import InstallerResult
from core.plugins.package import PluginManifest, PluginPackage
from utils.plugin_marketplace import PluginMetadata, MarketplaceResult


def _make_plugin_package(
    plugin_id="test-plugin",
    version="1.0.0",
    description="Test description",
    permissions=None
):
    """Build a PluginPackage test object compatible with current v26 models."""
    if permissions is None:
        permissions = []

    allowed_permissions = {"network", "filesystem", "sudo", "clipboard", "notifications"}
    manifest_permissions = [p for p in permissions if p in allowed_permissions]

    metadata = PluginMetadata(
        id=plugin_id,
        name=plugin_id,
        version=version,
        author="Test Author",
        description=description,
        category="UI",
        icon="🔌",
        download_url=f"https://example.com/{plugin_id}.loofi-plugin",
        checksum_sha256="a" * 64,
        featured=False,
        tags=[],
        requires=[]
    )
    manifest = PluginManifest(
        id=plugin_id,
        name=plugin_id,
        version=version,
        description=description,
        author="Test Author",
        permissions=manifest_permissions,
        entry_point="plugin.py"
    )
    # Preserve original permission strings for UI dialog assertions.
    manifest.permissions = permissions
    package = PluginPackage(manifest=manifest)
    package.metadata = metadata
    package.download_url = metadata.download_url
    return package


class TestCommunityTabMarketplace(unittest.TestCase):
    """Test plugin marketplace UI in Community tab."""

    @classmethod
    def setUpClass(cls):
        """Create QApplication instance once for all tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_marketplace_patcher = patch('ui.community_tab.PluginMarketplace')
        self.mock_installer_patcher = patch('ui.community_tab.PluginInstaller')
        self.mock_loader_patcher = patch('ui.community_tab.PluginLoader')

        self.mock_marketplace = self.mock_marketplace_patcher.start()
        self.mock_installer = self.mock_installer_patcher.start()
        self.mock_loader = self.mock_loader_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.mock_marketplace_patcher.stop()
        self.mock_installer_patcher.stop()
        self.mock_loader_patcher.stop()

    @patch('ui.community_tab.PresetMarketplace')
    @patch('ui.community_tab.ConfigManager')
    @patch('ui.community_tab.CloudSyncManager')
    @patch('ui.community_tab.PresetManager')
    @patch('ui.community_tab.DriftDetector')
    def test_marketplace_tab_creation(self, *mocks):
        """Test that marketplace tab is created with plugin browsing UI."""
        from ui.community_tab import CommunityTab

        tab = CommunityTab()

        # Check that plugin marketplace components exist
        self.assertTrue(hasattr(tab, 'plugin_marketplace'))
        self.assertTrue(hasattr(tab, 'plugin_installer'))
        self.assertTrue(hasattr(tab, 'marketplace_plugin_list'))
        self.assertTrue(hasattr(tab, 'install_plugin_btn'))

    @patch('ui.community_tab.PresetMarketplace')
    @patch('ui.community_tab.ConfigManager')
    @patch('ui.community_tab.CloudSyncManager')
    @patch('ui.community_tab.PresetManager')
    @patch('ui.community_tab.DriftDetector')
    def test_search_marketplace_plugins(self, *mocks):
        """Test marketplace plugin search functionality."""
        from ui.community_tab import CommunityTab

        mock_pkg = _make_plugin_package(permissions=["ui:integrate"])

        tab = CommunityTab()
        tab.plugin_marketplace.search_plugins = Mock(return_value=[mock_pkg])

        # Trigger search
        tab._search_marketplace_plugins()

        # Verify search was called
        tab.plugin_marketplace.search_plugins.assert_called_once()

    @patch('ui.community_tab.PresetMarketplace')
    @patch('ui.community_tab.ConfigManager')
    @patch('ui.community_tab.CloudSyncManager')
    @patch('ui.community_tab.PresetManager')
    @patch('ui.community_tab.DriftDetector')
    @patch('ui.community_tab.QMessageBox')
    def test_install_plugin_with_permissions(self, mock_msgbox, *mocks):
        """Test plugin installation with permission consent."""
        from ui.community_tab import CommunityTab

        tab = CommunityTab()

        mock_pkg = _make_plugin_package(
            description="Test",
            permissions=["system:execute", "network:access"]
        )

        tab.selected_marketplace_plugin = mock_pkg
        mock_result = InstallerResult(success=True, plugin_id="test-plugin", version="1.0.0")
        tab.plugin_installer.install = Mock(return_value=mock_result)

        # Mock permission dialog to accept
        with patch('ui.community_tab.PermissionConsentDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = mock_dialog_instance.DialogCode.Accepted = 1
            mock_dialog.return_value = mock_dialog_instance

            tab._install_marketplace_plugin()

            # Verify permission dialog was shown
            mock_dialog.assert_called_once()
            # Verify install was called
            tab.plugin_installer.install.assert_called_once_with("test-plugin")


class TestCLIMarketplace(unittest.TestCase):
    """Test CLI plugin marketplace commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_marketplace_patcher = patch('cli.main.PluginMarketplace')
        self.mock_installer_patcher = patch('cli.main.PluginInstaller')

        self.mock_marketplace_cls = self.mock_marketplace_patcher.start()
        self.mock_installer_cls = self.mock_installer_patcher.start()

        self.mock_marketplace = Mock()
        self.mock_installer = Mock()
        self.mock_marketplace_cls.return_value = self.mock_marketplace
        self.mock_installer_cls.return_value = self.mock_installer

    def tearDown(self):
        """Clean up patches."""
        self.mock_marketplace_patcher.stop()
        self.mock_installer_patcher.stop()

    @patch('cli.main._print')
    @patch('cli.main._json_output', False)
    def test_search_plugins(self, mock_print):
        """Test plugin search command."""
        from cli.main import cmd_plugin_marketplace

        mock_pkg = _make_plugin_package()
        self.mock_marketplace.search = Mock(
            return_value=MarketplaceResult(success=True, data=[mock_pkg.metadata])
        )

        # Create mock args
        args = Mock()
        args.action = "search"
        args.query = "test"
        args.category = ""

        result = cmd_plugin_marketplace(args)

        self.assertEqual(result, 0)
        self.mock_marketplace.search.assert_called_once()

    @patch('cli.main._print')
    @patch('cli.main._json_output', False)
    def test_plugin_info(self, mock_print):
        """Test plugin info command."""
        from cli.main import cmd_plugin_marketplace

        mock_pkg = _make_plugin_package()
        self.mock_marketplace.get_plugin = Mock(
            return_value=MarketplaceResult(success=True, data=[mock_pkg.metadata])
        )

        args = Mock()
        args.action = "info"
        args.plugin = "test-plugin"

        result = cmd_plugin_marketplace(args)

        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('cli.main._json_output', False)
    def test_install_plugin_cli(self, mock_print):
        """Test plugin installation via CLI."""
        from cli.main import cmd_plugin_marketplace

        mock_pkg = _make_plugin_package(description="Test")
        self.mock_marketplace.get_plugin = Mock(
            return_value=MarketplaceResult(success=True, data=[mock_pkg.metadata])
        )
        self.mock_installer.install = Mock(return_value=InstallerResult(
            success=True, plugin_id="test-plugin", version="1.0.0"
        ))

        args = Mock()
        args.action = "install"
        args.plugin = "test-plugin"
        args.accept_permissions = True

        result = cmd_plugin_marketplace(args)

        self.assertEqual(result, 0)
        self.mock_installer.install.assert_called_once()

    @patch('cli.main._print')
    @patch('cli.main._json_output', False)
    def test_uninstall_plugin_cli(self, mock_print):
        """Test plugin uninstallation via CLI."""
        from cli.main import cmd_plugin_marketplace

        self.mock_installer.uninstall = Mock(return_value=InstallerResult(
            success=True, plugin_id="test-plugin"
        ))

        args = Mock()
        args.action = "uninstall"
        args.plugin = "test-plugin"

        result = cmd_plugin_marketplace(args)

        self.assertEqual(result, 0)
        self.mock_installer.uninstall.assert_called_once_with("test-plugin")

    @patch('cli.main._print')
    @patch('cli.main._json_output', False)
    def test_update_plugin_cli(self, mock_print):
        """Test plugin update via CLI."""
        from cli.main import cmd_plugin_marketplace

        self.mock_installer.update = Mock(return_value=InstallerResult(
            success=True, plugin_id="test-plugin", version="1.1.0"
        ))

        args = Mock()
        args.action = "update"
        args.plugin = "test-plugin"

        result = cmd_plugin_marketplace(args)

        self.assertEqual(result, 0)
        self.mock_installer.update.assert_called_once_with("test-plugin")


class TestPermissionConsentDialog(unittest.TestCase):
    """Test permission consent dialog."""

    @classmethod
    def setUpClass(cls):
        """Create QApplication instance once for all tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def test_dialog_creation(self):
        """Test permission consent dialog creation."""
        from ui.permission_consent_dialog import PermissionConsentDialog

        mock_pkg = _make_plugin_package(
            description="Test",
            permissions=["system:execute", "network:access", "ui:integrate"]
        )

        dialog = PermissionConsentDialog(mock_pkg)

        # Check dialog was created
        self.assertIsNotNone(dialog)
        self.assertFalse(dialog.install_btn.isEnabled())  # Should be disabled until consent

    def test_consent_enables_install(self):
        """Test that checking consent checkbox enables install button."""
        from ui.permission_consent_dialog import PermissionConsentDialog

        mock_pkg = _make_plugin_package(description="Test", permissions=["ui:integrate"])

        dialog = PermissionConsentDialog(mock_pkg)

        # Initially disabled
        self.assertFalse(dialog.install_btn.isEnabled())

        # Check consent
        dialog.consent_checkbox.setChecked(True)

        # Should now be enabled
        self.assertTrue(dialog.install_btn.isEnabled())


class TestDaemonAutoUpdate(unittest.TestCase):
    """Test daemon auto-update functionality."""

    @patch('utils.daemon.PluginInstaller')
    @patch('utils.daemon.PluginLoader')
    @patch('utils.daemon.ConfigManager')
    def test_check_plugin_updates(self, mock_config, mock_loader_cls, mock_installer_cls):
        """Test daemon checks for plugin updates."""
        from utils.daemon import Daemon

        # Mock config
        mock_config.load_config = Mock(return_value={"plugin_auto_update": True})

        # Mock loader
        mock_loader = Mock()
        mock_loader.list_plugins = Mock(return_value=[
            {"name": "test-plugin", "enabled": True}
        ])
        mock_loader_cls.return_value = mock_loader

        # Mock installer
        mock_installer = Mock()
        mock_installer.check_update = Mock(return_value=InstallerResult(
            success=True,
            plugin_id="test-plugin",
            version="1.0.0",
            data={
                "update_available": True,
                "current_version": "1.0.0",
                "new_version": "1.1.0"
            }
        ))
        mock_installer.update = Mock(return_value=InstallerResult(
            success=True,
            plugin_id="test-plugin",
            version="1.1.0"
        ))
        mock_installer_cls.return_value = mock_installer

        # Run update check
        Daemon.check_plugin_updates()

        # Verify update was called
        mock_installer.check_update.assert_called_once_with("test-plugin")
        mock_installer.update.assert_called_once_with("test-plugin")

    @patch('utils.daemon.PluginInstaller')
    @patch('utils.daemon.PluginLoader')
    @patch('utils.daemon.ConfigManager')
    def test_auto_update_disabled(self, mock_config, mock_loader_cls, mock_installer_cls):
        """Test daemon respects auto-update disabled setting."""
        from utils.daemon import Daemon

        # Mock config with auto-update disabled
        mock_config.load_config = Mock(return_value={"plugin_auto_update": False})

        mock_installer = Mock()
        mock_installer_cls.return_value = mock_installer

        # Run update check
        Daemon.check_plugin_updates()

        # Verify no update check was performed
        mock_installer.check_update.assert_not_called()

    @patch('utils.daemon.PluginInstaller')
    @patch('utils.daemon.PluginLoader')
    @patch('utils.daemon.ConfigManager')
    def test_skip_disabled_plugins(self, mock_config, mock_loader_cls, mock_installer_cls):
        """Test daemon skips disabled plugins."""
        from utils.daemon import Daemon

        mock_config.load_config = Mock(return_value={"plugin_auto_update": True})

        # Mock loader with disabled plugin
        mock_loader = Mock()
        mock_loader.list_plugins = Mock(return_value=[
            {"name": "disabled-plugin", "enabled": False}
        ])
        mock_loader_cls.return_value = mock_loader

        mock_installer = Mock()
        mock_installer_cls.return_value = mock_installer

        # Run update check
        Daemon.check_plugin_updates()

        # Verify no update check for disabled plugin
        mock_installer.check_update.assert_not_called()


class TestPluginInstallerCheckUpdate(unittest.TestCase):
    """Test PluginInstaller.check_update method."""

    @patch('utils.plugin_installer.PluginMarketplace')
    def test_check_update_available(self, mock_marketplace_cls):
        """Test checking for available update."""
        from utils.plugin_installer import PluginInstaller

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{"test-plugin": {"version": "1.0.0"}}')):

            installer = PluginInstaller()

            # Mock marketplace
            mock_meta = PluginMetadata(
                name="test-plugin",
                version="1.1.0",
                author="Author",
                description="Test",
                category="UI"
            )
            installer.marketplace.get_plugin_info = Mock(return_value=mock_meta)

            result = installer.check_update("test-plugin")

            self.assertTrue(result.success)
            self.assertTrue(result.data["update_available"])
            self.assertEqual(result.data["current_version"], "1.0.0")  # fixture-version
            self.assertEqual(result.data["new_version"], "1.1.0")

    @patch('utils.plugin_installer.PluginMarketplace')
    def test_check_update_not_installed(self, mock_marketplace_cls):
        """Test checking update for non-installed plugin."""
        from utils.plugin_installer import PluginInstaller

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{}')):

            installer = PluginInstaller()

            result = installer.check_update("non-existent")

            self.assertFalse(result.success)
            self.assertIn("not installed", result.error)


if __name__ == "__main__":
    unittest.main()
