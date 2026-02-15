"""
Tests for utils/file_drop.py — Local HTTP-based file transfer for Loofi Link.

Covers:
- TransferInfo dataclass (creation, defaults, field access)
- FileDropManager.get_download_dir (directory creation, path expansion)
- FileDropManager.prepare_file_metadata (name, size, mime, checksum)
- FileDropManager.calculate_checksum (SHA-256 streaming)
- FileDropManager.validate_filename (traversal, null bytes, control chars,
  leading dots/dashes, length clamping, fallback)
- FileDropManager.generate_transfer_id (UUID4 format)
- FileDropManager.get_file_mime_type (known types, unknown fallback)
- FileDropManager.format_transfer_speed (B/s, KB/s, MB/s, GB/s)
- FileDropManager.format_file_size (B, KB, MB, GB, TB)
- FileDropManager.is_transfer_safe (size, dangerous ext, disk space)
- FileDropManager.get_available_disk_space (statvfs)
- FileDropManager.build_http_server_command (command tuple)
- FileDropManager.list_pending_transfers (filtering)
- FileDropManager.accept_transfer (state transitions, errors)
- FileDropManager.reject_transfer (state transitions, errors)
- FileDropManager.start_receive_server (start, already running)
- FileDropManager.stop_receive_server (stop, not running)
- FileDropManager.send_file (success, file missing, HTTP errors)
"""

import hashlib
import os
import sys
import tempfile
import unittest
from dataclasses import fields
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.file_drop import (
    CHUNK_SIZE,
    DANGEROUS_EXTENSIONS,
    DEFAULT_PORT,
    DOWNLOAD_DIR,
    MAX_FILE_SIZE,
    FileDropManager,
    TransferInfo,
)


class TestTransferInfoDataclass(unittest.TestCase):
    """Tests for the TransferInfo dataclass."""

    def test_creation_with_all_fields(self):
        """TransferInfo can be created with all fields specified."""
        info = TransferInfo(
            transfer_id="abc-123",
            filename="report.pdf",
            file_size=1024,
            sender_name="Alice",
            sender_address="192.168.1.10",
            status="pending",
            progress=0.5,
            speed_bps=50000,
        )
        self.assertEqual(info.transfer_id, "abc-123")
        self.assertEqual(info.filename, "report.pdf")
        self.assertEqual(info.file_size, 1024)
        self.assertEqual(info.sender_name, "Alice")
        self.assertEqual(info.sender_address, "192.168.1.10")
        self.assertEqual(info.status, "pending")
        self.assertEqual(info.progress, 0.5)
        self.assertEqual(info.speed_bps, 50000)

    def test_default_progress_and_speed(self):
        """TransferInfo defaults progress=0.0 and speed_bps=0."""
        info = TransferInfo(
            transfer_id="x",
            filename="f.txt",
            file_size=10,
            sender_name="Bob",
            sender_address="10.0.0.1",
            status="pending",
        )
        self.assertEqual(info.progress, 0.0)
        self.assertEqual(info.speed_bps, 0)

    def test_field_names(self):
        """TransferInfo has the expected set of fields."""
        field_names = {f.name for f in fields(TransferInfo)}
        expected = {
            "transfer_id",
            "filename",
            "file_size",
            "sender_name",
            "sender_address",
            "status",
            "progress",
            "speed_bps",
        }
        self.assertEqual(field_names, expected)


class TestConstants(unittest.TestCase):
    """Tests for module-level constants."""

    def test_default_port(self):
        """DEFAULT_PORT is 53317."""
        self.assertEqual(DEFAULT_PORT, 53317)

    def test_chunk_size(self):
        """CHUNK_SIZE is 64 KB."""
        self.assertEqual(CHUNK_SIZE, 65536)

    def test_max_file_size(self):
        """MAX_FILE_SIZE is 10 GB."""
        self.assertEqual(MAX_FILE_SIZE, 10 * 1024 * 1024 * 1024)

    def test_dangerous_extensions_contains_exe(self):
        """DANGEROUS_EXTENSIONS includes common dangerous types."""
        for ext in (".exe", ".bat", ".sh", ".ps1", ".msi"):
            self.assertIn(ext, DANGEROUS_EXTENSIONS)


