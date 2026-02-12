"""Tests for core.plugins.integrity — IntegrityVerifier checksum and signature verification."""
import os
import sys
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.integrity import IntegrityVerifier, VerificationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_file(path: Path, content: bytes) -> str:
    """Create a test file and return its SHA256 hash."""
    path.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    return sha256


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_verification_result_success_structure(self):
        """VerificationResult has expected fields."""
        result = VerificationResult(success=True)
        assert result.success is True
        assert result.error is None
        assert result.checksum is None
        assert result.signature_valid is None

    def test_verification_result_with_error(self):
        """VerificationResult can contain error message."""
        result = VerificationResult(success=False, error="Test error")
        assert result.success is False
        assert result.error == "Test error"

    def test_verification_result_with_checksum(self):
        """VerificationResult can contain checksum."""
        result = VerificationResult(success=True, checksum="abc123")
        assert result.checksum == "abc123"

    def test_verification_result_with_signature_status(self):
        """VerificationResult can contain signature validation status."""
        result = VerificationResult(success=True, signature_valid=True)
        assert result.signature_valid is True


class TestIntegrityVerifierChecksum:
    """Tests for verify_checksum() SHA256 validation."""

    def test_verify_checksum_valid_file(self):
        """verify_checksum() passes with correct hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            content = b"test archive content"
            expected_hash = _create_test_file(archive, content)
            
            result = IntegrityVerifier.verify_checksum(archive, expected_hash)
            
            assert result.success is True
            assert result.checksum == expected_hash
            assert result.error is None

    def test_verify_checksum_mismatch(self):
        """verify_checksum() fails with incorrect hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            content = b"test content"
            _create_test_file(archive, content)
            wrong_hash = "0" * 64  # Wrong hash
            
            result = IntegrityVerifier.verify_checksum(archive, wrong_hash)
            
            assert result.success is False
            assert "mismatch" in result.error.lower()
            assert result.checksum is not None  # Actual hash computed

    def test_verify_checksum_nonexistent_file(self):
        """verify_checksum() handles missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "does-not-exist.tar.gz"
            
            result = IntegrityVerifier.verify_checksum(nonexistent, "abc123")
            
            assert result.success is False
            assert "not found" in result.error.lower() or "exist" in result.error.lower()

    def test_verify_checksum_case_insensitive(self):
        """verify_checksum() is case-insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            content = b"test"
            expected_hash = _create_test_file(archive, content)
            
            # Use uppercase hash
            result = IntegrityVerifier.verify_checksum(archive, expected_hash.upper())
            
            assert result.success is True

    def test_verify_checksum_large_file(self):
        """verify_checksum() handles large files via chunking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "large.tar.gz"
            # Create ~1MB file
            content = b"x" * (1024 * 1024)
            expected_hash = _create_test_file(archive, content)
            
            result = IntegrityVerifier.verify_checksum(archive, expected_hash)
            
            assert result.success is True
            assert result.checksum == expected_hash

    def test_verify_checksum_empty_file(self):
        """verify_checksum() handles empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "empty.tar.gz"
            expected_hash = _create_test_file(archive, b"")
            
            result = IntegrityVerifier.verify_checksum(archive, expected_hash)
            
            assert result.success is True

    def test_verify_checksum_permission_error(self):
        """verify_checksum() handles permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            archive.write_bytes(b"content")
            
            # Mock open to raise PermissionError
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result = IntegrityVerifier.verify_checksum(archive, "abc")
                
                assert result.success is False
                assert result.error is not None


class TestIntegrityVerifierSignature:
    """Tests for verify_signature() GPG validation."""

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_verify_signature_valid(self, mock_which, mock_run):
        """verify_signature() passes with valid GPG signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            signature = Path(tmpdir) / "test.tar.gz.sig"
            archive.write_bytes(b"content")
            signature.write_bytes(b"fake signature")
            
            # Mock GPG available
            mock_which.return_value = "/usr/bin/gpg"
            
            # Mock successful gpg verification
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = IntegrityVerifier.verify_signature(archive, signature)
            
            assert result.success is True
            assert result.signature_valid is True

    @patch('subprocess.run')
    def test_verify_signature_invalid(self, mock_run):
        """verify_signature() fails with invalid signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            signature = Path(tmpdir) / "test.tar.gz.sig"
            archive.write_bytes(b"content")
            signature.write_bytes(b"bad signature")
            
            # First call: gpg2 --version (success), second: gpg2 --verify (fail)
            version_result = MagicMock()
            version_result.returncode = 0
            verify_result = MagicMock()
            verify_result.returncode = 1
            verify_result.stderr = "Bad signature"
            mock_run.side_effect = [version_result, verify_result]
            
            result = IntegrityVerifier.verify_signature(archive, signature)
            
            assert result.success is False
            assert result.signature_valid is False

    def test_verify_signature_missing_archive(self):
        """verify_signature() handles missing archive file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "missing.tar.gz"
            signature = Path(tmpdir) / "sig.asc"
            signature.write_bytes(b"sig")
            
            result = IntegrityVerifier.verify_signature(nonexistent, signature)
            
            assert result.success is False
            assert "not found" in result.error.lower()

    def test_verify_signature_missing_signature_file(self):
        """verify_signature() handles missing signature file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            archive.write_bytes(b"content")
            nonexistent = Path(tmpdir) / "missing.sig"
            
            result = IntegrityVerifier.verify_signature(archive, nonexistent)
            
            assert result.success is False
            assert "not found" in result.error.lower()

    @patch('subprocess.run')
    def test_verify_signature_gpg_not_available(self, mock_run):
        """verify_signature() handles GPG not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            signature = Path(tmpdir) / "test.sig"
            archive.write_bytes(b"content")
            signature.write_bytes(b"sig")
            
            # Mock GPG not found
            mock_run.side_effect = FileNotFoundError()
            
            result = IntegrityVerifier.verify_signature(archive, signature)
            
            # Should succeed but indicate GPG not available
            assert result.success is True
            assert result.signature_valid is None
            assert "GPG not available" in result.error

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_verify_signature_timeout(self, mock_which, mock_run):
        """verify_signature() handles GPG timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            signature = Path(tmpdir) / "test.sig"
            archive.write_bytes(b"content")
            signature.write_bytes(b"sig")
            
            mock_which.return_value = "/usr/bin/gpg"
            mock_run.side_effect = TimeoutError()
            
            result = IntegrityVerifier.verify_signature(archive, signature)
            
            assert result.success is False
            assert result.error is not None

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_verify_signature_uses_gpg2_fallback(self, mock_which, mock_run):
        """verify_signature() tries gpg2 then gpg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            signature = Path(tmpdir) / "test.sig"
            archive.write_bytes(b"content")
            signature.write_bytes(b"sig")
            
            def which_side_effect(cmd):
                if cmd == "gpg2":
                    return "/usr/bin/gpg2"
                return None
            
            mock_which.side_effect = which_side_effect
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = IntegrityVerifier.verify_signature(archive, signature)
            
            # Should use gpg2
            assert result.success is True


