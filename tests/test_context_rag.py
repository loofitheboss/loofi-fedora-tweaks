"""Tests for utils/context_rag.py — ContextRAGManager.

Covers all static methods: path helpers, sensitivity/binary detection,
chunking, path resolution, scanning, indexing, TF-IDF search, stats,
clear, and is_indexed. Both success and failure paths.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.context_rag import (
    ContextRAGManager,
    INDEXABLE_PATHS,
    MAX_FILE_SIZE,
    MAX_INDEX_SIZE,
    _CHUNK_OVERLAP,
    _CHUNK_SIZE,
    _SENSITIVE_FILENAME_KEYWORDS,
)


# ---------------------------------------------------------------------------
# get_index_path / _get_index_file_path
# ---------------------------------------------------------------------------


class TestGetIndexPath(unittest.TestCase):
    """Tests for index path helpers."""

    @patch("utils.context_rag.os.path.expanduser", return_value="/home/testuser")
    def test_get_index_path_returns_expected(self, mock_expand):
        """get_index_path returns ~/.config/loofi-fedora-tweaks/rag_index/."""
        result = ContextRAGManager.get_index_path()
        self.assertEqual(
            result,
            os.path.join(
                "/home/testuser", ".config", "loofi-fedora-tweaks", "rag_index"
            ),
        )
        mock_expand.assert_called_once_with("~")

    @patch("utils.context_rag.os.path.expanduser", return_value="/home/testuser")
    def test_get_index_file_path_appends_filename(self, mock_expand):
        """_get_index_file_path appends index.json to index path."""
        result = ContextRAGManager._get_index_file_path()
        self.assertTrue(result.endswith("index.json"))
        self.assertIn("rag_index", result)


# ---------------------------------------------------------------------------
# _is_sensitive_filename
# ---------------------------------------------------------------------------


class TestIsSensitiveFilename(unittest.TestCase):
    """Tests for sensitive filename detection."""

    def test_password_keyword(self):
        """Filenames containing 'password' are sensitive."""
        self.assertTrue(ContextRAGManager._is_sensitive_filename("my_password.txt"))

    def test_secret_keyword(self):
        """Filenames containing 'secret' are sensitive."""
        self.assertTrue(ContextRAGManager._is_sensitive_filename("app_secret.json"))

    def test_token_keyword(self):
        """Filenames containing 'token' are sensitive."""
        self.assertTrue(ContextRAGManager._is_sensitive_filename("access_token"))

    def test_key_keyword(self):
        """Filenames containing 'key' are sensitive."""
        self.assertTrue(ContextRAGManager._is_sensitive_filename("id_rsa_key"))

    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        self.assertTrue(ContextRAGManager._is_sensitive_filename("MY_SECRET.env"))
        self.assertTrue(ContextRAGManager._is_sensitive_filename("PASSWORD_FILE"))

    def test_safe_filename(self):
        """Regular filenames are not sensitive."""
        self.assertFalse(ContextRAGManager._is_sensitive_filename(".bashrc"))
        self.assertFalse(ContextRAGManager._is_sensitive_filename("config.json"))


# ---------------------------------------------------------------------------
# _is_binary_file
# ---------------------------------------------------------------------------


class TestIsBinaryFile(unittest.TestCase):
    """Tests for binary file detection."""

    @patch("builtins.open", mock_open(read_data=b"hello world"))
    def test_text_file_not_binary(self):
        """Text file without null bytes is not binary."""
        self.assertFalse(ContextRAGManager._is_binary_file("/tmp/text.txt"))

    @patch("builtins.open", mock_open(read_data=b"hello\x00world"))
    def test_binary_file_with_null(self):
        """File with null byte in first 512 bytes is binary."""
        self.assertTrue(ContextRAGManager._is_binary_file("/tmp/bin.dat"))

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_unreadable_file_treated_as_binary(self, mock_f):
        """Unreadable files default to binary (True)."""
        self.assertTrue(ContextRAGManager._is_binary_file("/tmp/noperm"))

    @patch("builtins.open", side_effect=IOError("IO error"))
    def test_ioerror_treated_as_binary(self, mock_f):
        """IOError defaults to binary (True)."""
        self.assertTrue(ContextRAGManager._is_binary_file("/tmp/broken"))


# ---------------------------------------------------------------------------
# _chunk_text
# ---------------------------------------------------------------------------


class TestChunkText(unittest.TestCase):
    """Tests for text chunking logic."""

    def test_empty_text(self):
        """Empty string produces no chunks."""
        self.assertEqual(ContextRAGManager._chunk_text(""), [])

    def test_whitespace_only(self):
        """Whitespace-only text produces no chunks."""
        self.assertEqual(ContextRAGManager._chunk_text("   \n\t  "), [])

    def test_short_text_single_chunk(self):
        """Text shorter than _CHUNK_SIZE returns a single chunk."""
        text = "Hello world"
        chunks = ContextRAGManager._chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_exact_chunk_size(self):
        """Text exactly _CHUNK_SIZE long returns a single chunk."""
        text = "a" * _CHUNK_SIZE
        chunks = ContextRAGManager._chunk_text(text)
        self.assertEqual(len(chunks), 1)

    def test_long_text_produces_overlapping_chunks(self):
        """Text longer than _CHUNK_SIZE is split with overlap."""
        text = "x" * (_CHUNK_SIZE * 3)
        chunks = ContextRAGManager._chunk_text(text)
        self.assertGreater(len(chunks), 1)
        # Each chunk should be at most _CHUNK_SIZE characters
        for chunk in chunks:
            self.assertLessEqual(len(chunk), _CHUNK_SIZE)

    def test_overlap_between_chunks(self):
        """Consecutive chunks overlap by _CHUNK_OVERLAP characters."""
        # Build a text with known content so we can verify overlap
        text = "".join(str(i % 10) for i in range(_CHUNK_SIZE + 100))
        chunks = ContextRAGManager._chunk_text(text)
        self.assertGreaterEqual(len(chunks), 2)
        # The end of chunk 0 should match the start of chunk 1
        tail = chunks[0][-_CHUNK_OVERLAP:]
        head = chunks[1][:_CHUNK_OVERLAP]
        self.assertEqual(tail, head)


# ---------------------------------------------------------------------------
# _resolve_paths
# ---------------------------------------------------------------------------


class TestResolvePaths(unittest.TestCase):
    """Tests for path resolution and filtering."""

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.path.getsize", return_value=100)
    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_resolves_single_file(
        self, mock_expand, mock_isfile, mock_isdir, mock_size, mock_binary
    ):
        """A valid text file is included in resolved list."""
        result = ContextRAGManager._resolve_paths(["~/.bashrc"])
        self.assertEqual(result, ["/home/test/.bashrc"])

    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_skips_sensitive_file(self, mock_expand, mock_isfile, mock_isdir):
        """Files with sensitive keywords in the name are skipped."""
        result = ContextRAGManager._resolve_paths(["~/my_password.txt"])
        self.assertEqual(result, [])

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.path.getsize", return_value=MAX_FILE_SIZE + 1)
    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_skips_oversized_file(
        self, mock_expand, mock_isfile, mock_isdir, mock_size, mock_binary
    ):
        """Files exceeding MAX_FILE_SIZE are skipped."""
        result = ContextRAGManager._resolve_paths(["~/.big_file"])
        self.assertEqual(result, [])

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=True)
    @patch("utils.context_rag.os.path.getsize", return_value=100)
    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_skips_binary_file(
        self, mock_expand, mock_isfile, mock_isdir, mock_size, mock_binary
    ):
        """Binary files are skipped."""
        result = ContextRAGManager._resolve_paths(["~/.bashrc"])
        self.assertEqual(result, [])

    @patch("utils.context_rag.os.path.getsize", side_effect=OSError("stat failed"))
    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_skips_file_on_stat_error(
        self, mock_expand, mock_isfile, mock_isdir, mock_size
    ):
        """Files that fail os.path.getsize are skipped."""
        result = ContextRAGManager._resolve_paths(["~/.bashrc"])
        self.assertEqual(result, [])

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.path.getsize", return_value=50)
    @patch(
        "utils.context_rag.os.walk",
        return_value=[
            ("/home/test/.config", ["Cache", "app"], ["settings.conf"]),
            ("/home/test/.config/app", [], ["config.ini"]),
        ],
    )
    @patch("utils.context_rag.os.path.isdir", return_value=True)
    @patch("utils.context_rag.os.path.isfile", return_value=False)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_walks_directories(
        self, mock_expand, mock_isfile, mock_isdir, mock_walk, mock_size, mock_binary
    ):
        """Directories are walked recursively, Cache subdirs excluded."""
        result = ContextRAGManager._resolve_paths(["~/.config/"])
        self.assertIn("/home/test/.config/settings.conf", result)
        self.assertIn("/home/test/.config/app/config.ini", result)

    @patch("utils.context_rag.os.walk", side_effect=PermissionError("denied"))
    @patch("utils.context_rag.os.path.isdir", return_value=True)
    @patch("utils.context_rag.os.path.isfile", return_value=False)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: p.replace("~", "/home/test"),
    )
    def test_handles_walk_permission_error(
        self, mock_expand, mock_isfile, mock_isdir, mock_walk
    ):
        """PermissionError during os.walk is handled gracefully."""
        result = ContextRAGManager._resolve_paths(["~/.config/"])
        self.assertEqual(result, [])

    def test_defaults_to_indexable_paths(self):
        """Passing None uses INDEXABLE_PATHS default."""
        with patch("utils.context_rag.os.path.expanduser", side_effect=lambda p: p):
            with patch("utils.context_rag.os.path.isfile", return_value=False):
                with patch("utils.context_rag.os.path.isdir", return_value=False):
                    result = ContextRAGManager._resolve_paths(None)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# scan_indexable_files
# ---------------------------------------------------------------------------


class TestScanIndexableFiles(unittest.TestCase):
    """Tests for scan_indexable_files."""

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.stat")
    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: "/home/test" + p[1:],
    )
    def test_scan_returns_file_info(
        self, mock_expand, mock_isfile, mock_isdir, mock_stat, mock_binary
    ):
        """Existing files produce info dicts with path/size/last_modified/indexable."""
        mock_stat.return_value = MagicMock(st_size=256, st_mtime=1700000000.0)
        results = ContextRAGManager.scan_indexable_files()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        first = results[0]
        self.assertIn("path", first)
        self.assertIn("size", first)
        self.assertIn("last_modified", first)
        self.assertIn("indexable", first)

    @patch("utils.context_rag.os.path.isdir", return_value=False)
    @patch("utils.context_rag.os.path.isfile", return_value=False)
    @patch(
        "utils.context_rag.os.path.expanduser",
        side_effect=lambda p: "/home/test" + p[1:],
    )
    def test_scan_missing_path_not_indexable(
        self, mock_expand, mock_isfile, mock_isdir
    ):
        """Non-existent paths produce entries with indexable=False."""
        results = ContextRAGManager.scan_indexable_files()
        for r in results:
            self.assertFalse(r["indexable"])


# ---------------------------------------------------------------------------
# _file_info
# ---------------------------------------------------------------------------


class TestFileInfo(unittest.TestCase):
    """Tests for _file_info helper."""

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.stat")
    def test_file_info_normal(self, mock_stat, mock_binary):
        """Normal file returns correct info dict."""
        mock_stat.return_value = MagicMock(st_size=1024, st_mtime=1700000000.0)
        info = ContextRAGManager._file_info("/tmp/test.conf")
        self.assertEqual(info["path"], "/tmp/test.conf")
        self.assertEqual(info["size"], 1024)
        self.assertEqual(info["last_modified"], 1700000000.0)
        self.assertTrue(info["indexable"])

    @patch("utils.context_rag.os.stat", side_effect=OSError("no such file"))
    def test_file_info_stat_error(self, mock_stat):
        """OSError on stat returns not-indexable entry."""
        info = ContextRAGManager._file_info("/tmp/gone.conf")
        self.assertEqual(info["size"], 0)
        self.assertFalse(info["indexable"])

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.stat")
    def test_file_info_sensitive_not_indexable(self, mock_stat, mock_binary):
        """Sensitive filename produces indexable=False."""
        mock_stat.return_value = MagicMock(st_size=100, st_mtime=1700000000.0)
        info = ContextRAGManager._file_info("/tmp/api_token.txt")
        self.assertFalse(info["indexable"])

    @patch("utils.context_rag.ContextRAGManager._is_binary_file", return_value=False)
    @patch("utils.context_rag.os.stat")
    def test_file_info_oversized_not_indexable(self, mock_stat, mock_binary):
        """File exceeding MAX_FILE_SIZE is not indexable."""
        mock_stat.return_value = MagicMock(st_size=MAX_FILE_SIZE + 1, st_mtime=1.0)
        info = ContextRAGManager._file_info("/tmp/huge.log")
        self.assertFalse(info["indexable"])


# ---------------------------------------------------------------------------
# build_index (uses tempfile for real file I/O)
# ---------------------------------------------------------------------------


class TestBuildIndex(unittest.TestCase):
    """Tests for build_index."""

    def test_build_index_success(self):
        """Build index from real temporary files and verify JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a text file to index
            src = os.path.join(tmpdir, "sample.conf")
            with open(src, "w") as f:
                f.write('alias ll="ls -la"\nexport EDITOR=vim\n')

            # Patch index path to use temp dir
            idx_dir = os.path.join(tmpdir, "rag_index")
            with patch.object(
                ContextRAGManager, "get_index_path", return_value=idx_dir
            ):
                with patch.object(
                    ContextRAGManager,
                    "_get_index_file_path",
                    return_value=os.path.join(idx_dir, "index.json"),
                ):
                    with patch.object(
                        ContextRAGManager, "_resolve_paths", return_value=[src]
                    ):
                        result = ContextRAGManager.build_index([src])

            self.assertTrue(result.success)
            self.assertIn("1 files", result.message)
            self.assertIsNotNone(result.data)
            self.assertEqual(result.data["total_files"], 1)

            # Verify the JSON index was written
            idx_file = os.path.join(idx_dir, "index.json")
            self.assertTrue(os.path.isfile(idx_file))
            with open(idx_file) as f:
                index = json.load(f)
            self.assertEqual(index["version"], 1)
            self.assertGreater(index["total_chunks"], 0)

    def test_build_index_no_files(self):
        """Build index with no resolved files returns failure."""
        with patch.object(ContextRAGManager, "_resolve_paths", return_value=[]):
            result = ContextRAGManager.build_index(["/nonexistent"])
        self.assertFalse(result.success)
        self.assertIn("No indexable files", result.message)

    def test_build_index_makedirs_failure(self):
        """Failure to create index directory returns error Result."""
        with patch.object(ContextRAGManager, "_resolve_paths", return_value=["/tmp/f"]):
            with patch("utils.context_rag.os.makedirs", side_effect=OSError("denied")):
                result = ContextRAGManager.build_index()
        self.assertFalse(result.success)
        self.assertIn("Cannot create", result.message)

    def test_build_index_empty_content(self):
        """Files with only whitespace produce no chunks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "empty.txt")
            with open(src, "w") as f:
                f.write("   \n\n   ")

            idx_dir = os.path.join(tmpdir, "rag_index")
            with patch.object(
                ContextRAGManager, "get_index_path", return_value=idx_dir
            ):
                with patch.object(
                    ContextRAGManager,
                    "_get_index_file_path",
                    return_value=os.path.join(idx_dir, "index.json"),
                ):
                    with patch.object(
                        ContextRAGManager, "_resolve_paths", return_value=[src]
                    ):
                        result = ContextRAGManager.build_index([src])

            self.assertFalse(result.success)
            self.assertIn("No content", result.message)

    def test_build_index_callback_called(self):
        """Progress callback receives messages during indexing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "data.txt")
            with open(src, "w") as f:
                f.write("Some meaningful content for indexing purposes here.")

            idx_dir = os.path.join(tmpdir, "rag_index")
            cb = MagicMock()
            with patch.object(
                ContextRAGManager, "get_index_path", return_value=idx_dir
            ):
                with patch.object(
                    ContextRAGManager,
                    "_get_index_file_path",
                    return_value=os.path.join(idx_dir, "index.json"),
                ):
                    with patch.object(
                        ContextRAGManager, "_resolve_paths", return_value=[src]
                    ):
                        ContextRAGManager.build_index([src], callback=cb)

            self.assertTrue(cb.called)

    def test_build_index_unreadable_file_skipped(self):
        """Unreadable file is skipped with callback notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_dir = os.path.join(tmpdir, "rag_index")
            cb = MagicMock()

            with patch.object(
                ContextRAGManager, "get_index_path", return_value=idx_dir
            ):
                with patch.object(
                    ContextRAGManager,
                    "_get_index_file_path",
                    return_value=os.path.join(idx_dir, "index.json"),
                ):
                    with patch.object(
                        ContextRAGManager,
                        "_resolve_paths",
                        return_value=["/nonexistent/missing.txt"],
                    ):
                        result = ContextRAGManager.build_index(callback=cb)

            # No readable content -> failure
            self.assertFalse(result.success)

    def test_build_index_write_failure(self):
        """OSError when writing index file returns failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "data.txt")
            with open(src, "w") as f:
                f.write("valid content")

            idx_dir = os.path.join(tmpdir, "rag_index")
            os.makedirs(idx_dir, exist_ok=True)
            idx_file = os.path.join(idx_dir, "index.json")

            with patch.object(
                ContextRAGManager, "get_index_path", return_value=idx_dir
            ):
                with patch.object(
                    ContextRAGManager, "_get_index_file_path", return_value=idx_file
                ):
                    with patch.object(
                        ContextRAGManager, "_resolve_paths", return_value=[src]
                    ):
                        with patch(
                            "builtins.open",
                            side_effect=[
                                open(src, "r"),  # first open reads the source file
                                OSError("disk full"),  # second open writes the index
                            ],
                        ):
                            result = ContextRAGManager.build_index([src])

            self.assertFalse(result.success)
            self.assertIn("Failed to write", result.message)


