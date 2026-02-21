"""
Tests for SystemService implementation (v23.0 Architecture Hardening).

Tests cover:
- Power management (reboot, shutdown, suspend)
- Bootloader updates (update_grub)
- Hostname management
- System detection delegation to SystemManager
- Success and failure paths
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
    from services.system import SystemService, BaseSystemService
    from core.executor.action_result import ActionResult
except ImportError:
    _SKIP_QT = True

pytestmark = pytest.mark.skipif(_SKIP_QT, reason="Qt/PyQt6 not available in headless environment")


class TestSystemServiceInit(unittest.TestCase):
    """Tests for SystemService initialization."""

    def test_inherits_base_system_service(self):
        """SystemService inherits from BaseSystemService."""
        service = SystemService()
        self.assertIsInstance(service, BaseSystemService)


@patch('services.system.service.CommandWorker')
class TestSystemServiceReboot(unittest.TestCase):
    """Tests for reboot operation."""

    def test_reboot_immediate(self, mock_worker_class):
        """reboot() without delay executes immediately."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        result = service.reboot()

        # Verify command
        call_args = mock_worker_class.call_args[0]
        self.assertEqual(call_args[0], "pkexec")
        self.assertIn("systemctl", call_args[1])
        self.assertIn("reboot", call_args[1])

        mock_worker.start.assert_called_once()
        mock_worker.wait.assert_called_once()
        self.assertTrue(result.success)

    def test_reboot_with_delay(self, mock_worker_class):
        """reboot() with delay includes --when parameter."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        service.reboot(delay_seconds=60)

        # Verify delay in command
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("--when=+60", call_args)

    def test_reboot_with_description(self, mock_worker_class):
        """reboot() uses custom description."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        service.reboot(description="Rebooting for updates")

        # Verify description was passed to CommandWorker
        call_kwargs = mock_worker_class.call_args[1]
        self.assertEqual(call_kwargs['description'], "Rebooting for updates")

    def test_reboot_failure(self, mock_worker_class):
        """reboot() returns failure ActionResult on error."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=False, message="failed", exit_code=1)

        service = SystemService()
        result = service.reboot()

        self.assertFalse(result.success)


@patch('services.system.service.CommandWorker')
class TestSystemServiceShutdown(unittest.TestCase):
    """Tests for shutdown operation."""

    def test_shutdown_immediate(self, mock_worker_class):
        """shutdown() without delay executes immediately."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        result = service.shutdown()

        # Verify command
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("systemctl", call_args)
        self.assertIn("poweroff", call_args)

        self.assertTrue(result.success)

    def test_shutdown_with_delay(self, mock_worker_class):
        """shutdown() with delay includes --when parameter."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        service.shutdown(delay_seconds=120)

        # Verify delay in command
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("--when=+120", call_args)


@patch('services.system.service.CommandWorker')
class TestSystemServiceSuspend(unittest.TestCase):
    """Tests for suspend operation."""

    def test_suspend(self, mock_worker_class):
        """suspend() executes systemctl suspend."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        result = service.suspend()

        # Verify command
        call_args = mock_worker_class.call_args[0]
        self.assertEqual(call_args[0], "systemctl")
        self.assertIn("suspend", call_args[1])

        self.assertTrue(result.success)

    def test_suspend_with_description(self, mock_worker_class):
        """suspend() uses custom description."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        service.suspend(description="Going to sleep")

        call_kwargs = mock_worker_class.call_args[1]
        self.assertEqual(call_kwargs['description'], "Going to sleep")


@patch('services.system.service.os.path.exists')
@patch('services.system.service.CommandWorker')
class TestSystemServiceUpdateGrub(unittest.TestCase):
    """Tests for GRUB update operation."""

    def test_update_grub_uefi(self, mock_worker_class, mock_exists):
        """update_grub() detects UEFI and uses correct config path."""
        mock_exists.return_value = True  # /sys/firmware/efi exists
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        result = service.update_grub()

        # Verify UEFI config path
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("/etc/grub2-efi.cfg", call_args)

        self.assertTrue(result.success)

    def test_update_grub_bios(self, mock_worker_class, mock_exists):
        """update_grub() detects BIOS and uses correct config path."""
        mock_exists.return_value = False  # /sys/firmware/efi does not exist
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        result = service.update_grub()

        # Verify BIOS config path
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("/etc/grub2.cfg", call_args)

        self.assertTrue(result.success)

    def test_update_grub_failure(self, mock_worker_class, mock_exists):
        """update_grub() returns failure on error."""
        mock_exists.return_value = True
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=False, message="failed", exit_code=1)

        service = SystemService()
        result = service.update_grub()

        self.assertFalse(result.success)


@patch('services.system.service.CommandWorker')
class TestSystemServiceHostname(unittest.TestCase):
    """Tests for hostname management."""

    def test_set_hostname_success(self, mock_worker_class):
        """set_hostname() updates hostname using hostnamectl."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        result = service.set_hostname("fedora-workstation")

        # Verify command
        call_args = mock_worker_class.call_args[0]
        self.assertEqual(call_args[0], "pkexec")
        self.assertIn("hostnamectl", call_args[1])
        self.assertIn("set-hostname", call_args[1])
        self.assertIn("fedora-workstation", call_args[1])

        self.assertTrue(result.success)

    def test_set_hostname_empty_string(self, mock_worker_class):
        """set_hostname() with empty string returns error."""
        service = SystemService()
        result = service.set_hostname("")

        self.assertFalse(result.success)
        self.assertIn("empty", result.message.lower())

    def test_set_hostname_whitespace_stripped(self, mock_worker_class):
        """set_hostname() strips whitespace from hostname."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        service.set_hostname("  fedora-box  ")

        # Verify whitespace was stripped
        call_args = mock_worker_class.call_args[0][1]
        self.assertIn("fedora-box", call_args)
        self.assertNotIn("  fedora-box  ", call_args)

    def test_set_hostname_with_description(self, mock_worker_class):
        """set_hostname() uses custom description."""
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker
        mock_worker.get_result.return_value = ActionResult(success=True, message="ok", exit_code=0)

        service = SystemService()
        service.set_hostname("newhost", description="Renaming server")

        call_kwargs = mock_worker_class.call_args[1]
        self.assertEqual(call_kwargs['description'], "Renaming server")


@patch('services.system.service.SystemManager')
class TestSystemServiceDelegation(unittest.TestCase):
    """Tests for SystemService delegation to SystemManager."""

    def test_is_atomic_delegates(self, mock_system_manager):
        """is_atomic() delegates to SystemManager.is_atomic()."""
        mock_system_manager.is_atomic.return_value = True

        result = SystemService.is_atomic()

        mock_system_manager.is_atomic.assert_called_once()
        self.assertTrue(result)

    def test_get_variant_name_delegates(self, mock_system_manager):
        """get_variant_name() delegates to SystemManager.get_variant_name()."""
        mock_system_manager.get_variant_name.return_value = "Silverblue"

        result = SystemService.get_variant_name()

        mock_system_manager.get_variant_name.assert_called_once()
        self.assertEqual(result, "Silverblue")

    def test_get_package_manager_delegates(self, mock_system_manager):
        """get_package_manager() delegates to SystemManager.get_package_manager()."""
        mock_system_manager.get_package_manager.return_value = "rpm-ostree"

        result = SystemService.get_package_manager()

        mock_system_manager.get_package_manager.assert_called_once()
        self.assertEqual(result, "rpm-ostree")

    def test_has_pending_reboot_delegates(self, mock_system_manager):
        """has_pending_reboot() delegates to SystemManager.has_pending_deployment()."""
        mock_system_manager.has_pending_deployment.return_value = True

        result = SystemService.has_pending_reboot()

        mock_system_manager.has_pending_deployment.assert_called_once()
        self.assertTrue(result)


if __name__ == '__main__':
    if not _SKIP_QT:
        import sys
        app = QCoreApplication(sys.argv)
    unittest.main()
