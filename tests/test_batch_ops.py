"""
Tests for BatchOpsManager — v31.0 Smart UX
"""
import unittest
import sys
import os
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.batch_ops import BatchOpsManager


class TestBatchOpsManager(unittest.TestCase):
    """Tests for BatchOpsManager."""

    @patch('utils.batch_ops.PrivilegedCommand.dnf')
    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="dnf")
    def test_batch_install_traditional(self, mock_pm, mock_dnf):
        """batch_install returns proper tuple for traditional Fedora."""
        mock_dnf.return_value = ("pkexec", ["dnf", "install", "-y", "vim", "git"], "Installing...")
        binary, args, desc = BatchOpsManager.batch_install(["vim", "git"])
        self.assertEqual(binary, "pkexec")
        self.assertIn("dnf", args)
        self.assertIn("2", desc)

    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="rpm-ostree")
    def test_batch_install_atomic(self, mock_pm):
        """batch_install uses rpm-ostree on Atomic Fedora."""
        binary, args, desc = BatchOpsManager.batch_install(["vim", "git"])
        self.assertEqual(binary, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("install", args)
        self.assertIn("vim", args)
        self.assertIn("git", args)

    def test_batch_install_empty_raises(self):
        """batch_install raises ValueError for empty list."""
        with self.assertRaises(ValueError):
            BatchOpsManager.batch_install([])

    @patch('utils.batch_ops.PrivilegedCommand.dnf')
    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="dnf")
    def test_batch_remove_traditional(self, mock_pm, mock_dnf):
        """batch_remove returns proper tuple for traditional Fedora."""
        mock_dnf.return_value = ("pkexec", ["dnf", "remove", "-y", "vim"], "Removing...")
        binary, args, desc = BatchOpsManager.batch_remove(["vim"])
        self.assertEqual(binary, "pkexec")
        self.assertIn("1", desc)

    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="rpm-ostree")
    def test_batch_remove_atomic(self, mock_pm):
        """batch_remove uses rpm-ostree uninstall on Atomic Fedora."""
        binary, args, desc = BatchOpsManager.batch_remove(["vim"])
        self.assertEqual(binary, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("uninstall", args)

    def test_batch_remove_empty_raises(self):
        """batch_remove raises ValueError for empty list."""
        with self.assertRaises(ValueError):
            BatchOpsManager.batch_remove([])

    @patch('utils.batch_ops.PrivilegedCommand.dnf')
    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="dnf")
    def test_batch_update_traditional(self, mock_pm, mock_dnf):
        """batch_update returns upgrade command for traditional Fedora."""
        mock_dnf.return_value = ("pkexec", ["dnf", "upgrade", "-y"], "Upgrading...")
        binary, args, desc = BatchOpsManager.batch_update()
        self.assertEqual(binary, "pkexec")
        self.assertIn("Updating", desc)

    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="rpm-ostree")
    def test_batch_update_atomic(self, mock_pm):
        """batch_update uses rpm-ostree upgrade on Atomic Fedora."""
        binary, args, desc = BatchOpsManager.batch_update()
        self.assertEqual(binary, "pkexec")
        self.assertIn("rpm-ostree", args)
        self.assertIn("upgrade", args)

    def test_validate_packages_normal(self):
        """validate_packages returns cleaned list."""
        result = BatchOpsManager.validate_packages(["vim", "git", "htop"])
        self.assertEqual(result, ["vim", "git", "htop"])

    def test_validate_packages_with_empty(self):
        """validate_packages removes empty strings."""
        result = BatchOpsManager.validate_packages(["vim", "", "  ", "git"])
        self.assertEqual(result, ["vim", "git"])

    def test_validate_packages_strips_whitespace(self):
        """validate_packages strips whitespace from names."""
        result = BatchOpsManager.validate_packages(["  vim  ", " git "])
        self.assertEqual(result, ["vim", "git"])

    def test_validate_packages_empty_list(self):
        """validate_packages returns empty list for empty input."""
        result = BatchOpsManager.validate_packages([])
        self.assertEqual(result, [])

    @patch('utils.batch_ops.PrivilegedCommand.dnf')
    @patch('utils.batch_ops.SystemManager.get_package_manager', return_value="dnf")
    def test_batch_install_many_packages_desc(self, mock_pm, mock_dnf):
        """batch_install description handles > 5 packages."""
        pkgs = [f"pkg{i}" for i in range(10)]
        mock_dnf.return_value = ("pkexec", ["dnf", "install", "-y"] + pkgs, "")
        binary, args, desc = BatchOpsManager.batch_install(pkgs)
        self.assertIn("10", desc)
        self.assertIn("5 more", desc)


if __name__ == '__main__':
    unittest.main()
