"""
Tests for utils/clipboard_sync.py — ClipboardSync.
Covers: display detection, clipboard read/write, tool detection,
encryption/decryption, pairing code generation, shared key derivation,
server start/stop, and send_clipboard_to_peer.
"""

import os
import sys
import socket
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.clipboard_sync import ClipboardSync


# ---------------------------------------------------------------------------
# TestDetectDisplayServer — display server detection
# ---------------------------------------------------------------------------

class TestDetectDisplayServer(unittest.TestCase):
    """Tests for detect_display_server with mocked env vars."""

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=False)
    def test_detect_wayland_via_xdg_session(self):
        """Detects Wayland via XDG_SESSION_TYPE."""
        self.assertEqual(ClipboardSync.detect_display_server(), "wayland")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False)
    def test_detect_x11_via_xdg_session(self):
        """Detects X11 via XDG_SESSION_TYPE."""
        self.assertEqual(ClipboardSync.detect_display_server(), "x11")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "wayland-0"}, clear=False)
    def test_detect_wayland_via_wayland_display(self):
        """Detects Wayland via WAYLAND_DISPLAY fallback."""
        self.assertEqual(ClipboardSync.detect_display_server(), "wayland")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ":0"}, clear=False)
    def test_detect_x11_via_display(self):
        """Detects X11 via DISPLAY fallback."""
        self.assertEqual(ClipboardSync.detect_display_server(), "x11")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ""}, clear=False)
    def test_detect_unknown(self):
        """Returns unknown when no display server detected."""
        self.assertEqual(ClipboardSync.detect_display_server(), "unknown")


# ---------------------------------------------------------------------------
# TestGetClipboardContent — clipboard reading
# ---------------------------------------------------------------------------

class TestGetClipboardContent(unittest.TestCase):
    """Tests for get_clipboard_content with mocked tools."""

    @patch('utils.clipboard_sync.subprocess.run')
    @patch('utils.clipboard_sync.shutil.which', return_value='/usr/bin/wl-paste')
    @patch.object(ClipboardSync, 'detect_display_server', return_value='wayland')
    def test_read_wayland_wl_paste(self, mock_display, mock_which, mock_run):
        """Reads clipboard via wl-paste on Wayland."""
        mock_run.return_value = MagicMock(returncode=0, stdout="clipboard text")

        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "clipboard text")

    @patch('utils.clipboard_sync.subprocess.run')
    @patch('utils.clipboard_sync.shutil.which')
    @patch.object(ClipboardSync, 'detect_display_server', return_value='x11')
    def test_read_x11_xclip(self, mock_display, mock_which, mock_run):
        """Reads clipboard via xclip on X11."""
        mock_which.side_effect = lambda name: '/usr/bin/xclip' if name == 'xclip' else None
        mock_run.return_value = MagicMock(returncode=0, stdout="x11 text")

        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "x11 text")

    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    @patch.object(ClipboardSync, 'detect_display_server', return_value='x11')
    def test_read_no_tools_returns_empty(self, mock_display, mock_which):
        """Returns empty string when no tools available."""
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# TestSetClipboardContent — clipboard writing
# ---------------------------------------------------------------------------

class TestSetClipboardContent(unittest.TestCase):
    """Tests for set_clipboard_content with mocked tools."""

    @patch('utils.clipboard_sync.subprocess.run')
    @patch('utils.clipboard_sync.shutil.which', return_value='/usr/bin/wl-copy')
    @patch.object(ClipboardSync, 'detect_display_server', return_value='wayland')
    def test_write_wayland_wl_copy(self, mock_display, mock_which, mock_run):
        """Writes clipboard via wl-copy on Wayland."""
        mock_run.return_value = MagicMock(returncode=0)

        result = ClipboardSync.set_clipboard_content("hello")
        self.assertTrue(result)

    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    @patch.object(ClipboardSync, 'detect_display_server', return_value='unknown')
    def test_write_no_tools_returns_false(self, mock_display, mock_which):
        """Returns False when no clipboard tools available."""
        result = ClipboardSync.set_clipboard_content("text")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# TestIsClipboardToolAvailable — tool detection
# ---------------------------------------------------------------------------

class TestIsClipboardToolAvailable(unittest.TestCase):
    """Tests for is_clipboard_tool_available."""

    @patch('utils.clipboard_sync.shutil.which')
    def test_both_available(self, mock_which):
        """Detects both X11 and Wayland tools."""
        mock_which.side_effect = lambda name: f'/usr/bin/{name}'

        tools = ClipboardSync.is_clipboard_tool_available()
        self.assertTrue(tools["x11"])
        self.assertTrue(tools["wayland"])

    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    def test_none_available(self, mock_which):
        """Returns False for both when no tools installed."""
        tools = ClipboardSync.is_clipboard_tool_available()
        self.assertFalse(tools["x11"])
        self.assertFalse(tools["wayland"])


# ---------------------------------------------------------------------------
# TestEncryptDecrypt — encryption/decryption roundtrip
# ---------------------------------------------------------------------------

