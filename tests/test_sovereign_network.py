"""
Tests for v12.0 "Sovereign Update" networking modules.
Covers: MeshDiscovery, ClipboardSync, FileDropManager.
"""

import hashlib
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.mesh_discovery import (
    MeshDiscovery, PeerDevice,
)
from utils.clipboard_sync import ClipboardSync
from utils.file_drop import (
    FileDropManager, TransferInfo, MAX_FILE_SIZE,
)


# ===========================================================================
# MeshDiscovery tests
# ===========================================================================

class TestMeshDiscoveryDeviceId(unittest.TestCase):
    """Tests for device ID generation and persistence."""

    @patch('utils.mesh_discovery.os.path.isfile', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='test-uuid-1234\n')
    def test_get_device_id_loads_existing(self, mock_file, mock_isfile):
        """Existing device ID file is read and returned."""
        result = MeshDiscovery.get_device_id()
        self.assertEqual(result, "test-uuid-1234")

    @patch('utils.mesh_discovery.os.path.isfile', return_value=False)
    @patch('utils.mesh_discovery.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('utils.mesh_discovery.uuid.uuid4', return_value='new-uuid-5678')
    def test_get_device_id_generates_new(self, mock_uuid, mock_file, mock_makedirs, mock_isfile):
        """New device ID is generated when file does not exist."""
        result = MeshDiscovery.get_device_id()
        self.assertEqual(result, "new-uuid-5678")
        mock_makedirs.assert_called_once()
        mock_file().write.assert_called_once_with("new-uuid-5678")

    @patch('utils.mesh_discovery.os.path.isfile', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='')
    @patch('utils.mesh_discovery.os.makedirs')
    @patch('utils.mesh_discovery.uuid.uuid4', return_value='fallback-uuid')
    def test_get_device_id_regenerates_on_empty_file(self, mock_uuid, mock_makedirs, mock_file_open, mock_isfile):
        """Empty device ID file triggers regeneration."""
        result = MeshDiscovery.get_device_id()
        self.assertEqual(result, "fallback-uuid")


class TestMeshDiscoveryNetwork(unittest.TestCase):
    """Tests for network-related discovery methods."""

    @patch('utils.mesh_discovery.socket.gethostname', return_value='my-laptop')
    def test_get_device_name(self, mock_hostname):
        """Device name comes from socket.gethostname()."""
        self.assertEqual(MeshDiscovery.get_device_name(), "my-laptop")

    @patch('utils.mesh_discovery.socket.socket')
    @patch('utils.mesh_discovery.socket.getaddrinfo', return_value=[])
    @patch('utils.mesh_discovery.socket.gethostname', return_value='host')
    def test_get_local_ips_via_udp(self, mock_hostname, mock_getaddrinfo, mock_sock_cls):
        """Local IP is discovered via UDP connect trick."""
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.42", 0)
        mock_sock_cls.return_value = mock_sock

        ips = MeshDiscovery.get_local_ips()
        self.assertIn("192.168.1.42", ips)

    @patch('utils.mesh_discovery.socket.socket')
    @patch('utils.mesh_discovery.socket.getaddrinfo', return_value=[])
    @patch('utils.mesh_discovery.socket.gethostname', return_value='host')
    def test_get_local_ips_excludes_loopback(self, mock_hostname, mock_getaddrinfo, mock_sock_cls):
        """Loopback 127.x addresses are excluded."""
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("127.0.0.1", 0)
        mock_sock_cls.return_value = mock_sock

        ips = MeshDiscovery.get_local_ips()
        self.assertNotIn("127.0.0.1", ips)

    @patch('utils.mesh_discovery.socket.socket')
    @patch('utils.mesh_discovery.socket.gethostname', return_value='host')
    @patch('utils.mesh_discovery.socket.getaddrinfo')
    def test_get_local_ips_hostname_fallback(self, mock_getaddrinfo, mock_hostname, mock_sock_cls):
        """Falls back to hostname resolution when UDP fails."""
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("no route")
        mock_sock_cls.return_value = mock_sock

        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('10.0.0.5', 0)),
        ]
        ips = MeshDiscovery.get_local_ips()
        self.assertIn("10.0.0.5", ips)


