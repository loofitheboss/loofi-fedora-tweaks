"""Tests for utils/errors.py — LoofiError hierarchy."""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.errors import (
    LoofiError,
    DnfLockedError,
    PrivilegeError,
    CommandFailedError,
    HardwareNotFoundError,
    NetworkError,
    ConfigError,
    CommandTimeoutError,
    ValidationError,
)


class TestLoofiError(unittest.TestCase):
    """Tests for base LoofiError class."""

    def test_default_fields(self):
        err = LoofiError("something broke")
        self.assertEqual(str(err), "something broke")
        self.assertEqual(err.code, "UNKNOWN")
        self.assertEqual(err.hint, "")
        self.assertTrue(err.recoverable)

    def test_custom_fields(self):
        err = LoofiError("oops", code="TEST_ERR", hint="Try again", recoverable=True)
        self.assertEqual(err.code, "TEST_ERR")
        self.assertEqual(err.hint, "Try again")
        self.assertTrue(err.recoverable)

    def test_is_exception(self):
        with self.assertRaises(LoofiError):
            raise LoofiError("test")


class TestDnfLockedError(unittest.TestCase):
    """Tests for DnfLockedError."""

    def test_defaults(self):
        err = DnfLockedError()
        self.assertEqual(err.code, "DNF_LOCKED")
        self.assertIn("package manager", str(err).lower())
        self.assertTrue(err.recoverable)
        self.assertIsInstance(err, LoofiError)

    def test_has_hint(self):
        err = DnfLockedError()
        self.assertIn("wait", err.hint.lower())


class TestPrivilegeError(unittest.TestCase):
    """Tests for PrivilegeError."""

    def test_defaults(self):
        err = PrivilegeError()
        self.assertEqual(err.code, "PERMISSION_DENIED")
        self.assertTrue(err.recoverable)

    def test_with_operation(self):
        err = PrivilegeError(operation="install package")
        self.assertIn("install package", str(err))


class TestCommandFailedError(unittest.TestCase):
    """Tests for CommandFailedError."""

    def test_requires_args(self):
        err = CommandFailedError("dnf update", 1)
        self.assertEqual(err.code, "COMMAND_FAILED")
        self.assertTrue(err.recoverable)

    def test_with_details(self):
        err = CommandFailedError("dnf install vim", 1, stderr="E: failed")
        self.assertIn("dnf install vim", str(err))
        self.assertIn("exit code 1", str(err))
        self.assertIn("E: failed", str(err))


class TestHardwareNotFoundError(unittest.TestCase):
    """Tests for HardwareNotFoundError."""

    def test_defaults(self):
        err = HardwareNotFoundError()
        self.assertEqual(err.code, "HARDWARE_NOT_FOUND")
        self.assertFalse(err.recoverable)
        self.assertIn("hardware", err.hint.lower())

    def test_with_component(self):
        err = HardwareNotFoundError(component="GPU")
        self.assertIn("GPU", str(err))


class TestNetworkError(unittest.TestCase):
    """Tests for NetworkError."""

    def test_defaults(self):
        err = NetworkError()
        self.assertEqual(err.code, "NETWORK_ERROR")
        self.assertTrue(err.recoverable)

    def test_custom_message(self):
        err = NetworkError("DNS resolution failed")
        self.assertIn("DNS resolution failed", str(err))


class TestConfigError(unittest.TestCase):
    """Tests for ConfigError."""

    def test_defaults(self):
        err = ConfigError()
        self.assertEqual(err.code, "CONFIG_ERROR")
        self.assertTrue(err.recoverable)

    def test_with_path_and_detail(self):
        err = ConfigError(path="/etc/config.json", detail="missing key")
        self.assertIn("/etc/config.json", str(err))


class TestCommandTimeoutError(unittest.TestCase):
    """Tests for CommandTimeoutError."""

    def test_defaults(self):
        err = CommandTimeoutError()
        self.assertEqual(err.code, "COMMAND_TIMEOUT")
        self.assertTrue(err.recoverable)

    def test_with_details(self):
        err = CommandTimeoutError(cmd="dnf update", timeout=30)
        self.assertIn("30", str(err))
        self.assertIn("dnf update", str(err))
        self.assertEqual(err.timeout, 30)


class TestValidationError(unittest.TestCase):
    """Tests for ValidationError."""

    def test_defaults(self):
        err = ValidationError()
        self.assertEqual(err.code, "VALIDATION_ERROR")
        self.assertTrue(err.recoverable)

    def test_with_param(self):
        err = ValidationError(param="timeout")
        self.assertIn("timeout", str(err))

    def test_with_param_and_detail(self):
        err = ValidationError(param="port", detail="must be 1-65535")
        msg = str(err)
        self.assertIn("port", msg)
        self.assertIn("must be 1-65535", msg)


class TestInheritanceHierarchy(unittest.TestCase):
    """Tests that all errors inherit from LoofiError."""

    def test_all_subclasses(self):
        classes = [
            DnfLockedError, PrivilegeError, CommandFailedError,
            HardwareNotFoundError, NetworkError, ConfigError,
            CommandTimeoutError, ValidationError,
        ]
        for cls in classes:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, LoofiError))
                self.assertTrue(issubclass(cls, Exception))


if __name__ == "__main__":
    unittest.main()
