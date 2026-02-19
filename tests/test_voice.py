"""Tests for utils/voice.py"""
import sys
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Pre-mock PyQt6 for import chain: containers -> install_hints -> services.system -> command_runner -> PyQt6
for _mod in ('PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'):
    sys.modules.setdefault(_mod, MagicMock())

from utils.voice import VoiceManager, WHISPER_MODELS


class TestIsAvailable(unittest.TestCase):
    """Tests for VoiceManager.is_available()."""

    @patch('utils.voice.shutil.which')
    def test_available_whisper_cpp(self, mock_which):
        def side_effect(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = side_effect
        self.assertTrue(VoiceManager.is_available())

    @patch('utils.voice.shutil.which', return_value=None)
    def test_not_available(self, mock_which):
        self.assertFalse(VoiceManager.is_available())

    @patch('utils.voice.shutil.which')
    def test_available_main_binary(self, mock_which):
        def side_effect(name):
            return "/usr/local/bin/main" if name == "main" else None
        mock_which.side_effect = side_effect
        self.assertTrue(VoiceManager.is_available())


class TestGetWhisperBinary(unittest.TestCase):
    """Tests for VoiceManager._get_whisper_binary()."""

    @patch('utils.voice.shutil.which')
    def test_finds_whisper_cpp(self, mock_which):
        def side_effect(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = side_effect
        result = VoiceManager._get_whisper_binary()
        self.assertEqual(result, "whisper-cpp")

    @patch('utils.voice.shutil.which', return_value=None)
    def test_returns_empty_when_not_found(self, mock_which):
        result = VoiceManager._get_whisper_binary()
        self.assertEqual(result, "")


class TestGetAvailableModels(unittest.TestCase):
    """Tests for VoiceManager.get_available_models()."""

    def test_returns_model_list(self):
        result = VoiceManager.get_available_models()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn("tiny", result)
        self.assertIn("base", result)

    def test_matches_catalog(self):
        result = VoiceManager.get_available_models()
        self.assertEqual(set(result), set(WHISPER_MODELS.keys()))


class TestCheckMicrophone(unittest.TestCase):
    """Tests for VoiceManager.check_microphone()."""

    @patch('utils.voice.shutil.which', return_value="/usr/bin/arecord")
    @patch('utils.voice.subprocess.run')
    @patch('builtins.open', mock_open(read_data="0 [PCH]: HDA-Intel\n"))
    @patch('utils.voice.os.path.exists', return_value=True)
    def test_check_microphone_with_devices(self, mock_exists, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="card 0: PCH [HDA Intel PCH], device 0: ALC S16 [ALC S16]\n"
        )
        result = VoiceManager.check_microphone()
        self.assertTrue(result["available"])
        self.assertGreater(len(result["devices"]), 0)

    @patch('utils.voice.shutil.which', return_value=None)
    @patch('utils.voice.os.path.exists', return_value=False)
    def test_check_microphone_no_devices(self, mock_exists, mock_which):
        result = VoiceManager.check_microphone()
        self.assertFalse(result["available"])
        self.assertEqual(result["devices"], [])
        self.assertIsNone(result["default"])

    @patch('utils.voice.shutil.which', return_value="/usr/bin/arecord")
    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.os.path.exists', return_value=True)
    @patch('builtins.open', mock_open(read_data="--- no soundcards ---"))
    def test_check_microphone_no_soundcards(self, mock_run, mock_exists, mock_which):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = VoiceManager.check_microphone()
        self.assertEqual(result["devices"], [])

    @patch('utils.voice.shutil.which', return_value="/usr/bin/arecord")
    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.os.path.exists', return_value=False)
    def test_check_microphone_arecord_timeout(self, mock_exists, mock_run, mock_which):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="arecord", timeout=5)
        result = VoiceManager.check_microphone()
        self.assertEqual(result["devices"], [])


class TestGetRecommendedModel(unittest.TestCase):
    """Tests for VoiceManager.get_recommended_model()."""

    def test_recommend_high_ram(self):
        result = VoiceManager.get_recommended_model(4000)
        self.assertIn(result, WHISPER_MODELS)

    def test_recommend_low_ram(self):
        result = VoiceManager.get_recommended_model(100)
        self.assertEqual(result, "tiny")

    def test_recommend_medium_ram(self):
        result = VoiceManager.get_recommended_model(1000)
        self.assertIn(result, WHISPER_MODELS)

    def test_recommend_picks_most_capable(self):
        result_high = VoiceManager.get_recommended_model(10000)
        result_low = VoiceManager.get_recommended_model(500)
        self.assertGreaterEqual(
            WHISPER_MODELS[result_high]["ram_required"],
            WHISPER_MODELS[result_low]["ram_required"]
        )


class TestTranscribe(unittest.TestCase):
    """Tests for VoiceManager.transcribe()."""

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    @patch('utils.voice.os.path.isfile', return_value=True)
    def test_transcribe_success(self, mock_isfile, mock_which, mock_run):
        def which_side(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = which_side
        mock_run.return_value = MagicMock(returncode=0, stdout="Hello world")

        result = VoiceManager.transcribe("/tmp/audio.wav", model="base")
        self.assertTrue(result.success)
        self.assertIn("Transcription complete", result.message)
        self.assertEqual(result.data["text"], "Hello world")

    @patch('utils.voice.os.path.isfile', return_value=False)
    def test_transcribe_file_not_found(self, mock_isfile):
        result = VoiceManager.transcribe("/nonexistent.wav")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.voice.shutil.which', return_value=None)
    @patch('utils.voice.os.path.isfile', return_value=True)
    def test_transcribe_no_whisper(self, mock_isfile, mock_which):
        result = VoiceManager.transcribe("/tmp/audio.wav")
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.voice.shutil.which')
    @patch('utils.voice.os.path.isfile', return_value=True)
    def test_transcribe_invalid_model(self, mock_isfile, mock_which):
        def which_side(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = which_side

        result = VoiceManager.transcribe("/tmp/audio.wav", model="nonexistent")
        self.assertFalse(result.success)
        self.assertIn("Unknown model", result.message)

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    @patch('utils.voice.os.path.isfile', return_value=True)
    def test_transcribe_command_failure(self, mock_isfile, mock_which, mock_run):
        def which_side(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = which_side
        mock_run.return_value = MagicMock(returncode=1, stderr="Model not found", stdout="")

        result = VoiceManager.transcribe("/tmp/audio.wav")
        self.assertFalse(result.success)
        self.assertIn("failed", result.message.lower())

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    @patch('utils.voice.os.path.isfile', return_value=True)
    def test_transcribe_timeout(self, mock_isfile, mock_which, mock_run):
        def which_side(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = which_side
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="whisper", timeout=120)

        result = VoiceManager.transcribe("/tmp/audio.wav")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    @patch('utils.voice.os.path.isfile', return_value=True)
    def test_transcribe_os_error(self, mock_isfile, mock_which, mock_run):
        def which_side(name):
            return "/usr/bin/whisper-cpp" if name == "whisper-cpp" else None
        mock_which.side_effect = which_side
        mock_run.side_effect = OSError("fail")

        result = VoiceManager.transcribe("/tmp/audio.wav")
        self.assertFalse(result.success)


class TestRecordAudio(unittest.TestCase):
    """Tests for VoiceManager.record_audio()."""

    @patch('utils.voice.os.path.isfile', return_value=True)
    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    def test_record_audio_arecord_success(self, mock_which, mock_run, mock_isfile):
        def which_side(name):
            return "/usr/bin/arecord" if name == "arecord" else None
        mock_which.side_effect = which_side
        mock_run.return_value = MagicMock(returncode=0)

        result = VoiceManager.record_audio(duration_seconds=5, output_path="/tmp/test.wav")
        self.assertEqual(result, "/tmp/test.wav")

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    def test_record_audio_arecord_failure_parecord_fallback(self, mock_which, mock_run):
        def which_side(name):
            if name == "arecord":
                return "/usr/bin/arecord"
            if name == "parecord":
                return "/usr/bin/parecord"
            return None
        mock_which.side_effect = which_side

        # arecord fails, parecord succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1),  # arecord fails
            MagicMock(returncode=0),  # parecord succeeds
        ]

        with patch('utils.voice.os.path.isfile', return_value=True):
            result = VoiceManager.record_audio(duration_seconds=3, output_path="/tmp/test.wav")
            self.assertEqual(result, "/tmp/test.wav")

    @patch('utils.voice.shutil.which', return_value=None)
    def test_record_audio_no_tools(self, mock_which):
        result = VoiceManager.record_audio(duration_seconds=3, output_path="/tmp/test.wav")
        self.assertEqual(result, "")

    @patch('utils.voice.os.close')
    @patch('utils.voice.tempfile.mkstemp', return_value=(5, "/tmp/loofi_voice_abc.wav"))
    @patch('utils.voice.os.path.isfile', return_value=True)
    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    def test_record_audio_auto_temp_file(self, mock_which, mock_run, mock_isfile, mock_mkstemp, mock_close):
        def which_side(name):
            return "/usr/bin/arecord" if name == "arecord" else None
        mock_which.side_effect = which_side
        mock_run.return_value = MagicMock(returncode=0)

        result = VoiceManager.record_audio(duration_seconds=5)
        self.assertIn("loofi_voice", result)

    @patch('utils.voice.subprocess.run')
    @patch('utils.voice.shutil.which')
    def test_record_audio_timeout(self, mock_which, mock_run):
        def which_side(name):
            return "/usr/bin/arecord" if name == "arecord" else None
        mock_which.side_effect = which_side
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="arecord", timeout=15)

        result = VoiceManager.record_audio(duration_seconds=5, output_path="/tmp/test.wav")
        self.assertEqual(result, "")


class TestIsRecordingAvailable(unittest.TestCase):
    """Tests for VoiceManager.is_recording_available()."""

    @patch('utils.voice.shutil.which')
    def test_arecord_available(self, mock_which):
        def side_effect(name):
            return "/usr/bin/arecord" if name == "arecord" else None
        mock_which.side_effect = side_effect
        self.assertTrue(VoiceManager.is_recording_available())

    @patch('utils.voice.shutil.which')
    def test_parecord_available(self, mock_which):
        def side_effect(name):
            return "/usr/bin/parecord" if name == "parecord" else None
        mock_which.side_effect = side_effect
        self.assertTrue(VoiceManager.is_recording_available())

    @patch('utils.voice.shutil.which', return_value=None)
    def test_no_recording_tools(self, mock_which):
        self.assertFalse(VoiceManager.is_recording_available())


if __name__ == '__main__':
    unittest.main()
