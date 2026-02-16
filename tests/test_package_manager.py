"""
Tests for utils/package_manager.py — PackageManager.
Covers: DNF install, rpm-ostree install, apply-live fallback, flatpak,
removal, system update, reset to base, layered packages, and error handling.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.package_manager import PackageManager, PackageResult


# ---------------------------------------------------------------------------
# TestPackageResultDataclass — dataclass tests
# ---------------------------------------------------------------------------

class TestPackageResultDataclass(unittest.TestCase):
    """Tests for PackageResult dataclass."""

    def test_package_result_creation(self):
        """PackageResult stores all fields."""
        r = PackageResult(success=True, message="Installed", needs_reboot=True, output="OK")
        self.assertTrue(r.success)
        self.assertTrue(r.needs_reboot)

    def test_package_result_defaults(self):
        """PackageResult has correct defaults."""
        r = PackageResult(success=False, message="Error")
        self.assertFalse(r.needs_reboot)
        self.assertEqual(r.output, "")


# ---------------------------------------------------------------------------
# TestInstallDNF — traditional DNF install
# ---------------------------------------------------------------------------

class TestInstallDNF(unittest.TestCase):
    """Tests for DNF install path."""

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_install_dnf_success(self, mock_sys, mock_run):
        """DNF install succeeds with returncode 0."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"
        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        pm = PackageManager()
        result = pm.install(["vim"])

        self.assertTrue(result.success)
        self.assertIn("vim", result.message)

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_install_dnf_failure(self, mock_sys, mock_run):
        """DNF install fails with non-zero returncode."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="No package found")

        pm = PackageManager()
        result = pm.install(["nonexistent-pkg"])

        self.assertFalse(result.success)

    @patch('utils.package_manager.SystemManager')
    def test_install_empty_packages(self, mock_sys):
        """Install with empty list returns failure."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"

        pm = PackageManager()
        result = pm.install([])

        self.assertFalse(result.success)
        self.assertIn("No packages", result.message)


# ---------------------------------------------------------------------------
# TestInstallRpmOstree — Atomic system install
# ---------------------------------------------------------------------------

class TestInstallRpmOstree(unittest.TestCase):
    """Tests for rpm-ostree install path."""

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_install_rpm_ostree_apply_live_success(self, mock_sys, mock_run):
        """rpm-ostree install with --apply-live succeeds."""
        mock_sys.is_atomic.return_value = True
        mock_sys.get_package_manager.return_value = "rpm-ostree"
        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        pm = PackageManager()
        result = pm.install(["htop"])

        self.assertTrue(result.success)
        self.assertFalse(result.needs_reboot)

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_install_rpm_ostree_fallback_to_reboot(self, mock_sys, mock_run):
        """rpm-ostree falls back to regular install when apply-live fails."""
        mock_sys.is_atomic.return_value = True
        mock_sys.get_package_manager.return_value = "rpm-ostree"

        # First call (--apply-live) fails, second call (regular) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="cannot apply live changes"),
            MagicMock(returncode=0, stdout="Done", stderr=""),
        ]

        pm = PackageManager()
        result = pm.install(["htop"])

        self.assertTrue(result.success)
        self.assertTrue(result.needs_reboot)

    @patch('utils.package_manager.subprocess.run', side_effect=OSError("exec failed"))
    @patch('utils.package_manager.SystemManager')
    def test_install_rpm_ostree_exception(self, mock_sys, mock_run):
        """rpm-ostree install handles exception."""
        mock_sys.is_atomic.return_value = True
        mock_sys.get_package_manager.return_value = "rpm-ostree"

        pm = PackageManager()
        result = pm.install(["pkg"])

        self.assertFalse(result.success)
        self.assertIn("Error", result.message)


# ---------------------------------------------------------------------------
# TestInstallFlatpak — flatpak install
# ---------------------------------------------------------------------------