class TestEncryptDecrypt(unittest.TestCase):
    """Tests for encrypt_payload and decrypt_payload."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting returns original data."""
        key = os.urandom(32)
        plaintext = b"Hello, mesh network!"

        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)

        self.assertEqual(decrypted, plaintext)

    def test_encrypt_decrypt_empty_data(self):
        """Encrypting empty data works."""
        key = os.urandom(32)
        plaintext = b""

        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)

        self.assertEqual(decrypted, plaintext)

    def test_encrypt_produces_different_ciphertext(self):
        """Two encryptions of same data produce different ciphertext (random nonce)."""
        key = os.urandom(32)
        plaintext = b"same data"

        ct1 = ClipboardSync.encrypt_payload(plaintext, key)
        ct2 = ClipboardSync.encrypt_payload(plaintext, key)

        self.assertNotEqual(ct1, ct2)

    def test_decrypt_with_wrong_key_fails(self):
        """Decrypting with wrong key raises ValueError."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"secret"

        encrypted = ClipboardSync.encrypt_payload(plaintext, key1)

        with self.assertRaises(ValueError) as ctx:
            ClipboardSync.decrypt_payload(encrypted, key2)
        self.assertIn("Authentication failed", str(ctx.exception))

    def test_decrypt_short_ciphertext_rejected(self):
        """Very short ciphertext raises ValueError."""
        key = os.urandom(32)

        with self.assertRaises(ValueError) as ctx:
            ClipboardSync.decrypt_payload(b"short", key)
        self.assertIn("too short", str(ctx.exception))

    def test_ciphertext_format(self):
        """Ciphertext has nonce (16) + encrypted data + tag (32) format."""
        key = os.urandom(32)
        plaintext = b"test data"

        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        # 16 nonce + len(plaintext) + 32 tag
        self.assertEqual(len(encrypted), 16 + len(plaintext) + 32)


# ---------------------------------------------------------------------------
# TestPairingCode — pairing code generation
# ---------------------------------------------------------------------------

class TestPairingCode(unittest.TestCase):
    """Tests for generate_pairing_key."""

    def test_pairing_code_is_6_digits(self):
        """Pairing code is exactly 6 digits."""
        code = ClipboardSync.generate_pairing_key()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_pairing_code_zero_padded(self):
        """Pairing code is zero-padded."""
        # Run many times to increase chance of hitting a low number
        codes = [ClipboardSync.generate_pairing_key() for _ in range(100)]
        for code in codes:
            self.assertEqual(len(code), 6)


# ---------------------------------------------------------------------------
# TestDeriveSharedKey — key derivation
# ---------------------------------------------------------------------------

class TestDeriveSharedKey(unittest.TestCase):
    """Tests for derive_shared_key."""

    def test_derive_shared_key_length(self):
        """Derived key is 32 bytes."""
        key = ClipboardSync.derive_shared_key("123456", "device-uuid-001")
        self.assertEqual(len(key), 32)

    def test_same_inputs_same_key(self):
        """Same pairing code and device_id produce same key."""
        k1 = ClipboardSync.derive_shared_key("123456", "device-001")
        k2 = ClipboardSync.derive_shared_key("123456", "device-001")
        self.assertEqual(k1, k2)

    def test_different_codes_different_keys(self):
        """Different pairing codes produce different keys."""
        k1 = ClipboardSync.derive_shared_key("123456", "device-001")
        k2 = ClipboardSync.derive_shared_key("654321", "device-001")
        self.assertNotEqual(k1, k2)

    def test_different_devices_different_keys(self):
        """Different device IDs produce different keys."""
        k1 = ClipboardSync.derive_shared_key("123456", "device-001")
        k2 = ClipboardSync.derive_shared_key("123456", "device-002")
        self.assertNotEqual(k1, k2)


# ---------------------------------------------------------------------------
# TestServerLifecycle — TCP server start/stop
# ---------------------------------------------------------------------------

class TestServerLifecycle(unittest.TestCase):
    """Tests for start_clipboard_server and stop_clipboard_server."""

    def setUp(self):
        """Ensure server is stopped before each test."""
        ClipboardSync.stop_clipboard_server()

    def tearDown(self):
        """Ensure server is stopped after each test."""
        ClipboardSync.stop_clipboard_server()

    def test_start_server_success(self):
        """Server starts successfully on an available port."""
        key = os.urandom(32)
        # Find a free port dynamically to avoid conflicts
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        result = ClipboardSync.start_clipboard_server(port, key)
        self.assertTrue(result)

    def test_start_server_already_running(self):
        """Second start returns False when server already running."""
        key = os.urandom(32)
        ClipboardSync.start_clipboard_server(49998, key)
        result = ClipboardSync.start_clipboard_server(49998, key)
        self.assertFalse(result)

    def test_stop_server_not_running(self):
        """Stopping when not running returns False."""
        result = ClipboardSync.stop_clipboard_server()
        self.assertFalse(result)

    def test_stop_server_running(self):
        """Stopping a running server returns True."""
        key = os.urandom(32)
        ClipboardSync.start_clipboard_server(49997, key)
        result = ClipboardSync.stop_clipboard_server()
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# TestSendToPeer — sending clipboard data
# ---------------------------------------------------------------------------

class TestSendToPeer(unittest.TestCase):
    """Tests for send_clipboard_to_peer."""

    def test_send_to_unreachable_host_returns_false(self):
        """send_clipboard_to_peer returns False for unreachable host."""
        key = os.urandom(32)
        result = ClipboardSync.send_clipboard_to_peer(
            "127.0.0.1", 49996, b"data", key
        )
        self.assertFalse(result)

    def test_send_and_receive_integration(self):
        """Full send/receive integration via localhost."""
        key = os.urandom(32)
        received_data = []

        def on_receive(data):
            received_data.append(data)

        # Start server
        started = ClipboardSync.start_clipboard_server(49995, key, on_receive)
        self.assertTrue(started)

        try:
            # Send data
            sent = ClipboardSync.send_clipboard_to_peer(
                "127.0.0.1", 49995, b"hello peer", key
            )
            self.assertTrue(sent)

            # Give server thread time to process
            import time
            time.sleep(0.5)

            self.assertEqual(len(received_data), 1)
            self.assertEqual(received_data[0], b"hello peer")
        finally:
            ClipboardSync.stop_clipboard_server()


if __name__ == '__main__':
    unittest.main()
