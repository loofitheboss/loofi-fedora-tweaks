"""
Secure Boot Manager - MOK (Machine Owner Key) management.
Helps users manage Secure Boot for third-party kernel modules.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SecureBootResult:
    """Result of a Secure Boot operation."""

    success: bool
    message: str
    output: str = ""
    requires_reboot: bool = False


@dataclass
class SecureBootStatus:
    """Secure Boot system status."""

    secure_boot_enabled: bool
    mok_enrolled: bool
    pending_mok: bool
    status_message: str


class SecureBootManager:
    """
    Manages Secure Boot and MOK (Machine Owner Key) enrollment.
    Useful for signing NVIDIA drivers, VirtualBox modules, etc.
    """

    MOK_KEY_DIR = Path.home() / ".local/share/loofi-fedora-tweaks/mok"
    PRIVATE_KEY = "MOK.priv"
    PUBLIC_KEY = "MOK.der"

    @classmethod
    def get_status(cls) -> SecureBootStatus:
        """
        Get current Secure Boot and MOK status.

        Returns:
            SecureBootStatus with current state.
        """
        # Check if Secure Boot is enabled
        secure_boot_enabled = False
        try:
            result = subprocess.run(
                ["mokutil", "--sb-state"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            secure_boot_enabled = "SecureBoot enabled" in result.stdout
            status_msg = result.stdout.strip()
        except FileNotFoundError:
            status_msg = "mokutil not installed"
        except Exception as e:
            status_msg = f"Error checking status: {e}"

        # Check for enrolled MOKs
        mok_enrolled = False
        try:
            result = subprocess.run(
                ["mokutil", "--list-enrolled"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            mok_enrolled = result.returncode == 0 and bool(result.stdout.strip())
        except Exception as e:
            logger.debug("Failed to check enrolled MOKs: %s", e)

        # Check for pending MOK enrollment
        pending_mok = False
        try:
            result = subprocess.run(
                ["mokutil", "--list-new"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            pending_mok = result.returncode == 0 and bool(result.stdout.strip())
        except Exception as e:
            logger.debug("Failed to check pending MOK enrollment: %s", e)

        return SecureBootStatus(
            secure_boot_enabled=secure_boot_enabled,
            mok_enrolled=mok_enrolled,
            pending_mok=pending_mok,
            status_message=status_msg,
        )

    @classmethod
    def generate_key(cls, password: str) -> SecureBootResult:
        """
        Generate a new MOK signing key pair.

        Args:
            password: Password to protect the key (needed during enrollment).

        Returns:
            SecureBootResult with key paths if successful.
        """
        if len(password) < 8:
            return SecureBootResult(False, "Password must be at least 8 characters")

        try:
            cls.MOK_KEY_DIR.mkdir(parents=True, exist_ok=True)

            priv_key = cls.MOK_KEY_DIR / cls.PRIVATE_KEY
            pub_key = cls.MOK_KEY_DIR / cls.PUBLIC_KEY

            # Generate private key
            cmd_priv = [
                "openssl",
                "req",
                "-new",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(priv_key),
                "-outform",
                "DER",
                "-out",
                str(pub_key),
                "-nodes",
                "-days",
                "36500",
                "-subj",
                "/CN=Loofi Fedora Tweaks MOK/",
            ]

            result = subprocess.run(
                cmd_priv, capture_output=True, text=True, check=False, timeout=60
            )

            if result.returncode != 0:
                return SecureBootResult(
                    False, f"Key generation failed: {result.stderr}"
                )

            # Set proper permissions
            os.chmod(priv_key, 0o600)

            return SecureBootResult(
                success=True,
                message=f"Keys generated:\n  Private: {priv_key}\n  Public: {pub_key}",
                output=f"Private key: {priv_key}\nPublic key: {pub_key}",
            )

        except Exception as e:
            return SecureBootResult(False, f"Error: {str(e)}")

    @classmethod
    def import_key(cls, password: str) -> SecureBootResult:
        """
        Import the MOK public key for enrollment.
        User will need to complete enrollment on next reboot.

        Args:
            password: Password for the key (will be needed at boot).

        Returns:
            SecureBootResult with enrollment status.
        """
        pub_key = cls.MOK_KEY_DIR / cls.PUBLIC_KEY

        if not pub_key.exists():
            return SecureBootResult(False, "No MOK key found. Generate one first.")

        try:
            # Import requires password input
            cmd = ["mokutil", "--import", str(pub_key)]

            # mokutil reads password from stdin
            result = subprocess.run(
                cmd,
                input=f"{password}\n{password}\n",
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

            if result.returncode == 0:
                return SecureBootResult(
                    success=True,
                    message="MOK key queued for enrollment.\n\n"
                    "On next reboot:\n"
                    "1. A blue MOK Manager screen will appear\n"
                    "2. Select 'Enroll MOK'\n"
                    "3. Select 'Continue'\n"
                    "4. Enter your password\n"
                    "5. Select 'Reboot'",
                    requires_reboot=True,
                )
            else:
                return SecureBootResult(False, f"Import failed: {result.stderr}")

        except Exception as e:
            return SecureBootResult(False, f"Error: {str(e)}")

    @classmethod
    def sign_module(cls, module_path: str) -> SecureBootResult:
        """
        Sign a kernel module with the MOK key.

        Args:
            module_path: Path to the .ko kernel module file.

        Returns:
            SecureBootResult with signing status.
        """
        priv_key = cls.MOK_KEY_DIR / cls.PRIVATE_KEY
        pub_key = cls.MOK_KEY_DIR / cls.PUBLIC_KEY

        if not priv_key.exists() or not pub_key.exists():
            return SecureBootResult(False, "MOK keys not found. Generate them first.")

        if not os.path.exists(module_path):
            return SecureBootResult(False, f"Module not found: {module_path}")

        # Find the sign-file utility
        sign_file = None
        for path in [
            "/usr/src/kernels/*/scripts/sign-file",
            "/lib/modules/*/build/scripts/sign-file",
        ]:
            import glob

            matches = glob.glob(path)
            if matches:
                sign_file = matches[0]
                break

        if not sign_file:
            return SecureBootResult(
                False, "sign-file utility not found. Install kernel-devel package."
            )

        try:
            cmd = [
                "pkexec",
                sign_file,
                "sha256",
                str(priv_key),
                str(pub_key),
                module_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=60
            )

            if result.returncode == 0:
                return SecureBootResult(
                    success=True, message=f"Module signed successfully: {module_path}"
                )
            else:
                return SecureBootResult(False, f"Signing failed: {result.stderr}")

        except Exception as e:
            return SecureBootResult(False, f"Error: {str(e)}")

    @classmethod
    def has_keys(cls) -> bool:
        """Check if MOK keys exist."""
        priv_key = cls.MOK_KEY_DIR / cls.PRIVATE_KEY
        pub_key = cls.MOK_KEY_DIR / cls.PUBLIC_KEY
        return priv_key.exists() and pub_key.exists()

    @classmethod
    def get_key_path(cls) -> Optional[Path]:
        """Get path to MOK public key if it exists."""
        pub_key = cls.MOK_KEY_DIR / cls.PUBLIC_KEY
        return pub_key if pub_key.exists() else None