class TestInstallFlatpak(unittest.TestCase):
    """Tests for Flatpak install path."""

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_install_flatpak_success(self, mock_sys, mock_run):
        """Flatpak install succeeds."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"
        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")

        pm = PackageManager()
        result = pm.install(["com.spotify.Client"], use_flatpak=True)

        self.assertTrue(result.success)

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_install_flatpak_partial_failure(self, mock_sys, mock_run):
        """Flatpak install reports partial failure."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="OK", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="not found"),
        ]

        pm = PackageManager()
        result = pm.install(["com.app.Good", "com.app.Bad"], use_flatpak=True)

        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestRemove — package removal
# ---------------------------------------------------------------------------

class TestRemove(unittest.TestCase):
    """Tests for package removal."""

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_remove_dnf_success(self, mock_sys, mock_run):
        """DNF remove succeeds."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"
        mock_run.return_value = MagicMock(returncode=0, stdout="Removed", stderr="")

        pm = PackageManager()
        result = pm.remove(["vim"])

        self.assertTrue(result.success)
        self.assertFalse(result.needs_reboot)

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_remove_atomic_needs_reboot(self, mock_sys, mock_run):
        """rpm-ostree removal indicates reboot needed."""
        mock_sys.is_atomic.return_value = True
        mock_sys.get_package_manager.return_value = "rpm-ostree"
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

        pm = PackageManager()
        result = pm.remove(["htop"])

        self.assertTrue(result.success)
        self.assertTrue(result.needs_reboot)

    @patch('utils.package_manager.SystemManager')
    def test_remove_empty_packages(self, mock_sys):
        """Remove with empty list returns failure."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"

        pm = PackageManager()
        result = pm.remove([])

        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestUpdate — system update
# ---------------------------------------------------------------------------

class TestUpdate(unittest.TestCase):
    """Tests for system update."""

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_update_dnf_success(self, mock_sys, mock_run):
        """DNF update succeeds."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"
        mock_run.return_value = MagicMock(returncode=0, stdout="Updated", stderr="")

        pm = PackageManager()
        result = pm.update()

        self.assertTrue(result.success)

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_update_failure(self, mock_sys, mock_run):
        """Update failure returns error."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

        pm = PackageManager()
        result = pm.update()

        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestResetToBase — atomic system reset
# ---------------------------------------------------------------------------

class TestResetToBase(unittest.TestCase):
    """Tests for reset_to_base."""

    @patch('utils.package_manager.SystemManager')
    def test_reset_non_atomic_rejected(self, mock_sys):
        """reset_to_base fails on non-atomic system."""
        mock_sys.is_atomic.return_value = False
        mock_sys.get_package_manager.return_value = "dnf"

        pm = PackageManager()
        result = pm.reset_to_base()

        self.assertFalse(result.success)
        self.assertIn("Not an Atomic", result.message)

    @patch('utils.package_manager.subprocess.run')
    @patch('utils.package_manager.SystemManager')
    def test_reset_atomic_success(self, mock_sys, mock_run):
        """reset_to_base succeeds on atomic system."""
        mock_sys.is_atomic.return_value = True
        mock_sys.get_package_manager.return_value = "rpm-ostree"
        mock_run.return_value = MagicMock(returncode=0, stdout="Reset", stderr="")

        pm = PackageManager()
        result = pm.reset_to_base()

        self.assertTrue(result.success)
        self.assertTrue(result.needs_reboot)


# ---------------------------------------------------------------------------
# TestGetLayeredPackages — querying layered packages
# ---------------------------------------------------------------------------

class TestGetLayeredPackages(unittest.TestCase):
    """Tests for get_layered_packages."""

    @patch('utils.package_manager.SystemManager')
    def test_get_layered_packages_delegates(self, mock_sys):
        """get_layered_packages delegates to SystemManager."""
        mock_sys.is_atomic.return_value = True
        mock_sys.get_package_manager.return_value = "rpm-ostree"
        mock_sys.get_layered_packages.return_value = ["vim", "htop"]

        pm = PackageManager()
        packages = pm.get_layered_packages()

        self.assertEqual(packages, ["vim", "htop"])
        mock_sys.get_layered_packages.assert_called_once()


if __name__ == '__main__':
    unittest.main()
