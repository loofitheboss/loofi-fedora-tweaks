"""
Encrypted clipboard sharing between Loofi instances.
Part of v12.0 "Sovereign Update".

Provides clipboard read/write for both X11 and Wayland sessions,
plus a simple symmetric encryption layer for transit security.
Includes TCP server/client for mesh network clipboard sync.
"""

import hashlib
import hmac
import logging
import os
import random
import shutil
import socket
import struct
import subprocess
import threading

from utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


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
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                    logger.debug("wl-paste failed: %s", e)

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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("xclip read failed: %s", e)

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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("xsel read failed: %s", e)

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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("wl-copy failed: %s", e)

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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("xclip write failed: %s", e)

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
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("xsel write failed: %s", e)

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
        """Encrypt data with HMAC-CTR stream cipher and authenticate with HMAC tag.

        Uses stdlib-only cryptography: HMAC-SHA256 in counter mode for
        encryption, plus a separate HMAC-SHA256 tag for authentication.

        Wire format: nonce (16 bytes) || ciphertext || HMAC tag (32 bytes)

        Args:
            data: Plaintext bytes to encrypt.
            shared_key: Symmetric key bytes (32 bytes recommended).

        Returns:
            Authenticated ciphertext bytes.
        """
        nonce = os.urandom(16)

        # Derive separate encryption and authentication keys via HKDF-like expand
        enc_key = hmac.new(shared_key, b"enc" + nonce, hashlib.sha256).digest()
        auth_key = hmac.new(shared_key, b"auth" + nonce, hashlib.sha256).digest()

        # HMAC-CTR stream cipher
        pad = ClipboardSync._derive_pad(enc_key, len(data))
        ciphertext = bytes(a ^ b for a, b in zip(data, pad))

        # Authenticate: HMAC-SHA256(auth_key, nonce || ciphertext)
        tag = hmac.new(auth_key, nonce + ciphertext, hashlib.sha256).digest()

        return nonce + ciphertext + tag

    @staticmethod
    def decrypt_payload(data: bytes, shared_key: bytes) -> bytes:
        """Decrypt and verify data encrypted with :meth:`encrypt_payload`.

        Raises ValueError if the authentication tag does not match.

        Args:
            data: Authenticated ciphertext (nonce + ciphertext + tag).
            shared_key: The same symmetric key used for encryption.

        Returns:
            Plaintext bytes.

        Raises:
            ValueError: If the data is too short or the HMAC tag is invalid.
        """
        if len(data) < 48:  # 16 nonce + 0 ciphertext + 32 tag minimum
            raise ValueError("Ciphertext too short")

        nonce = data[:16]
        tag = data[-32:]
        ciphertext = data[16:-32]

        # Re-derive keys
        enc_key = hmac.new(shared_key, b"enc" + nonce, hashlib.sha256).digest()
        auth_key = hmac.new(shared_key, b"auth" + nonce, hashlib.sha256).digest()

        # Verify tag first (constant-time comparison)
        expected_tag = hmac.new(auth_key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("Authentication failed: invalid HMAC tag")

        # Decrypt
        pad = ClipboardSync._derive_pad(enc_key, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, pad))

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

    # ------------------------------------------------------------------
    # TCP Network Clipboard Sync
    # ------------------------------------------------------------------

    # Class-level attributes for server state
    _server_socket = None
    _server_thread = None
    _server_shutdown = False

    @classmethod
    def start_clipboard_server(cls, port: int, shared_key: bytes, on_receive=None, bind_address: str = "127.0.0.1") -> bool:
        """Start a TCP server for receiving clipboard data from peers.

        Listens on the specified port for encrypted clipboard payloads.
        When data is received, decrypts with shared_key and calls the
        on_receive callback with the decrypted bytes.

        Wire format: 4-byte big-endian length prefix, then encrypted payload.

        Args:
            port: TCP port to listen on.
            shared_key: Symmetric key for decryption.
            on_receive: Callback function(data: bytes) called when data arrives.

        Returns:
            True if server started successfully.
        """
        if cls._server_socket is not None:
            return False  # Already running

        cls._server_shutdown = False

        try:
            cls._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cls._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            cls._server_socket.bind((bind_address, port))
            cls._server_socket.listen(5)
            cls._server_socket.settimeout(1.0)  # Allow periodic shutdown checks
        except OSError:
            cls._server_socket = None
            return False

        # Rate limiter: 10 connections/sec, burst of 20
        rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20)

        def server_loop():
            while not cls._server_shutdown:
                try:
                    conn, addr = cls._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                if not rate_limiter.acquire():
                    try:
                        conn.close()
                    except OSError as e:
                        logger.debug("Error closing rate-limited connection: %s", e)
                    continue

                try:
                    conn.settimeout(10.0)
                    # Read 4-byte length prefix
                    length_data = b""
                    while len(length_data) < 4:
                        chunk = conn.recv(4 - len(length_data))
                        if not chunk:
                            break
                        length_data += chunk

                    if len(length_data) < 4:
                        conn.close()
                        continue

                    payload_length = struct.unpack(">I", length_data)[0]

                    # Sanity check: limit payload size to 10MB
                    if payload_length > 10 * 1024 * 1024:
                        conn.close()
                        continue

                    # Read encrypted payload
                    encrypted_data = b""
                    while len(encrypted_data) < payload_length:
                        chunk = conn.recv(min(65536, payload_length - len(encrypted_data)))
                        if not chunk:
                            break
                        encrypted_data += chunk

                    if len(encrypted_data) == payload_length:
                        try:
                            decrypted = cls.decrypt_payload(encrypted_data, shared_key)
                            if on_receive is not None:
                                on_receive(decrypted)
                        except ValueError:
                            pass  # Decryption failed, ignore

                except (socket.timeout, OSError) as e:
                    logger.debug("Clipboard server connection error: %s", e)
                finally:
                    try:
                        conn.close()
                    except OSError as e:
                        logger.debug("Error closing connection in finally: %s", e)

        cls._server_thread = threading.Thread(target=server_loop, daemon=True)
        cls._server_thread.start()
        return True

    @classmethod
    def stop_clipboard_server(cls) -> bool:
        """Stop the TCP clipboard server.

        Sets the shutdown flag and closes the server socket, then waits
        for the server thread to finish.

        Returns:
            True if server was stopped, False if not running.
        """
        if cls._server_socket is None:
            return False

        cls._server_shutdown = True

        try:
            cls._server_socket.close()
        except OSError as e:
            logger.debug("Error closing server socket: %s", e)

        if cls._server_thread is not None:
            cls._server_thread.join(timeout=5.0)
            cls._server_thread = None

        cls._server_socket = None
        return True

    @staticmethod
    def send_clipboard_to_peer(host: str, port: int, data: bytes, shared_key: bytes) -> bool:
        """Send clipboard data to a peer over TCP.

        Encrypts the data with shared_key and sends it with a 4-byte
        big-endian length prefix.

        Args:
            host: Peer hostname or IP address.
            port: Peer TCP port.
            data: Raw clipboard data bytes to send.
            shared_key: Symmetric key for encryption.

        Returns:
            True if data was sent successfully.
        """
        try:
            encrypted = ClipboardSync.encrypt_payload(data, shared_key)
            length_prefix = struct.pack(">I", len(encrypted))

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((host, port))

            sock.sendall(length_prefix + encrypted)
            sock.close()
            return True
        except (OSError, socket.timeout):
            return False