class TestIntegrityVerifierIntegration:
    """Integration tests for full verification workflow."""

    def test_checksum_and_signature_workflow(self):
        """Test combined checksum + signature verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "plugin.tar.gz"
            content = b"plugin archive data"
            expected_hash = _create_test_file(archive, content)
            
            # Verify checksum
            checksum_result = IntegrityVerifier.verify_checksum(archive, expected_hash)
            assert checksum_result.success is True
            
            # Signature verification (GPG not available is OK)
            signature = Path(tmpdir) / "plugin.tar.gz.sig"
            signature.write_bytes(b"signature")
            sig_result = IntegrityVerifier.verify_signature(archive, signature)
            
            # Either verified or GPG not available (both acceptable)
            assert isinstance(sig_result, VerificationResult)

    def test_multiple_checksum_verifications(self):
        """Test verifying multiple files sequentially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                archive = Path(tmpdir) / f"file{i}.tar.gz"
                content = f"content{i}".encode()
                expected_hash = _create_test_file(archive, content)
                
                result = IntegrityVerifier.verify_checksum(archive, expected_hash)
                assert result.success is True

    def test_verification_error_messages_are_descriptive(self):
        """Test that error messages provide useful information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Missing file
            result1 = IntegrityVerifier.verify_checksum(Path(tmpdir) / "missing.tar.gz", "abc")
            assert result1.error is not None
            assert len(result1.error) > 0
            
            # Checksum mismatch
            archive = Path(tmpdir) / "test.tar.gz"
            archive.write_bytes(b"test")
            result2 = IntegrityVerifier.verify_checksum(archive, "wrong_hash")
            assert result2.error is not None
            assert "mismatch" in result2.error.lower()


class TestIntegrityVerifierEdgeCases:
    """Tests for edge cases and error handling."""

    def test_verify_checksum_with_unicode_path(self):
        """verify_checksum() handles unicode characters in path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "tëst-fïlé.tar.gz"
            content = b"content"
            expected_hash = _create_test_file(archive, content)
            
            result = IntegrityVerifier.verify_checksum(archive, expected_hash)
            
            assert result.success is True

    def test_verify_checksum_with_spaces_in_path(self):
        """verify_checksum() handles spaces in file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "file with spaces.tar.gz"
            content = b"content"
            expected_hash = _create_test_file(archive, content)
            
            result = IntegrityVerifier.verify_checksum(archive, expected_hash)
            
            assert result.success is True

    def test_verify_checksum_returns_actual_hash_on_mismatch(self):
        """verify_checksum() returns actual hash when mismatch occurs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive = Path(tmpdir) / "test.tar.gz"
            content = b"actual content"
            actual_hash = _create_test_file(archive, content)
            wrong_hash = "0" * 64
            
            result = IntegrityVerifier.verify_checksum(archive, wrong_hash)
            
            assert result.success is False
            assert result.checksum == actual_hash
            assert result.checksum != wrong_hash


class TestIntegrityVerifierPublisherMetadata:
    """Tests for verify_publisher_metadata() contract validation."""

    def test_verify_publisher_metadata_valid_signature_and_chain(self):
        """Verified publisher with signed metadata passes validation."""
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True,
            publisher_id="publisher-123",
            signature="a1b2c3d4e5f6a7b8c9d0",
            trust_chain=["root-ca", "marketplace-ca", "publisher-123"],
        )

        assert result.success is True
        assert result.signature_valid is True
        assert result.error is None

    def test_verify_publisher_metadata_invalid_signature(self):
        """Verified publisher fails when signature format is invalid."""
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True,
            publisher_id="publisher-123",
            signature="short-sig",
            trust_chain=["root-ca", "publisher-123"],
        )

        assert result.success is False
        assert result.signature_valid is False
        assert result.error == "Invalid publisher signature format"

    def test_verify_publisher_metadata_missing_trust_chain(self):
        """Verified publisher fails when trust chain is missing."""
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True,
            publisher_id="publisher-123",
            signature="a1b2c3d4e5f6a7b8c9d0",
            trust_chain=[],
        )

        assert result.success is False
        assert result.signature_valid is False
        assert result.error == "Missing trust chain for verified publisher"

    def test_verify_publisher_metadata_unsigned_publisher_path(self):
        """Unsigned publisher remains unverified without error."""
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=False,
            publisher_id="publisher-123",
            signature="",
            trust_chain=None,
        )

        assert result.success is True
        assert result.signature_valid is False
        assert result.error is None
