"""Tests for utils/ai.py."""

import os
import sys
import unittest
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.ai import AIConfigManager, LlamaCppManager, OllamaManager


class TestOllamaManager(unittest.TestCase):
    """Coverage tests for OllamaManager."""

    @patch('utils.ai.shutil.which', return_value='/usr/bin/ollama')
    def test_is_installed_true(self, mock_which):
        self.assertTrue(OllamaManager.is_installed())

    @patch('utils.ai.subprocess.run')
    def test_is_running_user_service_active(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(OllamaManager.is_running())

    @patch('utils.ai.subprocess.run')
    def test_is_running_system_service_active(self, mock_run):
        mock_run.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
        self.assertTrue(OllamaManager.is_running())

    @patch('utils.ai.subprocess.run')
    def test_is_running_fallback_to_pgrep(self, mock_run):
        mock_run.side_effect = [Exception('svc fail'), MagicMock(returncode=0)]
        self.assertTrue(OllamaManager.is_running())

    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_install_already_installed(self, mock_is_installed):
        result = OllamaManager.install()
        self.assertTrue(result.success)
        self.assertIn("already", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=False)
    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.os.unlink')
    @patch('tempfile.NamedTemporaryFile')
    def test_install_success(self, mock_temp, mock_unlink, mock_run, mock_is_installed):
        """Test successful Ollama installation."""
        # Mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/ollama_install.sh'
        mock_temp.return_value.__enter__.return_value = mock_temp_file
        
        # Mock successful download and install
        mock_run.side_effect = [
            MagicMock(returncode=0),  # download
            MagicMock(returncode=0),  # install
        ]
        
        result = OllamaManager.install()
        self.assertTrue(result.success)
        self.assertIn("successfully", result.message.lower())
        
        # Verify two-step process was used
        self.assertEqual(mock_run.call_count, 2)
        # First call should be curl download
        first_call = mock_run.call_args_list[0][0][0]
        self.assertEqual(first_call[0], "curl")
        self.assertIn("-o", first_call)
        # Second call should be bash execution
        second_call = mock_run.call_args_list[1][0][0]
        self.assertEqual(second_call[0], "bash")

    @patch('utils.ai.OllamaManager.is_installed', return_value=False)
    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.os.unlink')
    @patch('tempfile.NamedTemporaryFile')
    def test_install_download_failure(self, mock_temp, mock_unlink, mock_run, mock_is_installed):
        """Test Ollama installation when download fails."""
        # Mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/ollama_install.sh'
        mock_temp.return_value.__enter__.return_value = mock_temp_file
        
        # Mock failed download
        mock_run.return_value = MagicMock(returncode=1, stderr="Download error")
        
        result = OllamaManager.install()
        self.assertFalse(result.success)
        self.assertIn("download failed", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=False)
    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.os.unlink')
    @patch('tempfile.NamedTemporaryFile')
    def test_install_execution_failure(self, mock_temp, mock_unlink, mock_run, mock_is_installed):
        """Test Ollama installation when script execution fails."""
        # Mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = '/tmp/ollama_install.sh'
        mock_temp.return_value.__enter__.return_value = mock_temp_file
        
        # Mock successful download but failed install
        mock_run.side_effect = [
            MagicMock(returncode=0),  # download succeeds
            MagicMock(returncode=1, stderr="Install error"),  # install fails
        ]
        
        result = OllamaManager.install()
        self.assertFalse(result.success)
        self.assertIn("installation failed", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=False)
    @patch('utils.ai.subprocess.run')
    def test_install_timeout(self, mock_run, mock_is_installed):
        mock_run.side_effect = TimeoutExpired(cmd='curl', timeout=1)
        result = OllamaManager.install()
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=False)
    def test_start_service_not_installed(self, mock_is_installed):
        result = OllamaManager.start_service()
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message.lower())

    @patch('utils.ai.subprocess.Popen')
    @patch('utils.ai.OllamaManager.is_running', return_value=False)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_start_service_success(self, mock_is_installed, mock_is_running, mock_popen):
        result = OllamaManager.start_service()
        self.assertTrue(result.success)
        mock_popen.assert_called_once()

    @patch('utils.ai.OllamaManager.is_running', return_value=False)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_stop_service_already_stopped(self, mock_is_installed, mock_is_running):
        result = OllamaManager.stop_service()
        self.assertTrue(result.success)
        self.assertIn("already stopped", result.message.lower())

    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.OllamaManager.is_running', return_value=True)
    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    def test_stop_service_fallback_pkill(self, mock_is_installed, mock_is_running, mock_run):
        mock_run.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
        result = OllamaManager.stop_service()
        self.assertTrue(result.success)
        self.assertIn("stopped", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    @patch('utils.ai.subprocess.run')
    def test_list_models_parse(self, mock_run, mock_is_installed):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NAME ID SIZE MODIFIED\nllama3.2:3b abc 2.0GB now\n",
        )
        models = OllamaManager.list_models()
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["name"], "llama3.2:3b")

    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    @patch('utils.ai.subprocess.Popen')
    def test_pull_model_failure_with_output(self, mock_popen, mock_is_installed):
        process = MagicMock()
        process.stdout = iter(["pulling\n", "error network\n"])
        process.returncode = 1
        process.wait.return_value = None
        mock_popen.return_value = process

        result = OllamaManager.pull_model("llama3.2")
        self.assertFalse(result.success)
        self.assertIn("download failed", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    @patch('utils.ai.subprocess.run')
    def test_delete_model_failure(self, mock_run, mock_is_installed):
        mock_run.return_value = MagicMock(returncode=1, stderr='nope')
        result = OllamaManager.delete_model('bad:model')
        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())

    @patch('utils.ai.OllamaManager.is_installed', return_value=True)
    @patch('utils.ai.subprocess.run')
    def test_run_prompt_timeout(self, mock_run, mock_is_installed):
        mock_run.side_effect = TimeoutExpired(cmd='ollama', timeout=1)
        result = OllamaManager.run_prompt('llama3.2', 'hi')
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message.lower())