class TestMeshDiscoveryAvahi(unittest.TestCase):
    """Tests for Avahi availability and peer discovery."""

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-browse')
    def test_avahi_available(self, mock_which):
        """Returns True when avahi-browse is on PATH."""
        self.assertTrue(MeshDiscovery.is_avahi_available())

    @patch('utils.mesh_discovery.shutil.which', return_value=None)
    def test_avahi_not_available(self, mock_which):
        """Returns False when avahi-browse is missing."""
        self.assertFalse(MeshDiscovery.is_avahi_available())

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-browse')
    @patch('utils.mesh_discovery.subprocess.run')
    def test_discover_peers_parses_avahi_output(self, mock_run, mock_which):
        """Parses avahi-browse resolved output into PeerDevice objects."""
        avahi_output = (
            '=;eth0;IPv4;Loofi-Desktop;_loofi._tcp;local;desktop.local;192.168.1.100;53317;'
            '"device_id=abc-123" "version=12.0.0" "platform=linux" "name=Desktop" "capabilities=clipboard,filedrop"'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=avahi_output, stderr="")

        peers = MeshDiscovery.discover_peers(timeout=3)
        self.assertEqual(len(peers), 1)
        self.assertEqual(peers[0].address, "192.168.1.100")
        self.assertEqual(peers[0].port, 53317)
        self.assertEqual(peers[0].device_id, "abc-123")
        self.assertEqual(peers[0].platform, "linux")
        self.assertIn("clipboard", peers[0].capabilities)

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-browse')
    @patch('utils.mesh_discovery.subprocess.run')
    def test_discover_peers_empty_output(self, mock_run, mock_which):
        """Returns empty list when avahi-browse finds no services."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        peers = MeshDiscovery.discover_peers()
        self.assertEqual(peers, [])

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-browse')
    @patch('utils.mesh_discovery.subprocess.run')
    def test_discover_peers_timeout_returns_empty(self, mock_run, mock_which):
        """Returns empty list on subprocess timeout."""
        mock_run.side_effect = __import__('subprocess').TimeoutExpired(cmd="avahi-browse", timeout=5)
        peers = MeshDiscovery.discover_peers(timeout=5)
        self.assertEqual(peers, [])

    @patch('utils.mesh_discovery.shutil.which', return_value=None)
    def test_discover_peers_no_avahi(self, mock_which):
        """Returns empty list when avahi-browse is not installed."""
        peers = MeshDiscovery.discover_peers()
        self.assertEqual(peers, [])

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-browse')
    @patch('utils.mesh_discovery.subprocess.run')
    def test_discover_peers_nonzero_exit(self, mock_run, mock_which):
        """Returns empty list when avahi-browse exits with error."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        peers = MeshDiscovery.discover_peers()
        self.assertEqual(peers, [])


class TestMeshDiscoveryServiceInfo(unittest.TestCase):
    """Tests for service info building."""

    @patch('utils.mesh_discovery.MeshDiscovery.get_device_id', return_value='test-id-999')
    @patch('utils.mesh_discovery.MeshDiscovery.get_device_name', return_value='test-host')
    @patch('version.__version__', '12.0.0')
    def test_build_service_info_fields(self, mock_name, mock_id):
        """Service info contains all required TXT record fields."""
        info = MeshDiscovery.build_service_info()
        self.assertEqual(info["device_id"], "test-id-999")
        self.assertEqual(info["platform"], "linux")
        self.assertEqual(info["name"], "test-host")
        self.assertIn("version", info)
        self.assertIn("capabilities", info)
        self.assertIn("clipboard", info["capabilities"])
        self.assertIn("filedrop", info["capabilities"])


