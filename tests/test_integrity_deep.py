"""Tests for core.plugins.integrity — IntegrityVerifier (67 miss, 55.3%)."""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from core.plugins.integrity import IntegrityVerifier, VerificationResult


class TestVerifyChecksum(unittest.TestCase):
    def test_matching_checksum(self):
        with tempfile.NamedTemporaryFile(suffix=".loofi-plugin", delete=False) as f:
            f.write(b"test content for checksum")
            f.flush()
            expected = hashlib.sha256(b"test content for checksum").hexdigest()
            result = IntegrityVerifier.verify_checksum(Path(f.name), expected)
            self.assertTrue(result.success)
            self.assertEqual(result.checksum, expected)
        os.unlink(f.name)

    def test_mismatching_checksum(self):
        with tempfile.NamedTemporaryFile(suffix=".loofi-plugin", delete=False) as f:
            f.write(b"actual content")
            f.flush()
            result = IntegrityVerifier.verify_checksum(Path(f.name), "deadbeef" * 8)
            self.assertFalse(result.success)
            self.assertIn("mismatch", result.error.lower())
        os.unlink(f.name)

    def test_archive_not_found(self):
        result = IntegrityVerifier.verify_checksum(Path("/nonexistent/archive.tar"), "abc")
        self.assertFalse(result.success)
        self.assertIn("not found", result.error.lower())

    def test_case_insensitive(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            f.flush()
            expected = hashlib.sha256(b"data").hexdigest().upper()
            result = IntegrityVerifier.verify_checksum(Path(f.name), expected)
            self.assertTrue(result.success)
        os.unlink(f.name)


class TestVerifySignature(unittest.TestCase):
    def test_archive_not_found(self):
        result = IntegrityVerifier.verify_signature(
            Path("/nonexistent/a.tar"), Path("/nonexistent/a.sig")
        )
        self.assertFalse(result.success)

    def test_signature_not_found(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            f.flush()
            result = IntegrityVerifier.verify_signature(
                Path(f.name), Path("/nonexistent/a.sig")
            )
            self.assertFalse(result.success)
        os.unlink(f.name)

    @patch("subprocess.run")
    def test_gpg_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("no gpg")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as a:
            a.write(b"archive")
            a.flush()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sig") as s:
                s.write(b"sig")
                s.flush()
                result = IntegrityVerifier.verify_signature(Path(a.name), Path(s.name))
                # GPG not available is treated as soft success
                self.assertTrue(result.success)
                self.assertIsNone(result.signature_valid)
        os.unlink(a.name)
        os.unlink(s.name)

    @patch("subprocess.run")
    def test_gpg_valid_signature(self, mock_run):
        # First call: gpg --version (success), second: gpg --verify (success)
        mock_run.return_value = MagicMock(returncode=0, stdout="gpg 2.3", stderr="")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as a:
            a.write(b"archive")
            a.flush()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sig") as s:
                s.write(b"sig")
                s.flush()
                result = IntegrityVerifier.verify_signature(Path(a.name), Path(s.name))
                self.assertTrue(result.success)
                self.assertTrue(result.signature_valid)
        os.unlink(a.name)
        os.unlink(s.name)

    @patch("subprocess.run")
    def test_gpg_invalid_signature(self, mock_run):
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="gpg 2.3", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="BAD signature")
        mock_run.side_effect = side_effect
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as a:
            a.write(b"archive")
            a.flush()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sig") as s:
                s.write(b"sig")
                s.flush()
                result = IntegrityVerifier.verify_signature(Path(a.name), Path(s.name))
                self.assertFalse(result.success)
                self.assertFalse(result.signature_valid)
        os.unlink(a.name)
        os.unlink(s.name)

    @patch("subprocess.run")
    def test_gpg_timeout(self, mock_run):
        import subprocess as sp
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="gpg 2.3")
            raise sp.TimeoutExpired(cmd, 10)
        mock_run.side_effect = side_effect
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as a:
            a.write(b"archive")
            a.flush()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sig") as s:
                s.write(b"sig")
                s.flush()
                result = IntegrityVerifier.verify_signature(Path(a.name), Path(s.name))
                self.assertFalse(result.success)
                self.assertIn("timed out", result.error.lower())
        os.unlink(a.name)
        os.unlink(s.name)


