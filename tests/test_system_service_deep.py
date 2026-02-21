"""Tests for services.system.service — SystemService (70 miss, 0% covered)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class _FakeResult:
    def __init__(self, success=True, message="ok"):
        self.success = success
        self.message = message


def _make_worker(result=None):
    w = MagicMock()
    w.get_result.return_value = result
    return w


@patch("services.system.service.CommandWorker")
class TestReboot(unittest.TestCase):
    def _svc(self):
        from services.system.service import SystemService
        return SystemService()

    def test_reboot_success(self, MockWorker):
        r = _FakeResult(True, "rebooting")
        MockWorker.return_value = _make_worker(r)
        result = self._svc().reboot()
        self.assertTrue(result.success)

    def test_reboot_failure_none(self, MockWorker):
        MockWorker.return_value = _make_worker(None)
        result = self._svc().reboot()
        self.assertFalse(result.success)

    def test_reboot_with_delay(self, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        self._svc().reboot(delay_seconds=60)
        args = MockWorker.call_args[0]
        self.assertIn("--when=+60", args[1])

    def test_reboot_custom_desc(self, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        self._svc().reboot(description="custom reboot")
        kw = MockWorker.call_args[1]
        self.assertEqual(kw["description"], "custom reboot")


@patch("services.system.service.CommandWorker")
class TestShutdown(unittest.TestCase):
    def _svc(self):
        from services.system.service import SystemService
        return SystemService()

    def test_shutdown_success(self, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        result = self._svc().shutdown()
        self.assertTrue(result.success)

    def test_shutdown_failure(self, MockWorker):
        MockWorker.return_value = _make_worker(None)
        result = self._svc().shutdown()
        self.assertFalse(result.success)

    def test_shutdown_with_delay(self, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        self._svc().shutdown(delay_seconds=30)
        args = MockWorker.call_args[0]
        self.assertIn("--when=+30", args[1])


@patch("services.system.service.CommandWorker")
class TestSuspend(unittest.TestCase):
    def _svc(self):
        from services.system.service import SystemService
        return SystemService()

    def test_suspend_success(self, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        result = self._svc().suspend()
        self.assertTrue(result.success)

    def test_suspend_fail(self, MockWorker):
        MockWorker.return_value = _make_worker(None)
        result = self._svc().suspend()
        self.assertFalse(result.success)


@patch("services.system.service.CommandWorker")
class TestUpdateGrub(unittest.TestCase):
    def _svc(self):
        from services.system.service import SystemService
        return SystemService()

    @patch("os.path.exists", return_value=True)
    def test_update_grub_uefi(self, mock_exists, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        result = self._svc().update_grub()
        self.assertTrue(result.success)
        args = MockWorker.call_args[0]
        self.assertIn("/etc/grub2-efi.cfg", args[1])

    @patch("os.path.exists", return_value=False)
    def test_update_grub_bios(self, mock_exists, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        result = self._svc().update_grub()
        self.assertTrue(result.success)
        args = MockWorker.call_args[0]
        self.assertIn("/etc/grub2.cfg", args[1])

    @patch("os.path.exists", side_effect=OSError("boom"))
    def test_update_grub_detection_error(self, mock_exists, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        result = self._svc().update_grub()
        self.assertTrue(result.success)

    def test_update_grub_failure(self, MockWorker):
        MockWorker.return_value = _make_worker(None)
        result = self._svc().update_grub()
        self.assertFalse(result.success)


@patch("services.system.service.CommandWorker")
class TestSetHostname(unittest.TestCase):
    def _svc(self):
        from services.system.service import SystemService
        return SystemService()

    def test_set_hostname_success(self, MockWorker):
        r = _FakeResult(True)
        MockWorker.return_value = _make_worker(r)
        result = self._svc().set_hostname("myhost")
        self.assertTrue(result.success)

    def test_set_hostname_empty(self, MockWorker):
        result = self._svc().set_hostname("")
        self.assertFalse(result.success)
        self.assertIn("empty", result.message.lower())

    def test_set_hostname_whitespace(self, MockWorker):
        result = self._svc().set_hostname("   ")
        self.assertFalse(result.success)

    def test_set_hostname_failure(self, MockWorker):
        MockWorker.return_value = _make_worker(None)
        result = self._svc().set_hostname("host")
        self.assertFalse(result.success)


class TestStaticDelegates(unittest.TestCase):
    @patch("services.system.service.SystemManager.is_atomic", return_value=True)
    def test_is_atomic(self, mock):
        from services.system.service import SystemService
        self.assertTrue(SystemService.is_atomic())

    @patch("services.system.service.SystemManager.get_variant_name", return_value="Silverblue")
    def test_get_variant_name(self, mock):
        from services.system.service import SystemService
        self.assertEqual(SystemService.get_variant_name(), "Silverblue")

    @patch("services.system.service.SystemManager.get_package_manager", return_value="dnf")
    def test_get_package_manager(self, mock):
        from services.system.service import SystemService
        self.assertEqual(SystemService.get_package_manager(), "dnf")

    @patch("services.system.service.SystemManager.has_pending_deployment", return_value=False)
    def test_has_pending_reboot(self, mock):
        from services.system.service import SystemService
        self.assertFalse(SystemService.has_pending_reboot())


if __name__ == "__main__":
    unittest.main()
