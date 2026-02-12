"""Tests for CLI plugin-marketplace commands."""
import os
import sys
import json
from unittest.mock import MagicMock, Mock, patch
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from cli.main import cmd_plugin_marketplace
from utils.plugin_marketplace import PluginMetadata, MarketplaceResult
from utils.plugin_installer import InstallerResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin_metadata(plugin_id: str = "test-plugin") -> PluginMetadata:
    """Create mock PluginMetadata."""
    return PluginMetadata(
        id=plugin_id,
        name=plugin_id.replace("-", " ").title(),
        description=f"Description for {plugin_id}",
        version="1.0.0",
        author="Test Author",
        category="Utility",
        icon="🔌",
        download_url=f"https://example.com/{plugin_id}.tar.gz",
        checksum_sha256="a" * 64,
        featured=False,
        tags=["test"],
        requires=[],
        homepage="https://example.com",
        license="MIT"
    )


def _make_args(action: str, **kwargs):
    """Create mock argparse Namespace."""
    args = {
        'action': action,
        'query': None,
        'category': None,
        'plugin_id': None,
        'json': False,
        'accept_permissions': False,
        **kwargs
    }
    return type('Args', (), args)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCLIMarketplaceSearch:
    """Tests for 'search' action."""

    @patch('cli.main.PluginMarketplace')
    def test_search_displays_results(self, mock_marketplace_class):
        """search command displays plugin results."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        
        plugins = [
            _make_plugin_metadata("plugin-1"),
            _make_plugin_metadata("plugin-2")
        ]
        mock_mp.search.return_value = MarketplaceResult(success=True, data=plugins)
        
        args = _make_args('search', query="test")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "plugin-1" in output or "Plugin 1" in output
            assert "plugin-2" in output or "Plugin 2" in output

    @patch('cli.main.PluginMarketplace')
    def test_search_json_output(self, mock_marketplace_class):
        """search with --json flag outputs JSON."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        
        plugins = [_make_plugin_metadata("test-plugin")]
        mock_mp.search.return_value = MarketplaceResult(success=True, data=plugins)
        
        args = _make_args('search', query="test", json=True)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            # Should be valid JSON
            try:
                data = json.loads(output)
                assert isinstance(data, (list, dict))
            except json.JSONDecodeError:
                assert False, "Output is not valid JSON"

    @patch('cli.main.PluginMarketplace')
    def test_search_with_category_filter(self, mock_marketplace_class):
        """search respects category filter."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.search.return_value = MarketplaceResult(success=True, data=[])
        
        args = _make_args('search', query="test", category="Security")
        
        cmd_plugin_marketplace(args)
        
        # Verify search was called with category
        mock_mp.search.assert_called_once()
        call_kwargs = mock_mp.search.call_args[1]
        assert call_kwargs.get('category') == "Security"

    @patch('cli.main.PluginMarketplace')
    def test_search_handles_no_results(self, mock_marketplace_class):
        """search handles empty results gracefully."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.search.return_value = MarketplaceResult(success=True, data=[])
        
        args = _make_args('search', query="nonexistent")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "no" in output.lower() or "found" in output.lower() or len(output.strip()) == 0

    @patch('cli.main.PluginMarketplace')
    def test_search_handles_api_error(self, mock_marketplace_class):
        """search handles marketplace API errors."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.search.return_value = MarketplaceResult(
            success=False,
            error="Network error"
        )
        
        args = _make_args('search', query="test")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            cmd_plugin_marketplace(args)
            output = mock_stderr.getvalue()
            
            assert "error" in output.lower() or "failed" in output.lower()


class TestCLIMarketplaceInfo:
    """Tests for 'info' action."""

    @patch('cli.main.PluginMarketplace')
    def test_info_displays_plugin_details(self, mock_marketplace_class):
        """info command displays detailed plugin information."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        
        plugin = _make_plugin_metadata("my-plugin")
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        
        args = _make_args('info', plugin_id="my-plugin")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "my-plugin" in output or "My Plugin" in output
            assert "1.0.0" in output  # Version
            assert "Test Author" in output  # Author

    @patch('cli.main.PluginMarketplace')
    def test_info_json_output(self, mock_marketplace_class):
        """info with --json outputs JSON."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        
        plugin = _make_plugin_metadata("test-plugin")
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        
        args = _make_args('info', plugin_id="test-plugin", json=True)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            data = json.loads(output)
            assert data['id'] == "test-plugin"
            assert data['version'] == "1.0.0"

    @patch('cli.main.PluginMarketplace')
    def test_info_plugin_not_found(self, mock_marketplace_class):
        """info handles plugin not found."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.get_plugin.return_value = MarketplaceResult(
            success=False,
            error="Plugin not found"
        )
        
        args = _make_args('info', plugin_id="nonexistent")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            cmd_plugin_marketplace(args)
            output = mock_stderr.getvalue()
            
            assert "not found" in output.lower() or "error" in output.lower()