class TestGetDownloadDir(unittest.TestCase):
    """Tests for FileDropManager.get_download_dir."""

    @patch("utils.file_drop.os.makedirs")
    @patch(
        "utils.file_drop.os.path.expanduser", return_value="/home/user/Downloads/Loofi"
    )
    def test_creates_directory_and_returns_path(self, mock_expand, mock_makedirs):
        """get_download_dir expands path, creates directory, and returns it."""
        result = FileDropManager.get_download_dir()
        mock_expand.assert_called_once_with(DOWNLOAD_DIR)
        mock_makedirs.assert_called_once_with(
            "/home/user/Downloads/Loofi", exist_ok=True
        )
        self.assertEqual(result, "/home/user/Downloads/Loofi")


class TestPrepareFileMetadata(unittest.TestCase):
    """Tests for FileDropManager.prepare_file_metadata."""

    @patch(
        "utils.file_drop.FileDropManager.calculate_checksum", return_value="deadbeef"
    )
    @patch(
        "utils.file_drop.FileDropManager.get_file_mime_type", return_value="text/plain"
    )
    @patch("utils.file_drop.os.path.getsize", return_value=42)
    @patch("utils.file_drop.os.path.abspath", return_value="/tmp/notes.txt")
    def test_returns_metadata_dict(self, mock_abs, mock_size, mock_mime, mock_checksum):
        """prepare_file_metadata returns dict with name, size, mime_type, checksum."""
        meta = FileDropManager.prepare_file_metadata("/tmp/notes.txt")
        self.assertEqual(meta["name"], "notes.txt")
        self.assertEqual(meta["size"], 42)
        self.assertEqual(meta["mime_type"], "text/plain")
        self.assertEqual(meta["checksum_sha256"], "deadbeef")


class TestCalculateChecksum(unittest.TestCase):
    """Tests for FileDropManager.calculate_checksum."""

    def test_checksum_of_known_content(self):
        """calculate_checksum returns correct SHA-256 for known data."""
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

    def test_checksum_of_empty_file(self):
        """calculate_checksum returns SHA-256 of empty data for empty file."""
        expected = hashlib.sha256(b"").hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            result = FileDropManager.calculate_checksum(tmp_path)
            self.assertEqual(result, expected)
        finally:
            os.unlink(tmp_path)