class TestGenerateChecksums(unittest.TestCase):
    def test_valid_directory(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "file1.py").write_text("hello")
            (Path(d) / "file2.txt").write_text("world")
            result = IntegrityVerifier.generate_checksums(Path(d))
            self.assertEqual(len(result), 2)
            self.assertIn("file1.py", result)

    def test_skips_checksums_file(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "CHECKSUMS.sha256").write_text("skip me")
            (Path(d) / "real.py").write_text("code")
            result = IntegrityVerifier.generate_checksums(Path(d))
            self.assertNotIn("CHECKSUMS.sha256", result)
            self.assertIn("real.py", result)

    def test_nonexistent_dir(self):
        result = IntegrityVerifier.generate_checksums(Path("/nonexistent/dir"))
        self.assertEqual(result, {})

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            result = IntegrityVerifier.generate_checksums(Path(d))
            self.assertEqual(result, {})


class TestVerifyDirectoryChecksums(unittest.TestCase):
    def test_all_match(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.py").write_bytes(b"hello")
            expected = hashlib.sha256(b"hello").hexdigest()
            result = IntegrityVerifier.verify_directory_checksums(
                Path(d), {"a.py": expected}
            )
            self.assertTrue(result.success)

    def test_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.py").write_bytes(b"hello")
            result = IntegrityVerifier.verify_directory_checksums(
                Path(d), {"a.py": "wrong" * 16}
            )
            self.assertFalse(result.success)
            self.assertIn("mismatch", result.error.lower())

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            result = IntegrityVerifier.verify_directory_checksums(
                Path(d), {"missing.py": "abc123"}
            )
            self.assertFalse(result.success)
            self.assertIn("missing", result.error.lower())

    def test_dir_not_found(self):
        result = IntegrityVerifier.verify_directory_checksums(
            Path("/nonexistent"), {"a.py": "abc"}
        )
        self.assertFalse(result.success)


class TestVerifyPublisherMetadata(unittest.TestCase):
    def test_not_verified(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=False, publisher_id="", signature=""
        )
        self.assertTrue(result.success)
        self.assertFalse(result.signature_valid)

    def test_missing_publisher_id(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="", signature="a" * 20,
            trust_chain=["root"]
        )
        self.assertFalse(result.success)

    def test_missing_signature(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="",
            trust_chain=["root"]
        )
        self.assertFalse(result.success)

    def test_short_signature(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="short",
            trust_chain=["root"]
        )
        self.assertFalse(result.success)

    def test_missing_trust_chain(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="a" * 20,
            trust_chain=None
        )
        self.assertFalse(result.success)

    def test_empty_trust_chain(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="a" * 20,
            trust_chain=[]
        )
        self.assertFalse(result.success)

    def test_invalid_chain_entry(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="a" * 20,
            trust_chain=["root", ""]
        )
        self.assertFalse(result.success)

    def test_duplicate_chain_entries(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="a" * 20,
            trust_chain=["root", "root"]
        )
        self.assertFalse(result.success)

    def test_valid_publisher(self):
        result = IntegrityVerifier.verify_publisher_metadata(
            verified=True, publisher_id="pub1", signature="a" * 20,
            trust_chain=["root", "intermediate"]
        )
        self.assertTrue(result.success)
        self.assertTrue(result.signature_valid)


class TestVerificationResult(unittest.TestCase):
    def test_defaults(self):
        r = VerificationResult(success=True)
        self.assertTrue(r.success)
        self.assertIsNone(r.error)
        self.assertIsNone(r.checksum)
        self.assertIsNone(r.signature_valid)


if __name__ == "__main__":
    unittest.main()
