"""
Tests for mesh networking integration features.
Part of v12.0 "Sovereign Update".

Tests:
- ClipboardSync TCP server/client
- FileDropManager HTTP server/client
- Round-trip clipboard sync
- Round-trip file transfer
- Error handling (connection refused, timeout, etc.)
"""

import hashlib
import os
import socket
import sys
import tempfile
import time
import unittest

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.clipboard_sync import ClipboardSync
from utils.file_drop import FileDropManager


# ===========================================================================
# ClipboardSync TCP Server Tests
# ===========================================================================

class TestClipboardServerStartStop(unittest.TestCase):
    """Tests for clipboard server start/stop functionality."""

    def tearDown(self):
        """Ensure server is stopped after each test."""
        ClipboardSync.stop_clipboard_server()
        ClipboardSync._server_socket = None
        ClipboardSync._server_thread = None
        ClipboardSync._server_shutdown = False

    def test_start_server_success(self):
        """Server starts successfully on available port."""
        shared_key = b"testkeyfortesting1234567890abcdef"
        result = ClipboardSync.start_clipboard_server(0, shared_key)  # Port 0 = auto-assign
        self.assertTrue(result)
        self.assertIsNotNone(ClipboardSync._server_socket)
        self.assertIsNotNone(ClipboardSync._server_thread)

    def test_start_server_already_running(self):
        """Starting server when already running returns False."""
        shared_key = b"testkeyfortesting1234567890abcdef"
        ClipboardSync.start_clipboard_server(0, shared_key)
        # Try to start again
        result = ClipboardSync.start_clipboard_server(0, shared_key)
        self.assertFalse(result)

    def test_stop_server_when_running(self):
        """Stopping a running server returns True."""
        shared_key = b"testkeyfortesting1234567890abcdef"
        ClipboardSync.start_clipboard_server(0, shared_key)
        result = ClipboardSync.stop_clipboard_server()
        self.assertTrue(result)
        self.assertIsNone(ClipboardSync._server_socket)

    def test_stop_server_when_not_running(self):
        """Stopping a non-running server returns False."""
        result = ClipboardSync.stop_clipboard_server()
        self.assertFalse(result)


class TestClipboardSendToPeer(unittest.TestCase):
    """Tests for sending clipboard data to peer."""

    def test_send_to_nonexistent_host(self):
        """Sending to non-existent host returns False."""
        shared_key = b"testkeyfortesting1234567890abcdef"
        result = ClipboardSync.send_clipboard_to_peer(
            "192.0.2.1",  # RFC 5737 TEST-NET-1 (guaranteed non-routable)
            12345,
            b"test data",
            shared_key
        )
        self.assertFalse(result)

    def test_send_to_refused_connection(self):
        """Sending to a port with no listener returns False."""
        shared_key = b"testkeyfortesting1234567890abcdef"
        # Find an unused port by briefly binding
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        # Port is now closed, send should fail
        result = ClipboardSync.send_clipboard_to_peer(
            "127.0.0.1",
            port,
            b"test data",
            shared_key
        )
        self.assertFalse(result)


class TestClipboardRoundTrip(unittest.TestCase):
    """Tests for round-trip clipboard sync."""

    def tearDown(self):
        """Ensure server is stopped after each test."""
        ClipboardSync.stop_clipboard_server()
        ClipboardSync._server_socket = None
        ClipboardSync._server_thread = None
        ClipboardSync._server_shutdown = False

    def test_roundtrip_clipboard_sync(self):
        """Data sent to server is decrypted and received correctly."""
        shared_key = b"roundtriptestkey1234567890abcdef"
        received_data = []

        def on_receive(data):
            received_data.append(data)

        # Start server on random port
        ClipboardSync.start_clipboard_server(0, shared_key, on_receive)

        # Get the actual port
        port = ClipboardSync._server_socket.getsockname()[1]

        # Give server time to start
        time.sleep(0.1)

        # Send data
        test_data = b"Hello, this is clipboard content!"
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", port, test_data, shared_key)

        self.assertTrue(result)

        # Wait for callback
        time.sleep(0.2)

        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0], test_data)

    def test_roundtrip_unicode_content(self):
        """Unicode content is properly transferred."""
        shared_key = b"unicodetestkey123456789012345678"
        received_data = []

        def on_receive(data):
            received_data.append(data)

        ClipboardSync.start_clipboard_server(0, shared_key, on_receive)
        port = ClipboardSync._server_socket.getsockname()[1]
        time.sleep(0.1)

        test_data = "Hello, World!".encode("utf-8")
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", port, test_data, shared_key)

        self.assertTrue(result)
        time.sleep(0.2)

        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0].decode("utf-8"), "Hello, World!")

    def test_roundtrip_empty_data(self):
        """Empty data is properly transferred."""
        shared_key = b"emptydatatestkey1234567890abcdef"
        received_data = []

        def on_receive(data):
            received_data.append(data)

        ClipboardSync.start_clipboard_server(0, shared_key, on_receive)
        port = ClipboardSync._server_socket.getsockname()[1]
        time.sleep(0.1)

        test_data = b""
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", port, test_data, shared_key)

        self.assertTrue(result)
        time.sleep(0.2)

        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0], b"")


