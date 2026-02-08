"""
Local HTTP-based file transfer for Loofi Link File Drop.
Part of v12.0 "Sovereign Update".

Handles file metadata, checksum verification, filename sanitisation,
transfer safety checks, and download directory management.
Compatible with LocalSend protocol concepts.
Includes HTTP server for receiving files and client for sending.
"""

import hashlib
import mimetypes
import os
import re
import threading
import uuid
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from utils.containers import Result


DEFAULT_PORT = 53317
CHUNK_SIZE = 65536  # 64 KB chunks
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB limit
DOWNLOAD_DIR = "~/Downloads/Loofi"

# Extensions the user should be warned about before accepting
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi", ".vbs",
    ".com", ".scr", ".pif", ".reg", ".jar", ".cpl",
}


@dataclass
class TransferInfo:
    """Tracks state of a single file transfer."""
    transfer_id: str       # UUID
    filename: str
    file_size: int
    sender_name: str
    sender_address: str
    status: str            # "pending", "in_progress", "completed", "failed", "cancelled"
    progress: float = 0.0  # 0.0 to 1.0
    speed_bps: int = 0     # bytes per second


class FileDropManager:
    """Manages local file transfer operations for Loofi Link."""

    # In-memory transfer registry
    _transfers: dict = {}  # transfer_id -> TransferInfo

    @staticmethod
    def get_download_dir() -> str:
        """Create ~/Downloads/Loofi if it does not exist and return its path.

        Returns:
            Absolute path to the download directory.
        """
        path = os.path.expanduser(DOWNLOAD_DIR)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def prepare_file_metadata(file_path: str) -> dict:
        """Build metadata dict for a file to be transferred.

        Args:
            file_path: Absolute path to the file.

        Returns:
            Dict with keys: name, size, mime_type, checksum_sha256.
        """
        abs_path = os.path.abspath(file_path)
        return {
            "name": os.path.basename(abs_path),
            "size": os.path.getsize(abs_path),
            "mime_type": FileDropManager.get_file_mime_type(abs_path),
            "checksum_sha256": FileDropManager.calculate_checksum(abs_path),
        }

    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        """Compute the SHA-256 hex digest of a file using streaming reads.

        Args:
            file_path: Path to the file.

        Returns:
            Hex-encoded SHA-256 digest string.
        """
        sha = hashlib.sha256()
        with open(file_path, "rb") as fh:
            while True:
                chunk = fh.read(CHUNK_SIZE)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def validate_filename(filename: str) -> str:
        """Sanitise a filename to prevent path-traversal and injection.

        Removes directory separators, null bytes, leading dots/dashes, and
        clamps total length to 255 characters.

        Args:
            filename: The raw filename from the sender.

        Returns:
            A safe filename string.
        """
        # Remove null bytes
        filename = filename.replace("\x00", "")

        # Strip any directory components (path traversal)
        filename = os.path.basename(filename)
        filename = filename.replace("..", "")
        filename = filename.replace("/", "")
        filename = filename.replace("\\", "")

        # Remove control characters
        filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)

        # Strip leading dots and dashes (hidden files / option injection)
        filename = filename.lstrip(".-")

        # Clamp length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[: 255 - len(ext)] + ext

        # Fallback for empty result
        if not filename:
            filename = "unnamed_file"

        return filename

    @staticmethod
    def generate_transfer_id() -> str:
        """Generate a new UUID4 transfer identifier.

        Returns:
            UUID string.
        """
        return str(uuid.uuid4())

    @staticmethod
    def get_file_mime_type(file_path: str) -> str:
        """Guess the MIME type of a file.

        Args:
            file_path: Path to the file.

        Returns:
            MIME type string, defaulting to ``application/octet-stream``.
        """
        mime, _ = mimetypes.guess_type(file_path)
        return mime or "application/octet-stream"

    @staticmethod
    def format_transfer_speed(bytes_per_sec: int) -> str:
        """Format a transfer speed into a human-readable string.

        Args:
            bytes_per_sec: Speed in bytes per second.

        Returns:
            String like ``"2.5 MB/s"``.
        """
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.1f} GB/s"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format a file size into a human-readable string.

        Args:
            size_bytes: Size in bytes.

        Returns:
            String like ``"4.2 MB"``.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes < 1024 * 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024 * 1024):.1f} TB"

    @staticmethod
    def is_transfer_safe(filename: str, file_size: int) -> tuple:
        """Check whether a proposed file transfer is safe to accept.

        Validates file size, extension, and available disk space.

        Args:
            filename: The sanitised filename.
            file_size: Size in bytes.

        Returns:
            Tuple of (is_safe: bool, reason: str).
        """
        # Size check
        if file_size > MAX_FILE_SIZE:
            return (False, f"File exceeds maximum allowed size of {FileDropManager.format_file_size(MAX_FILE_SIZE)}.")

        if file_size < 0:
            return (False, "Invalid file size.")

        # Dangerous extension check
        _, ext = os.path.splitext(filename)
        if ext.lower() in DANGEROUS_EXTENSIONS:
            return (False, f"Potentially dangerous file extension: {ext}")

        # Disk space check
        download_dir = FileDropManager.get_download_dir()
        available = FileDropManager.get_available_disk_space(download_dir)
        if file_size > available:
            return (False, "Insufficient disk space for this transfer.")

        return (True, "Transfer is safe.")

    @staticmethod
    def get_available_disk_space(path: str) -> int:
        """Return available disk space in bytes at the given path.

        Args:
            path: Directory path to check.

        Returns:
            Available space in bytes.
        """
        stat = os.statvfs(path)
        return stat.f_bavail * stat.f_frsize

    @staticmethod
    def build_http_server_command(port: int, directory: str) -> tuple:
        """Build a command tuple for a simple Python HTTP file server.

        Args:
            port: TCP port to listen on.
            directory: Directory to serve files from.

        Returns:
            Tuple of (command, args) suitable for subprocess.
        """
        return (
            "python3",
            ["-m", "http.server", str(port), "--directory", directory],
        )

    @classmethod
    def list_pending_transfers(cls) -> list:
        """Return all transfers with status ``'pending'``.

        Returns:
            List of TransferInfo objects.
        """
        return [t for t in cls._transfers.values() if t.status == "pending"]

    @classmethod
    def accept_transfer(cls, transfer_id: str) -> Result:
        """Accept a pending incoming transfer.

        Args:
            transfer_id: UUID of the transfer.

        Returns:
            Result with success/failure.
        """
        transfer = cls._transfers.get(transfer_id)
        if transfer is None:
            return Result(success=False, message="Transfer not found.")
        if transfer.status != "pending":
            return Result(success=False, message=f"Transfer is not pending (status: {transfer.status}).")
        transfer.status = "in_progress"
        return Result(success=True, message="Transfer accepted.")

    @classmethod
    def reject_transfer(cls, transfer_id: str) -> Result:
        """Reject a pending incoming transfer.

        Args:
            transfer_id: UUID of the transfer.

        Returns:
            Result with success/failure.
        """
        transfer = cls._transfers.get(transfer_id)
        if transfer is None:
            return Result(success=False, message="Transfer not found.")
        if transfer.status != "pending":
            return Result(success=False, message=f"Transfer is not pending (status: {transfer.status}).")
        transfer.status = "cancelled"
        return Result(success=True, message="Transfer rejected.")

    # ------------------------------------------------------------------
    # HTTP File Transfer Server/Client
    # ------------------------------------------------------------------

    # Class-level server state
    _http_server = None
    _http_server_thread = None
    _http_save_dir = None
    _http_shared_key = None

    @classmethod
    def start_receive_server(cls, port: int, save_dir: str, shared_key: bytes = None) -> bool:
        """Start an HTTP server for receiving file uploads.

        Accepts POST requests to /upload with file data. The file is saved
        to save_dir after optional checksum verification.

        Headers:
            X-Filename: Original filename
            X-Checksum-SHA256: Expected SHA-256 checksum (optional)

        Args:
            port: TCP port to listen on.
            save_dir: Directory to save received files.
            shared_key: Optional shared key (reserved for future encryption).

        Returns:
            True if server started successfully.
        """
        if cls._http_server is not None:
            return False  # Already running

        # Ensure save directory exists
        os.makedirs(save_dir, exist_ok=True)
        cls._http_save_dir = save_dir
        cls._http_shared_key = shared_key

        class FileUploadHandler(BaseHTTPRequestHandler):
            """HTTP request handler for file uploads."""

            def log_message(self, format, *args):
                """Suppress default logging."""
                pass

            def do_POST(self):
                """Handle POST /upload requests."""
                if self.path != "/upload":
                    self.send_error(404, "Not Found")
                    return

                # Get headers
                filename = self.headers.get("X-Filename", "uploaded_file")
                expected_checksum = self.headers.get("X-Checksum-SHA256", "")
                content_length = int(self.headers.get("Content-Length", 0))

                if content_length <= 0:
                    self.send_error(400, "No content")
                    return

                # Sanity check size (10GB max)
                if content_length > MAX_FILE_SIZE:
                    self.send_error(413, "File too large")
                    return

                # Sanitize filename
                safe_filename = FileDropManager.validate_filename(filename)

                # Read file data
                file_data = b""
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(CHUNK_SIZE, remaining)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    file_data += chunk
                    remaining -= len(chunk)

                # Verify checksum if provided
                if expected_checksum:
                    actual_checksum = hashlib.sha256(file_data).hexdigest()
                    if actual_checksum != expected_checksum:
                        self.send_error(400, "Checksum mismatch")
                        return

                # Save file
                save_path = os.path.join(cls._http_save_dir, safe_filename)

                # Handle filename conflicts
                base, ext = os.path.splitext(save_path)
                counter = 1
                while os.path.exists(save_path):
                    save_path = f"{base}_{counter}{ext}"
                    counter += 1

                with open(save_path, "wb") as f:
                    f.write(file_data)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')

        try:
            cls._http_server = HTTPServer(("0.0.0.0", port), FileUploadHandler)
        except OSError:
            cls._http_server = None
            return False

        def server_loop():
            cls._http_server.serve_forever()

        cls._http_server_thread = threading.Thread(target=server_loop, daemon=True)
        cls._http_server_thread.start()
        return True

    @classmethod
    def stop_receive_server(cls) -> bool:
        """Stop the HTTP receive server.

        Returns:
            True if server was stopped, False if not running.
        """
        if cls._http_server is None:
            return False

        cls._http_server.shutdown()

        if cls._http_server_thread is not None:
            cls._http_server_thread.join(timeout=5.0)
            cls._http_server_thread = None

        cls._http_server = None
        cls._http_save_dir = None
        cls._http_shared_key = None
        return True

    @staticmethod
    def send_file(host: str, port: int, file_path: str, shared_key: bytes = None) -> Result:
        """Send a file to a peer via HTTP POST.

        Uploads the file to http://host:port/upload with filename and
        checksum headers.

        Args:
            host: Peer hostname or IP address.
            port: Peer HTTP port.
            file_path: Path to the file to send.
            shared_key: Optional shared key (reserved for future encryption).

        Returns:
            Result with success/failure.
        """
        if not os.path.isfile(file_path):
            return Result(success=False, message=f"File not found: {file_path}")

        try:
            filename = os.path.basename(file_path)
            checksum = FileDropManager.calculate_checksum(file_path)
            file_size = os.path.getsize(file_path)

            with open(file_path, "rb") as f:
                file_data = f.read()

            url = f"http://{host}:{port}/upload"
            headers = {
                "X-Filename": filename,
                "X-Checksum-SHA256": checksum,
                "Content-Type": "application/octet-stream",
                "Content-Length": str(file_size),
            }

            request = Request(url, data=file_data, headers=headers, method="POST")

            with urlopen(request, timeout=60) as response:
                if response.status == 200:
                    return Result(success=True, message=f"File sent successfully: {filename}")
                else:
                    return Result(success=False, message=f"Server returned status {response.status}")

        except HTTPError as e:
            return Result(success=False, message=f"HTTP error: {e.code} {e.reason}")
        except URLError as e:
            return Result(success=False, message=f"Connection error: {e.reason}")
        except OSError as e:
            return Result(success=False, message=f"File error: {e}")
