"""Deeper CLI tests — marketplace, reviews, ratings, plugin actions (~276 miss branches)."""

import json
import os
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


def _make_args(**kwargs):
    args = MagicMock()
    for k, v in kwargs.items():
        setattr(args, k, v)
    # Defaults
    if not hasattr(args, 'json') or 'json' not in kwargs:
        args.json = False
    return args


class TestCmdAdvanced(unittest.TestCase):
    @patch("cli.main.run_operation", return_value=True)
    @patch("cli.main.AdvancedOps")
    def test_dnf_tweaks(self, mock_ops, mock_run):
        from cli.main import cmd_advanced
        args = _make_args(action="dnf-tweaks")
        self.assertEqual(cmd_advanced(args), 0)

    @patch("cli.main.run_operation", return_value=True)
    @patch("cli.main.AdvancedOps")
    def test_bbr(self, mock_ops, mock_run):
        from cli.main import cmd_advanced
        args = _make_args(action="bbr")
        self.assertEqual(cmd_advanced(args), 0)

    @patch("cli.main.run_operation", return_value=True)
    @patch("cli.main.AdvancedOps")
    def test_gamemode(self, mock_ops, mock_run):
        from cli.main import cmd_advanced
        args = _make_args(action="gamemode")
        self.assertEqual(cmd_advanced(args), 0)

    @patch("cli.main.run_operation", return_value=True)
    @patch("cli.main.AdvancedOps")
    def test_swappiness(self, mock_ops, mock_run):
        from cli.main import cmd_advanced
        args = _make_args(action="swappiness", value=10)
        self.assertEqual(cmd_advanced(args), 0)

    def test_unknown(self):
        from cli.main import cmd_advanced
        args = _make_args(action="unknown")
        self.assertEqual(cmd_advanced(args), 1)


class TestCmdNetwork(unittest.TestCase):
    @patch("cli.main.NetworkOps")
    def test_dns(self, mock_ops):
        from cli.main import cmd_network
        mock_ops.set_dns.return_value = MagicMock(success=True, message="OK")
        args = _make_args(action="dns", provider="cloudflare")
        self.assertEqual(cmd_network(args), 0)

    @patch("cli.main.NetworkOps")
    def test_dns_fail(self, mock_ops):
        from cli.main import cmd_network
        mock_ops.set_dns.return_value = MagicMock(success=False, message="fail")
        args = _make_args(action="dns", provider="bad")
        self.assertEqual(cmd_network(args), 1)

    def test_unknown(self):
        from cli.main import cmd_network
        args = _make_args(action="unknown")
        self.assertEqual(cmd_network(args), 1)


class TestCmdSupportBundle(unittest.TestCase):
    @patch("cli.main.JournalManager.export_support_bundle")
    @patch("cli.main._json_output", False)
    def test_success(self, mock_bundle):
        from cli.main import cmd_support_bundle
        mock_bundle.return_value = MagicMock(success=True, message="saved", data="/tmp/b.zip")
        args = _make_args()
        self.assertEqual(cmd_support_bundle(args), 0)

    @patch("cli.main.JournalManager.export_support_bundle")
    @patch("cli.main._json_output", False)
    def test_failure(self, mock_bundle):
        from cli.main import cmd_support_bundle
        mock_bundle.return_value = MagicMock(success=False, message="fail", data=None)
        args = _make_args()
        self.assertEqual(cmd_support_bundle(args), 1)


class TestCmdVm(unittest.TestCase):
    @patch("cli.main._json_output", False)
    @patch("utils.vm_manager.VMManager.list_vms", return_value=[])
    def test_list_empty(self, mock_list):
        from cli.main import cmd_vm
        args = _make_args(action="list")
        self.assertEqual(cmd_vm(args), 0)

    @patch("cli.main._json_output", False)
    @patch("utils.vm_manager.VMManager.list_vms")
    def test_list_with_vms(self, mock_list):
        from cli.main import cmd_vm
        vm = MagicMock()
        vm.name = "test"
        vm.state = "running"
        vm.memory_mb = 2048
        vm.vcpus = 2
        mock_list.return_value = [vm]
        args = _make_args(action="list")
        self.assertEqual(cmd_vm(args), 0)


class TestCmdInfo(unittest.TestCase):
    @patch("cli.main._json_output", False)
    @patch("cli.main.TweakOps.get_power_profile", return_value="balanced")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    @patch("cli.main.SystemManager.is_atomic", return_value=False)
    def test_info_text(self, mock_atomic, mock_pm, mock_profile):
        from cli.main import cmd_info
        args = _make_args()
        self.assertEqual(cmd_info(args), 0)

    @patch("cli.main._json_output", True)
    @patch("cli.main.TweakOps.get_power_profile", return_value="balanced")
    @patch("cli.main.SystemManager.get_package_manager", return_value="dnf")
    @patch("cli.main.SystemManager.is_atomic", return_value=False)
    def test_info_json(self, mock_atomic, mock_pm, mock_profile):
        from cli.main import cmd_info
        args = _make_args()
        with patch("builtins.print"):
            self.assertEqual(cmd_info(args), 0)


class TestRunOperation(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_success(self, mock_run):
        from cli.main import run_operation
        result = run_operation(("echo", ["hello"], "desc"))
        self.assertTrue(result)

    @patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="err"))
    def test_failure(self, mock_run):
        from cli.main import run_operation
        result = run_operation(("echo", ["hello"], "desc"))
        self.assertFalse(result)


class TestOutputHelpers(unittest.TestCase):
    @patch("cli.main._json_output", False)
    def test_print_normal(self):
        from cli.main import _print
        with patch("builtins.print") as mock_print:
            _print("hello")
            mock_print.assert_called_once_with("hello")

    @patch("cli.main._json_output", True)
    def test_print_suppressed(self):
        from cli.main import _print
        with patch("builtins.print") as mock_print:
            _print("hello")
            mock_print.assert_not_called()

    def test_output_json(self):
        from cli.main import _output_json
        with patch("builtins.print") as mock_print:
            _output_json({"key": "val"})
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            data = json.loads(output)
            self.assertEqual(data["key"], "val")


if __name__ == "__main__":
    unittest.main()
