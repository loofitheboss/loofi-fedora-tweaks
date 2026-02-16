"""
AI Manager - Local AI/LLM support utilities.
Part of v8.1 "Neural" update.

Provides:
- Ollama installation and management
- Model downloading and management
- GPU acceleration configuration
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from services.system import SystemManager

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Operation result."""

    success: bool
    message: str
    data: Optional[dict] = None


class OllamaManager:
    """
    Manages Ollama installation and model operations.
    Ollama is the recommended local LLM runtime for ease of use.
    """

    # Popular models optimized for local use
    RECOMMENDED_MODELS = {
        "llama3.2": {
            "name": "Llama 3.2 (3B)",
            "size": "2.0 GB",
            "desc": "Meta's latest, fast and capable",
        },
        "mistral": {
            "name": "Mistral 7B",
            "size": "4.1 GB",
            "desc": "Excellent general-purpose model",
        },
        "codellama": {
            "name": "Code Llama (7B)",
            "size": "3.8 GB",
            "desc": "Specialized for code generation",
        },
        "phi3": {
            "name": "Phi-3 Mini",
            "size": "2.3 GB",
            "desc": "Microsoft's efficient small model",
        },
        "gemma2:2b": {
            "name": "Gemma 2 (2B)",
            "size": "1.6 GB",
            "desc": "Google's lightweight model",
        },
        "qwen2.5:3b": {
            "name": "Qwen 2.5 (3B)",
            "size": "1.9 GB",
            "desc": "Alibaba's multilingual model",
        },
    }

    @classmethod
    def is_installed(cls) -> bool:
        """Check if Ollama is installed."""
        return shutil.which("ollama") is not None

    @classmethod
    def is_running(cls) -> bool:
        """Check if Ollama service is running."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "ollama"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True

            # Try system service
            result = subprocess.run(
                ["systemctl", "is-active", "ollama"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check Ollama service status via systemctl: %s", e)
            # Check if process is running
            try:
                result = subprocess.run(
                    ["pgrep", "-x", "ollama"], capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
            except (subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to check Ollama process via pgrep: %s", e)
                return False

    @classmethod
    def install(cls) -> Result:
        """
        Install Ollama using official script.
        This is the recommended installation method.
        """
        if cls.is_installed():
            return Result(True, "Ollama is already installed")

        try:
            # Use official install script
            result = subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode == 0:
                return Result(True, "Ollama installed successfully")
            else:
                return Result(False, f"Installation failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            return Result(False, "Installation timed out")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Installation error: {e}")

    @classmethod
    def start_service(cls) -> Result:
        """Start Ollama service."""
        if not cls.is_installed():
            return Result(False, "Ollama is not installed")

        if cls.is_running():
            return Result(True, "Ollama is already running")

        try:
            # Try to start background process
            subprocess.Popen(  # noqa: timeout — fire-and-forget background daemon
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return Result(True, "Ollama service started")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Failed to start: {e}")

    @classmethod
    def stop_service(cls) -> Result:
        """Stop the Ollama service."""
        if not cls.is_installed():
            return Result(False, "Ollama is not installed")

        if not cls.is_running():
            return Result(True, "Ollama is already stopped")

        try:
            # Try systemctl first (if running as a service)
            result = subprocess.run(
                ["systemctl", "--user", "stop", "ollama"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return Result(True, "Ollama service stopped")

            # Fallback: kill the process
            result = subprocess.run(
                ["pkill", "-f", "ollama serve"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return Result(True, "Ollama process stopped")

            return Result(False, "Could not stop Ollama")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Failed to stop: {e}")

    @classmethod
    def list_models(cls) -> list[dict]:
        """List installed models."""
        if not cls.is_installed():
            return []

        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return []

            models = []
            lines = result.stdout.strip().split("\n")[1:]  # Skip header

            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        models.append(
                            {
                                "name": parts[0],
                                "size": parts[1] if len(parts) > 1 else "unknown",
                            }
                        )

            return models
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list Ollama models: %s", e)
            return []

    @classmethod
    def pull_model(cls, model_name: str, callback=None) -> Result:
        """
        Download a model from Ollama library.

        Args:
            model_name: Name of model to pull (e.g., "llama3.2", "mistral")
            callback: Optional callback for progress updates
        """
        if not cls.is_installed():
            return Result(False, "Ollama is not installed")

        try:
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            output = []
            if process.stdout:
                for line in process.stdout:
                    output.append(line.strip())
                    if callback:
                        callback(line.strip())

            process.wait(timeout=600)

            if process.returncode == 0:
                return Result(True, f"Model '{model_name}' downloaded successfully")
            else:
                return Result(False, f"Download failed: {' '.join(output[-3:])}")

        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Download error: {e}")

    @classmethod
    def delete_model(cls, model_name: str) -> Result:
        """Delete a downloaded model."""
        if not cls.is_installed():
            return Result(False, "Ollama is not installed")

        try:
            result = subprocess.run(
                ["ollama", "rm", model_name], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return Result(True, f"Model '{model_name}' deleted")
            else:
                return Result(False, f"Delete failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Delete error: {e}")

    @classmethod
    def run_prompt(cls, model: str, prompt: str, timeout: int = 60) -> Result:
        """
        Run a single prompt through a model.

        Args:
            model: Model name
            prompt: Text prompt
            timeout: Timeout in seconds

        Returns:
            Result with response in data["response"]
        """
        if not cls.is_installed():
            return Result(False, "Ollama is not installed")

        try:
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                return Result(
                    True, "Response generated", {"response": result.stdout.strip()}
                )
            else:
                return Result(False, f"Generation failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            return Result(False, "Response timed out")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")


class LlamaCppManager:
    """
    Manager for llama.cpp - lower level but more control.
    Use when you need specific quantization or advanced options.
    """

    @classmethod
    def is_installed(cls) -> bool:
        """Check if llama.cpp main binary is available."""
        return shutil.which("llama-cli") is not None or shutil.which("main") is not None

    @classmethod
    def install(cls) -> Result:
        """Install llama.cpp from source or package."""
        # Check if already installed
        if cls.is_installed():
            return Result(True, "llama.cpp is already installed")

        # Try package manager (if packaged)
        try:
            pm = SystemManager.get_package_manager()
            if pm == "rpm-ostree":
                # On Atomic, check if package is available via rpm-ostree
                result = subprocess.run(
                    ["rpm", "-q", "llama-cpp"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return Result(
                        False,
                        "llama.cpp package found. Install with: pkexec rpm-ostree install llama-cpp",
                    )
            else:
                if shutil.which(pm):
                    result = subprocess.run(
                        [pm, "list", "llama-cpp"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        return Result(
                            False,
                            "llama.cpp package found. Install with: pkexec dnf install llama-cpp",
                        )
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to check llama.cpp package availability: %s", e)

        return Result(
            False,
            "llama.cpp requires manual installation. See: https://github.com/ggerganov/llama.cpp",
        )


class AIConfigManager:
    """
    Manages AI-related system configuration.
    Handles GPU acceleration setup for AI workloads.
    """

    @classmethod
    def configure_nvidia_for_ai(cls) -> Result:
        """
        Configure NVIDIA GPU for AI workloads.
        Ensures CUDA toolkit is available.
        """
        if not shutil.which("nvidia-smi"):
            return Result(False, "NVIDIA GPU not detected")

        # Check if CUDA toolkit is installed
        cuda_paths = ["/usr/local/cuda", "/usr/lib64/cuda", "/opt/cuda"]

        cuda_found = any(os.path.exists(p) for p in cuda_paths)

        if cuda_found:
            return Result(True, "CUDA toolkit is already configured")

        pm = SystemManager.get_package_manager()
        install_cmd = "pkexec %s install" % pm
        return Result(
            False,
            "CUDA toolkit not found. Install with:\n"
            "%s cuda-toolkit\n"
            "Or enable RPM Fusion and install: %s nvidia-driver-cuda"
            % (install_cmd, install_cmd),
        )

    @classmethod
    def configure_rocm_for_ai(cls) -> Result:
        """
        Configure AMD GPU for AI workloads via ROCm.
        """
        if not shutil.which("rocminfo"):
            # Check if AMD GPU exists
            try:
                result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=10
                )
                if "AMD" not in result.stdout or "VGA" not in result.stdout:
                    return Result(False, "AMD GPU not detected")
            except (subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to detect AMD GPU via lspci: %s", e)

            pm = SystemManager.get_package_manager()
            return Result(
                False,
                "ROCm not installed. Install with:\n"
                "pkexec %s install rocm-hip rocm-runtime rocm-smi" % pm,
            )

        return Result(True, "ROCm is configured and ready")

    @classmethod
    def get_gpu_memory(cls) -> dict:
        """Get GPU memory information."""
        result = {"total_mb": 0, "used_mb": 0, "free_mb": 0}

        # Try NVIDIA
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.total,memory.used,memory.free",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if out.returncode == 0:
                    parts = out.stdout.strip().split(",")
                    if len(parts) >= 3:
                        result["total_mb"] = int(parts[0].strip())
                        result["used_mb"] = int(parts[1].strip())
                        result["free_mb"] = int(parts[2].strip())
            except (subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to query NVIDIA GPU memory: %s", e)

        return result