class TestValidateFilename(unittest.TestCase):
    """Tests for FileDropManager.validate_filename."""

    def test_normal_filename_unchanged(self):
        """A safe filename passes through unchanged."""
        self.assertEqual(FileDropManager.validate_filename("report.pdf"), "report.pdf")

    def test_path_traversal_stripped(self):
        """Directory traversal components are removed."""
        result = FileDropManager.validate_filename("../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_null_bytes_removed(self):
        """Null bytes are removed from filename."""
        result = FileDropManager.validate_filename("file\x00name.txt")
        self.assertNotIn("\x00", result)
        self.assertEqual(result, "filename.txt")

    def test_control_characters_removed(self):
        """Control characters (0x00-0x1f, 0x7f) are stripped."""
        result = FileDropManager.validate_filename("file\x01\x02\x7fname.txt")
        self.assertNotIn("\x01", result)
        self.assertNotIn("\x02", result)
        self.assertNotIn("\x7f", result)

    def test_leading_dots_stripped(self):
        """Leading dots are removed to prevent hidden files."""
        result = FileDropManager.validate_filename("...hidden")
        self.assertFalse(result.startswith("."))

    def test_leading_dashes_stripped(self):
        """Leading dashes are removed to prevent option injection."""
        result = FileDropManager.validate_filename("--dangerous")
        self.assertFalse(result.startswith("-"))

    def test_leading_dots_and_dashes_stripped(self):
        """Both leading dots and dashes are removed together."""
        result = FileDropManager.validate_filename(".-.-file.txt")
        self.assertFalse(result.startswith("."))
        self.assertFalse(result.startswith("-"))
        self.assertIn("file.txt", result)

    def test_length_clamped_to_255(self):
        """Filenames longer than 255 characters are truncated."""
        long_name = "a" * 300 + ".txt"
        result = FileDropManager.validate_filename(long_name)
        self.assertLessEqual(len(result), 255)
        self.assertTrue(result.endswith(".txt"))

    def test_empty_string_returns_fallback(self):
        """An empty filename returns 'unnamed_file'."""
        self.assertEqual(FileDropManager.validate_filename(""), "unnamed_file")

    def test_only_dots_returns_fallback(self):
        """A filename of only dots and dashes returns 'unnamed_file'."""
        self.assertEqual(FileDropManager.validate_filename("...---"), "unnamed_file")

    def test_backslash_path_stripped(self):
        """Windows-style backslash paths are sanitized."""
        result = FileDropManager.validate_filename("C:\\Users\\evil\\payload.exe")
        self.assertNotIn("\\", result)

    def test_forward_slash_stripped(self):
        """Forward slashes are removed."""
        result = FileDropManager.validate_filename("/etc/shadow")
        self.assertNotIn("/", result)


class TestGenerateTransferId(unittest.TestCase):
    """Tests for FileDropManager.generate_transfer_id."""

    def test_returns_uuid_string(self):
        """generate_transfer_id returns a valid UUID4 string."""
        tid = FileDropManager.generate_transfer_id()
        self.assertIsInstance(tid, str)
        # UUID4 format: 8-4-4-4-12 hex digits
        parts = tid.split("-")
        self.assertEqual(len(parts), 5)
        self.assertEqual(len(parts[0]), 8)
        self.assertEqual(len(parts[1]), 4)
        self.assertEqual(len(parts[2]), 4)
        self.assertEqual(len(parts[3]), 4)
        self.assertEqual(len(parts[4]), 12)

    def test_unique_ids(self):
        """Successive calls return unique transfer IDs."""
        ids = {FileDropManager.generate_transfer_id() for _ in range(50)}
        self.assertEqual(len(ids), 50)


class TestGetFileMimeType(unittest.TestCase):
    """Tests for FileDropManager.get_file_mime_type."""

    def test_text_file(self):
        """A .txt file returns a text MIME type."""
        mime = FileDropManager.get_file_mime_type("readme.txt")
        self.assertIn("text/", mime)

    def test_png_image(self):
        """A .png file returns image/png."""
        mime = FileDropManager.get_file_mime_type("photo.png")
        self.assertEqual(mime, "image/png")

    def test_unknown_extension(self):
        """An unknown extension returns application/octet-stream."""
        mime = FileDropManager.get_file_mime_type("data.xyz12345")
        self.assertEqual(mime, "application/octet-stream")

    def test_no_extension(self):
        """A file with no extension returns application/octet-stream."""
        mime = FileDropManager.get_file_mime_type("Makefile")
        # Makefile might or might not be recognized; the fallback is octet-stream
        self.assertIsInstance(mime, str)
        self.assertTrue(len(mime) > 0)


class TestFormatTransferSpeed(unittest.TestCase):
    """Tests for FileDropManager.format_transfer_speed."""

    def test_bytes_per_second(self):
        """Speeds under 1 KB are shown in B/s."""
        self.assertEqual(FileDropManager.format_transfer_speed(500), "500 B/s")

    def test_zero_speed(self):
        """Zero speed is shown in B/s."""
        self.assertEqual(FileDropManager.format_transfer_speed(0), "0 B/s")

    def test_kilobytes_per_second(self):
        """Speeds in the KB range are shown in KB/s."""
        result = FileDropManager.format_transfer_speed(2048)
        self.assertIn("KB/s", result)
        self.assertIn("2.0", result)

    def test_megabytes_per_second(self):
        """Speeds in the MB range are shown in MB/s."""
        result = FileDropManager.format_transfer_speed(5 * 1024 * 1024)
        self.assertIn("MB/s", result)
        self.assertIn("5.0", result)

    def test_gigabytes_per_second(self):
        """Speeds >= 1 GB are shown in GB/s."""
        result = FileDropManager.format_transfer_speed(2 * 1024 * 1024 * 1024)
        self.assertIn("GB/s", result)
        self.assertIn("2.0", result)


class TestFormatFileSize(unittest.TestCase):
    """Tests for FileDropManager.format_file_size."""

    def test_bytes(self):
        """Sizes under 1 KB are shown in B."""
        self.assertEqual(FileDropManager.format_file_size(100), "100 B")

    def test_zero_bytes(self):
        """Zero bytes is shown correctly."""
        self.assertEqual(FileDropManager.format_file_size(0), "0 B")

    def test_kilobytes(self):
        """Sizes in the KB range are shown in KB."""
        result = FileDropManager.format_file_size(4096)
        self.assertIn("KB", result)
        self.assertIn("4.0", result)

    def test_megabytes(self):
        """Sizes in the MB range are shown in MB."""
        result = FileDropManager.format_file_size(10 * 1024 * 1024)
        self.assertIn("MB", result)

    def test_gigabytes(self):
        """Sizes in the GB range are shown in GB."""
        result = FileDropManager.format_file_size(3 * 1024 * 1024 * 1024)
        self.assertIn("GB", result)

    def test_terabytes(self):
        """Sizes >= 1 TB are shown in TB."""
        result = FileDropManager.format_file_size(2 * 1024 * 1024 * 1024 * 1024)
        self.assertIn("TB", result)
        self.assertIn("2.0", result)


class TestIsTransferSafe(unittest.TestCase):
    """Tests for FileDropManager.is_transfer_safe."""

    @patch(
        "utils.file_drop.FileDropManager.get_available_disk_space",
        return_value=100 * 1024 * 1024 * 1024,
    )
    @patch(
        "utils.file_drop.FileDropManager.get_download_dir", return_value="/tmp/Loofi"
    )
    def test_safe_transfer(self, mock_dir, mock_space):
        """A normal file within size limits is safe."""
        safe, reason = FileDropManager.is_transfer_safe("document.pdf", 1024)
        self.assertTrue(safe)
        self.assertIn("safe", reason.lower())

    @patch(
        "utils.file_drop.FileDropManager.get_download_dir", return_value="/tmp/Loofi"
    )
    def test_exceeds_max_file_size(self, mock_dir):
        """A file exceeding MAX_FILE_SIZE is rejected."""
        safe, reason = FileDropManager.is_transfer_safe("huge.iso", MAX_FILE_SIZE + 1)
        self.assertFalse(safe)
        self.assertIn("maximum", reason.lower())

    @patch(
        "utils.file_drop.FileDropManager.get_download_dir", return_value="/tmp/Loofi"
    )
    def test_negative_file_size(self, mock_dir):
        """A negative file size is rejected."""
        safe, reason = FileDropManager.is_transfer_safe("file.txt", -1)
        self.assertFalse(safe)
        self.assertIn("invalid", reason.lower())

    @patch(
        "utils.file_drop.FileDropManager.get_download_dir", return_value="/tmp/Loofi"
    )
    def test_dangerous_extension_blocked(self, mock_dir):
        """A file with a dangerous extension is rejected."""
        safe, reason = FileDropManager.is_transfer_safe("virus.exe", 1024)
        self.assertFalse(safe)
        self.assertIn("dangerous", reason.lower())

    @patch(
        "utils.file_drop.FileDropManager.get_download_dir", return_value="/tmp/Loofi"
    )
    def test_dangerous_extension_case_insensitive(self, mock_dir):
        """Dangerous extension check is case-insensitive."""
        safe, reason = FileDropManager.is_transfer_safe("script.SH", 1024)
        self.assertFalse(safe)
        self.assertIn("dangerous", reason.lower())

    @patch("utils.file_drop.FileDropManager.get_available_disk_space", return_value=100)
    @patch(
        "utils.file_drop.FileDropManager.get_download_dir", return_value="/tmp/Loofi"
    )
    def test_insufficient_disk_space(self, mock_dir, mock_space):
        """A file larger than available disk space is rejected."""
        safe, reason = FileDropManager.is_transfer_safe("big.zip", 10000)
        self.assertFalse(safe)
        self.assertIn("disk space", reason.lower())


class TestGetAvailableDiskSpace(unittest.TestCase):
    """Tests for FileDropManager.get_available_disk_space."""

    @patch("utils.file_drop.os.statvfs")
    def test_returns_available_bytes(self, mock_statvfs):
        """get_available_disk_space returns f_bavail * f_frsize."""
        stat_result = MagicMock()
        stat_result.f_bavail = 1000
        stat_result.f_frsize = 4096
        mock_statvfs.return_value = stat_result
        result = FileDropManager.get_available_disk_space("/tmp")
        self.assertEqual(result, 1000 * 4096)
        mock_statvfs.assert_called_once_with("/tmp")


class TestBuildHttpServerCommand(unittest.TestCase):
    """Tests for FileDropManager.build_http_server_command."""

    def test_returns_command_tuple(self):
        """build_http_server_command returns (binary, args) tuple."""
        cmd, args = FileDropManager.build_http_server_command(8080, "/srv/files")
        self.assertEqual(cmd, "python3")
        self.assertEqual(
            args, ["-m", "http.server", "8080", "--directory", "/srv/files"]
        )

    def test_port_is_stringified(self):
        """The port number is converted to a string in the args list."""
        _, args = FileDropManager.build_http_server_command(53317, "/tmp")
        self.assertIn("53317", args)


class TestListPendingTransfers(unittest.TestCase):
    """Tests for FileDropManager.list_pending_transfers."""

    def setUp(self):
        """Clear the transfer registry before each test."""
        FileDropManager._transfers.clear()

    def tearDown(self):
        """Clear the transfer registry after each test."""
        FileDropManager._transfers.clear()

    def test_empty_registry(self):
        """Returns empty list when no transfers exist."""
        self.assertEqual(FileDropManager.list_pending_transfers(), [])

    def test_filters_only_pending(self):
        """Returns only transfers with status 'pending'."""
        FileDropManager._transfers["a"] = TransferInfo(
            "a", "f1.txt", 100, "Alice", "10.0.0.1", "pending"
        )
        FileDropManager._transfers["b"] = TransferInfo(
            "b", "f2.txt", 200, "Bob", "10.0.0.2", "completed"
        )
        FileDropManager._transfers["c"] = TransferInfo(
            "c", "f3.txt", 300, "Charlie", "10.0.0.3", "pending"
        )
        pending = FileDropManager.list_pending_transfers()
        self.assertEqual(len(pending), 2)
        ids = {t.transfer_id for t in pending}
        self.assertEqual(ids, {"a", "c"})

    def test_no_pending(self):
        """Returns empty list when all transfers have non-pending status."""
        FileDropManager._transfers["x"] = TransferInfo(
            "x", "done.zip", 500, "Dave", "10.0.0.4", "completed"
        )
        self.assertEqual(FileDropManager.list_pending_transfers(), [])


class TestAcceptTransfer(unittest.TestCase):
    """Tests for FileDropManager.accept_transfer."""

    def setUp(self):
        """Seed a pending transfer."""
        FileDropManager._transfers.clear()
        FileDropManager._transfers["t1"] = TransferInfo(
            "t1", "file.txt", 1024, "Alice", "10.0.0.1", "pending"
        )

    def tearDown(self):
        """Clean up transfer registry."""
        FileDropManager._transfers.clear()

    def test_accept_pending(self):
        """Accepting a pending transfer sets status to 'in_progress'."""
        result = FileDropManager.accept_transfer("t1")
        self.assertTrue(result.success)
        self.assertEqual(FileDropManager._transfers["t1"].status, "in_progress")

    def test_accept_not_found(self):
        """Accepting a non-existent transfer returns failure."""
        result = FileDropManager.accept_transfer("nonexistent")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())

    def test_accept_non_pending(self):
        """Accepting a transfer that is not pending returns failure."""
        FileDropManager._transfers["t1"].status = "completed"
        result = FileDropManager.accept_transfer("t1")
        self.assertFalse(result.success)
        self.assertIn("not pending", result.message.lower())


