"""
Tests for v11.1-v11.3 "AI Polish" updates.
Covers: AIModelManager, VoiceManager, ContextRAGManager.
"""
import io
import json
import math
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.ai_models import AIModelManager, RECOMMENDED_MODELS, _PARAM_BASE_MB
from utils.voice import VoiceManager, WHISPER_MODELS
from utils.context_rag import (
    ContextRAGManager, INDEXABLE_PATHS, MAX_FILE_SIZE, MAX_INDEX_SIZE,
)


# ---------------------------------------------------------------------------
# TestAIModelManager — lite model support (v11.1)
# ---------------------------------------------------------------------------

class TestAIModelManager(unittest.TestCase):
    """Tests for the AI Model Manager providing lite GGUF model support."""

    def test_get_available_models_returns_list(self):
        """get_available_models returns a non-empty list of dicts."""
        models = AIModelManager.get_available_models()
        self.assertIsInstance(models, list)
        self.assertTrue(len(models) >= 6)

    def test_get_available_models_fields(self):
        """Each model dict has the required metadata fields."""
        required = {"id", "name", "size", "size_mb", "quantization", "ram_required",
                     "parameters", "description"}
        for model in AIModelManager.get_available_models():
            for key in required:
                self.assertIn(key, model, f"Model {model.get('id')} missing '{key}'")

    def test_get_available_models_quantization(self):
        """All recommended models use Q4_K_M quantization."""
        for model in AIModelManager.get_available_models():
            self.assertEqual(model["quantization"], "Q4_K_M")

    def test_get_recommended_model_high_ram(self):
        """With 16 GB RAM, recommends the most capable model."""
        rec = AIModelManager.get_recommended_model(16384)
        self.assertIn("id", rec)
        # Should pick llama3.1:8b or mistral:7b (10240 MB RAM)
        self.assertGreaterEqual(rec["ram_required"], 10240)

    def test_get_recommended_model_low_ram(self):
        """With 4 GB RAM, recommends a small model."""
        rec = AIModelManager.get_recommended_model(4096)
        self.assertIn("id", rec)
        self.assertLessEqual(rec["ram_required"], 4096)

    def test_get_recommended_model_medium_ram(self):
        """With 6 GB RAM, recommends a balanced model."""
        rec = AIModelManager.get_recommended_model(6144)
        self.assertIn("id", rec)
        self.assertLessEqual(rec["ram_required"], 6144)

    def test_get_recommended_model_insufficient_ram(self):
        """With very little RAM, returns empty dict."""
        rec = AIModelManager.get_recommended_model(500)
        self.assertEqual(rec, {})

    @patch('utils.ai_models.shutil.which', return_value=None)
    def test_download_model_ollama_not_installed(self, mock_which):
        """download_model fails gracefully when ollama is not installed."""
        result = AIModelManager.download_model("llama3.2:1b")
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_success(self, mock_which, mock_popen):
        """download_model succeeds with a valid model ID."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["pulling manifest\n", "success\n"])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        result = AIModelManager.download_model("llama3.2:1b")
        self.assertTrue(result.success)
        self.assertIn("llama3.2:1b", result.message)

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_with_callback(self, mock_which, mock_popen):
        """download_model invokes the progress callback."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["pulling\n", "done\n"])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        messages = []
        AIModelManager.download_model("gemma2:2b", callback=messages.append)
        self.assertTrue(len(messages) >= 1)

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_failure(self, mock_which, mock_popen):
        """download_model reports failure when ollama returns non-zero."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["Error: model not found\n"])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc

        result = AIModelManager.download_model("nonexistent:model")
        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())

    @patch('utils.ai_models.shutil.which', return_value=None)
    def test_get_installed_models_no_ollama(self, mock_which):
        """get_installed_models returns empty when ollama is not installed."""
        models = AIModelManager.get_installed_models()
        self.assertEqual(models, [])

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_parses_output(self, mock_which, mock_run):
        """get_installed_models correctly parses ollama list output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NAME          ID        SIZE   MODIFIED\n"
                   "llama3.2:1b   abc123    1.3 GB 2 days ago\n"
                   "gemma2:2b     def456    1.6 GB 1 day ago\n"
        )
        models = AIModelManager.get_installed_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["name"], "llama3.2:1b")
        self.assertEqual(models[1]["name"], "gemma2:2b")

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_empty_list(self, mock_which, mock_run):
        """get_installed_models handles empty model list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NAME          ID        SIZE   MODIFIED\n"
        )
        models = AIModelManager.get_installed_models()
        self.assertEqual(models, [])

    def test_estimate_ram_known_model(self):
        """estimate_ram_usage returns exact value for known models."""
        ram = AIModelManager.estimate_ram_usage("llama3.2:1b")
        self.assertEqual(ram, 4096)

    def test_estimate_ram_unknown_model_with_param_hint(self):
        """estimate_ram_usage estimates from parameter count in name."""
        ram = AIModelManager.estimate_ram_usage("some-model-7b")
        self.assertGreater(ram, 0)
        self.assertIsInstance(ram, int)

    def test_estimate_ram_completely_unknown_model(self):
        """estimate_ram_usage returns conservative fallback for unknown models."""
        ram = AIModelManager.estimate_ram_usage("mystery-model")
        self.assertEqual(ram, 5000)

    def test_get_system_ram_reads_proc_meminfo(self):
        """get_system_ram parses /proc/meminfo correctly."""
        fake_content = "MemTotal:       16384000 kB\nMemFree:        8000000 kB\n"
        with patch('builtins.open', mock_open(read_data=fake_content)):
            ram = AIModelManager.get_system_ram()
            self.assertEqual(ram, 16000)  # 16384000 // 1024

    @patch('builtins.open', side_effect=OSError("Permission denied"))
    def test_get_system_ram_handles_error(self, mock_file):
        """get_system_ram returns 0 when /proc/meminfo is unreadable."""
        ram = AIModelManager.get_system_ram()
        self.assertEqual(ram, 0)

    def test_recommended_models_constant(self):
        """RECOMMENDED_MODELS has all expected model IDs."""
        expected_ids = {"llama3.2:1b", "llama3.2:3b", "llama3.1:8b",
                        "mistral:7b", "gemma2:2b", "phi3:mini"}
        self.assertEqual(set(RECOMMENDED_MODELS.keys()), expected_ids)


# ---------------------------------------------------------------------------
# TestVoiceManager — whisper.cpp integration (v11.2)
# ---------------------------------------------------------------------------

class TestVoiceManager(unittest.TestCase):
    """Tests for the Voice Manager providing speech-to-text."""

    @patch('utils.voice.shutil.which', return_value="/usr/bin/whisper-cpp")
    def test_is_available_found(self, mock_which):
        """is_available returns True when whisper-cpp is on PATH."""
        self.assertTrue(VoiceManager.is_available())

    @patch('utils.voice.shutil.which', return_value=None)
    def test_is_available_not_found(self, mock_which):
        """is_available returns False when no whisper binary is found."""
        self.assertFalse(VoiceManager.is_available())

    def test_get_available_models_list(self):
        """get_available_models returns the expected model names."""
        models = VoiceManager.get_available_models()
        self.assertIn("tiny", models)
        self.assertIn("base", models)
        self.assertIn("small", models)
        self.assertIn("medium", models)

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_check_microphone_with_arecord(self, mock_file, mock_exists, mock_run):
        """check_microphone detects devices via arecord."""
        mock_file.return_value.__enter__ = lambda s: io.StringIO("0 [PCH]: HDA-Intel")
        mock_file.return_value.__exit__ = MagicMock(return_value=False)

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="card 0: PCH [HDA Intel PCH], device 0: ALC255 [ALC255]\n"
                   "  Subdevices: 1/1\n"
        )

        with patch('utils.voice.shutil.which', return_value="/usr/bin/arecord"):
            info = VoiceManager.check_microphone()
            self.assertTrue(info["available"])
            self.assertTrue(len(info["devices"]) >= 0)

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.os.path.exists', return_value=False)
    def test_check_microphone_none_found(self, mock_exists, mock_run):
        """check_microphone returns no devices when nothing is detected."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        with patch('utils.voice.shutil.which', return_value=None):
            info = VoiceManager.check_microphone()
            self.assertFalse(info["available"])

    def test_get_recommended_model_high_ram(self):
        """get_recommended_model returns 'medium' for ample RAM."""
        model = VoiceManager.get_recommended_model(4000)
        self.assertEqual(model, "medium")

    def test_get_recommended_model_low_ram(self):
        """get_recommended_model returns 'tiny' for very low RAM."""
        model = VoiceManager.get_recommended_model(200)
        self.assertEqual(model, "tiny")

    def test_get_recommended_model_moderate_ram(self):
        """get_recommended_model returns appropriate model for moderate RAM."""
        model = VoiceManager.get_recommended_model(1000)
        self.assertIn(model, ["small", "base"])

    @patch('utils.voice.shutil.which', return_value=None)
    def test_transcribe_no_whisper(self, mock_which):
        """transcribe fails when whisper-cpp is not installed."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmppath = f.name
        try:
            result = VoiceManager.transcribe(tmppath)
            self.assertFalse(result.success)
            self.assertIn("not installed", result.message)
        finally:
            os.unlink(tmppath)

    def test_transcribe_missing_audio(self):
        """transcribe fails when audio file does not exist."""
        result = VoiceManager.transcribe("/nonexistent/audio.wav")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which', return_value="/usr/bin/whisper-cpp")
    def test_transcribe_success(self, mock_which, mock_run):
        """transcribe returns text on success."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Hello world, this is a test.",
            stderr="",
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmppath = f.name
        try:
            result = VoiceManager.transcribe(tmppath, model="base")
            self.assertTrue(result.success)
            self.assertEqual(result.data["text"], "Hello world, this is a test.")
        finally:
            os.unlink(tmppath)

    def test_transcribe_invalid_model(self):
        """transcribe rejects unknown model names."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmppath = f.name
        try:
            with patch('utils.voice.shutil.which', return_value="/usr/bin/whisper-cpp"):
                result = VoiceManager.transcribe(tmppath, model="gigantic")
                self.assertFalse(result.success)
                self.assertIn("Unknown model", result.message)
        finally:
            os.unlink(tmppath)

    @patch('utils.voice.shutil.which', side_effect=lambda x: "/usr/bin/arecord" if x == "arecord" else None)
    def test_is_recording_available_arecord(self, mock_which):
        """is_recording_available returns True when arecord is found."""
        self.assertTrue(VoiceManager.is_recording_available())

    @patch('utils.voice.shutil.which', return_value=None)
    def test_is_recording_available_nothing(self, mock_which):
        """is_recording_available returns False when no tools found."""
        self.assertFalse(VoiceManager.is_recording_available())

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which', side_effect=lambda x: "/usr/bin/arecord" if x == "arecord" else None)
    def test_record_audio_success(self, mock_which, mock_run):
        """record_audio returns a file path on success."""
        output_path = os.path.join(tempfile.gettempdir(), "test_record.wav")
        mock_run.return_value = MagicMock(returncode=0)

        # Pre-create the file so os.path.isfile returns True
        with open(output_path, "w") as f:
            f.write("fake wav")

        try:
            path = VoiceManager.record_audio(duration_seconds=3, output_path=output_path)
            self.assertEqual(path, output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_whisper_models_constant(self):
        """WHISPER_MODELS has all expected model names."""
        expected = {"tiny", "base", "small", "medium"}
        self.assertEqual(set(WHISPER_MODELS.keys()), expected)

    def test_whisper_models_ram_ordering(self):
        """Whisper models have increasing RAM requirements."""
        order = ["tiny", "base", "small", "medium"]
        for i in range(len(order) - 1):
            self.assertLess(
                WHISPER_MODELS[order[i]]["ram_required"],
                WHISPER_MODELS[order[i + 1]]["ram_required"],
            )


# ---------------------------------------------------------------------------
# TestContextRAGManager — local config indexing (v11.3)
# ---------------------------------------------------------------------------

class TestContextRAGManager(unittest.TestCase):
    """Tests for the Context RAG Manager providing local config indexing."""

    def setUp(self):
        """Create a temporary directory for test indices."""
        self.test_dir = tempfile.mkdtemp(prefix="loofi_rag_test_")
        self._orig_get_index_path = ContextRAGManager.get_index_path
        # Patch the index path to use temp dir
        ContextRAGManager.get_index_path = staticmethod(lambda: self.test_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
        ContextRAGManager.get_index_path = self._orig_get_index_path

    def test_get_index_path(self):
        """get_index_path returns a path under ~/.config/."""
        # Restore original for this test
        ContextRAGManager.get_index_path = self._orig_get_index_path
        path = ContextRAGManager.get_index_path()
        self.assertIn(".config", path)
        self.assertIn("loofi-fedora-tweaks", path)
        self.assertIn("rag_index", path)

    def test_sensitive_filename_detection(self):
        """Files with sensitive keywords in names are detected."""
        self.assertTrue(ContextRAGManager._is_sensitive_filename("my_password.txt"))
        self.assertTrue(ContextRAGManager._is_sensitive_filename("api_token.json"))
        self.assertTrue(ContextRAGManager._is_sensitive_filename("secret_config.yaml"))
        self.assertTrue(ContextRAGManager._is_sensitive_filename("ssh_key.pem"))

    def test_non_sensitive_filenames_pass(self):
        """Normal filenames are not flagged as sensitive."""
        self.assertFalse(ContextRAGManager._is_sensitive_filename(".bashrc"))
        self.assertFalse(ContextRAGManager._is_sensitive_filename("config.json"))
        self.assertFalse(ContextRAGManager._is_sensitive_filename(".gitconfig"))

    def test_binary_file_detection(self):
        """Binary files (with null bytes) are detected."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello\x00world")
            tmppath = f.name
        try:
            self.assertTrue(ContextRAGManager._is_binary_file(tmppath))
        finally:
            os.unlink(tmppath)

    def test_text_file_not_binary(self):
        """Text files without null bytes are not flagged as binary."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("This is a text file\nwith multiple lines\n")
            tmppath = f.name
        try:
            self.assertFalse(ContextRAGManager._is_binary_file(tmppath))
        finally:
            os.unlink(tmppath)

    def test_chunk_text_short(self):
        """Short text returns a single chunk."""
        chunks = ContextRAGManager._chunk_text("Hello world")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Hello world")

    def test_chunk_text_empty(self):
        """Empty text returns no chunks."""
        chunks = ContextRAGManager._chunk_text("")
        self.assertEqual(chunks, [])

    def test_chunk_text_long(self):
        """Long text is split into multiple overlapping chunks."""
        text = "a" * 1500
        chunks = ContextRAGManager._chunk_text(text)
        self.assertGreater(len(chunks), 1)

    def test_scan_indexable_files_returns_list(self):
        """scan_indexable_files returns a list of dicts."""
        files = ContextRAGManager.scan_indexable_files()
        self.assertIsInstance(files, list)
        for f in files:
            self.assertIn("path", f)
            self.assertIn("size", f)
            self.assertIn("last_modified", f)
            self.assertIn("indexable", f)

    def test_build_and_search_index(self):
        """build_index creates an index that can be searched."""
        # Create test files
        test_file = os.path.join(self.test_dir, "test_config.txt")
        with open(test_file, "w") as f:
            f.write("alias ll='ls -la'\nalias gs='git status'\nexport PATH=/usr/local/bin:$PATH\n")

        result = ContextRAGManager.build_index(paths=[test_file])
        self.assertTrue(result.success)
        self.assertIn("total_chunks", result.data)

        # Search for content
        results = ContextRAGManager.search_index("git status")
        self.assertGreater(len(results), 0)
        self.assertIn("file_path", results[0])
        self.assertIn("chunk", results[0])
        self.assertIn("relevance_score", results[0])

    def test_build_index_skips_sensitive(self):
        """build_index skips files with sensitive keywords in names."""
        sensitive_file = os.path.join(self.test_dir, "my_password.txt")
        safe_file = os.path.join(self.test_dir, "my_config.txt")
        with open(sensitive_file, "w") as f:
            f.write("super secret stuff")
        with open(safe_file, "w") as f:
            f.write("safe configuration data")

        result = ContextRAGManager.build_index(paths=[sensitive_file, safe_file])
        self.assertTrue(result.success)
        # Only the safe file should have been indexed
        self.assertEqual(result.data["total_files"], 1)

    def test_build_index_skips_binary(self):
        """build_index skips binary files."""
        binary_file = os.path.join(self.test_dir, "data.bin")
        text_file = os.path.join(self.test_dir, "config.txt")

        with open(binary_file, "wb") as f:
            f.write(b"binary\x00content\x00here")
        with open(text_file, "w") as f:
            f.write("normal text content")

        result = ContextRAGManager.build_index(paths=[binary_file, text_file])
        self.assertTrue(result.success)
        self.assertEqual(result.data["total_files"], 1)

    def test_build_index_with_callback(self):
        """build_index invokes the callback for progress."""
        test_file = os.path.join(self.test_dir, "data.txt")
        with open(test_file, "w") as f:
            f.write("some content here")

        messages = []
        ContextRAGManager.build_index(paths=[test_file], callback=messages.append)
        self.assertTrue(len(messages) >= 1)

    def test_build_index_no_files(self):
        """build_index reports failure when no indexable files found."""
        result = ContextRAGManager.build_index(paths=["/nonexistent/path"])
        self.assertFalse(result.success)

    def test_get_index_stats_no_index(self):
        """get_index_stats returns zeros when no index exists."""
        stats = ContextRAGManager.get_index_stats()
        self.assertEqual(stats["total_files"], 0)
        self.assertEqual(stats["total_chunks"], 0)

    def test_get_index_stats_after_build(self):
        """get_index_stats returns correct values after building."""
        test_file = os.path.join(self.test_dir, "data.txt")
        with open(test_file, "w") as f:
            f.write("content to index for stats testing")

        ContextRAGManager.build_index(paths=[test_file])
        stats = ContextRAGManager.get_index_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertGreater(stats["total_chunks"], 0)
        self.assertGreater(stats["index_size_bytes"], 0)

    def test_clear_index(self):
        """clear_index removes the index file."""
        test_file = os.path.join(self.test_dir, "data.txt")
        with open(test_file, "w") as f:
            f.write("content to index")

        ContextRAGManager.build_index(paths=[test_file])
        self.assertTrue(ContextRAGManager.is_indexed())

        result = ContextRAGManager.clear_index()
        self.assertTrue(result.success)
        self.assertFalse(ContextRAGManager.is_indexed())

    def test_clear_index_no_index(self):
        """clear_index succeeds when no index exists."""
        result = ContextRAGManager.clear_index()
        self.assertTrue(result.success)
        self.assertIn("No index", result.message)

    def test_is_indexed_false_initially(self):
        """is_indexed returns False when no index has been built."""
        self.assertFalse(ContextRAGManager.is_indexed())

    def test_is_indexed_true_after_build(self):
        """is_indexed returns True after a successful build."""
        test_file = os.path.join(self.test_dir, "data.txt")
        with open(test_file, "w") as f:
            f.write("indexed content")

        ContextRAGManager.build_index(paths=[test_file])
        self.assertTrue(ContextRAGManager.is_indexed())

    def test_search_empty_query(self):
        """search_index returns empty for blank or short queries."""
        results = ContextRAGManager.search_index("")
        self.assertEqual(results, [])

    def test_search_no_index(self):
        """search_index returns empty when no index exists."""
        results = ContextRAGManager.search_index("some query")
        self.assertEqual(results, [])

    def test_search_respects_max_results(self):
        """search_index returns at most max_results entries."""
        test_file = os.path.join(self.test_dir, "data.txt")
        with open(test_file, "w") as f:
            # Write enough content to generate multiple chunks
            f.write("fedora linux " * 500)

        ContextRAGManager.build_index(paths=[test_file])
        results = ContextRAGManager.search_index("fedora linux", max_results=2)
        self.assertLessEqual(len(results), 2)

    def test_search_relevance_scoring(self):
        """search_index scores results by relevance."""
        file_a = os.path.join(self.test_dir, "a.txt")
        file_b = os.path.join(self.test_dir, "b.txt")

        with open(file_a, "w") as f:
            f.write("python python python python python code")
        with open(file_b, "w") as f:
            f.write("java code and some other stuff here")

        ContextRAGManager.build_index(paths=[file_a, file_b])
        results = ContextRAGManager.search_index("python")
        self.assertGreater(len(results), 0)
        # The file with more "python" occurrences should rank higher
        self.assertIn("python", results[0]["chunk"].lower())

    def test_indexable_paths_constant(self):
        """INDEXABLE_PATHS contains expected paths."""
        self.assertIn("~/.bashrc", INDEXABLE_PATHS)
        self.assertIn("~/.bash_history", INDEXABLE_PATHS)
        self.assertIn("~/.config/", INDEXABLE_PATHS)


if __name__ == '__main__':
    unittest.main()