class TestCLIMarketplaceInstall:
    """Tests for 'install' action."""

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_install_successful(self, mock_marketplace_class, mock_installer_class):
        """install command installs plugin successfully."""
        # Mock marketplace
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        plugin = _make_plugin_metadata("test-plugin")
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        
        # Mock installer
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.install.return_value = InstallerResult(
            success=True,
            plugin_id="test-plugin",
            version="1.0.0"
        )
        
        args = _make_args('install', plugin_id="test-plugin", accept_permissions=True)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "success" in output.lower() or "installed" in output.lower()

    @patch('cli.main.PluginMarketplace')
    def test_install_requires_accept_permissions_flag(self, mock_marketplace_class):
        """install without --accept-permissions prompts or fails."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        plugin = _make_plugin_metadata("test-plugin")
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        
        args = _make_args('install', plugin_id="test-plugin", accept_permissions=False)
        
        # Without --accept-permissions, should prompt or fail
        with patch('sys.stdout', new_callable=StringIO):
            with patch('builtins.input', return_value='n'):  # Decline consent
                cmd_plugin_marketplace(args)
                # Should not proceed with installation

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_install_handles_failure(self, mock_marketplace_class, mock_installer_class):
        """install handles installation failures."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        plugin = _make_plugin_metadata("test-plugin")
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.install.return_value = InstallerResult(
            success=False,
            plugin_id="test-plugin",
            error="Download failed"
        )
        
        args = _make_args('install', plugin_id="test-plugin", accept_permissions=True)
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            cmd_plugin_marketplace(args)
            output = mock_stderr.getvalue()
            
            assert "error" in output.lower() or "failed" in output.lower()


class TestCLIMarketplaceUninstall:
    """Tests for 'uninstall' action."""

    @patch('cli.main.PluginInstaller')
    def test_uninstall_successful(self, mock_installer_class):
        """uninstall command removes plugin."""
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.uninstall.return_value = InstallerResult(
            success=True,
            plugin_id="test-plugin"
        )
        
        args = _make_args('uninstall', plugin_id="test-plugin")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "success" in output.lower() or "uninstalled" in output.lower()

    @patch('cli.main.PluginInstaller')
    def test_uninstall_plugin_not_found(self, mock_installer_class):
        """uninstall handles plugin not installed."""
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.uninstall.return_value = InstallerResult(
            success=False,
            plugin_id="nonexistent",
            error="Plugin not found"
        )
        
        args = _make_args('uninstall', plugin_id="nonexistent")
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            cmd_plugin_marketplace(args)
            output = mock_stderr.getvalue()
            
            assert "not found" in output.lower() or "error" in output.lower()


