"""Tests for utils/clipboard_sync.py — Clipboard operations and encryption."""

import os
import sys
import socket
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.clipboard_sync import ClipboardSync


class TestDetectDisplayServer(unittest.TestCase):
    """Tests for detect_display_server."""

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=False)
    def test_detect_wayland_via_session_type(self):
        self.assertEqual(ClipboardSync.detect_display_server(), "wayland")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False)
    def test_detect_x11_via_session_type(self):
        self.assertEqual(ClipboardSync.detect_display_server(), "x11")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "wayland-0"}, clear=False)
    def test_detect_wayland_via_display(self):
        self.assertEqual(ClipboardSync.detect_display_server(), "wayland")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ":0"}, clear=False)
    def test_detect_x11_via_display(self):
        self.assertEqual(ClipboardSync.detect_display_server(), "x11")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ""}, clear=False)
    def test_detect_unknown(self):
        self.assertEqual(ClipboardSync.detect_display_server(), "unknown")


class TestIsClipboardToolAvailable(unittest.TestCase):
    """Tests for is_clipboard_tool_available."""

    @patch('utils.clipboard_sync.shutil.which')
    def test_both_available(self, mock_which):
        mock_which.side_effect = lambda t: "/usr/bin/" + t
        result = ClipboardSync.is_clipboard_tool_available()
        self.assertTrue(result["x11"])
        self.assertTrue(result["wayland"])

    @patch('utils.clipboard_sync.shutil.which')
    def test_none_available(self, mock_which):
        mock_which.return_value = None
        result = ClipboardSync.is_clipboard_tool_available()
        self.assertFalse(result["x11"])
        self.assertFalse(result["wayland"])


class TestGetClipboardContent(unittest.TestCase):
    """Tests for get_clipboard_content."""

    @patch.object(ClipboardSync, 'detect_display_server', return_value="wayland")
    @patch('utils.clipboard_sync.shutil.which')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_wayland_wl_paste_success(self, mock_run, mock_which, _mock_detect):
        mock_which.return_value = "/usr/bin/wl-paste"
        mock_run.return_value = MagicMock(returncode=0, stdout="clipboard text")
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "clipboard text")

    @patch.object(ClipboardSync, 'detect_display_server', return_value="x11")
    @patch('utils.clipboard_sync.shutil.which')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_x11_xclip_success(self, mock_run, mock_which, _mock_detect):
        mock_which.side_effect = lambda t: "/usr/bin/xclip" if t == "xclip" else None
        mock_run.return_value = MagicMock(returncode=0, stdout="x11 text")
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "x11 text")

    @patch.object(ClipboardSync, 'detect_display_server', return_value="x11")
    @patch('utils.clipboard_sync.shutil.which')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_xsel_fallback(self, mock_run, mock_which, _mock_detect):
        def which_side(t):
            if t == "xsel":
                return "/usr/bin/xsel"
            return None
        mock_which.side_effect = which_side
        mock_run.return_value = MagicMock(returncode=0, stdout="xsel text")
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "xsel text")

    @patch.object(ClipboardSync, 'detect_display_server', return_value="x11")
    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    def test_no_tools_returns_empty(self, mock_which, _mock_detect):
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "")

    @patch.object(ClipboardSync, 'detect_display_server', return_value="x11")
    @patch('utils.clipboard_sync.shutil.which', return_value="/usr/bin/xclip")
    @patch('utils.clipboard_sync.subprocess.run')
    def test_subprocess_error_returns_empty(self, mock_run, mock_which, _mock_detect):
        mock_run.side_effect = OSError("not found")
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "")


class TestSetClipboardContent(unittest.TestCase):
    """Tests for set_clipboard_content."""

    @patch.object(ClipboardSync, 'detect_display_server', return_value="wayland")
    @patch('utils.clipboard_sync.shutil.which')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_wayland_wl_copy_success(self, mock_run, mock_which, _mock_detect):
        mock_which.return_value = "/usr/bin/wl-copy"
        mock_run.return_value = MagicMock(returncode=0)
        result = ClipboardSync.set_clipboard_content("hello")
        self.assertTrue(result)

    @patch.object(ClipboardSync, 'detect_display_server', return_value="x11")
    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    def test_no_tools_returns_false(self, mock_which, _mock_detect):
        result = ClipboardSync.set_clipboard_content("hello")
        self.assertFalse(result)

    @patch.object(ClipboardSync, 'detect_display_server', return_value="x11")
    @patch('utils.clipboard_sync.shutil.which', return_value="/usr/bin/xclip")
    @patch('utils.clipboard_sync.subprocess.run')
    def test_subprocess_error_returns_false(self, mock_run, mock_which, _mock_detect):
        mock_run.side_effect = OSError("broken")
        result = ClipboardSync.set_clipboard_content("hello")
        self.assertFalse(result)