class TestClipboardWrongKey(unittest.TestCase):
    """Tests for wrong key handling."""

    def tearDown(self):
        """Ensure server is stopped after each test."""
        ClipboardSync.stop_clipboard_server()
        ClipboardSync._server_socket = None
        ClipboardSync._server_thread = None
        ClipboardSync._server_shutdown = False

    def test_wrong_key_rejected(self):
        """Data encrypted with wrong key is rejected (callback not called)."""
        server_key = b"serverkeytesting1234567890abcdef"
        client_key = b"wrongkeoftesting1234567890abcdef"
        received_data = []

        def on_receive(data):
            received_data.append(data)

        ClipboardSync.start_clipboard_server(0, server_key, on_receive)
        port = ClipboardSync._server_socket.getsockname()[1]
        time.sleep(0.1)

        # Send with wrong key
        test_data = b"This should be rejected"
        result = ClipboardSync.send_clipboard_to_peer("127.0.0.1", port, test_data, client_key)

        # Send succeeds (connection works) but decryption fails
        self.assertTrue(result)
        time.sleep(0.2)

        # Callback should not have been called due to decryption failure
        self.assertEqual(len(received_data), 0)


# ===========================================================================
# FileDropManager HTTP Server Tests
# ===========================================================================

class TestFileDropServerStartStop(unittest.TestCase):
    """Tests for file drop server start/stop functionality."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Ensure server is stopped and cleanup."""
        FileDropManager.stop_receive_server()
        FileDropManager._http_server = None
        FileDropManager._http_server_thread = None
        FileDropManager._http_save_dir = None
        FileDropManager._http_shared_key = None
        # Cleanup temp dir
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_server_success(self):
        """HTTP server starts successfully."""
        result = FileDropManager.start_receive_server(0, self.temp_dir)
        self.assertTrue(result)
        self.assertIsNotNone(FileDropManager._http_server)

    def test_start_server_already_running(self):
        """Starting server when already running returns False."""
        FileDropManager.start_receive_server(0, self.temp_dir)
        result = FileDropManager.start_receive_server(0, self.temp_dir)
        self.assertFalse(result)

    def test_stop_server_when_running(self):
        """Stopping a running server returns True."""
        FileDropManager.start_receive_server(0, self.temp_dir)
        result = FileDropManager.stop_receive_server()
        self.assertTrue(result)
        self.assertIsNone(FileDropManager._http_server)

    def test_stop_server_when_not_running(self):
        """Stopping a non-running server returns False."""
        result = FileDropManager.stop_receive_server()
        self.assertFalse(result)


