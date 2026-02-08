"""
Local HTTP-based file transfer for Loofi Link File Drop.
Part of v12.0 "Sovereign Update".

Handles file metadata, checksum verification, filename sanitisation,
transfer safety checks, and download directory management.
Compatible with LocalSend protocol concepts.
"""

import hashlib
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

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