class TestMeshDiscoveryServiceRegistration(unittest.TestCase):
    """Tests for mDNS service registration/unregistration."""

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-publish')
    @patch('utils.mesh_discovery.subprocess.Popen')
    @patch('utils.mesh_discovery.MeshDiscovery.build_service_info', return_value={"device_id": "x"})
    @patch('utils.mesh_discovery.MeshDiscovery.get_device_name', return_value='host')
    def test_register_service_success(self, mock_name, mock_info, mock_popen, mock_which):
        """Successful service registration returns success Result."""
        MeshDiscovery._publish_process = None
        result = MeshDiscovery.register_service()
        self.assertTrue(result.success)
        self.assertIn("registered", result.message)
        # Clean up
        MeshDiscovery._publish_process = None

    @patch('utils.mesh_discovery.shutil.which', return_value=None)
    def test_register_service_no_avahi_publish(self, mock_which):
        """Registration fails when avahi-publish is not installed."""
        MeshDiscovery._publish_process = None
        result = MeshDiscovery.register_service()
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    def test_unregister_service_when_not_registered(self):
        """Unregister fails when no service is registered."""
        MeshDiscovery._publish_process = None
        result = MeshDiscovery.unregister_service()
        self.assertFalse(result.success)

    @patch('utils.mesh_discovery.shutil.which', return_value='/usr/bin/avahi-publish')
    def test_register_service_already_registered(self, mock_which):
        """Registration fails when a service is already active."""
        MeshDiscovery._publish_process = MagicMock()
        result = MeshDiscovery.register_service()
        self.assertFalse(result.success)
        self.assertIn("already", result.message)
        MeshDiscovery._publish_process = None


class TestMeshDiscoveryPeerAlive(unittest.TestCase):
    """Tests for TCP peer alive check."""

    @patch('utils.mesh_discovery.socket.socket')
    def test_peer_alive_success(self, mock_sock_cls):
        """Returns True when TCP connect succeeds."""
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock

        peer = PeerDevice(
            name="test", address="192.168.1.10", port=53317,
            device_id="x", platform="linux", version="12",
            last_seen=time.time(), capabilities=[],
        )
        self.assertTrue(MeshDiscovery.is_peer_alive(peer))
        mock_sock.connect.assert_called_once_with(("192.168.1.10", 53317))

    @patch('utils.mesh_discovery.socket.socket')
    def test_peer_alive_failure(self, mock_sock_cls):
        """Returns False when TCP connect fails."""
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("refused")
        mock_sock_cls.return_value = mock_sock

        peer = PeerDevice(
            name="test", address="192.168.1.10", port=53317,
            device_id="x", platform="linux", version="12",
            last_seen=time.time(), capabilities=[],
        )
        self.assertFalse(MeshDiscovery.is_peer_alive(peer))


# ===========================================================================
# ClipboardSync tests
# ===========================================================================

class TestClipboardSyncDisplayServer(unittest.TestCase):
    """Tests for display server detection."""

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "", "DISPLAY": ""})
    def test_detect_wayland_via_xdg(self):
        """Detects Wayland from XDG_SESSION_TYPE."""
        self.assertEqual(ClipboardSync.detect_display_server(), "wayland")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": "", "DISPLAY": ""})
    def test_detect_x11_via_xdg(self):
        """Detects X11 from XDG_SESSION_TYPE."""
        self.assertEqual(ClipboardSync.detect_display_server(), "x11")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ""})
    def test_detect_wayland_via_display_env(self):
        """Falls back to WAYLAND_DISPLAY env var."""
        self.assertEqual(ClipboardSync.detect_display_server(), "wayland")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ":0"})
    def test_detect_x11_via_display_env(self):
        """Falls back to DISPLAY env var."""
        self.assertEqual(ClipboardSync.detect_display_server(), "x11")

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ""}, clear=True)
    def test_detect_unknown(self):
        """Returns 'unknown' when no display info available."""
        self.assertEqual(ClipboardSync.detect_display_server(), "unknown")