class TestEncryptDecryptPayload(unittest.TestCase):
    """Tests for encrypt_payload and decrypt_payload roundtrip."""

    def test_roundtrip_small_data(self):
        key = os.urandom(32)
        plaintext = b"Hello, World!"
        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_roundtrip_empty_data(self):
        key = os.urandom(32)
        plaintext = b""
        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_roundtrip_large_data(self):
        key = os.urandom(32)
        plaintext = os.urandom(10000)
        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_different_keys_fail_decryption(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        encrypted = ClipboardSync.encrypt_payload(b"secret", key1)
        with self.assertRaises(ValueError):
            ClipboardSync.decrypt_payload(encrypted, key2)

    def test_tampered_ciphertext_fails(self):
        key = os.urandom(32)
        encrypted = ClipboardSync.encrypt_payload(b"data", key)
        # Flip a byte in the ciphertext (after nonce, before tag)
        tampered = bytearray(encrypted)
        if len(tampered) > 20:
            tampered[20] ^= 0xFF
        with self.assertRaises(ValueError):
            ClipboardSync.decrypt_payload(bytes(tampered), key)

    def test_too_short_data_raises(self):
        key = os.urandom(32)
        with self.assertRaises(ValueError):
            ClipboardSync.decrypt_payload(b"short", key)

    def test_encrypted_format_has_nonce_and_tag(self):
        key = os.urandom(32)
        encrypted = ClipboardSync.encrypt_payload(b"test", key)
        # Minimum: 16 nonce + 0 ciphertext + 32 tag = 48
        # With 4 bytes data: 16 + 4 + 32 = 52
        self.assertEqual(len(encrypted), 52)


class TestGeneratePairingKey(unittest.TestCase):
    """Tests for generate_pairing_key."""

    def test_returns_6_digit_string(self):
        code = ClipboardSync.generate_pairing_key()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_codes_differ(self):
        codes = {ClipboardSync.generate_pairing_key() for _ in range(10)}
        # Statistically, 10 random 6-digit codes should not all be the same
        self.assertGreater(len(codes), 1)


class TestDeriveSharedKey(unittest.TestCase):
    """Tests for derive_shared_key."""

    def test_returns_32_bytes(self):
        key = ClipboardSync.derive_shared_key("123456", "device-uuid")
        self.assertEqual(len(key), 32)

    def test_same_inputs_same_key(self):
        k1 = ClipboardSync.derive_shared_key("111111", "dev1")
        k2 = ClipboardSync.derive_shared_key("111111", "dev1")
        self.assertEqual(k1, k2)

    def test_different_code_different_key(self):
        k1 = ClipboardSync.derive_shared_key("111111", "dev1")
        k2 = ClipboardSync.derive_shared_key("222222", "dev1")
        self.assertNotEqual(k1, k2)

    def test_different_device_different_key(self):
        k1 = ClipboardSync.derive_shared_key("111111", "dev1")
        k2 = ClipboardSync.derive_shared_key("111111", "dev2")
        self.assertNotEqual(k1, k2)


class TestDerivePad(unittest.TestCase):
    """Tests for _derive_pad internal helper."""

    def test_returns_exact_length(self):
        key = os.urandom(32)
        pad = ClipboardSync._derive_pad(key, 100)
        self.assertEqual(len(pad), 100)

    def test_zero_length(self):
        key = os.urandom(32)
        pad = ClipboardSync._derive_pad(key, 0)
        self.assertEqual(len(pad), 0)

    def test_deterministic(self):
        key = b"fixed-key-32-bytes-for-testing!!"
        p1 = ClipboardSync._derive_pad(key, 64)
        p2 = ClipboardSync._derive_pad(key, 64)
        self.assertEqual(p1, p2)


class TestClipboardServer(unittest.TestCase):
    """Tests for start/stop clipboard server."""

    def setUp(self):
        """Reset server state between tests."""
        ClipboardSync._server_socket = None
        ClipboardSync._server_thread = None
        ClipboardSync._server_shutdown = False

    @patch('utils.clipboard_sync.socket.socket')
    def test_start_server_success(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        key = os.urandom(32)
        result = ClipboardSync.start_clipboard_server(12345, key, bind_address="127.0.0.1")
        self.assertTrue(result)
        mock_sock.bind.assert_called_once_with(("127.0.0.1", 12345))
        mock_sock.listen.assert_called_once_with(5)
        # Cleanup
        ClipboardSync.stop_clipboard_server()

    @patch('utils.clipboard_sync.socket.socket')
    def test_start_server_bind_error(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address in use")
        mock_socket_cls.return_value = mock_sock
        key = os.urandom(32)
        result = ClipboardSync.start_clipboard_server(12345, key)
        self.assertFalse(result)

    def test_start_server_already_running(self):
        ClipboardSync._server_socket = MagicMock()
        key = os.urandom(32)
        result = ClipboardSync.start_clipboard_server(12345, key)
        self.assertFalse(result)
        ClipboardSync._server_socket = None

    def test_stop_server_not_running(self):
        result = ClipboardSync.stop_clipboard_server()
        self.assertFalse(result)

    def test_stop_server_running(self):
        mock_sock = MagicMock()
        mock_thread = MagicMock()
        ClipboardSync._server_socket = mock_sock
        ClipboardSync._server_thread = mock_thread
        result = ClipboardSync.stop_clipboard_server()
        self.assertTrue(result)
        mock_sock.close.assert_called_once()
        mock_thread.join.assert_called_once()


class TestSendClipboardToPeer(unittest.TestCase):
    """Tests for send_clipboard_to_peer."""

    @patch('utils.clipboard_sync.socket.socket')
    def test_send_success(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock
        key = os.urandom(32)
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", 12345, b"hello", key)
        self.assertTrue(result)
        mock_sock.connect.assert_called_once_with(("127.0.0.1", 12345))
        mock_sock.sendall.assert_called_once()
        mock_sock.close.assert_called_once()

    @patch('utils.clipboard_sync.socket.socket')
    def test_send_connection_refused(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("Connection refused")
        mock_socket_cls.return_value = mock_sock
        key = os.urandom(32)
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", 12345, b"hello", key)
        self.assertFalse(result)

    @patch('utils.clipboard_sync.socket.socket')
    def test_send_timeout(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.timeout("timed out")
        mock_socket_cls.return_value = mock_sock
        key = os.urandom(32)
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", 12345, b"hello", key)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
