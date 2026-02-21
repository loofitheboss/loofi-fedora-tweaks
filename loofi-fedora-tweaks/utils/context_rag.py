"""
Context RAG Manager - Index local configs and history for AI-powered Q&A.
Part of v11.3 "AI Polish" update.

Provides:
- Scan and index user config files and shell history
- Simple TF-IDF-like keyword search over indexed content
- JSON-based index with no external dependencies
- Security filtering (skip files with sensitive names, binary files)
"""

import json
import math
import os
import time

from utils.containers import Result

# Paths to consider indexing (relative to user home)
INDEXABLE_PATHS = [
    "~/.bash_history",
    "~/.bashrc",
    "~/.bash_profile",
    "~/.zshrc",
    "~/.zsh_history",
    "~/.profile",
    "~/.gitconfig",
    "~/.ssh/config",
    "~/.config/",
]

# Filenames containing these substrings are NEVER indexed (security)
_SENSITIVE_FILENAME_KEYWORDS = [
    "password",
    "secret",
    "token",
    "key",
]

# Maximum individual file size to index (1 MB)
MAX_FILE_SIZE = 1 * 1024 * 1024

# Maximum total index size (50 MB)
MAX_INDEX_SIZE = 50 * 1024 * 1024

# Chunk size for splitting file content (in characters)
_CHUNK_SIZE = 500

# Overlap between consecutive chunks (in characters)
_CHUNK_OVERLAP = 50

# Default index directory name within user config
_INDEX_DIR_NAME = "rag_index"

# Index filename
_INDEX_FILENAME = "index.json"