class TestClipboardSyncToolAvailability(unittest.TestCase):
    """Tests for clipboard tool availability detection."""

    @patch('utils.clipboard_sync.shutil.which')
    def test_x11_tools_available(self, mock_which):
        """Detects X11 clipboard tools."""
        mock_which.side_effect = lambda cmd: '/usr/bin/xclip' if cmd == 'xclip' else None
        result = ClipboardSync.is_clipboard_tool_available()
        self.assertTrue(result["x11"])
        self.assertFalse(result["wayland"])

    @patch('utils.clipboard_sync.shutil.which')
    def test_wayland_tools_available(self, mock_which):
        """Detects Wayland clipboard tools."""
        def which_side_effect(cmd):
            if cmd in ('wl-copy', 'wl-paste'):
                return f'/usr/bin/{cmd}'
            return None
        mock_which.side_effect = which_side_effect
        result = ClipboardSync.is_clipboard_tool_available()
        self.assertFalse(result["x11"])
        self.assertTrue(result["wayland"])

    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    def test_no_tools_available(self, mock_which):
        """Both x11 and wayland are False when no tools installed."""
        result = ClipboardSync.is_clipboard_tool_available()
        self.assertFalse(result["x11"])
        self.assertFalse(result["wayland"])


class TestClipboardSyncEncryption(unittest.TestCase):
    """Tests for encrypt/decrypt round-trip."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting returns original data."""
        key = b"supersecretkey1234567890abcdefgh"
        plaintext = b"Hello, this is a secret message!"
        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_encrypted_differs_from_plaintext(self):
        """Encrypted data should not be identical to plaintext."""
        key = b"mysecretkey12345678901234567890ab"
        plaintext = b"This should be hidden"
        encrypted = ClipboardSync.encrypt_payload(plaintext, key)
        self.assertNotEqual(encrypted, plaintext)

    def test_different_keys_produce_different_ciphertext(self):
        """Different keys produce different ciphertext."""
        plaintext = b"Same data"
        key1 = b"key-one-1234567890123456"
        key2 = b"key-two-1234567890123456"
        enc1 = ClipboardSync.encrypt_payload(plaintext, key1)
        enc2 = ClipboardSync.encrypt_payload(plaintext, key2)
        self.assertNotEqual(enc1, enc2)

    def test_encrypt_empty_data(self):
        """Encrypting empty data round-trips correctly and produces minimum 48 bytes."""
        key = b"supersecretkey1234567890abcdefgh"
        # Encrypt empty data
        encrypted = ClipboardSync.encrypt_payload(b"", key)
        # HMAC-CTR produces: nonce(16) + ciphertext + HMAC(32) = minimum 48 bytes
        self.assertGreaterEqual(len(encrypted), 48)
        # Verify round-trip: decrypting should return empty bytes
        decrypted = ClipboardSync.decrypt_payload(encrypted, key)
        self.assertEqual(decrypted, b"")


class TestClipboardSyncPairing(unittest.TestCase):
    """Tests for pairing key generation and key derivation."""

    def test_pairing_key_format(self):
        """Pairing key is exactly 6 digits."""
        for _ in range(20):
            code = ClipboardSync.generate_pairing_key()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

    def test_pairing_key_zero_padded(self):
        """Pairing code '000001' is properly zero-padded."""
        with patch('utils.clipboard_sync.random.SystemRandom') as mock_rng:
            mock_instance = MagicMock()
            mock_instance.randint.return_value = 1
            mock_rng.return_value = mock_instance
            code = ClipboardSync.generate_pairing_key()
            self.assertEqual(code, "000001")

    def test_derive_shared_key_deterministic(self):
        """Same inputs always produce the same derived key."""
        key1 = ClipboardSync.derive_shared_key("123456", "device-abc")
        key2 = ClipboardSync.derive_shared_key("123456", "device-abc")
        self.assertEqual(key1, key2)

    def test_derive_shared_key_length(self):
        """Derived key is exactly 32 bytes."""
        key = ClipboardSync.derive_shared_key("999999", "device-xyz")
        self.assertEqual(len(key), 32)

    def test_derive_shared_key_different_codes(self):
        """Different pairing codes produce different keys."""
        key1 = ClipboardSync.derive_shared_key("111111", "device-abc")
        key2 = ClipboardSync.derive_shared_key("222222", "device-abc")
        self.assertNotEqual(key1, key2)

    def test_derive_shared_key_different_devices(self):
        """Same code with different device IDs produces different keys."""
        key1 = ClipboardSync.derive_shared_key("123456", "device-one")
        key2 = ClipboardSync.derive_shared_key("123456", "device-two")
        self.assertNotEqual(key1, key2)


