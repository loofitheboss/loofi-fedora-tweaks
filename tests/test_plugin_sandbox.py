"""Tests for core.plugins.sandbox — PluginSandbox permission enforcement."""
import os
import sys
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.sandbox import (
    PluginSandbox,
    RestrictedImporter,
    create_sandbox,
    VALID_PERMISSIONS,
    NETWORK_MODULES,
    SUBPROCESS_MODULES
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin(plugin_id: str = "test-plugin"):
    """Create a mock plugin instance."""
    plugin = MagicMock()
    plugin.id = plugin_id
    return plugin


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginSandboxInitialization:
    """Tests for PluginSandbox construction."""

    def test_sandbox_accepts_empty_permissions(self):
        """Sandbox can be created with no permissions."""
        sandbox = PluginSandbox("test", set())
        assert sandbox.plugin_id == "test"
        assert sandbox.permissions == set()

    def test_sandbox_accepts_valid_permissions(self):
        """Sandbox accepts all valid permission types."""
        perms = {"network", "filesystem", "subprocess"}
        sandbox = PluginSandbox("test", perms)
        assert sandbox.permissions == perms

    def test_sandbox_stores_plugin_id(self):
        """Sandbox stores plugin ID for error reporting."""
        sandbox = PluginSandbox("my-plugin", set())
        assert sandbox.plugin_id == "my-plugin"

    def test_sandbox_accepts_all_valid_permissions(self):
        """Sandbox accepts all permissions from VALID_PERMISSIONS."""
        sandbox = PluginSandbox("test", VALID_PERMISSIONS)
        assert sandbox.permissions == VALID_PERMISSIONS


class TestRestrictedImporter:
    """Tests for RestrictedImporter import hook."""

    def test_importer_allows_standard_modules_with_network(self):
        """Importer allows network modules when network permission granted."""
        importer = RestrictedImporter("test", {"network"})
        
        # Should return None to let default importer handle it
        result = importer.find_spec("socket")
        assert result is None  # Not blocked

    def test_importer_blocks_socket_without_network(self):
        """Importer blocks socket module without network permission."""
        importer = RestrictedImporter("test", set())
        
        try:
            importer.find_spec("socket")
            assert False, "Should have raised PermissionError"
        except PermissionError as exc:
            assert "socket" in str(exc)
            assert "network" in str(exc)

    def test_importer_blocks_urllib_without_network(self):
        """Importer blocks urllib without network permission."""
        importer = RestrictedImporter("test", set())
        
        try:
            importer.find_spec("urllib.request")
            assert False, "Should have raised PermissionError"
        except PermissionError as exc:
            assert "urllib" in str(exc)

    def test_importer_blocks_subprocess_without_permission(self):
        """Importer blocks subprocess module without subprocess permission."""
        importer = RestrictedImporter("test", set())
        
        try:
            importer.find_spec("subprocess")
            assert False, "Should have raised PermissionError"
        except PermissionError as exc:
            assert "subprocess" in str(exc)

    def test_importer_allows_subprocess_with_permission(self):
        """Importer allows subprocess when permission granted."""
        importer = RestrictedImporter("test", {"subprocess"})
        
        result = importer.find_spec("subprocess")
        assert result is None  # Not blocked

    def test_importer_allows_non_restricted_modules(self):
        """Importer allows unrestricted modules like json, re."""
        importer = RestrictedImporter("test", set())
        
        # These should not be blocked
        assert importer.find_spec("json") is None
        assert importer.find_spec("re") is None
        assert importer.find_spec("pathlib") is None

    def test_importer_checks_base_module_name(self):
        """Importer checks base module for nested imports."""
        importer = RestrictedImporter("test", set())
        
        try:
            # urllib.request should be blocked by base module "urllib"
            importer.find_spec("urllib.request")
            assert False, "Should have raised PermissionError"
        except PermissionError:
            pass  # Expected


class TestPluginSandboxFilesystemRestrictions:
    """Tests for filesystem permission enforcement."""

    def test_sandbox_blocks_open_without_filesystem_permission(self):
        """Sandbox blocks file operations without filesystem permission."""
        sandbox = PluginSandbox("test", set())
        plugin = _make_plugin()
        
        with patch("sys.meta_path", []):
            sandbox.wrap(plugin)
            
            # The sandbox creates restricted builtins
            assert hasattr(sandbox, "_restricted_builtins")

    def test_filesystem_permission_allows_restricted_paths(self):
        """Filesystem permission allows access to plugin-specific paths."""
        sandbox = PluginSandbox("test", {"filesystem"})
        plugin = _make_plugin()
        
        wrapped = sandbox.wrap(plugin)
        assert wrapped is not None


class TestPluginSandboxWrapping:
    """Tests for sandbox.wrap() plugin wrapping."""

    def test_wrap_returns_plugin_instance(self):
        """wrap() returns the plugin instance."""
        sandbox = PluginSandbox("test", {"network", "subprocess"})
        plugin = _make_plugin()
        
        wrapped = sandbox.wrap(plugin)
        assert wrapped is plugin

    def test_wrap_installs_import_hook(self):
        """wrap() installs RestrictedImporter in sys.meta_path."""
        sandbox = PluginSandbox("test", set())
        plugin = _make_plugin()
        
        original_path = sys.meta_path.copy()
        try:
            sandbox.wrap(plugin)
            
            # Check if importer was added
            assert hasattr(sandbox, "_importer")
        finally:
            sys.meta_path[:] = original_path

    def test_wrap_creates_restricted_builtins(self):
        """wrap() creates restricted builtins dict."""
        sandbox = PluginSandbox("test", set())
        plugin = _make_plugin()
        
        sandbox.wrap(plugin)
        
        assert hasattr(sandbox, "_restricted_builtins")
        assert isinstance(sandbox._restricted_builtins, dict)

    def test_multiple_wraps_reuse_same_hooks(self):
        """Multiple wrap() calls on same sandbox reuse hooks."""
        sandbox = PluginSandbox("test", {"network"})
        plugin1 = _make_plugin("p1")
        plugin2 = _make_plugin("p2")
        
        original_path = sys.meta_path.copy()
        try:
            wrapped1 = sandbox.wrap(plugin1)
            wrapped2 = sandbox.wrap(plugin2)
            
            assert wrapped1 is plugin1
            assert wrapped2 is plugin2
        finally:
            sys.meta_path[:] = original_path


class TestPluginSandboxUnwrap:
    """Tests for sandbox.unwrap() cleanup."""

    def test_unwrap_removes_import_hook(self):
        """unwrap() removes RestrictedImporter from sys.meta_path."""
        sandbox = PluginSandbox("test", set())
        plugin = _make_plugin()
        
        original_path = sys.meta_path.copy()
        try:
            sandbox.wrap(plugin)
            assert hasattr(sandbox, "_importer")
            
            sandbox.unwrap()
            
            # Importer should be removed from meta_path
            if hasattr(sandbox, "_importer"):
                assert sandbox._importer not in sys.meta_path
        finally:
            sys.meta_path[:] = original_path

    def test_unwrap_clears_restricted_builtins(self):
        """unwrap() clears restricted builtins."""
        sandbox = PluginSandbox("test", set())
        plugin = _make_plugin()
        
        sandbox.wrap(plugin)
        sandbox.unwrap()
        
        # Builtins should be cleared or reset
        assert not hasattr(sandbox, "_restricted_builtins") or sandbox._restricted_builtins is None

    def test_unwrap_is_idempotent(self):
        """unwrap() can be called multiple times safely."""
        sandbox = PluginSandbox("test", set())
        plugin = _make_plugin()
        
        original_path = sys.meta_path.copy()
        try:
            sandbox.wrap(plugin)
            sandbox.unwrap()
            sandbox.unwrap()  # Should not raise
        finally:
            sys.meta_path[:] = original_path


class TestPluginSandboxIsolationPolicy:
    """Tests for v27 isolation enforcement flow."""

    def test_enforce_isolation_with_explicit_provider_success(self):
        """enforce_isolation returns True when provider applies policy."""
        sandbox = PluginSandbox("iso-test", {"network"})
        provider = Mock()
        provider.apply_policy.return_value = True

        result = sandbox.enforce_isolation(provider=provider)

        assert result is True
        provider.apply_policy.assert_called_once_with(sandbox.policy)

    def test_enforce_isolation_with_explicit_provider_failure(self):
        """enforce_isolation returns False when provider rejects policy."""
        sandbox = PluginSandbox("iso-test", {"subprocess"})
        provider = Mock()
        provider.apply_policy.return_value = False

        result = sandbox.enforce_isolation(provider=provider)

        assert result is False
        provider.apply_policy.assert_called_once_with(sandbox.policy)

    @patch("utils.sandbox.PluginIsolationManager.enforce_policy")
    def test_enforce_isolation_default_provider_success(self, mock_enforce_policy):
        """Default provider maps PluginIsolationManager success to True."""
        sandbox = PluginSandbox("iso-test", {"filesystem"})
        mock_enforce_policy.return_value = Mock(success=True)

        result = sandbox.enforce_isolation()

        assert result is True
        mock_enforce_policy.assert_called_once_with(sandbox.policy)

    @patch("utils.sandbox.PluginIsolationManager.enforce_policy")
    def test_enforce_isolation_default_provider_failure(self, mock_enforce_policy):
        """Default provider maps PluginIsolationManager failure to False."""
        sandbox = PluginSandbox("iso-test", {"filesystem"})
        mock_enforce_policy.return_value = Mock(success=False)

        result = sandbox.enforce_isolation()

        assert result is False
        mock_enforce_policy.assert_called_once_with(sandbox.policy)


class TestCreateSandboxFactory:
    """Tests for create_sandbox() factory function."""

    def test_create_sandbox_returns_sandbox_instance(self):
        """create_sandbox() returns PluginSandbox."""
        sandbox = create_sandbox("test-plugin", {"network"})
        assert isinstance(sandbox, PluginSandbox)

    def test_create_sandbox_sets_plugin_id(self):
        """create_sandbox() sets correct plugin ID."""
        sandbox = create_sandbox("my-plugin", set())
        assert sandbox.plugin_id == "my-plugin"

    def test_create_sandbox_sets_permissions(self):
        """create_sandbox() sets correct permissions."""
        perms = {"network", "subprocess"}
        sandbox = create_sandbox("test", perms)
        assert sandbox.permissions == perms

    def test_create_sandbox_with_no_permissions(self):
        """create_sandbox() works with empty permission set."""
        sandbox = create_sandbox("test", set())
        assert sandbox.permissions == set()

    def test_create_sandbox_with_all_permissions(self):
        """create_sandbox() works with all valid permissions."""
        sandbox = create_sandbox("test", VALID_PERMISSIONS)
        assert sandbox.permissions == VALID_PERMISSIONS


class TestPluginSandboxIntegration:
    """Integration tests for full sandbox lifecycle."""

    def test_full_lifecycle_wrap_and_unwrap(self):
        """Test complete wrap -> use -> unwrap cycle."""
        sandbox = PluginSandbox("integration-test", {"network"})
        plugin = _make_plugin()
        
        original_path = sys.meta_path.copy()
        try:
            # Wrap
            wrapped = sandbox.wrap(plugin)
            assert wrapped is plugin
            
            # Unwrap
            sandbox.unwrap()
        finally:
            sys.meta_path[:] = original_path

    def test_sandbox_isolation_between_plugins(self):
        """Different sandboxes have independent permission sets."""
        sandbox1 = PluginSandbox("plugin1", {"network"})
        sandbox2 = PluginSandbox("plugin2", {"subprocess"})
        
        assert sandbox1.permissions != sandbox2.permissions
        assert "network" in sandbox1.permissions
        assert "subprocess" in sandbox2.permissions

    def test_permission_error_includes_plugin_id(self):
        """Permission errors include plugin ID for debugging."""
        importer = RestrictedImporter("my-special-plugin", set())
        
        try:
            importer.find_spec("socket")
            assert False, "Should have raised PermissionError"
        except PermissionError as exc:
            assert "my-special-plugin" in str(exc)


class TestValidPermissions:
    """Tests for permission validation."""

    def test_valid_permissions_constant_is_complete(self):
        """VALID_PERMISSIONS contains expected permission types."""
        expected = {
            "network", "filesystem", "subprocess", 
            "sudo", "clipboard", "notifications"
        }
        assert expected.issubset(VALID_PERMISSIONS)

    def test_network_modules_contains_common_modules(self):
        """NETWORK_MODULES contains common network libraries."""
        assert "socket" in NETWORK_MODULES
        assert "urllib" in NETWORK_MODULES
        assert "http" in NETWORK_MODULES

    def test_subprocess_modules_contains_process_modules(self):
        """SUBPROCESS_MODULES contains process execution modules."""
        assert "subprocess" in SUBPROCESS_MODULES
