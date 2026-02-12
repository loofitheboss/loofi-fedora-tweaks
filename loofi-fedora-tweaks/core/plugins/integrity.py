"""
Plugin integrity verification with SHA256 checksums and optional GPG signatures.
Part of v26.0 Phase 1 (T6).
"""
import hashlib
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of integrity verification operation."""
    success: bool
    error: Optional[str] = None
    checksum: Optional[str] = None
    signature_valid: Optional[bool] = None


class IntegrityVerifier:
    """Verify plugin archive integrity with checksums and signatures."""

    @staticmethod
    def verify_checksum(archive_path: Path, expected_hash: str) -> VerificationResult:
        """
        Verify SHA256 checksum of plugin archive.

        Args:
            archive_path: Path to .loofi-plugin archive
            expected_hash: Expected SHA256 hash (hex string)

        Returns:
            VerificationResult with success status
        """
        try:
            if not archive_path.exists():
                return VerificationResult(
                    success=False,
                    error=f"Archive not found: {archive_path}"
                )

            logger.info("Verifying checksum for %s", archive_path.name)

            # Calculate SHA256 hash
            sha256_hash = hashlib.sha256()
            with open(archive_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(chunk)

            actual_hash = sha256_hash.hexdigest()

            # Compare hashes (case-insensitive)
            if actual_hash.lower() == expected_hash.lower():
                logger.info("Checksum verified successfully")
                return VerificationResult(
                    success=True,
                    checksum=actual_hash
                )
            else:
                logger.error("Checksum mismatch: expected %s, got %s", expected_hash, actual_hash)
                return VerificationResult(
                    success=False,
                    error=f"Checksum mismatch: expected {expected_hash}, got {actual_hash}",
                    checksum=actual_hash
                )

        except OSError as exc:
            logger.error("Failed to read archive: %s", exc)
            return VerificationResult(
                success=False,
                error=f"Failed to read archive: {exc}"
            )
        except Exception as exc:
            logger.error("Unexpected error during checksum verification: %s", exc)
            return VerificationResult(
                success=False,
                error=f"Verification error: {exc}"
            )

    @staticmethod
    def verify_signature(archive_path: Path, signature_path: Path) -> VerificationResult:
        """
        Verify GPG signature of plugin archive (optional).

        Args:
            archive_path: Path to .loofi-plugin archive
            signature_path: Path to .sig file

        Returns:
            VerificationResult with signature validation status
        """
        try:
            if not archive_path.exists():
                return VerificationResult(
                    success=False,
                    error=f"Archive not found: {archive_path}"
                )

            if not signature_path.exists():
                return VerificationResult(
                    success=False,
                    error=f"Signature file not found: {signature_path}"
                )

            # Check if gpg is available
            gpg_cmd = None
            for cmd in ["gpg2", "gpg"]:
                try:
                    result = subprocess.run(
                        [cmd, "--version"],
                        capture_output=True,
                        timeout=5,
                        check=False
                    )
                    if result.returncode == 0:
                        gpg_cmd = cmd
                        break
                except (FileNotFoundError, subprocess.SubprocessError):
                    continue

            if not gpg_cmd:
                logger.warning("GPG not available, skipping signature verification")
                return VerificationResult(
                    success=True,
                    signature_valid=None,
                    error="GPG not available (optional)"
                )

            logger.info("Verifying GPG signature for %s", archive_path.name)

            # Verify signature
            result = subprocess.run(
                [gpg_cmd, "--verify", str(signature_path), str(archive_path)],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode == 0:
                logger.info("GPG signature verified successfully")
                return VerificationResult(
                    success=True,
                    signature_valid=True
                )
            else:
                logger.error("GPG signature verification failed: %s", result.stderr)
                return VerificationResult(
                    success=False,
                    error=f"Invalid signature: {result.stderr.strip()}",
                    signature_valid=False
                )

        except subprocess.TimeoutExpired:
            logger.error("GPG verification timed out")
            return VerificationResult(
                success=False,
                error="GPG verification timed out"
            )
        except Exception as exc:
            logger.error("Unexpected error during signature verification: %s", exc)
            return VerificationResult(
                success=False,
                error=f"Signature verification error: {exc}"
            )

    @staticmethod
    def generate_checksums(plugin_dir: Path) -> Dict[str, str]:
        """
        Generate SHA256 checksums for all files in plugin directory.
        For plugin authors to create CHECKSUMS.sha256 file.

        Args:
            plugin_dir: Path to plugin directory

        Returns:
            Dictionary mapping relative paths to SHA256 hashes
        """
        checksums = {}

        try:
            if not plugin_dir.exists() or not plugin_dir.is_dir():
                logger.error("Plugin directory not found: %s", plugin_dir)
                return checksums

            logger.info("Generating checksums for %s", plugin_dir)

            # Walk directory and hash all files
            for root, _, files in os.walk(plugin_dir):
                for filename in files:
                    if filename == "CHECKSUMS.sha256":
                        continue  # Skip existing checksum file

                    file_path = Path(root) / filename
                    relative_path = file_path.relative_to(plugin_dir)

                    try:
                        sha256_hash = hashlib.sha256()
                        with open(file_path, "rb") as f:
                            for chunk in iter(lambda: f.read(65536), b""):
                                sha256_hash.update(chunk)

                        checksums[str(relative_path)] = sha256_hash.hexdigest()
                        logger.debug("Hashed %s: %s", relative_path, checksums[str(relative_path)])

                    except OSError as exc:
                        logger.warning("Failed to hash %s: %s", relative_path, exc)
                        continue

            logger.info("Generated %d checksums", len(checksums))

        except Exception as exc:
            logger.error("Failed to generate checksums: %s", exc)

        return checksums

    @staticmethod
    def verify_directory_checksums(plugin_dir: Path, checksums: Dict[str, str]) -> VerificationResult:
        """
        Verify all files in plugin directory against provided checksums.

        Args:
            plugin_dir: Path to plugin directory
            checksums: Dictionary mapping relative paths to expected SHA256 hashes

        Returns:
            VerificationResult with overall verification status
        """
        try:
            if not plugin_dir.exists():
                return VerificationResult(
                    success=False,
                    error=f"Plugin directory not found: {plugin_dir}"
                )

            logger.info("Verifying directory checksums for %s", plugin_dir)

            mismatches = []
            missing = []

            for relative_path, expected_hash in checksums.items():
                file_path = plugin_dir / relative_path

                if not file_path.exists():
                    missing.append(relative_path)
                    logger.warning("Missing file: %s", relative_path)
                    continue

                # Calculate actual hash
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        sha256_hash.update(chunk)

                actual_hash = sha256_hash.hexdigest()

                if actual_hash.lower() != expected_hash.lower():
                    mismatches.append(relative_path)
                    logger.warning("Checksum mismatch for %s", relative_path)

            if mismatches or missing:
                errors = []
                if mismatches:
                    errors.append(f"Checksum mismatches: {', '.join(mismatches)}")
                if missing:
                    errors.append(f"Missing files: {', '.join(missing)}")

                return VerificationResult(
                    success=False,
                    error="; ".join(errors)
                )

            logger.info("All directory checksums verified successfully")
            return VerificationResult(success=True)

        except Exception as exc:
            logger.error("Failed to verify directory checksums: %s", exc)
            return VerificationResult(
                success=False,
                error=f"Directory verification error: {exc}"
            )
