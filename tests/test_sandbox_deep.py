"""
Deep-branch tests for core/plugins/sandbox.py.
Focuses on wrap_subprocess privileged-command checks, wrap_open edge cases,
wrap_plugin/unwrap_plugin with real module patching, and enforce_isolation.
"""

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from core.plugins.sandbox import (
    IsolationMode,
    PluginIsolationPolicy,
    PluginSandbox,
    RestrictedImporter,
)


class TestRestrictedImporterDeep(unittest.TestCase):
    """Extra branches not in test_plugin_sandbox.py."""

    def test_block_requests_without_network(self):
        imp = RestrictedImporter("p", set())
        with self.assertRaises(PermissionError):
            imp.find_spec("requests")

    def test_block_aiohttp_without_network(self):
        imp = RestrictedImporter("p", set())
        with self.assertRaises(PermissionError):
            imp.find_spec("aiohttp")

    def test_block_httpx_without_network(self):
        imp = RestrictedImporter("p", set())
        with self.assertRaises(PermissionError):
            imp.find_spec("httpx")

    def test_allow_with_both_permissions(self):
        imp = RestrictedImporter("p", {"network", "subprocess"})
        self.assertIsNone(imp.find_spec("socket"))
        self.assertIsNone(imp.find_spec("subprocess"))

    def test_block_os_system_without_subprocess(self):
        imp = RestrictedImporter("p", set())
        with self.assertRaises(PermissionError):
            imp.find_spec("os.system")

    def test_find_spec_with_extra_args(self):
        """find_spec accepts path and target args."""
        imp = RestrictedImporter("p", {"network"})
        self.assertIsNone(imp.find_spec("json", path=None, target=None))


class TestSandboxWrapSubprocessDeep(unittest.TestCase):

    def test_check_call_blocked_without_permission(self):
        sb = PluginSandbox("p", [])
        mock_sp = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.check_call(["ls"])

    def test_check_output_blocked_without_permission(self):
        sb = PluginSandbox("p", [])
        mock_sp = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.check_output(["whoami"])

    def test_popen_blocked_without_permission(self):
        sb = PluginSandbox("p", [])
        mock_sp = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.Popen(["cat"])

    def test_allowed_non_privileged_commands(self):
        """With subprocess but not sudo, normal commands pass through."""
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock(return_value="ok")
        mock_sp.Popen = MagicMock(return_value="ok")
        mock_sp.check_call = MagicMock(return_value=0)
        mock_sp.check_output = MagicMock(return_value=b"output")
        wrapped = sb.wrap_subprocess(mock_sp)
        wrapped.run(["ls"])
        wrapped.check_call(["echo", "hi"])
        wrapped.check_output(["date"])

    def test_block_doas_without_sudo(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock()
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.run(["doas", "something"])

    def test_block_su_without_sudo(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock()
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.Popen(["su", "-c", "whoami"])

    def test_popen_privileged_blocked(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock()
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.Popen(["sudo", "rm", "-rf", "/"])

    def test_check_call_privileged_blocked(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock()
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.check_call(["pkexec", "bash"])

    def test_check_output_privileged_blocked(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock()
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        with self.assertRaises(PermissionError):
            wrapped.check_output(["sudo", "cat", "/etc/shadow"])

    def test_empty_command(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock(return_value="ok")
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        # Empty string command should not raise
        wrapped.run("")

    def test_string_non_privileged(self):
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock(return_value="ok")
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        wrapped.run("ls -la /tmp")

    def test_non_string_non_list_command(self):
        """Numeric command => binary becomes empty string."""
        sb = PluginSandbox("p", ["subprocess"])
        mock_sp = types.ModuleType("subprocess")
        mock_sp.run = MagicMock(return_value="ok")
        mock_sp.Popen = MagicMock()
        mock_sp.check_call = MagicMock()
        mock_sp.check_output = MagicMock()
        wrapped = sb.wrap_subprocess(mock_sp)
        wrapped.run(42)  # Should not raise (binary == "")


class TestWrapOpenDeep(unittest.TestCase):

    def test_exclusive_create_blocked(self):
        sb = PluginSandbox("p", ["filesystem"])
        original = MagicMock()
        wrapped = sb.wrap_open(original)
        with self.assertRaises(PermissionError):
            wrapped("/etc/test", "x")

    def test_read_binary_allowed(self):
        sb = PluginSandbox("p", [])
        original = MagicMock(return_value="handle")
        wrapped = sb.wrap_open(original)
        wrapped("/etc/hostname", "rb")
        original.assert_called_once()


class TestWrapPluginUnwrapPlugin(unittest.TestCase):

    def test_wrap_plugin_with_module(self):
        sb = PluginSandbox("p", ["filesystem"])
        mod = types.ModuleType("test_plugin_mod")
        sys.modules["test_plugin_mod"] = mod
        try:
            plugin = MagicMock()
            plugin.__module__ = "test_plugin_mod"
            result = sb.wrap_plugin(plugin)
            self.assertIs(result, plugin)
            # Module should have wrapped open
            self.assertTrue(hasattr(mod, "_sandbox_original_open"))
        finally:
            sb.unwrap_plugin(plugin)
            if "test_plugin_mod" in sys.modules:
                del sys.modules["test_plugin_mod"]

    def test_wrap_plugin_exception_safe(self):
        """wrap_plugin should not raise even on internal errors."""
        sb = PluginSandbox("p", [])
        plugin = MagicMock()
        plugin.__module__ = "nonexistent_module_xyz"
        result = sb.wrap_plugin(plugin)
        self.assertIs(result, plugin)

    def test_unwrap_plugin_no_module(self):
        """unwrap_plugin should handle missing module gracefully."""
        sb = PluginSandbox("p", [])
        sb.install()
        plugin = MagicMock()
        plugin.__module__ = "nonexistent_xyz"
        sb.unwrap_plugin(plugin)  # Should not raise


class TestEnforceIsolationDeep(unittest.TestCase):

    def test_with_custom_policy(self):
        sb = PluginSandbox("p", [])
        custom = PluginIsolationPolicy(
            plugin_id="p", mode=IsolationMode.OS,
            allow_network=True,
        )
        provider = MagicMock()
        provider.apply_policy.return_value = True
        self.assertTrue(sb.enforce_isolation(provider=provider, policy=custom))
        provider.apply_policy.assert_called_once_with(custom)

    @patch("utils.sandbox.PluginIsolationManager.enforce_policy")
    def test_default_provider(self, mock_enforce):
        mock_enforce.return_value = MagicMock(success=True)
        sb = PluginSandbox("p", [])
        self.assertTrue(sb.enforce_isolation())

    @patch("utils.sandbox.PluginIsolationManager.enforce_policy")
    def test_default_provider_failure(self, mock_enforce):
        mock_enforce.return_value = MagicMock(success=False)
        sb = PluginSandbox("p", [])
        self.assertFalse(sb.enforce_isolation())


class TestValidatePathEdge(unittest.TestCase):

    def test_oserror_returns_false(self):
        sb = PluginSandbox("p", ["filesystem"])
        with patch.object(Path, "resolve", side_effect=OSError("broken")):
            self.assertFalse(sb.validate_path(Path("/broken")))


if __name__ == "__main__":
    unittest.main()