class TestFileDropSendFile(unittest.TestCase):
    """Tests for sending files."""

    def test_send_nonexistent_file(self):
        """Sending non-existent file returns error."""
        result = FileDropManager.send_file("127.0.0.1", 12345, "/nonexistent/file.txt")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())

    def test_send_to_refused_connection(self):
        """Sending to a port with no listener returns connection error."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            # Find an unused port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]

            result = FileDropManager.send_file("127.0.0.1", port, temp_path)
            self.assertFalse(result.success)
            self.assertIn("onnection", result.message)  # Connection error
        finally:
            os.unlink(temp_path)


class TestFileDropRoundTrip(unittest.TestCase):
    """Tests for round-trip file transfer."""

    def setUp(self):
        """Create temp directories for tests."""
        self.save_dir = tempfile.mkdtemp()
        self.source_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Ensure server is stopped and cleanup."""
        FileDropManager.stop_receive_server()
        FileDropManager._http_server = None
        FileDropManager._http_server_thread = None
        FileDropManager._http_save_dir = None
        FileDropManager._http_shared_key = None
        # Cleanup
        import shutil
        shutil.rmtree(self.save_dir, ignore_errors=True)
        shutil.rmtree(self.source_dir, ignore_errors=True)

    def test_roundtrip_file_transfer(self):
        """File is correctly transferred and saved."""
        # Create source file
        source_path = os.path.join(self.source_dir, "test_file.txt")
        content = b"This is test file content for transfer."
        with open(source_path, "wb") as f:
            f.write(content)

        # Start server
        FileDropManager.start_receive_server(0, self.save_dir)
        port = FileDropManager._http_server.server_address[1]
        time.sleep(0.1)

        # Send file
        result = FileDropManager.send_file("127.0.0.1", port, source_path)
        self.assertTrue(result.success)

        # Check received file
        received_path = os.path.join(self.save_dir, "test_file.txt")
        self.assertTrue(os.path.exists(received_path))

        with open(received_path, "rb") as f:
            received_content = f.read()
        self.assertEqual(received_content, content)

    def test_roundtrip_checksum_verified(self):
        """Checksum is verified on received file."""
        # Create source file
        source_path = os.path.join(self.source_dir, "checksum_test.bin")
        content = os.urandom(1024)  # Random binary content
        with open(source_path, "wb") as f:
            f.write(content)

        # Start server
        FileDropManager.start_receive_server(0, self.save_dir)
        port = FileDropManager._http_server.server_address[1]
        time.sleep(0.1)

        # Send file
        result = FileDropManager.send_file("127.0.0.1", port, source_path)
        self.assertTrue(result.success)

        # Verify checksum of received file
        received_path = os.path.join(self.save_dir, "checksum_test.bin")
        original_checksum = hashlib.sha256(content).hexdigest()
        received_checksum = FileDropManager.calculate_checksum(received_path)
        self.assertEqual(original_checksum, received_checksum)

    def test_roundtrip_filename_sanitized(self):
        """Dangerous filename is sanitized on receive."""
        # Test that validate_filename properly sanitizes dangerous filenames
        # The server uses this function internally when receiving files
        sanitized = FileDropManager.validate_filename("../../../etc/passwd")
        self.assertNotIn("/", sanitized)
        self.assertNotIn("..", sanitized)

    def test_roundtrip_filename_conflict_resolved(self):
        """Filename conflict is resolved by adding suffix."""
        # Create source file
        source_path = os.path.join(self.source_dir, "conflict.txt")
        content1 = b"first file"
        content2 = b"second file"
        with open(source_path, "wb") as f:
            f.write(content1)

        # Start server
        FileDropManager.start_receive_server(0, self.save_dir)
        port = FileDropManager._http_server.server_address[1]
        time.sleep(0.1)

        # Send first file
        result1 = FileDropManager.send_file("127.0.0.1", port, source_path)
        self.assertTrue(result1.success)

        # Overwrite source with new content
        with open(source_path, "wb") as f:
            f.write(content2)

        # Send second file (same name)
        result2 = FileDropManager.send_file("127.0.0.1", port, source_path)
        self.assertTrue(result2.success)

        # Check both files exist with different names
        files = os.listdir(self.save_dir)
        self.assertEqual(len(files), 2)


class TestFileDropErrorHandling(unittest.TestCase):
    """Tests for file drop error handling."""

    def setUp(self):
        """Create temp directory."""
        self.save_dir = tempfile.mkdtemp()
        self.source_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup."""
        FileDropManager.stop_receive_server()
        import shutil
        shutil.rmtree(self.save_dir, ignore_errors=True)
        shutil.rmtree(self.source_dir, ignore_errors=True)

    def test_send_to_invalid_host(self):
        """Sending to an invalid host returns error."""
        source_path = os.path.join(self.source_dir, "test.txt")
        with open(source_path, "wb") as f:
            f.write(b"test")

        result = FileDropManager.send_file("invalid-host-that-does-not-exist", 12345, source_path)
        self.assertFalse(result.success)


# ===========================================================================
# Combined Integration Tests
# ===========================================================================

class TestMeshNetworkingIntegration(unittest.TestCase):
    """Integration tests combining clipboard and file transfer."""

    def setUp(self):
        """Setup for integration tests."""
        self.save_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup after integration tests."""
        ClipboardSync.stop_clipboard_server()
        FileDropManager.stop_receive_server()
        import shutil
        shutil.rmtree(self.save_dir, ignore_errors=True)

    def test_both_servers_can_run_simultaneously(self):
        """Clipboard and file servers can run at the same time."""
        shared_key = b"integrationtestkey12345678901234"

        # Start both servers
        clip_result = ClipboardSync.start_clipboard_server(0, shared_key)
        file_result = FileDropManager.start_receive_server(0, self.save_dir)

        self.assertTrue(clip_result)
        self.assertTrue(file_result)

        # Both should have sockets
        self.assertIsNotNone(ClipboardSync._server_socket)
        self.assertIsNotNone(FileDropManager._http_server)

        # Stop both
        ClipboardSync.stop_clipboard_server()
        FileDropManager.stop_receive_server()


if __name__ == '__main__':
    unittest.main()