class TestRejectTransfer(unittest.TestCase):
    """Tests for FileDropManager.reject_transfer."""

    def setUp(self):
        """Seed a pending transfer."""
        FileDropManager._transfers.clear()
        FileDropManager._transfers["t2"] = TransferInfo(
            "t2", "data.bin", 2048, "Bob", "10.0.0.2", "pending"
        )

    def tearDown(self):
        """Clean up transfer registry."""
        FileDropManager._transfers.clear()

    def test_reject_pending(self):
        """Rejecting a pending transfer sets status to 'cancelled'."""
        result = FileDropManager.reject_transfer("t2")
        self.assertTrue(result.success)
        self.assertEqual(FileDropManager._transfers["t2"].status, "cancelled")

    def test_reject_not_found(self):
        """Rejecting a non-existent transfer returns failure."""
        result = FileDropManager.reject_transfer("ghost")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())

    def test_reject_non_pending(self):
        """Rejecting a transfer that is already in_progress returns failure."""
        FileDropManager._transfers["t2"].status = "in_progress"
        result = FileDropManager.reject_transfer("t2")
        self.assertFalse(result.success)
        self.assertIn("not pending", result.message.lower())


class TestStartReceiveServer(unittest.TestCase):
    """Tests for FileDropManager.start_receive_server."""

    def setUp(self):
        """Reset server state before each test."""
        FileDropManager._http_server = None
        FileDropManager._http_server_thread = None
        FileDropManager._http_save_dir = None
        FileDropManager._http_shared_key = None

    def tearDown(self):
        """Stop any running server."""
        if FileDropManager._http_server is not None:
            try:
                FileDropManager._http_server.shutdown()
            except Exception:
                pass
        FileDropManager._http_server = None
        FileDropManager._http_server_thread = None
        FileDropManager._http_save_dir = None
        FileDropManager._http_shared_key = None

    @patch("utils.file_drop.threading.Thread")
    @patch("utils.file_drop.HTTPServer")
    @patch("utils.file_drop.os.makedirs")
    def test_start_success(self, mock_makedirs, mock_http_server, mock_thread_cls):
        """start_receive_server returns True on successful start."""
        mock_server_instance = MagicMock()
        mock_http_server.return_value = mock_server_instance
        mock_thread_instance = MagicMock()
        mock_thread_cls.return_value = mock_thread_instance

        result = FileDropManager.start_receive_server(8080, "/tmp/save")
        self.assertTrue(result)
        mock_makedirs.assert_called_once_with("/tmp/save", exist_ok=True)
        mock_thread_instance.start.assert_called_once()

    @patch("utils.file_drop.threading.Thread")
    @patch("utils.file_drop.HTTPServer")
    @patch("utils.file_drop.os.makedirs")
    def test_start_already_running(
        self, mock_makedirs, mock_http_server, mock_thread_cls
    ):
        """start_receive_server returns False when server is already running."""
        FileDropManager._http_server = MagicMock()
        result = FileDropManager.start_receive_server(8080, "/tmp/save")
        self.assertFalse(result)
        # HTTPServer should not be constructed again
        mock_http_server.assert_not_called()

    @patch("utils.file_drop.HTTPServer", side_effect=OSError("Address in use"))
    @patch("utils.file_drop.os.makedirs")
    def test_start_oserror(self, mock_makedirs, mock_http_server):
        """start_receive_server returns False on OSError (port in use)."""
        result = FileDropManager.start_receive_server(8080, "/tmp/save")
        self.assertFalse(result)
        self.assertIsNone(FileDropManager._http_server)