class TestLlamaCppManager(unittest.TestCase):
    """Coverage tests for LlamaCppManager."""

    @patch('utils.ai.shutil.which')
    def test_is_installed_checks_two_binaries(self, mock_which):
        mock_which.side_effect = [None, '/usr/bin/main']
        self.assertTrue(LlamaCppManager.is_installed())

    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.LlamaCppManager.is_installed', return_value=False)
    def test_install_detects_dnf_package(self, mock_is_installed, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = LlamaCppManager.install()
        self.assertFalse(result.success)
        self.assertIn("sudo dnf install llama-cpp", result.message)


class TestAIConfigManager(unittest.TestCase):
    """Coverage tests for AIConfigManager."""

    @patch('utils.ai.shutil.which', return_value=None)
    def test_configure_nvidia_for_ai_no_gpu(self, mock_which):
        result = AIConfigManager.configure_nvidia_for_ai()
        self.assertFalse(result.success)
        self.assertIn("not detected", result.message.lower())

    @patch('utils.ai.os.path.exists')
    @patch('utils.ai.shutil.which', return_value='/usr/bin/nvidia-smi')
    def test_configure_nvidia_for_ai_cuda_present(self, mock_which, mock_exists):
        mock_exists.side_effect = [False, True, False]
        result = AIConfigManager.configure_nvidia_for_ai()
        self.assertTrue(result.success)
        self.assertIn("already configured", result.message.lower())

    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.shutil.which')
    def test_configure_rocm_for_ai_no_amd_gpu(self, mock_which, mock_run):
        mock_which.return_value = None
        mock_run.return_value = MagicMock(returncode=0, stdout='Intel VGA')
        result = AIConfigManager.configure_rocm_for_ai()
        self.assertFalse(result.success)
        self.assertIn("amd gpu not detected", result.message.lower())

    @patch('utils.ai.subprocess.run')
    @patch('utils.ai.shutil.which', return_value='/usr/bin/nvidia-smi')
    def test_get_gpu_memory_parse(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='8192, 2048, 6144\n')
        result = AIConfigManager.get_gpu_memory()
        self.assertEqual(result['total_mb'], 8192)
        self.assertEqual(result['used_mb'], 2048)
        self.assertEqual(result['free_mb'], 6144)


if __name__ == '__main__':
    unittest.main()