# ---------------------------------------------------------------------------
# search_index (uses tempfile for real index)
# ---------------------------------------------------------------------------


class TestSearchIndex(unittest.TestCase):
    """Tests for search_index TF-IDF search."""

    def _build_temp_index(self, tmpdir, chunks_data, total_files=1):
        """Helper to write a temporary index file.

        Args:
            tmpdir: Temporary directory path.
            chunks_data: List of chunk entry dicts.
            total_files: Number of files represented.

        Returns:
            Path to the index file.
        """
        idx_file = os.path.join(tmpdir, "index.json")
        index = {
            "version": 1,
            "created_at": time.time(),
            "total_files": total_files,
            "total_chunks": len(chunks_data),
            "chunks": chunks_data,
        }
        with open(idx_file, "w") as f:
            json.dump(index, f)
        return idx_file

    def test_search_returns_matching_results(self):
        """Search finds chunks containing query words."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = [
                {"file_path": "/a.conf", "chunk_index": 0, "text": "vim is my editor"},
                {
                    "file_path": "/b.conf",
                    "chunk_index": 0,
                    "text": "nano is another editor",
                },
                {
                    "file_path": "/c.conf",
                    "chunk_index": 0,
                    "text": "nothing relevant here",
                },
            ]
            idx_file = self._build_temp_index(tmpdir, chunks)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("vim editor")

            self.assertGreater(len(results), 0)
            # The vim chunk should score highest (matches both words)
            self.assertEqual(results[0]["file_path"], "/a.conf")

    def test_search_respects_max_results(self):
        """Number of results is capped by max_results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = [
                {
                    "file_path": f"/f{i}.conf",
                    "chunk_index": 0,
                    "text": f"word{i} common",
                }
                for i in range(20)
            ]
            idx_file = self._build_temp_index(tmpdir, chunks, total_files=20)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("common", max_results=3)

            self.assertLessEqual(len(results), 3)

    def test_search_empty_query(self):
        """Empty or single-char-word query returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = [{"file_path": "/a", "chunk_index": 0, "text": "some text"}]
            idx_file = self._build_temp_index(tmpdir, chunks)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("a b")
            self.assertEqual(results, [])

    def test_search_no_index_file(self):
        """Missing index file returns empty list."""
        with patch.object(
            ContextRAGManager,
            "_get_index_file_path",
            return_value="/nonexistent/index.json",
        ):
            results = ContextRAGManager.search_index("test")
        self.assertEqual(results, [])

    def test_search_corrupt_index(self):
        """Corrupt JSON index returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = os.path.join(tmpdir, "index.json")
            with open(idx_file, "w") as f:
                f.write("{invalid json!!")

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("test")
            self.assertEqual(results, [])

    def test_search_no_matching_chunks(self):
        """Query with no matches returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = [
                {"file_path": "/a.conf", "chunk_index": 0, "text": "hello world"},
            ]
            idx_file = self._build_temp_index(tmpdir, chunks)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("zyxwvut")
            self.assertEqual(results, [])

    def test_search_results_have_score(self):
        """Each result dict contains a relevance_score field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks = [
                {
                    "file_path": "/a.conf",
                    "chunk_index": 0,
                    "text": "export PATH variable",
                },
            ]
            idx_file = self._build_temp_index(tmpdir, chunks)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("PATH")
            self.assertGreater(len(results), 0)
            self.assertIn("relevance_score", results[0])
            self.assertGreater(results[0]["relevance_score"], 0)

    def test_search_empty_chunks_list(self):
        """Index with empty chunks list returns empty results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = self._build_temp_index(tmpdir, [])
            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                results = ContextRAGManager.search_index("test query")
            self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# get_index_stats
# ---------------------------------------------------------------------------


class TestGetIndexStats(unittest.TestCase):
    """Tests for get_index_stats."""

    def test_stats_no_index(self):
        """Missing index file returns zeroed stats."""
        with patch.object(
            ContextRAGManager,
            "_get_index_file_path",
            return_value="/nonexistent/index.json",
        ):
            with patch("utils.context_rag.os.path.isfile", return_value=False):
                stats = ContextRAGManager.get_index_stats()

        self.assertEqual(stats["total_files"], 0)
        self.assertEqual(stats["total_chunks"], 0)
        self.assertEqual(stats["index_size_bytes"], 0)

    def test_stats_valid_index(self):
        """Valid index file returns correct statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = os.path.join(tmpdir, "index.json")
            index = {
                "version": 1,
                "created_at": 1700000000.0,
                "total_files": 5,
                "total_chunks": 42,
                "chunks": [],
            }
            with open(idx_file, "w") as f:
                json.dump(index, f)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                with patch("utils.context_rag.os.path.isfile", return_value=True):
                    stats = ContextRAGManager.get_index_stats()

            self.assertEqual(stats["total_files"], 5)
            self.assertEqual(stats["total_chunks"], 42)
            self.assertEqual(stats["last_indexed"], 1700000000.0)
            self.assertGreater(stats["index_size_bytes"], 0)

    def test_stats_corrupt_json(self):
        """Corrupt index file returns zeroed stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = os.path.join(tmpdir, "index.json")
            with open(idx_file, "w") as f:
                f.write("NOT JSON")

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                with patch("utils.context_rag.os.path.isfile", return_value=True):
                    stats = ContextRAGManager.get_index_stats()

            self.assertEqual(stats["total_files"], 0)


# ---------------------------------------------------------------------------
# clear_index
# ---------------------------------------------------------------------------


class TestClearIndex(unittest.TestCase):
    """Tests for clear_index."""

    @patch("utils.context_rag.os.remove")
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    def test_clear_existing_index(self, mock_isfile, mock_remove):
        """Clearing an existing index file succeeds."""
        result = ContextRAGManager.clear_index()
        self.assertTrue(result.success)
        self.assertIn("cleared", result.message)
        mock_remove.assert_called_once()

    @patch("utils.context_rag.os.path.isfile", return_value=False)
    def test_clear_no_index(self, mock_isfile):
        """Clearing when no index exists still returns success."""
        result = ContextRAGManager.clear_index()
        self.assertTrue(result.success)
        self.assertIn("No index", result.message)

    @patch("utils.context_rag.os.remove", side_effect=OSError("permission denied"))
    @patch("utils.context_rag.os.path.isfile", return_value=True)
    def test_clear_permission_error(self, mock_isfile, mock_remove):
        """OSError during removal returns failure Result."""
        result = ContextRAGManager.clear_index()
        self.assertFalse(result.success)
        self.assertIn("Failed to clear", result.message)


# ---------------------------------------------------------------------------
# is_indexed
# ---------------------------------------------------------------------------


class TestIsIndexed(unittest.TestCase):
    """Tests for is_indexed."""

    @patch("utils.context_rag.os.path.isfile", return_value=False)
    def test_not_indexed_when_no_file(self, mock_isfile):
        """Returns False when index file does not exist."""
        self.assertFalse(ContextRAGManager.is_indexed())

    def test_indexed_with_valid_index(self):
        """Returns True when valid index with chunks exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = os.path.join(tmpdir, "index.json")
            with open(idx_file, "w") as f:
                json.dump({"total_chunks": 10, "chunks": []}, f)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                with patch("utils.context_rag.os.path.isfile", return_value=True):
                    self.assertTrue(ContextRAGManager.is_indexed())

    def test_not_indexed_with_zero_chunks(self):
        """Returns False when index exists but has zero chunks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = os.path.join(tmpdir, "index.json")
            with open(idx_file, "w") as f:
                json.dump({"total_chunks": 0, "chunks": []}, f)

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                with patch("utils.context_rag.os.path.isfile", return_value=True):
                    self.assertFalse(ContextRAGManager.is_indexed())

    def test_not_indexed_corrupt_json(self):
        """Returns False when index file contains invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx_file = os.path.join(tmpdir, "index.json")
            with open(idx_file, "w") as f:
                f.write("CORRUPT")

            with patch.object(
                ContextRAGManager, "_get_index_file_path", return_value=idx_file
            ):
                with patch("utils.context_rag.os.path.isfile", return_value=True):
                    self.assertFalse(ContextRAGManager.is_indexed())


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    """Sanity checks for module-level constants."""

    def test_indexable_paths_is_list(self):
        """INDEXABLE_PATHS is a non-empty list."""
        self.assertIsInstance(INDEXABLE_PATHS, list)
        self.assertGreater(len(INDEXABLE_PATHS), 0)

    def test_chunk_size_positive(self):
        """_CHUNK_SIZE is a positive integer."""
        self.assertGreater(_CHUNK_SIZE, 0)

    def test_chunk_overlap_less_than_size(self):
        """_CHUNK_OVERLAP is smaller than _CHUNK_SIZE."""
        self.assertLess(_CHUNK_OVERLAP, _CHUNK_SIZE)

    def test_max_file_size_one_mb(self):
        """MAX_FILE_SIZE is 1 MB."""
        self.assertEqual(MAX_FILE_SIZE, 1 * 1024 * 1024)

    def test_max_index_size_fifty_mb(self):
        """MAX_INDEX_SIZE is 50 MB."""
        self.assertEqual(MAX_INDEX_SIZE, 50 * 1024 * 1024)

    def test_sensitive_keywords_has_expected_entries(self):
        """_SENSITIVE_FILENAME_KEYWORDS contains password, secret, token, key."""
        for kw in ["password", "secret", "token", "key"]:
            self.assertIn(kw, _SENSITIVE_FILENAME_KEYWORDS)


if __name__ == "__main__":
    unittest.main()
