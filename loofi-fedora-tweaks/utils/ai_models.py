"""
AI Model Manager - Lite quantized GGUF model support for low-RAM systems.
Part of v11.1 "AI Polish" update.

Provides:
- Recommended model catalog with RAM requirements
- Hardware-aware model recommendation
- Model download/install via Ollama
- Installed model listing and RAM estimation
"""

import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class Result:
    """Operation result."""
    success: bool
    message: str
    data: Optional[dict] = None


# Recommended quantized models optimized for local use on constrained hardware
RECOMMENDED_MODELS = {
    "llama3.2:1b": {
        "name": "Llama 3.2 (1B)",
        "size": "1.3 GB",
        "size_mb": 1331,
        "quantization": "Q4_K_M",
        "ram_required": 4096,
        "parameters": "1B",
        "description": "Lightweight model, good for simple tasks",
    },
    "llama3.2:3b": {
        "name": "Llama 3.2 (3B)",
        "size": "2.0 GB",
        "size_mb": 2048,
        "quantization": "Q4_K_M",
        "ram_required": 6144,
        "parameters": "3B",
        "description": "Balanced performance and resource usage",
    },
    "llama3.1:8b": {
        "name": "Llama 3.1 (8B)",
        "size": "4.7 GB",
        "size_mb": 4813,
        "quantization": "Q4_K_M",
        "ram_required": 10240,
        "parameters": "8B",
        "description": "Highly capable, needs more RAM",
    },
    "mistral:7b": {
        "name": "Mistral 7B",
        "size": "4.1 GB",
        "size_mb": 4198,
        "quantization": "Q4_K_M",
        "ram_required": 10240,
        "parameters": "7B",
        "description": "Excellent general-purpose alternative",
    },
    "gemma2:2b": {
        "name": "Gemma 2 (2B)",
        "size": "1.6 GB",
        "size_mb": 1638,
        "quantization": "Q4_K_M",
        "ram_required": 4096,
        "parameters": "2B",
        "description": "Google's small but capable model",
    },
    "phi3:mini": {
        "name": "Phi-3 Mini",
        "size": "2.3 GB",
        "size_mb": 2355,
        "quantization": "Q4_K_M",
        "ram_required": 6144,
        "parameters": "3.8B",
        "description": "Microsoft's efficient small model",
    },
}

# RAM estimation multipliers by quantization type
_QUANT_RAM_MULTIPLIERS = {
    "Q4_K_M": 1.2,
    "Q4_K_S": 1.15,
    "Q5_K_M": 1.35,
    "Q5_K_S": 1.3,
    "Q8_0": 1.8,
    "F16": 3.0,
    "F32": 5.5,
}

# Parameter count to base memory mapping (MB per billion params at Q4_K_M)
_PARAM_BASE_MB = {
    "1B": 1300,
    "2B": 1600,
    "3B": 2000,
    "3.8B": 2350,
    "7B": 4100,
    "8B": 4700,
    "13B": 7800,
    "70B": 40000,
}


