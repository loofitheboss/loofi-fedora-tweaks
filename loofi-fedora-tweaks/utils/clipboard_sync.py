"""
Encrypted clipboard sharing between Loofi instances.
Part of v12.0 "Sovereign Update".

Provides clipboard read/write for both X11 and Wayland sessions,
plus a simple symmetric encryption layer for transit security.
"""

import hashlib
import hmac
import os
import random
import shutil
import subprocess


class ClipboardSync:
    """Clipboard synchronisation across Loofi Link peers."""

    @staticmethod
    def get_clipboard_content() -> str:
        """Read the current clipboard content using the appropriate tool.

        Tries wayland tools first when running under Wayland, then X11 tools.

        Returns:
            The clipboard text, or an empty string on failure.
        """
        display = ClipboardSync.detect_display_server()

        if display == "wayland":
            # Try wl-paste first
            if shutil.which("wl-paste"):
                try:
                    result = subprocess.run(
                        ["wl-paste", "--no-newline"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return result.stdout
                except (subprocess.TimeoutExpired, Exception):
                    pass

        # X11 / fallback
        if shutil.which("xclip"):
            try:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout
            except (subprocess.TimeoutExpired, Exception):
                pass

        if shutil.which("xsel"):
            try:
                result = subprocess.run(
                    ["xsel", "--clipboard", "--output"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout
            except (subprocess.TimeoutExpired, Exception):
                pass

        return ""

    @staticmethod
    def set_clipboard_content(text: str) -> bool:
        """Write text to the system clipboard.

        Args:
            text: The string to place on the clipboard.

        Returns:
            True if the write succeeded.
        """
        display = ClipboardSync.detect_display_server()

        if display == "wayland" and shutil.which("wl-copy"):
            try:
                result = subprocess.run(
                    ["wl-copy"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, Exception):
                pass

        if shutil.which("xclip"):
            try:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, Exception):
                pass

        if shutil.which("xsel"):
            try:
                result = subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, Exception):
                pass

        return False

    @staticmethod
    def is_clipboard_tool_available() -> dict:
        """Check which clipboard tools are installed.

        Returns:
            Dict with keys ``"x11"`` and ``"wayland"``, each a bool.
        """
        x11 = (shutil.which("xclip") is not None) or (shutil.which("xsel") is not None)
        wayland = shutil.which("wl-copy") is not None and shutil.which("wl-paste") is not None
        return {"x11": x11, "wayland": wayland}

    @staticmethod
    def detect_display_server() -> str:
        """Detect whether the session is X11, Wayland, or unknown.

        Returns:
            ``"wayland"``, ``"x11"``, or ``"unknown"``.
        """
        xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if xdg_session == "wayland":
            return "wayland"
        if xdg_session == "x11":
            return "x11"

        # Secondary check
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("DISPLAY"):
            return "x11"

        return "unknown"

    @staticmethod
    def encrypt_payload(data: bytes, shared_key: bytes) -> bytes:
        """Encrypt data with a simple XOR pad derived from the shared key.

        This is a **placeholder** for production-grade NaCl/WireGuard encryption.
        NOT suitable for real adversarial security in its current form.

        Args:
            data: Plaintext bytes to encrypt.
            shared_key: Symmetric key bytes.

        Returns:
            Ciphertext bytes (same length as data).
        """
        pad = ClipboardSync._derive_pad(shared_key, len(data))
        return bytes(a ^ b for a, b in zip(data, pad))

    @staticmethod
    def decrypt_payload(data: bytes, shared_key: bytes) -> bytes:
        """Decrypt data previously encrypted with :meth:`encrypt_payload`.

        XOR encryption is symmetric so this is identical to encrypt.

        Args:
            data: Ciphertext bytes.
            shared_key: The same symmetric key used for encryption.

        Returns:
            Plaintext bytes.
        """
        return ClipboardSync.encrypt_payload(data, shared_key)

    @staticmethod
    def generate_pairing_key() -> str:
        """Generate a 6-digit numeric pairing code for device pairing.

        Returns:
            A string of exactly 6 digits, zero-padded.
        """
        code = random.SystemRandom().randint(0, 999999)
        return f"{code:06d}"

    @staticmethod
    def derive_shared_key(pairing_code: str, device_id: str) -> bytes:
        """Derive a 32-byte shared key using PBKDF2-HMAC-SHA256.

        The pairing code acts as the password and the device_id as the salt,
        ensuring the same pairing code on a different device pair produces
        a different key.

        Args:
            pairing_code: The 6-digit numeric pairing code.
            device_id: UUID of the peer device (used as salt).

        Returns:
            32-byte derived key.
        """
        return hashlib.pbkdf2_hmac(
            "sha256",
            pairing_code.encode("utf-8"),
            device_id.encode("utf-8"),
            iterations=100_000,
            dklen=32,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_pad(key: bytes, length: int) -> bytes:
        """Create an XOR pad of *length* bytes from *key* via iterated HMAC.

        Args:
            key: The symmetric key.
            length: Number of pad bytes required.

        Returns:
            Bytes of the requested length.
        """
        pad = b""
        counter = 0
        while len(pad) < length:
            block = hmac.new(
                key,
                counter.to_bytes(4, "big"),
                hashlib.sha256,
            ).digest()
            pad += block
            counter += 1
        return pad[:length]