class TestCLIMarketplaceUpdate:
    """Tests for 'update' action."""

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_update_successful(self, mock_marketplace_class, mock_installer_class):
        """update command updates plugin."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        plugin = _make_plugin_metadata("test-plugin")
        plugin.version = "2.0.0"
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.update.return_value = InstallerResult(
            success=True,
            plugin_id="test-plugin",
            version="2.0.0"
        )
        
        args = _make_args('update', plugin_id="test-plugin")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "success" in output.lower() or "updated" in output.lower()

    @patch('cli.main.PluginInstaller')
    def test_update_no_update_available(self, mock_installer_class):
        """update handles no update available."""
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.check_update.return_value = InstallerResult(
            success=True,
            plugin_id="test-plugin",
            data={"update_available": False}
        )
        
        args = _make_args('update', plugin_id="test-plugin")
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "up to date" in output.lower() or "no update" in output.lower()


class TestCLIMarketplaceListInstalled:
    """Tests for 'list-installed' action."""

    @patch('cli.main.PluginInstaller')
    def test_list_installed_displays_plugins(self, mock_installer_class):
        """list-installed displays installed plugins."""
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        
        plugins = [
            {"id": "plugin-1", "name": "Plugin 1", "version": "1.0.0"},
            {"id": "plugin-2", "name": "Plugin 2", "version": "2.0.0"}
        ]
        mock_installer.list_installed.return_value = InstallerResult(
            success=True,
            plugin_id="",
            data=plugins
        )
        
        args = _make_args('list-installed')
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "plugin-1" in output or "Plugin 1" in output
            assert "plugin-2" in output or "Plugin 2" in output

    @patch('cli.main.PluginInstaller')
    def test_list_installed_json_output(self, mock_installer_class):
        """list-installed with --json outputs JSON."""
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.list_installed.return_value = InstallerResult(
            success=True,
            plugin_id="",
            data=[{"id": "test", "name": "Test", "version": "1.0"}]
        )
        
        args = _make_args('list-installed', json=True)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            data = json.loads(output)
            assert isinstance(data, list)
            assert len(data) == 1

    @patch('cli.main.PluginInstaller')
    def test_list_installed_no_plugins(self, mock_installer_class):
        """list-installed handles no plugins installed."""
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        mock_installer.list_installed.return_value = InstallerResult(
            success=True,
            plugin_id="",
            data=[]
        )
        
        args = _make_args('list-installed')
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()
            
            assert "no plugins" in output.lower() or "none" in output.lower()


class TestCLIMarketplaceReviews:
    """Tests for 'reviews' and 'review-submit' actions."""

    @patch('cli.main.PluginMarketplace')
    def test_reviews_plain_output_success(self, mock_marketplace_class):
        """reviews prints human output for fetched reviews."""
        from utils.plugin_marketplace import MarketplaceReview

        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.fetch_reviews.return_value = MarketplaceResult(
            success=True,
            data=[
                MarketplaceReview(
                    plugin_id="test-plugin",
                    reviewer="Alice",
                    rating=5,
                    title="Great",
                    comment="Works perfectly",
                    created_at="2026-01-01T00:00:00Z",
                )
            ],
        )

        args = _make_args('reviews', plugin_id="test-plugin", limit=10, offset=0)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()

            assert exit_code == 0
            assert "Alice" in output
            assert "5/5" in output
            assert "Works perfectly" in output

    @patch('cli.main.PluginMarketplace')
    def test_reviews_json_output_success(self, mock_marketplace_class):
        """reviews with --json outputs expected JSON envelope."""
        from utils.plugin_marketplace import MarketplaceReview

        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.fetch_reviews.return_value = MarketplaceResult(
            success=True,
            data=[
                MarketplaceReview(
                    plugin_id="test-plugin",
                    reviewer="Alice",
                    rating=4,
                    title="Solid",
                    comment="Nice plugin",
                    created_at="2026-01-01T00:00:00Z",
                )
            ],
        )

        args = _make_args('reviews', plugin_id="test-plugin", limit=20, offset=0, json=True)

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = cmd_plugin_marketplace(args)
            payload = json.loads(mock_stdout.getvalue())

            assert exit_code == 0
            assert payload["plugin_id"] == "test-plugin"
            assert payload["count"] == 1
            assert payload["reviews"][0]["reviewer"] == "Alice"
            assert payload["reviews"][0]["rating"] == 4

    @patch('cli.main.PluginMarketplace')
    def test_reviews_error_output(self, mock_marketplace_class):
        """reviews returns non-zero and prints errors to stderr."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.fetch_reviews.return_value = MarketplaceResult(
            success=False,
            error="Review validation failed",
        )

        args = _make_args('reviews', plugin_id="test-plugin", limit=0, offset=0)

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            exit_code = cmd_plugin_marketplace(args)
            output = mock_stderr.getvalue()

            assert exit_code == 1
            assert "Review validation failed" in output

    @patch('cli.main.PluginMarketplace')
    def test_review_submit_plain_output_success(self, mock_marketplace_class):
        """review-submit prints success in plain mode."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.submit_review.return_value = MarketplaceResult(
            success=True,
            data={"id": "rev-1"},
        )

        args = _make_args(
            'review-submit',
            plugin_id="test-plugin",
            reviewer="Alice",
            rating=5,
            title="Great",
            comment="Loved it",
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = cmd_plugin_marketplace(args)
            output = mock_stdout.getvalue()

            assert exit_code == 0
            assert "Review submitted" in output
            mock_mp.submit_review.assert_called_once()

    @patch('cli.main.PluginMarketplace')
    def test_review_submit_json_output_success(self, mock_marketplace_class):
        """review-submit with --json outputs status + payload."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.submit_review.return_value = MarketplaceResult(
            success=True,
            data={"id": "rev-1", "rating": 5},
        )

        args = _make_args(
            'review-submit',
            plugin_id="test-plugin",
            reviewer="Alice",
            rating=5,
            title="Great",
            comment="Loved it",
            json=True,
        )

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = cmd_plugin_marketplace(args)
            payload = json.loads(mock_stdout.getvalue())

            assert exit_code == 0
            assert payload["status"] == "success"
            assert payload["plugin_id"] == "test-plugin"
            assert payload["review"]["id"] == "rev-1"

    @patch('cli.main.PluginMarketplace')
    def test_review_submit_error_output(self, mock_marketplace_class):
        """review-submit returns non-zero and prints validation errors."""
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_mp.submit_review.return_value = MarketplaceResult(
            success=False,
            error="Rating must be between 1 and 5",
        )

        args = _make_args(
            'review-submit',
            plugin_id="test-plugin",
            reviewer="Alice",
            rating=8,
        )

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            exit_code = cmd_plugin_marketplace(args)
            output = mock_stderr.getvalue()

            assert exit_code == 1
            assert "Rating must be between 1 and 5" in output