class TestStopReceiveServer(unittest.TestCase):
    """Tests for FileDropManager.stop_receive_server."""

    def setUp(self):
        """Reset server state."""
        FileDropManager._http_server = None
        FileDropManager._http_server_thread = None
        FileDropManager._http_save_dir = None
        FileDropManager._http_shared_key = None

    def tearDown(self):
        """Clean up."""
        FileDropManager._http_server = None
        FileDropManager._http_server_thread = None
        FileDropManager._http_save_dir = None
        FileDropManager._http_shared_key = None

    def test_stop_not_running(self):
        """stop_receive_server returns False when no server is running."""
        result = FileDropManager.stop_receive_server()
        self.assertFalse(result)

    def test_stop_running_server(self):
        """stop_receive_server shuts down server and resets state."""
        mock_server = MagicMock()
        mock_thread = MagicMock()
        FileDropManager._http_server = mock_server
        FileDropManager._http_server_thread = mock_thread
        FileDropManager._http_save_dir = "/tmp/save"
        FileDropManager._http_shared_key = b"key"

        result = FileDropManager.stop_receive_server()
        self.assertTrue(result)
        mock_server.shutdown.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5.0)
        self.assertIsNone(FileDropManager._http_server)
        self.assertIsNone(FileDropManager._http_server_thread)
        self.assertIsNone(FileDropManager._http_save_dir)
        self.assertIsNone(FileDropManager._http_shared_key)


