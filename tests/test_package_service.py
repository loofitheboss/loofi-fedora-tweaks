"""
Tests for PackageService implementations (v23.0 Architecture Hardening).

Tests cover:
- Factory pattern (get_package_service)
- DnfPackageService operations
- RpmOstreePackageService operations
- Success and failure paths
- Edge cases (empty packages, invalid args)
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pytest

_SKIP_QT = os.environ.get("DISPLAY") is None and os.environ.get("WAYLAND_DISPLAY") is None

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

try:
    from PyQt6.QtCore import QCoreApplication
    from services.package import (
        DnfPackageService,
        RpmOstreePackageService,
        get_package_service
    )
    from core.executor.action_result import ActionResult
except ImportError:
    _SKIP_QT = True

pytestmark = pytest.mark.skipif(_SKIP_QT, reason="Qt/PyQt6 not available in headless environment")


class TestPackageServiceFactory(unittest.TestCase):
    """Tests for get_package_service factory."""

    @patch('services.package.service.SystemManager.get_package_manager')
    def test_factory_returns_dnf_service(self, mock_get_pm):
        """Factory returns DnfPackageService for traditional Fedora."""
        mock_get_pm.return_value = "dnf"

        service = get_package_service()

        self.assertIsInstance(service, DnfPackageService)

    @patch('services.package.service.SystemManager.get_package_manager')
    def test_factory_returns_rpm_ostree_service(self, mock_get_pm):
        """Factory returns RpmOstreePackageService for Atomic Fedora."""
        mock_get_pm.return_value = "rpm-ostree"

        service = get_package_service()

        self.assertIsInstance(service, RpmOstreePackageService)


@patch('services.package.service.CommandWorker')
class TestDnfPackageService(unittest.TestCase):
    """Tests for DnfPackageService."""

    def test_install_success(self, mock_worker_class):
        """install() returns success ActionResult."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(
            success=True,
            message="Package installed successfully",
            exit_code=0
        )

        service = DnfPackageService()
        result = service.install(["vim"], description="Installing vim")

        # Verify CommandWorker was created with correct args
        mock_worker_class.assert_called_once()
        call_args = mock_worker_class.call_args
        self.assertEqual(call_args[0][0], "pkexec")
        self.assertIn("dnf", call_args[0][1])
        self.assertIn("install", call_args[0][1])
        self.assertIn("vim", call_args[0][1])

        # Verify worker was started and waited
        mock_worker.start.assert_called_once()
        mock_worker.wait.assert_called_once()

        # Verify result
        self.assertTrue(result.success)

    def test_install_empty_packages(self, mock_worker_class):
        """install() with empty list returns error."""
        service = DnfPackageService()
        result = service.install([])

        self.assertFalse(result.success)
        self.assertIn("No packages", result.message)

    def test_install_multiple_packages(self, mock_worker_class):
        """install() handles multiple packages."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = DnfPackageService()
        service.install(["vim", "htop", "git"])

        # Verify all packages in command
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("vim", call_args)
        self.assertIn("htop", call_args)
        self.assertIn("git", call_args)

    def test_install_with_callback(self, mock_worker_class):
        """install() connects callback to progress signal."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        callback = MagicMock()
        service = DnfPackageService()
        service.install(["vim"], callback=callback)

        # Verify progress signal was connected
        mock_worker.progress.connect.assert_called_once()

    def test_remove_success(self, mock_worker_class):
        """remove() returns success ActionResult."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = DnfPackageService()
        result = service.remove(["vim"])

        # Verify command contains 'remove'
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("remove", call_args)
        self.assertIn("vim", call_args)

        self.assertTrue(result.success)

    def test_update_all_packages(self, mock_worker_class):
        """update() without args updates all packages."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = DnfPackageService()
        service.update()

        # Verify command is 'dnf update -y' without specific packages
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("update", call_args)

    def test_update_specific_packages(self, mock_worker_class):
        """update() with packages updates only those packages."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = DnfPackageService()
        service.update(packages=["vim", "git"])

        # Verify specific packages in command
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("vim", call_args)
        self.assertIn("git", call_args)

    def test_search(self, mock_worker_class):
        """search() returns results with package list."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker

        # Mock search output
        search_output = """
vim.x86_64 : Enhanced vi editor
vim-common.x86_64 : Common files for vim
        """
        mock_worker.get_result.return_value = ActionResult(
            success=True,
            message="ok",
            exit_code=0,
            stdout=search_output
        )

        service = DnfPackageService()
        result = service.search("vim")

        self.assertTrue(result.success)
        self.assertIn("data", result.__dict__)

    def test_info(self, mock_worker_class):
        """info() returns package information."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(
            success=True,
            message="ok",
            exit_code=0,
            stdout="Name: vim\nVersion: 9.0"
        )

        service = DnfPackageService()
        result = service.info("vim")

        self.assertTrue(result.success)

    def test_list_installed(self, mock_worker_class):
        """list_installed() returns list of packages."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(
            success=True,
            message="ok",
            exit_code=0,
            stdout="vim.x86_64\ngit.x86_64\n"
        )

        service = DnfPackageService()
        result = service.list_installed()

        self.assertTrue(result.success)

    def test_is_installed_true(self, mock_worker_class):
        """is_installed() returns True when package is installed."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = DnfPackageService()
        installed = service.is_installed("vim")

        self.assertTrue(installed)

    def test_is_installed_false(self, mock_worker_class):
        """is_installed() returns False when package is not installed."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=False, message="failed", exit_code=1)

        service = DnfPackageService()
        installed = service.is_installed("nonexistent-package")

        self.assertFalse(installed)


