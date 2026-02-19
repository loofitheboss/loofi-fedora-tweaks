"""Tests for utils/ai_models.py"""
import sys
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.ai_models import AIModelManager, RECOMMENDED_MODELS, Result


class TestGetAvailableModels(unittest.TestCase):
    """Tests for AIModelManager.get_available_models()."""

    def test_get_available_models_returns_list(self):
        result = AIModelManager.get_available_models()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_available_models_has_required_keys(self):
        result = AIModelManager.get_available_models()
        for model in result:
            self.assertIn("id", model)
            self.assertIn("name", model)
            self.assertIn("size", model)
            self.assertIn("size_mb", model)
            self.assertIn("quantization", model)
            self.assertIn("ram_required", model)
            self.assertIn("parameters", model)
            self.assertIn("description", model)

    def test_get_available_models_count_matches_catalog(self):
        result = AIModelManager.get_available_models()
        self.assertEqual(len(result), len(RECOMMENDED_MODELS))


class TestGetRecommendedModel(unittest.TestCase):
    """Tests for AIModelManager.get_recommended_model()."""

    def test_recommend_for_high_ram(self):
        result = AIModelManager.get_recommended_model(16384)
        self.assertIsInstance(result, dict)
        self.assertIn("id", result)
        # Should pick a capable model
        self.assertGreater(result["ram_required"], 0)

    def test_recommend_for_low_ram(self):
        result = AIModelManager.get_recommended_model(4096)
        self.assertIsInstance(result, dict)
        self.assertIn("id", result)
        self.assertLessEqual(result["ram_required"], 4096)

    def test_recommend_for_very_low_ram(self):
        result = AIModelManager.get_recommended_model(100)
        self.assertEqual(result, {})

    def test_recommend_for_medium_ram(self):
        result = AIModelManager.get_recommended_model(6144)
        self.assertIsInstance(result, dict)
        if result:
            self.assertLessEqual(result["ram_required"], 6144)

    def test_recommend_picks_most_capable(self):
        """Should pick the largest model that fits."""
        result_high = AIModelManager.get_recommended_model(16384)
        result_low = AIModelManager.get_recommended_model(4096)
        if result_high and result_low:
            self.assertGreaterEqual(result_high["ram_required"], result_low["ram_required"])


class TestDownloadModel(unittest.TestCase):
    """Tests for AIModelManager.download_model()."""

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_success(self, mock_which, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = iter(["Downloading...\n", "Done\n"])
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = AIModelManager.download_model("llama3.2:1b")
        self.assertTrue(result.success)
        self.assertIn("downloaded successfully", result.message)

    @patch('utils.ai_models.shutil.which', return_value=None)
    def test_download_model_ollama_not_installed(self, mock_which):
        result = AIModelManager.download_model("llama3.2:1b")
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_failure(self, mock_which, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = iter(["Error: model not found\n"])
        mock_process.returncode = 1
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = AIModelManager.download_model("nonexistent:model")
        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_file_not_found(self, mock_which, mock_popen):
        mock_popen.side_effect = FileNotFoundError("binary not found")
        result = AIModelManager.download_model("llama3.2:1b")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_subprocess_error(self, mock_which, mock_popen):
        mock_popen.side_effect = subprocess.SubprocessError("fail")
        result = AIModelManager.download_model("llama3.2:1b")
        self.assertFalse(result.success)
        self.assertIn("error", result.message.lower())

    @patch('utils.ai_models.subprocess.Popen')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_download_model_with_callback(self, mock_which, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = iter(["Progress 50%\n", "Progress 100%\n"])
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        callback = MagicMock()
        result = AIModelManager.download_model("llama3.2:1b", callback=callback)
        self.assertTrue(result.success)
        self.assertEqual(callback.call_count, 2)


class TestGetInstalledModels(unittest.TestCase):
    """Tests for AIModelManager.get_installed_models()."""

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NAME\tSIZE\nllama3.2:1b\t1.3GB\nmistral:7b\t4.1GB\n"
        )
        result = AIModelManager.get_installed_models()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "llama3.2:1b")

    @patch('utils.ai_models.shutil.which', return_value=None)
    def test_get_installed_models_no_ollama(self, mock_which):
        result = AIModelManager.get_installed_models()
        self.assertEqual(result, [])

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_command_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = AIModelManager.get_installed_models()
        self.assertEqual(result, [])

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_timeout(self, mock_which, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ollama", timeout=10)
        result = AIModelManager.get_installed_models()
        self.assertEqual(result, [])

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_os_error(self, mock_which, mock_run):
        mock_run.side_effect = OSError("fail")
        result = AIModelManager.get_installed_models()
        self.assertEqual(result, [])

    @patch('utils.ai_models.subprocess.run')
    @patch('utils.ai_models.shutil.which', return_value="/usr/bin/ollama")
    def test_get_installed_models_empty_output(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="NAME\tSIZE\n")
        result = AIModelManager.get_installed_models()
        self.assertEqual(result, [])


class TestEstimateRamUsage(unittest.TestCase):
    """Tests for AIModelManager.estimate_ram_usage()."""

    def test_estimate_known_model(self):
        for model_id in RECOMMENDED_MODELS:
            result = AIModelManager.estimate_ram_usage(model_id)
            self.assertGreater(result, 0)
            self.assertEqual(result, int(RECOMMENDED_MODELS[model_id]["ram_required"]))

    def test_estimate_unknown_model_with_param_hint(self):
        result = AIModelManager.estimate_ram_usage("custom:7b")
        self.assertGreater(result, 0)

    def test_estimate_unknown_model_no_hint(self):
        result = AIModelManager.estimate_ram_usage("totally-unknown-model")
        self.assertEqual(result, 5000)  # conservative fallback

    def test_estimate_model_with_param_in_name(self):
        result = AIModelManager.estimate_ram_usage("some-model-13b")
        self.assertGreater(result, 0)


class TestGetSystemRam(unittest.TestCase):
    """Tests for AIModelManager.get_system_ram()."""

    def test_get_system_ram_success(self):
        meminfo = "MemTotal:       16384000 kB\nMemFree:        8000000 kB\n"
        with patch('builtins.open', mock_open(read_data=meminfo)):
            result = AIModelManager.get_system_ram()
            self.assertEqual(result, 16000)  # 16384000 // 1024

    def test_get_system_ram_file_not_found(self):
        with patch('builtins.open', side_effect=OSError):
            result = AIModelManager.get_system_ram()
            self.assertEqual(result, 0)

    def test_get_system_ram_malformed(self):
        meminfo = "SomethingElse: 12345\n"
        with patch('builtins.open', mock_open(read_data=meminfo)):
            result = AIModelManager.get_system_ram()
            self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