class ContextRAGManager:
    """
    Indexes user's local configuration files and shell history
    for AI-powered Q&A. Uses a simple JSON-based index with
    TF-IDF-like keyword matching for search.
    """

    @staticmethod
    def get_index_path() -> str:
        """
        Get the path to the RAG index directory.

        Returns:
            Absolute path to ~/.config/loofi-fedora-tweaks/rag_index/
        """
        return os.path.join(
            os.path.expanduser("~"),
            ".config",
            "loofi-fedora-tweaks",
            _INDEX_DIR_NAME,
        )

    @staticmethod
    def _get_index_file_path() -> str:
        """Get the full path to the index JSON file."""
        return os.path.join(
            ContextRAGManager.get_index_path(),
            _INDEX_FILENAME,
        )

    @staticmethod
    def _is_sensitive_filename(filename: str) -> bool:
        """
        Check if a filename contains sensitive keywords.

        Args:
            filename: Base filename to check.

        Returns:
            True if the filename contains a sensitive keyword.
        """
        lower_name = filename.lower()
        for keyword in _SENSITIVE_FILENAME_KEYWORDS:
            if keyword in lower_name:
                return True
        return False

    @staticmethod
    def _is_binary_file(file_path: str) -> bool:
        """
        Check if a file is binary by looking for null bytes in the first 512 bytes.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file appears to be binary.
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(512)
                return b"\x00" in chunk
        except (OSError, IOError):
            return True

    @staticmethod
    def _chunk_text(text: str) -> list:
        """
        Split text into overlapping chunks.

        Args:
            text: The text to split.

        Returns:
            List of chunk strings.
        """
        if len(text) <= _CHUNK_SIZE:
            return [text] if text.strip() else []

        chunks = []
        start = 0
        while start < len(text):
            end = start + _CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - _CHUNK_OVERLAP
            if start >= len(text):
                break

        return chunks

    @staticmethod
    def _resolve_paths(paths: list = None) -> list:  # type: ignore[assignment]
        """
        Resolve INDEXABLE_PATHS to actual file paths.

        Expands ~ and recursively walks directories. Filters out
        sensitive filenames and binary files.

        Args:
            paths: Optional list of paths to resolve. Uses INDEXABLE_PATHS if None.

        Returns:
            List of absolute file paths to index.
        """
        if paths is None:
            paths = INDEXABLE_PATHS

        resolved = []
        for raw_path in paths:
            expanded = os.path.expanduser(raw_path)

            if os.path.isfile(expanded):
                basename = os.path.basename(expanded)
                if ContextRAGManager._is_sensitive_filename(basename):
                    continue
                try:
                    size = os.path.getsize(expanded)
                except OSError:
                    continue
                if size > MAX_FILE_SIZE:
                    continue
                if ContextRAGManager._is_binary_file(expanded):
                    continue
                resolved.append(expanded)

            elif os.path.isdir(expanded):
                try:
                    for dirpath, dirnames, filenames in os.walk(expanded):
                        # Skip hidden subdirectories that look like caches
                        dirnames[:] = [
                            d for d in dirnames
                            if not d.startswith("__") and d != "Cache" and d != "cache"
                        ]
                        for fname in filenames:
                            if ContextRAGManager._is_sensitive_filename(fname):
                                continue
                            fpath = os.path.join(dirpath, fname)
                            try:
                                size = os.path.getsize(fpath)
                            except OSError:
                                continue
                            if size > MAX_FILE_SIZE:
                                continue
                            if ContextRAGManager._is_binary_file(fpath):
                                continue
                            resolved.append(fpath)
                except (OSError, PermissionError):
                    continue

        return resolved

    @staticmethod
    def scan_indexable_files() -> list:
        """
        Scan for files that can be indexed.

        Returns:
            List of dicts with path, size, last_modified, indexable fields.
        """
        results = []

        for raw_path in INDEXABLE_PATHS:
            expanded = os.path.expanduser(raw_path)

            if os.path.isfile(expanded):
                results.append(
                    ContextRAGManager._file_info(expanded)
                )
            elif os.path.isdir(expanded):
                try:
                    for dirpath, dirnames, filenames in os.walk(expanded):
                        dirnames[:] = [
                            d for d in dirnames
                            if not d.startswith("__") and d != "Cache" and d != "cache"
                        ]
                        for fname in filenames:
                            fpath = os.path.join(dirpath, fname)
                            results.append(
                                ContextRAGManager._file_info(fpath)
                            )
                except (OSError, PermissionError):
                    continue
            else:
                # Path does not exist
                results.append({
                    "path": expanded,
                    "size": 0,
                    "last_modified": 0,
                    "indexable": False,
                })

        return results

    @staticmethod
    def _file_info(file_path: str) -> dict:
        """Build file info dict for a single file."""
        try:
            stat = os.stat(file_path)
            size = stat.st_size
            mtime = stat.st_mtime
        except OSError:
            return {
                "path": file_path,
                "size": 0,
                "last_modified": 0,
                "indexable": False,
            }

        basename = os.path.basename(file_path)
        indexable = (
            not ContextRAGManager._is_sensitive_filename(basename)
            and size <= MAX_FILE_SIZE
            and not ContextRAGManager._is_binary_file(file_path)
        )

        return {
            "path": file_path,
            "size": size,
            "last_modified": mtime,
            "indexable": indexable,
        }

    @staticmethod
    def build_index(paths: list = None, callback=None) -> Result:  # type: ignore[assignment]
        """
        Build the search index from the specified or default paths.

        Reads each file, splits into chunks, and saves a JSON index.

        Args:
            paths: Optional list of paths to index. Uses INDEXABLE_PATHS if None.
            callback: Optional callable for progress updates, receives str.

        Returns:
            Result with indexing statistics in data.
        """
        resolved = ContextRAGManager._resolve_paths(paths)

        if not resolved:
            return Result(False, "No indexable files found")

        index_dir = ContextRAGManager.get_index_path()
        try:
            os.makedirs(index_dir, exist_ok=True)
        except OSError as e:
            return Result(False, f"Cannot create index directory: {e}")

        chunks_data = []
        total_size = 0
        files_indexed = 0

        for file_path in resolved:
            if total_size >= MAX_INDEX_SIZE:
                if callback:
                    callback(f"Index size limit reached ({MAX_INDEX_SIZE // (1024 * 1024)} MB)")
                break

            try:
                with open(file_path, "r", errors="replace") as f:
                    content = f.read()
            except (OSError, IOError):
                if callback:
                    callback(f"Skipped (unreadable): {file_path}")
                continue

            if not content.strip():
                continue

            file_chunks = ContextRAGManager._chunk_text(content)
            for i, chunk in enumerate(file_chunks):
                chunk_entry = {
                    "file_path": file_path,
                    "chunk_index": i,
                    "text": chunk,
                }
                chunk_size = len(json.dumps(chunk_entry))
                if total_size + chunk_size > MAX_INDEX_SIZE:
                    break
                chunks_data.append(chunk_entry)
                total_size += chunk_size

            files_indexed += 1
            if callback:
                callback(f"Indexed: {file_path} ({len(file_chunks)} chunks)")

        if not chunks_data:
            return Result(False, "No content could be indexed")

        # Build the index structure
        index = {
            "version": 1,
            "created_at": time.time(),
            "total_files": files_indexed,
            "total_chunks": len(chunks_data),
            "chunks": chunks_data,
        }

        index_file = ContextRAGManager._get_index_file_path()
        try:
            with open(index_file, "w") as f:
                json.dump(index, f)
        except (OSError, IOError) as e:
            return Result(False, f"Failed to write index: {e}")

        return Result(
            True,
            f"Indexed {files_indexed} files ({len(chunks_data)} chunks)",
            {
                "total_files": files_indexed,
                "total_chunks": len(chunks_data),
                "index_size_bytes": os.path.getsize(index_file),
            },
        )

    @staticmethod
    def search_index(query: str, max_results: int = 5) -> list:
        """
        Search the index with basic TF-IDF-like keyword matching.

        Scores chunks by counting query word occurrences weighted by
        inverse frequency across all chunks.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of dicts with file_path, chunk, relevance_score fields.
        """
        index_file = ContextRAGManager._get_index_file_path()

        try:
            with open(index_file, "r") as f:
                index = json.load(f)
        except (OSError, json.JSONDecodeError):
            return []

        chunks = index.get("chunks", [])
        if not chunks:
            return []

        # Tokenize query
        query_words = [w.lower() for w in query.split() if len(w) >= 2]
        if not query_words:
            return []

        total_chunks = len(chunks)

        # Compute document frequency for each query word
        doc_freq = {}
        for word in query_words:
            count = 0
            for chunk_entry in chunks:
                if word in chunk_entry["text"].lower():
                    count += 1
            doc_freq[word] = count if count > 0 else 1

        # Score each chunk
        scored = []
        for chunk_entry in chunks:
            text_lower = chunk_entry["text"].lower()
            score = 0.0

            for word in query_words:
                # Term frequency: count of word in chunk
                tf = text_lower.count(word)
                if tf > 0:
                    # IDF: log(total / doc_frequency)
                    idf = math.log(total_chunks / doc_freq[word]) + 1.0
                    score += tf * idf

            if score > 0:
                scored.append({
                    "file_path": chunk_entry["file_path"],
                    "chunk": chunk_entry["text"],
                    "relevance_score": round(score, 4),
                })

        # Sort by score descending and return top results
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:max_results]

    @staticmethod
    def get_index_stats() -> dict:
        """
        Get statistics about the current index.

        Returns:
            Dict with total_files, total_chunks, last_indexed, index_size_bytes.
        """
        index_file = ContextRAGManager._get_index_file_path()

        default_stats = {
            "total_files": 0,
            "total_chunks": 0,
            "last_indexed": 0,
            "index_size_bytes": 0,
        }

        if not os.path.isfile(index_file):
            return default_stats

        try:
            size = os.path.getsize(index_file)
            with open(index_file, "r") as f:
                index = json.load(f)

            return {
                "total_files": index.get("total_files", 0),
                "total_chunks": index.get("total_chunks", 0),
                "last_indexed": index.get("created_at", 0),
                "index_size_bytes": size,
            }
        except (OSError, json.JSONDecodeError):
            return default_stats

    @staticmethod
    def clear_index() -> Result:
        """
        Remove the RAG index.

        Returns:
            Result indicating success or failure.
        """
        index_file = ContextRAGManager._get_index_file_path()

        if not os.path.isfile(index_file):
            return Result(True, "No index to clear")

        try:
            os.remove(index_file)
            return Result(True, "Index cleared successfully")
        except OSError as e:
            return Result(False, f"Failed to clear index: {e}")

    @staticmethod
    def is_indexed() -> bool:
        """
        Check if an index exists.

        Returns:
            True if a valid index file exists.
        """
        index_file = ContextRAGManager._get_index_file_path()
        if not os.path.isfile(index_file):
            return False

        try:
            with open(index_file, "r") as f:
                index = json.load(f)
            return bool(index.get("total_chunks", 0) > 0)
        except (OSError, json.JSONDecodeError):
            return False