@patch('services.package.service.CommandWorker')
class TestRpmOstreePackageService(unittest.TestCase):
    """Tests for RpmOstreePackageService."""

    def test_install_with_apply_live(self, mock_worker_class):
        """install() tries --apply-live first."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = RpmOstreePackageService()
        service.install(["vim"])

        # Verify --apply-live in command
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("rpm-ostree", call_args)
        self.assertIn("--apply-live", call_args)

    def test_install_fallback_without_apply_live(self, mock_worker_class):
        """install() falls back to regular install if --apply-live fails."""
        mock_worker = MagicMock()

        # First call (with --apply-live) fails
        first_result = ActionResult(
            success=False,
            message="failed",
            exit_code=1,
            stdout="error: cannot apply live"
        )
        # Second call (without --apply-live) succeeds
        second_result = ActionResult(success=True, message="ok", exit_code=0)
        second_result.needs_reboot = False  # Will be set by service

        mock_worker.get_result.side_effect = [first_result, second_result]
        mock_worker_class.return_value = mock_worker

        service = RpmOstreePackageService()
        result = service.install(["packagekit"])

        # Verify two worker instances were created
        self.assertEqual(mock_worker_class.call_count, 2)

        # Second result should have needs_reboot=True
        self.assertTrue(result.needs_reboot)

    def test_remove_sets_needs_reboot(self, mock_worker_class):
        """remove() sets needs_reboot=True."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = RpmOstreePackageService()
        result = service.remove(["vim"])

        # Verify needs_reboot is set
        self.assertTrue(result.needs_reboot)

    def test_update_sets_needs_reboot(self, mock_worker_class):
        """update() sets needs_reboot=True."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = RpmOstreePackageService()
        result = service.update()

        # Verify needs_reboot is set
        self.assertTrue(result.needs_reboot)

    def test_update_with_specific_packages_fails(self, mock_worker_class):
        """update() with specific packages returns error (not supported)."""
        service = RpmOstreePackageService()
        result = service.update(packages=["vim"])

        self.assertFalse(result.success)
        self.assertIn("selective", result.message.lower())

    def test_search_not_implemented(self, mock_worker_class):
        """search() returns not implemented error."""
        service = RpmOstreePackageService()
        result = service.search("vim")

        self.assertFalse(result.success)
        self.assertIn("not implemented", result.message.lower())

    def test_is_installed_uses_rpm(self, mock_worker_class):
        """is_installed() uses rpm -q command."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = RpmOstreePackageService()
        installed = service.is_installed("vim")

        # Verify rpm command was used
        call_args = mock_worker_class.call_args[0][0]
        self.assertEqual(call_args, "rpm")

        self.assertTrue(installed)


if __name__ == '__main__':
    if not _SKIP_QT:
        import sys
        app = QCoreApplication(sys.argv)
    unittest.main()
