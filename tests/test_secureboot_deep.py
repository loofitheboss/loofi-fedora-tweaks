"""
Tests for utils/secureboot.py — Secure Boot / MOK manager.

Covers:
- SecureBootManager.get_status (enabled, disabled, no mokutil)
- generate_key (success, short password, failure)
- import_key (success, no key, failure)
- sign_module (success, no keys, no module, no sign-file, failure)
- has_keys
- get_key_path
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.secureboot import SecureBootManager, SecureBootResult, SecureBootStatus


class TestGetStatus(unittest.TestCase):

    @patch("subprocess.run")
    def test_enabled(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="SecureBoot enabled\n"),  # --sb-state
            MagicMock(returncode=0, stdout="[key #1]\n"),            # --list-enrolled
            MagicMock(returncode=0, stdout=""),                       # --list-new
        ]
        status = SecureBootManager.get_status()
        self.assertTrue(status.secure_boot_enabled)
        self.assertTrue(status.mok_enrolled)
        self.assertFalse(status.pending_mok)

    @patch("subprocess.run")
    def test_disabled(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="SecureBoot disabled\n"),
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout=""),
        ]
        status = SecureBootManager.get_status()
        self.assertFalse(status.secure_boot_enabled)
        self.assertFalse(status.mok_enrolled)

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_no_mokutil(self, mock_run):
        status = SecureBootManager.get_status()
        self.assertFalse(status.secure_boot_enabled)
        self.assertIn("not installed", status.status_message)

    @patch("subprocess.run")
    def test_pending_mok(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="SecureBoot enabled\n"),
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="Some pending key\n"),
        ]
        status = SecureBootManager.get_status()
        self.assertTrue(status.pending_mok)

    @patch("subprocess.run", side_effect=OSError("general error"))
    def test_exception_in_sb_state(self, mock_run):
        status = SecureBootManager.get_status()
        self.assertFalse(status.secure_boot_enabled)
        self.assertIn("Error", status.status_message)


class TestGenerateKey(unittest.TestCase):

    def test_short_password(self):
        r = SecureBootManager.generate_key("abc")
        self.assertFalse(r.success)
        self.assertIn("8 characters", r.message)

    @patch("os.chmod")
    @patch("subprocess.run")
    @patch("pathlib.Path.mkdir")
    def test_success(self, mock_mkdir, mock_run, mock_chmod):
        mock_run.return_value = MagicMock(returncode=0)
        r = SecureBootManager.generate_key("longpassword123")
        self.assertTrue(r.success)
        self.assertIn("Keys generated", r.message)

    @patch("subprocess.run")
    @patch("pathlib.Path.mkdir")
    def test_openssl_failure(self, mock_mkdir, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="openssl error")
        r = SecureBootManager.generate_key("longpassword123")
        self.assertFalse(r.success)

    @patch("pathlib.Path.mkdir", side_effect=OSError("no space"))
    def test_mkdir_failure(self, mock_mkdir):
        r = SecureBootManager.generate_key("longpassword123")
        self.assertFalse(r.success)


class TestImportKey(unittest.TestCase):

    @patch("pathlib.Path.exists", return_value=False)
    def test_no_key(self, mock_exists):
        r = SecureBootManager.import_key("password123")
        self.assertFalse(r.success)
        self.assertIn("No MOK key", r.message)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists", return_value=True)
    def test_success(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = SecureBootManager.import_key("password123")
        self.assertTrue(r.success)
        self.assertTrue(r.requires_reboot)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists", return_value=True)
    def test_failure(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="import failed")
        r = SecureBootManager.import_key("password123")
        self.assertFalse(r.success)

    @patch("pathlib.Path.exists", return_value=True)
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_exists):
        r = SecureBootManager.import_key("password123")
        self.assertFalse(r.success)


class TestSignModule(unittest.TestCase):

    @patch("pathlib.Path.exists", return_value=False)
    def test_no_keys(self, mock_exists):
        r = SecureBootManager.sign_module("/lib/modules/test.ko")
        self.assertFalse(r.success)
        self.assertIn("keys not found", r.message)

    @patch("os.path.exists", return_value=False)
    @patch("pathlib.Path.exists", return_value=True)
    def test_no_module(self, mock_path_exists, mock_os_exists):
        r = SecureBootManager.sign_module("/nonexistent/module.ko")
        self.assertFalse(r.success)
        self.assertIn("not found", r.message)

    @patch("glob.glob", return_value=[])
    @patch("os.path.exists", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    def test_no_sign_file(self, mock_path, mock_os, mock_glob):
        r = SecureBootManager.sign_module("/lib/modules/test.ko")
        self.assertFalse(r.success)
        self.assertIn("sign-file", r.message)

    @patch("subprocess.run")
    @patch("glob.glob", return_value=["/usr/src/kernels/6.0/scripts/sign-file"])
    @patch("os.path.exists", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    def test_success(self, mock_path, mock_os, mock_glob, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = SecureBootManager.sign_module("/lib/modules/test.ko")
        self.assertTrue(r.success)
        self.assertIn("signed successfully", r.message)

    @patch("subprocess.run")
    @patch("glob.glob", return_value=["/usr/src/kernels/6.0/scripts/sign-file"])
    @patch("os.path.exists", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    def test_sign_failure(self, mock_path, mock_os, mock_glob, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="err")
        r = SecureBootManager.sign_module("/lib/modules/test.ko")
        self.assertFalse(r.success)

    @patch("glob.glob", return_value=["/usr/src/kernels/6.0/scripts/sign-file"])
    @patch("os.path.exists", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_path, mock_os, mock_glob):
        r = SecureBootManager.sign_module("/lib/modules/test.ko")
        self.assertFalse(r.success)


class TestHasKeys(unittest.TestCase):

    @patch("pathlib.Path.exists", return_value=True)
    def test_has_keys(self, mock_exists):
        self.assertTrue(SecureBootManager.has_keys())

    @patch("pathlib.Path.exists", return_value=False)
    def test_no_keys(self, mock_exists):
        self.assertFalse(SecureBootManager.has_keys())


class TestGetKeyPath(unittest.TestCase):

    @patch("pathlib.Path.exists", return_value=True)
    def test_exists(self, mock_exists):
        result = SecureBootManager.get_key_path()
        self.assertIsNotNone(result)

    @patch("pathlib.Path.exists", return_value=False)
    def test_not_exists(self, mock_exists):
        result = SecureBootManager.get_key_path()
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