class TestClipboardSyncReadWrite(unittest.TestCase):
    """Tests for reading/setting clipboard content."""

    @patch('utils.clipboard_sync.ClipboardSync.detect_display_server', return_value='x11')
    @patch('utils.clipboard_sync.shutil.which', return_value='/usr/bin/xclip')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_get_clipboard_x11(self, mock_run, mock_which, mock_display):
        """Reads clipboard via xclip on X11."""
        mock_run.return_value = MagicMock(returncode=0, stdout="clipboard text")
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "clipboard text")

    @patch('utils.clipboard_sync.ClipboardSync.detect_display_server', return_value='wayland')
    @patch('utils.clipboard_sync.shutil.which', return_value='/usr/bin/wl-paste')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_get_clipboard_wayland(self, mock_run, mock_which, mock_display):
        """Reads clipboard via wl-paste on Wayland."""
        mock_run.return_value = MagicMock(returncode=0, stdout="wayland text")
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "wayland text")

    @patch('utils.clipboard_sync.ClipboardSync.detect_display_server', return_value='x11')
    @patch('utils.clipboard_sync.shutil.which', return_value='/usr/bin/xclip')
    @patch('utils.clipboard_sync.subprocess.run')
    def test_set_clipboard_x11(self, mock_run, mock_which, mock_display):
        """Sets clipboard via xclip on X11."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(ClipboardSync.set_clipboard_content("test"))

    @patch('utils.clipboard_sync.ClipboardSync.detect_display_server', return_value='unknown')
    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    def test_get_clipboard_no_tools(self, mock_which, mock_display):
        """Returns empty string when no clipboard tools are available."""
        result = ClipboardSync.get_clipboard_content()
        self.assertEqual(result, "")

    @patch('utils.clipboard_sync.ClipboardSync.detect_display_server', return_value='unknown')
    @patch('utils.clipboard_sync.shutil.which', return_value=None)
    def test_set_clipboard_no_tools(self, mock_which, mock_display):
        """Returns False when no clipboard tools are available."""
        self.assertFalse(ClipboardSync.set_clipboard_content("test"))


# ===========================================================================
# FileDropManager tests
# ===========================================================================

class TestFileDropDownloadDir(unittest.TestCase):
    """Tests for download directory creation."""

    @patch('utils.file_drop.os.makedirs')
    @patch('utils.file_drop.os.path.expanduser', return_value='/home/user/Downloads/Loofi')
    def test_get_download_dir_creates_directory(self, mock_expand, mock_makedirs):
        """Creates download directory if missing."""
        path = FileDropManager.get_download_dir()
        self.assertEqual(path, "/home/user/Downloads/Loofi")
        mock_makedirs.assert_called_once_with("/home/user/Downloads/Loofi", exist_ok=True)


class TestFileDropMetadata(unittest.TestCase):
    """Tests for file metadata extraction."""

    @patch('utils.file_drop.FileDropManager.calculate_checksum', return_value='abc123')
    @patch('utils.file_drop.FileDropManager.get_file_mime_type', return_value='text/plain')
    @patch('utils.file_drop.os.path.getsize', return_value=1024)
    @patch('utils.file_drop.os.path.abspath', return_value='/tmp/test.txt')
    def test_prepare_file_metadata(self, mock_abs, mock_size, mock_mime, mock_checksum):
        """Metadata dict has expected keys and values."""
        meta = FileDropManager.prepare_file_metadata("/tmp/test.txt")
        self.assertEqual(meta["name"], "test.txt")
        self.assertEqual(meta["size"], 1024)
        self.assertEqual(meta["mime_type"], "text/plain")
        self.assertEqual(meta["checksum_sha256"], "abc123")


class TestFileDropChecksum(unittest.TestCase):
    """Tests for SHA-256 checksum calculation."""

    def test_calculate_checksum(self):
        """Checksum is computed correctly for known content."""
        content = b"hello world"
        expected = hashlib.sha256(content).hexdigest()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = FileDropManager.calculate_checksum(tmp_path)
            self.assertEqual(result, expected)
        finally:
            os.unlink(tmp_path)

    def test_calculate_checksum_empty_file(self):
        """Checksum of empty file matches SHA-256 of empty bytes."""
        expected = hashlib.sha256(b"").hexdigest()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = FileDropManager.calculate_checksum(tmp_path)
            self.assertEqual(result, expected)
        finally:
            os.unlink(tmp_path)


class TestFileDropFilenameSanitization(unittest.TestCase):
    """Tests for filename sanitisation against injection attacks."""

    def test_basic_filename(self):
        """Normal filename passes through unchanged."""
        self.assertEqual(FileDropManager.validate_filename("photo.jpg"), "photo.jpg")

    def test_path_traversal_unix(self):
        """Unix path traversal components are stripped."""
        result = FileDropManager.validate_filename("../../etc/passwd")
        self.assertNotIn("/", result)
        self.assertNotIn("..", result)

    def test_path_traversal_windows(self):
        """Windows path traversal components are stripped."""
        result = FileDropManager.validate_filename("..\\..\\windows\\system32\\config")
        self.assertNotIn("\\", result)
        self.assertNotIn("..", result)

    def test_null_bytes_removed(self):
        """Null bytes are removed from filename."""
        result = FileDropManager.validate_filename("file\x00.txt")
        self.assertNotIn("\x00", result)

    def test_leading_dots_stripped(self):
        """Leading dots (hidden files) are stripped."""
        result = FileDropManager.validate_filename(".hidden_file")
        self.assertFalse(result.startswith("."))

    def test_leading_dashes_stripped(self):
        """Leading dashes (option injection) are stripped."""
        result = FileDropManager.validate_filename("--flag-file.txt")
        self.assertFalse(result.startswith("-"))

    def test_long_filename_clamped(self):
        """Filenames exceeding 255 characters are clamped."""
        long_name = "a" * 300 + ".txt"
        result = FileDropManager.validate_filename(long_name)
        self.assertLessEqual(len(result), 255)
        self.assertTrue(result.endswith(".txt"))

    def test_empty_filename_fallback(self):
        """Empty filename gets a fallback name."""
        result = FileDropManager.validate_filename("")
        self.assertEqual(result, "unnamed_file")

    def test_only_dots_filename(self):
        """Filename made entirely of dots gets fallback."""
        result = FileDropManager.validate_filename("...")
        self.assertTrue(len(result) > 0)
        self.assertNotEqual(result, "...")

    def test_control_characters_removed(self):
        """ASCII control characters are removed."""
        result = FileDropManager.validate_filename("file\x01\x02name.txt")
        self.assertNotIn("\x01", result)
        self.assertNotIn("\x02", result)


class TestFileDropTransferSafety(unittest.TestCase):
    """Tests for transfer safety checks."""

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_safe_transfer(self, mock_dir, mock_space):
        """Normal file passes safety checks."""
        safe, reason = FileDropManager.is_transfer_safe("photo.jpg", 1024 * 1024)
        self.assertTrue(safe)

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_oversized_file_rejected(self, mock_dir, mock_space):
        """File exceeding MAX_FILE_SIZE is rejected."""
        safe, reason = FileDropManager.is_transfer_safe("big.iso", MAX_FILE_SIZE + 1)
        self.assertFalse(safe)
        self.assertIn("maximum", reason.lower())

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_dangerous_exe_extension(self, mock_dir, mock_space):
        """Dangerous .exe extension is flagged."""
        safe, reason = FileDropManager.is_transfer_safe("malware.exe", 1024)
        self.assertFalse(safe)
        self.assertIn(".exe", reason)

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_dangerous_sh_extension(self, mock_dir, mock_space):
        """Dangerous .sh extension is flagged."""
        safe, reason = FileDropManager.is_transfer_safe("install.sh", 1024)
        self.assertFalse(safe)
        self.assertIn(".sh", reason)

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_dangerous_ps1_extension(self, mock_dir, mock_space):
        """Dangerous .ps1 extension is flagged."""
        safe, reason = FileDropManager.is_transfer_safe("script.ps1", 1024)
        self.assertFalse(safe)
        self.assertIn(".ps1", reason)

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_dangerous_bat_extension(self, mock_dir, mock_space):
        """Dangerous .bat extension is flagged."""
        safe, reason = FileDropManager.is_transfer_safe("run.bat", 1024)
        self.assertFalse(safe)
        self.assertIn(".bat", reason)

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=500)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_insufficient_disk_space(self, mock_dir, mock_space):
        """Transfer rejected when insufficient disk space."""
        safe, reason = FileDropManager.is_transfer_safe("photo.jpg", 1024)
        self.assertFalse(safe)
        self.assertIn("disk space", reason.lower())

    @patch('utils.file_drop.FileDropManager.get_available_disk_space', return_value=100 * 1024 * 1024 * 1024)
    @patch('utils.file_drop.FileDropManager.get_download_dir', return_value='/tmp')
    def test_negative_file_size(self, mock_dir, mock_space):
        """Negative file size is rejected."""
        safe, reason = FileDropManager.is_transfer_safe("file.txt", -1)
        self.assertFalse(safe)
        self.assertIn("invalid", reason.lower())


class TestFileDropFormatting(unittest.TestCase):
    """Tests for human-readable formatting helpers."""

    def test_format_file_size_bytes(self):
        """Small sizes formatted as bytes."""
        self.assertEqual(FileDropManager.format_file_size(500), "500 B")

    def test_format_file_size_kb(self):
        """Kilobyte sizes formatted correctly."""
        result = FileDropManager.format_file_size(2048)
        self.assertIn("KB", result)

    def test_format_file_size_mb(self):
        """Megabyte sizes formatted correctly."""
        result = FileDropManager.format_file_size(5 * 1024 * 1024)
        self.assertIn("MB", result)

    def test_format_file_size_gb(self):
        """Gigabyte sizes formatted correctly."""
        result = FileDropManager.format_file_size(2 * 1024 * 1024 * 1024)
        self.assertIn("GB", result)

    def test_format_file_size_tb(self):
        """Terabyte sizes formatted correctly."""
        result = FileDropManager.format_file_size(3 * 1024 * 1024 * 1024 * 1024)
        self.assertIn("TB", result)

    def test_format_transfer_speed_bytes(self):
        """Low speeds show B/s."""
        self.assertEqual(FileDropManager.format_transfer_speed(500), "500 B/s")

    def test_format_transfer_speed_kb(self):
        """Kilobyte speeds formatted correctly."""
        result = FileDropManager.format_transfer_speed(50 * 1024)
        self.assertIn("KB/s", result)

    def test_format_transfer_speed_mb(self):
        """Megabyte speeds formatted correctly."""
        result = FileDropManager.format_transfer_speed(2 * 1024 * 1024 + 512 * 1024)
        self.assertIn("MB/s", result)

    def test_format_transfer_speed_gb(self):
        """Gigabyte speeds formatted correctly."""
        result = FileDropManager.format_transfer_speed(2 * 1024 * 1024 * 1024)
        self.assertIn("GB/s", result)


class TestFileDropMimeType(unittest.TestCase):
    """Tests for MIME type detection."""

    def test_mime_type_txt(self):
        """Text files detected as text/plain."""
        result = FileDropManager.get_file_mime_type("document.txt")
        self.assertEqual(result, "text/plain")

    def test_mime_type_png(self):
        """PNG files detected correctly."""
        result = FileDropManager.get_file_mime_type("image.png")
        self.assertEqual(result, "image/png")

    def test_mime_type_unknown(self):
        """Unknown extensions fallback to application/octet-stream."""
        result = FileDropManager.get_file_mime_type("data.xyz_unknown")
        self.assertEqual(result, "application/octet-stream")


class TestFileDropTransferManagement(unittest.TestCase):
    """Tests for transfer accept/reject workflow."""

    def setUp(self):
        """Clear transfer registry before each test."""
        FileDropManager._transfers = {}

    def test_accept_pending_transfer(self):
        """Accepting a pending transfer changes status to in_progress."""
        tid = FileDropManager.generate_transfer_id()
        transfer = TransferInfo(
            transfer_id=tid, filename="test.txt", file_size=100,
            sender_name="peer", sender_address="192.168.1.5",
            status="pending",
        )
        FileDropManager._transfers[tid] = transfer

        result = FileDropManager.accept_transfer(tid)
        self.assertTrue(result.success)
        self.assertEqual(transfer.status, "in_progress")

    def test_reject_pending_transfer(self):
        """Rejecting a pending transfer changes status to cancelled."""
        tid = FileDropManager.generate_transfer_id()
        transfer = TransferInfo(
            transfer_id=tid, filename="test.txt", file_size=100,
            sender_name="peer", sender_address="192.168.1.5",
            status="pending",
        )
        FileDropManager._transfers[tid] = transfer

        result = FileDropManager.reject_transfer(tid)
        self.assertTrue(result.success)
        self.assertEqual(transfer.status, "cancelled")

    def test_accept_nonexistent_transfer(self):
        """Accepting a nonexistent transfer fails."""
        result = FileDropManager.accept_transfer("nonexistent-id")
        self.assertFalse(result.success)

    def test_reject_nonexistent_transfer(self):
        """Rejecting a nonexistent transfer fails."""
        result = FileDropManager.reject_transfer("nonexistent-id")
        self.assertFalse(result.success)

    def test_accept_non_pending_transfer(self):
        """Accepting a non-pending transfer fails."""
        tid = FileDropManager.generate_transfer_id()
        transfer = TransferInfo(
            transfer_id=tid, filename="test.txt", file_size=100,
            sender_name="peer", sender_address="192.168.1.5",
            status="completed",
        )
        FileDropManager._transfers[tid] = transfer

        result = FileDropManager.accept_transfer(tid)
        self.assertFalse(result.success)

    def test_list_pending_transfers(self):
        """list_pending_transfers returns only pending transfers."""
        tid1 = "id-1"
        tid2 = "id-2"
        FileDropManager._transfers[tid1] = TransferInfo(
            transfer_id=tid1, filename="a.txt", file_size=10,
            sender_name="p1", sender_address="1.1.1.1", status="pending",
        )
        FileDropManager._transfers[tid2] = TransferInfo(
            transfer_id=tid2, filename="b.txt", file_size=20,
            sender_name="p2", sender_address="2.2.2.2", status="completed",
        )
        pending = FileDropManager.list_pending_transfers()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].transfer_id, tid1)


class TestFileDropHttpServer(unittest.TestCase):
    """Tests for HTTP server command builder."""

    def test_build_http_server_command(self):
        """Command tuple is correctly formed."""
        cmd, args = FileDropManager.build_http_server_command(8080, "/tmp/share")
        self.assertEqual(cmd, "python3")
        self.assertIn("-m", args)
        self.assertIn("http.server", args)
        self.assertIn("8080", args)
        self.assertIn("/tmp/share", args)


class TestFileDropTransferId(unittest.TestCase):
    """Tests for transfer ID generation."""

    def test_transfer_id_is_uuid(self):
        """Generated transfer ID is a valid UUID4 string."""
        import uuid
        tid = FileDropManager.generate_transfer_id()
        parsed = uuid.UUID(tid, version=4)
        self.assertEqual(str(parsed), tid)

    def test_transfer_ids_are_unique(self):
        """Multiple calls generate different IDs."""
        ids = {FileDropManager.generate_transfer_id() for _ in range(50)}
        self.assertEqual(len(ids), 50)


class TestFileDropDiskSpace(unittest.TestCase):
    """Tests for disk space check."""

    @patch('utils.file_drop.os.statvfs')
    def test_get_available_disk_space(self, mock_statvfs):
        """Disk space is computed from statvfs."""
        mock_stat = MagicMock()
        mock_stat.f_bavail = 1000
        mock_stat.f_frsize = 4096
        mock_statvfs.return_value = mock_stat

        result = FileDropManager.get_available_disk_space("/tmp")
        self.assertEqual(result, 1000 * 4096)


if __name__ == '__main__':
    unittest.main()
