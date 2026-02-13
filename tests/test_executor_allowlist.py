"""
Tests for API executor command allowlist validation (Security Fix).
Verifies that only allowed commands can be executed via the API.
"""
from __future__ import annotations

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from api.routes.executor import _validate_command, ALLOWED_COMMANDS, SHELL_METACHARACTERS


class TestCommandValidation(unittest.TestCase):
    """Tests for command validation against allowlist."""
    
    def test_allowed_command_dnf(self):
        """Test that dnf command is allowed."""
        is_valid, resolved, error = _validate_command("dnf", ["check-update"])
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "/usr/bin/dnf")
        self.assertEqual(error, "")
    
    def test_allowed_command_systemctl(self):
        """Test that systemctl command is allowed."""
        is_valid, resolved, error = _validate_command("systemctl", ["status", "sshd"])
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "/usr/bin/systemctl")
        self.assertEqual(error, "")
    
    def test_allowed_command_rpm_ostree(self):
        """Test that rpm-ostree command is allowed."""
        is_valid, resolved, error = _validate_command("rpm-ostree", ["status"])
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "/usr/bin/rpm-ostree")
        self.assertEqual(error, "")
    
    def test_disallowed_command_bash(self):
        """Test that arbitrary command (bash) is rejected."""
        is_valid, resolved, error = _validate_command("bash", ["-c", "echo test"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("not allowed", error.lower())
        self.assertIn("bash", error)
    
    def test_disallowed_command_rm(self):
        """Test that dangerous command (rm) is rejected."""
        is_valid, resolved, error = _validate_command("rm", ["-rf", "/tmp/test"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("not allowed", error.lower())
    
    def test_disallowed_command_arbitrary(self):
        """Test that arbitrary unknown command is rejected."""
        is_valid, resolved, error = _validate_command("malicious_tool", ["arg1"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("not allowed", error.lower())
    
    def test_arg_with_semicolon(self):
        """Test that args containing semicolon are rejected."""
        is_valid, resolved, error = _validate_command("dnf", ["install", "pkg; rm -rf /"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_arg_with_pipe(self):
        """Test that args containing pipe are rejected."""
        is_valid, resolved, error = _validate_command("systemctl", ["status | grep active"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_arg_with_ampersand(self):
        """Test that args containing ampersand are rejected."""
        is_valid, resolved, error = _validate_command("dnf", ["update", "&"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_arg_with_dollar_sign(self):
        """Test that args containing dollar sign are rejected."""
        is_valid, resolved, error = _validate_command("systemctl", ["restart", "$SERVICE"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_arg_with_backtick(self):
        """Test that args containing backtick are rejected."""
        is_valid, resolved, error = _validate_command("dnf", ["install", "`whoami`"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_arg_with_redirect(self):
        """Test that args containing redirect operators are rejected."""
        is_valid, resolved, error = _validate_command("dnf", ["list", ">", "/tmp/output"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_arg_with_newline(self):
        """Test that args containing newline are rejected."""
        is_valid, resolved, error = _validate_command("systemctl", ["status\nrm -rf /"])
        self.assertFalse(is_valid)
        self.assertEqual(resolved, "")
        self.assertIn("metacharacters", error.lower())
    
    def test_safe_args_with_hyphens(self):
        """Test that safe args with hyphens are allowed."""
        is_valid, resolved, error = _validate_command("dnf", ["install", "-y", "package-name"])
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "/usr/bin/dnf")
        self.assertEqual(error, "")
    
    def test_safe_args_with_equals(self):
        """Test that safe args with equals signs are allowed."""
        is_valid, resolved, error = _validate_command("systemctl", ["set-property", "foo.service", "CPUQuota=50%"])
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "/usr/bin/systemctl")
        self.assertEqual(error, "")
    
    def test_empty_args(self):
        """Test that commands with no args are allowed."""
        is_valid, resolved, error = _validate_command("dnf", [])
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "/usr/bin/dnf")
        self.assertEqual(error, "")
    
    def test_all_critical_commands_present(self):
        """Test that all critical system commands are in allowlist."""
        critical_commands = [
            "dnf", "rpm-ostree", "flatpak", "systemctl", "journalctl",
            "fwupdmgr", "cpupower", "grubby", "sysctl", "firewall-cmd"
        ]
        for cmd in critical_commands:
            self.assertIn(cmd, ALLOWED_COMMANDS, f"Critical command {cmd} missing from allowlist")
    
    def test_shell_metacharacters_defined(self):
        """Test that shell metacharacters set is properly defined."""
        expected_chars = {';', '|', '&', '$', '`', '(', ')', '{', '}', '>', '<', '\n', '\r'}
        self.assertEqual(SHELL_METACHARACTERS, expected_chars)


class TestExecutorAPIIntegration(unittest.TestCase):
    """Integration tests for the executor API endpoint."""
    
    @patch('api.routes.executor.ActionExecutor.run')
    def test_allowed_command_executes(self, mock_run):
        """Test that allowed commands execute successfully."""
        from api.routes.executor import execute_action, ActionPayload
        from utils.action_result import ActionResult
        
        # Mock successful execution
        mock_result = ActionResult.ok("Success", exit_code=0)
        mock_run.return_value = mock_result
        
        # Create payload with allowed command
        payload = ActionPayload(
            command="dnf",
            args=["check-update"],
            preview=False,
            pkexec=False,
        )
        
        # Mock auth (bypass authentication for test)
        with patch('api.routes.executor.AuthManager.verify_bearer_token', return_value="valid_token"):
            response = execute_action(payload, _auth="valid_token")
        
        # Verify execution was attempted with resolved path
        self.assertTrue(mock_run.called)
        # Should be called with resolved path
        call_args = mock_run.call_args_list[0][0]
        self.assertEqual(call_args[0], "/usr/bin/dnf")
    
    @patch('api.routes.executor.ActionExecutor.run')
    def test_disallowed_command_blocked(self, mock_run):
        """Test that disallowed commands are blocked before execution."""
        from api.routes.executor import execute_action, ActionPayload
        
        # Create payload with disallowed command
        payload = ActionPayload(
            command="bash",
            args=["-c", "rm -rf /"],
            preview=False,
            pkexec=False,
        )
        
        # Mock auth
        with patch('api.routes.executor.AuthManager.verify_bearer_token', return_value="valid_token"):
            response = execute_action(payload, _auth="valid_token")
        
        # Verify execution was NOT attempted
        mock_run.assert_not_called()
        
        # Verify error response
        self.assertIn("not allowed", response.result["message"].lower())
        self.assertFalse(response.result["success"])
    
    @patch('api.routes.executor.ActionExecutor.run')
    def test_shell_metacharacters_blocked(self, mock_run):
        """Test that args with shell metacharacters are blocked."""
        from api.routes.executor import execute_action, ActionPayload
        
        # Create payload with shell injection attempt
        payload = ActionPayload(
            command="dnf",
            args=["install", "pkg; rm -rf /"],
            preview=False,
            pkexec=False,
        )
        
        # Mock auth
        with patch('api.routes.executor.AuthManager.verify_bearer_token', return_value="valid_token"):
            response = execute_action(payload, _auth="valid_token")
        
        # Verify execution was NOT attempted
        mock_run.assert_not_called()
        
        # Verify error response
        self.assertIn("metacharacters", response.result["message"].lower())
        self.assertFalse(response.result["success"])


if __name__ == '__main__':
    unittest.main()