class TestSendFile(unittest.TestCase):
    """Tests for FileDropManager.send_file."""

    @patch("utils.file_drop.os.path.isfile", return_value=False)
    def test_file_not_found(self, mock_isfile):
        """send_file returns failure when file does not exist."""
        result = FileDropManager.send_file("localhost", 8080, "/missing/file.txt")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())

    @patch("utils.file_drop.urlopen")
    @patch("builtins.open", mock_open(read_data=b"content"))
    @patch("utils.file_drop.os.path.getsize", return_value=7)
    @patch("utils.file_drop.FileDropManager.calculate_checksum", return_value="abc123")
    @patch("utils.file_drop.os.path.isfile", return_value=True)
    def test_send_success(self, mock_isfile, mock_checksum, mock_size, mock_urlopen):
        """send_file returns success on HTTP 200 response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = FileDropManager.send_file("localhost", 8080, "/tmp/test.txt")
        self.assertTrue(result.success)
        self.assertIn("successfully", result.message.lower())

    @patch("utils.file_drop.urlopen")
    @patch("builtins.open", mock_open(read_data=b"content"))
    @patch("utils.file_drop.os.path.getsize", return_value=7)
    @patch("utils.file_drop.FileDropManager.calculate_checksum", return_value="abc123")
    @patch("utils.file_drop.os.path.isfile", return_value=True)
    def test_send_http_error(self, mock_isfile, mock_checksum, mock_size, mock_urlopen):
        """send_file returns failure on HTTPError."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="http://localhost:8080/upload",
            code=500,
            msg="Internal Server Error",
            hdrs=MagicMock(),
            fp=None,
        )
        result = FileDropManager.send_file("localhost", 8080, "/tmp/test.txt")
        self.assertFalse(result.success)
        self.assertIn("http error", result.message.lower())

    @patch("utils.file_drop.urlopen")
    @patch("builtins.open", mock_open(read_data=b"content"))
    @patch("utils.file_drop.os.path.getsize", return_value=7)
    @patch("utils.file_drop.FileDropManager.calculate_checksum", return_value="abc123")
    @patch("utils.file_drop.os.path.isfile", return_value=True)
    def test_send_url_error(self, mock_isfile, mock_checksum, mock_size, mock_urlopen):
        """send_file returns failure on URLError (connection refused)."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")
        result = FileDropManager.send_file("localhost", 8080, "/tmp/test.txt")
        self.assertFalse(result.success)
        self.assertIn("connection error", result.message.lower())

    @patch("utils.file_drop.os.path.getsize", side_effect=OSError("Permission denied"))
    @patch("utils.file_drop.FileDropManager.calculate_checksum", return_value="abc")
    @patch("utils.file_drop.os.path.isfile", return_value=True)
    def test_send_os_error(self, mock_isfile, mock_checksum, mock_size):
        """send_file returns failure on OSError during file read."""
        result = FileDropManager.send_file("localhost", 8080, "/tmp/test.txt")
        self.assertFalse(result.success)
        self.assertIn("file error", result.message.lower())


class TestValidateFilenameEdgeCases(unittest.TestCase):
    """Additional edge-case tests for validate_filename."""

    def test_filename_exactly_255_chars(self):
        """A filename of exactly 255 characters is unchanged."""
        name = "a" * 251 + ".txt"  # 255 total
        result = FileDropManager.validate_filename(name)
        self.assertEqual(len(result), 255)

    def test_single_character_filename(self):
        """A single-character filename is valid."""
        self.assertEqual(FileDropManager.validate_filename("x"), "x")

    def test_whitespace_only_filename(self):
        """A filename of only spaces is not empty after basename (spaces kept)."""
        result = FileDropManager.validate_filename("   ")
        # Spaces are not control characters, so the name may survive
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_dot_extension_only(self):
        """A filename that is only an extension like '.exe' has dot stripped."""
        result = FileDropManager.validate_filename(".exe")
        # Leading dot stripped -> 'exe'
        self.assertEqual(result, "exe")


if __name__ == "__main__":
    unittest.main()
