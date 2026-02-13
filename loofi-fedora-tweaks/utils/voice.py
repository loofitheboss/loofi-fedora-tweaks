"""
Voice Manager - Local speech-to-text via whisper.cpp.
Part of v11.2 "AI Polish" update.

Provides:
- whisper.cpp availability detection
- Microphone detection and status
- Audio recording via arecord/parecord
- Speech-to-text transcription
- Hardware-aware model recommendation
"""

import logging
import subprocess
import shutil
import os
import tempfile
from typing import Any, Optional

from utils.containers import Result

logger = logging.getLogger(__name__)


# Whisper model sizes and their RAM requirements in MB
WHISPER_MODELS: dict[str, dict[str, Any]] = {
    "tiny": {
        "name": "Tiny",
        "size_mb": 75,
        "ram_required": 400,
        "description": "Fastest, lowest accuracy",
    },
    "base": {
        "name": "Base",
        "size_mb": 142,
        "ram_required": 500,
        "description": "Good balance of speed and accuracy",
    },
    "small": {
        "name": "Small",
        "size_mb": 466,
        "ram_required": 1000,
        "description": "Better accuracy, moderate speed",
    },
    "medium": {
        "name": "Medium",
        "size_mb": 1500,
        "ram_required": 2600,
        "description": "High accuracy, slower",
    },
}

# Binary names to search for whisper.cpp
_WHISPER_BINARIES = [
    "whisper-cpp",
    "whisper.cpp",
    "whisper",
    "main",  # Default build name from whisper.cpp repo
]


class VoiceManager:
    """
    Manages local speech-to-text via whisper.cpp.
    Provides microphone detection, audio recording, and transcription.
    """

    @staticmethod
    def is_available() -> bool:
        """
        Check if whisper.cpp or a compatible binary is installed.

        Returns:
            True if a whisper.cpp binary is found on PATH.
        """
        for binary in _WHISPER_BINARIES:
            if shutil.which(binary):
                return True
        return False

    @staticmethod
    def _get_whisper_binary() -> str:
        """
        Find the whisper.cpp binary name.

        Returns:
            Binary name string, or empty string if not found.
        """
        for binary in _WHISPER_BINARIES:
            if shutil.which(binary):
                return binary
        return ""

    @staticmethod
    def get_available_models() -> list:
        """
        Get the list of available whisper model names.

        Returns:
            List of model name strings (e.g. ["tiny", "base", "small", "medium"]).
        """
        return list(WHISPER_MODELS.keys())

    @staticmethod
    def check_microphone() -> dict:
        """
        Check for available recording devices.

        Probes /proc/asound/ and arecord -l for device info.

        Returns:
            Dict with 'available' (bool), 'devices' (list of str),
            and 'default' (str or None).
        """
        info: dict[str, Any] = {
            "available": False,
            "devices": [],
            "default": None,
        }

        # Method 1: Check /proc/asound for sound cards
        try:
            asound_path = "/proc/asound/cards"
            if os.path.exists(asound_path):
                with open(asound_path, "r") as f:
                    content = f.read().strip()
                    if content and content != "--- no soundcards ---":
                        info["available"] = True
        except (OSError, IOError):
            pass

        # Method 2: Use arecord -l to detect capture devices
        if shutil.which("arecord"):
            try:
                result = subprocess.run(
                    ["arecord", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if line.startswith("card"):
                            info["devices"].append(line.strip())
                    if info["devices"]:
                        info["available"] = True
                        info["default"] = info["devices"][0]
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("arecord device detection failed: %s", e)

        return info

    @staticmethod
    def get_recommended_model(available_ram_mb: int) -> str:
        """
        Recommend the best whisper model for available RAM.

        Args:
            available_ram_mb: Available RAM in megabytes.

        Returns:
            Model name string (e.g. "base"). Returns "tiny" if RAM is very low.
        """
        # Sort by ram_required descending to pick the most capable that fits
        candidates = sorted(
            WHISPER_MODELS.items(),
            key=lambda item: int(item[1]["ram_required"]),
            reverse=True,
        )

        for model_name, info in candidates:
            if int(info["ram_required"]) <= available_ram_mb:
                return model_name

        # Fallback to the smallest model
        return "tiny"

    @staticmethod
    def transcribe(audio_path: str, model: str = "base") -> Result:
        """
        Transcribe an audio file using whisper.cpp.

        Args:
            audio_path: Path to the WAV audio file.
            model: Whisper model name (tiny, base, small, medium).

        Returns:
            Result with transcribed text in data["text"].
        """
        if not os.path.isfile(audio_path):
            return Result(False, f"Audio file not found: {audio_path}")

        # Find the whisper binary
        binary = ""
        for name in _WHISPER_BINARIES:
            if shutil.which(name):
                binary = name
                break

        if not binary:
            return Result(False, "whisper.cpp is not installed")

        if model not in WHISPER_MODELS:
            return Result(False, f"Unknown model: {model}. Use one of: {', '.join(WHISPER_MODELS.keys())}")

        try:
            result = subprocess.run(
                [binary, "-m", f"ggml-{model}.bin", "-f", audio_path, "--no-timestamps"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                text = result.stdout.strip()
                return Result(
                    True,
                    "Transcription complete",
                    {"text": text, "model": model, "audio_path": audio_path},
                )
            else:
                error = result.stderr.strip() or "Unknown transcription error"
                return Result(False, f"Transcription failed: {error}")

        except subprocess.TimeoutExpired:
            return Result(False, "Transcription timed out after 120 seconds")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Transcription error: {e}")

    @staticmethod
    def record_audio(duration_seconds: int = 5, output_path: Optional[str] = None) -> str:
        """
        Record audio from the default microphone.

        Uses arecord (ALSA) or parecord (PulseAudio) with safe argument arrays.

        Args:
            duration_seconds: Duration to record in seconds.
            output_path: Optional path for the output WAV file.
                         If None, a temporary file is created.

        Returns:
            Path to the recorded WAV file, or empty string on failure.
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="loofi_voice_")
            os.close(fd)

        # Try arecord first (ALSA)
        if shutil.which("arecord"):
            try:
                result = subprocess.run(
                    [
                        "arecord",
                        "-f", "S16_LE",
                        "-r", "16000",
                        "-c", "1",
                        "-d", str(duration_seconds),
                        output_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=duration_seconds + 10,
                )
                if result.returncode == 0 and os.path.isfile(output_path):
                    return output_path
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("arecord failed: %s", e)

        # Fallback: parecord (PulseAudio)
        if shutil.which("parecord"):
            try:
                result = subprocess.run(
                    [
                        "parecord",
                        "--rate=16000",
                        "--channels=1",
                        "--format=s16le",
                        f"--process-time-msec={duration_seconds * 1000}",
                        output_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=duration_seconds + 10,
                )
                if result.returncode == 0 and os.path.isfile(output_path):
                    return output_path
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("parecord failed: %s", e)

        return ""

    @staticmethod
    def is_recording_available() -> bool:
        """
        Check if audio recording tools are available.

        Returns:
            True if arecord or parecord is found on PATH.
        """
        return shutil.which("arecord") is not None or \
            shutil.which("parecord") is not None