class AIModelManager:
    """
    Manages quantized GGUF models for local AI inference.
    Supports users with 16GB RAM or less by recommending appropriate
    quantized models via Ollama.
    """

    @staticmethod
    def get_available_models() -> list:
        """
        Get the catalog of recommended models with metadata.

        Returns:
            List of dicts with name, size, quantization, ram_required fields.
        """
        models = []
        for model_id, info in RECOMMENDED_MODELS.items():
            models.append({
                "id": model_id,
                "name": info["name"],
                "size": info["size"],
                "size_mb": info["size_mb"],
                "quantization": info["quantization"],
                "ram_required": info["ram_required"],
                "parameters": info["parameters"],
                "description": info["description"],
            })
        return models

    @staticmethod
    def get_recommended_model(available_ram_mb: int) -> dict:
        """
        Recommend the best model for the user's available RAM.

        Picks the most capable model that fits within the available RAM,
        preferring models with more parameters when RAM allows.

        Args:
            available_ram_mb: Available system RAM in megabytes.

        Returns:
            Dict with model id and metadata, or empty dict if none fit.
        """
        # Sort by ram_required descending so we pick the most capable first
        candidates = sorted(
            RECOMMENDED_MODELS.items(),
            key=lambda item: item[1]["ram_required"],
            reverse=True,
        )

        for model_id, info in candidates:
            if info["ram_required"] <= available_ram_mb:
                return {
                    "id": model_id,
                    "name": info["name"],
                    "size": info["size"],
                    "size_mb": info["size_mb"],
                    "quantization": info["quantization"],
                    "ram_required": info["ram_required"],
                    "parameters": info["parameters"],
                    "description": info["description"],
                }

        return {}

    @staticmethod
    def download_model(model_id: str, callback=None) -> Result:
        """
        Download a model via ollama pull.

        Args:
            model_id: Model identifier (e.g. "llama3.2:1b").
            callback: Optional callable for progress updates, receives str.

        Returns:
            Result with success status and message.
        """
        if not shutil.which("ollama"):
            return Result(False, "Ollama is not installed")

        try:
            process = subprocess.Popen(
                ["ollama", "pull", model_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            output_lines = []
            for line in process.stdout:
                stripped = line.strip()
                output_lines.append(stripped)
                if callback:
                    callback(stripped)

            process.wait()

            if process.returncode == 0:
                return Result(
                    True,
                    f"Model '{model_id}' downloaded successfully",
                    {"model_id": model_id},
                )
            else:
                tail = " ".join(output_lines[-3:]) if output_lines else "Unknown error"
                return Result(False, f"Download failed: {tail}")

        except FileNotFoundError:
            return Result(False, "Ollama binary not found")
        except Exception as e:
            return Result(False, f"Download error: {e}")

    @staticmethod
    def get_installed_models() -> list:
        """
        List models currently installed via Ollama.

        Returns:
            List of dicts with name and size fields.
        """
        if not shutil.which("ollama"):
            return []

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            models = []
            lines = result.stdout.strip().split("\n")
            # Skip header line
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    models.append({
                        "name": parts[0],
                        "size": parts[1] if len(parts) > 1 else "unknown",
                    })

            return models

        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []

    @staticmethod
    def estimate_ram_usage(model_name: str) -> int:
        """
        Estimate RAM usage in MB for a given model.

        Uses parameter count and quantization level to estimate.
        Falls back to a conservative estimate for unknown models.

        Args:
            model_name: Model name/id (e.g. "llama3.2:1b", "mistral:7b").

        Returns:
            Estimated RAM usage in megabytes.
        """
        # Check if it's in our catalog first
        if model_name in RECOMMENDED_MODELS:
            return RECOMMENDED_MODELS[model_name]["ram_required"]

        # Try to parse parameter count from the name
        name_lower = model_name.lower()

        # Extract parameter count indicators
        param_size = None
        for key in sorted(_PARAM_BASE_MB.keys(), key=lambda k: -len(k)):
            if key.lower() in name_lower:
                param_size = key
                break

        if param_size is None:
            # Try extracting numbers like "7b", "13b", "70b"
            for token in name_lower.replace(":", " ").replace("-", " ").split():
                token = token.strip()
                if token.endswith("b") and token[:-1].replace(".", "").isdigit():
                    param_size = token.upper()
                    break

        if param_size and param_size in _PARAM_BASE_MB:
            base_mb = _PARAM_BASE_MB[param_size]
            # Assume Q4_K_M if quantization unknown
            return int(base_mb * _QUANT_RAM_MULTIPLIERS.get("Q4_K_M", 1.2))

        # Conservative fallback: assume 7B Q4_K_M
        return 5000

    @staticmethod
    def get_system_ram() -> int:
        """
        Get total system RAM in megabytes from /proc/meminfo.

        Returns:
            Total RAM in MB, or 0 if unable to read.
        """
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        # Format: "MemTotal:       16384000 kB"
                        parts = line.split()
                        if len(parts) >= 2:
                            kb = int(parts[1])
                            return kb // 1024
        except (OSError, ValueError):
            pass

        return 0