class TestCLIMarketplaceIntegration:
    """Integration tests for CLI marketplace workflow."""

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_full_cli_workflow(self, mock_marketplace_class, mock_installer_class):
        """Test complete search -> info -> install workflow."""
        # Setup mocks
        mock_mp = MagicMock()
        mock_marketplace_class.return_value = mock_mp
        mock_installer = MagicMock()
        mock_installer_class.return_value = mock_installer
        
        plugin = _make_plugin_metadata("workflow-plugin")
        mock_mp.search.return_value = MarketplaceResult(success=True, data=[plugin])
        mock_mp.get_plugin.return_value = MarketplaceResult(success=True, data=plugin)
        mock_installer.install.return_value = InstallerResult(
            success=True,
            plugin_id="workflow-plugin",
            version="1.0.0"
        )
        
        # Search
        search_args = _make_args('search', query="workflow")
        with patch('sys.stdout', new_callable=StringIO):
            cmd_plugin_marketplace(search_args)
        
        # Info
        info_args = _make_args('info', plugin_id="workflow-plugin")
        with patch('sys.stdout', new_callable=StringIO):
            cmd_plugin_marketplace(info_args)
        
        # Install
        install_args = _make_args('install', plugin_id="workflow-plugin", accept_permissions=True)
        with patch('sys.stdout', new_callable=StringIO):
            cmd_plugin_marketplace(install_args)
        
        # Verify install was called
        mock_installer.install.assert_called_once()
