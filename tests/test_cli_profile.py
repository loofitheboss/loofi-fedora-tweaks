"""Tests for CLI profile import/export extensions (v24.0)."""

import argparse
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

import cli.main as cli_main
from utils.containers import Result


class TestCLIProfileCommands(unittest.TestCase):
    """Tests for cmd_profile action routing and exit codes."""

    def setUp(self):
        cli_main._json_output = False

    @patch('cli.main.ProfileManager.export_profile_json')
    def test_export_profile_success(self, mock_export):
        from cli.main import cmd_profile
        mock_export.return_value = Result(True, "ok", {})
        args = argparse.Namespace(action="export", name="gaming", path="/tmp/a.json")
        code = cmd_profile(args)
        self.assertEqual(code, 0)
        mock_export.assert_called_once_with("gaming", "/tmp/a.json")

    @patch('cli.main.ProfileManager.import_profile_json')
    def test_import_profile_overwrite(self, mock_import):
        from cli.main import cmd_profile
        mock_import.return_value = Result(True, "imported", {"key": "x"})
        args = argparse.Namespace(action="import", name=None, path="/tmp/in.json", overwrite=True)
        code = cmd_profile(args)
        self.assertEqual(code, 0)
        mock_import.assert_called_once_with("/tmp/in.json", overwrite=True)

    @patch('cli.main.ProfileManager.export_bundle_json')
    def test_export_all_uses_include_builtins_flag(self, mock_export_bundle):
        from cli.main import cmd_profile
        mock_export_bundle.return_value = Result(True, "bundle", {})
        args = argparse.Namespace(
            action="export-all",
            name="/tmp/all.json",
            path=None,
            include_builtins=True,
        )
        code = cmd_profile(args)
        self.assertEqual(code, 0)
        mock_export_bundle.assert_called_once_with("/tmp/all.json", include_builtins=True)

    @patch('cli.main.ProfileManager.import_bundle_json')
    def test_import_all_failure_exit_code(self, mock_import_bundle):
        from cli.main import cmd_profile
        mock_import_bundle.return_value = Result(False, "bad", {})
        args = argparse.Namespace(action="import-all", name=None, path="/tmp/all.json", overwrite=False)
        code = cmd_profile(args)
        self.assertEqual(code, 1)

    @patch('cli.main.ProfileManager.apply_profile')
    def test_apply_profile_no_snapshot_flag(self, mock_apply):
        from cli.main import cmd_profile
        mock_apply.return_value = Result(True, "applied", {})
        args = argparse.Namespace(action="apply", name="gaming", no_snapshot=True)
        code = cmd_profile(args)
        self.assertEqual(code, 0)
        mock_apply.assert_called_once_with("gaming", create_snapshot=False)

    def test_export_requires_name_and_path(self):
        from cli.main import cmd_profile
        args = argparse.Namespace(action="export", name="gaming", path=None)
        code = cmd_profile(args)
        self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
