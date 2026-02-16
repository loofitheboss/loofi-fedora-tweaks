"""
Hardware Manager - Central hardware control abstraction.
Handles CPU governors, GPU modes, fan control, and thermal management.
"""

import logging
import os
import glob
import subprocess
import shutil
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HardwareManager:
    """Manages hardware settings: CPU, GPU, Fans, Thermals."""

    # ==================== CPU GOVERNOR ====================

    CPU_GOVERNOR_PATH = "/sys/devices/system/cpu/cpu0/cpufreq"

    @classmethod
    def get_available_governors(cls) -> list:
        """
        Get list of available CPU governors.
        Common governors: powersave, performance, schedutil, ondemand, conservative
        """
        path = f"{cls.CPU_GOVERNOR_PATH}/scaling_available_governors"
        try:
            with open(path, "r") as f:
                return f.read().strip().split()
        except FileNotFoundError:
            return ["powersave", "performance"]  # Fallback
        except PermissionError:
            return []

    @classmethod
    def get_current_governor(cls) -> str:
        """Get the current CPU governor."""
        path = f"{cls.CPU_GOVERNOR_PATH}/scaling_governor"
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except OSError as e:
            logger.debug("Failed to read CPU governor: %s", e)
            return "unknown"

    @classmethod
    def set_governor(cls, governor: str) -> bool:
        """
        Set CPU governor for all cores.
        Requires root access (uses pkexec).
        """
        if governor not in cls.get_available_governors():
            return False

        # Create a script to set all governors
        script = f"""
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "{governor}" > "$cpu"
done
"""
        try:
            result = subprocess.run(
                ["pkexec", "bash", "-c", script],
                capture_output=True, text=True, check=False, timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to set governor: %s", e)
            return False

    @classmethod
    def get_cpu_frequency(cls) -> dict:
        """Get current and max CPU frequency in MHz."""
        result = {"current": 0, "max": 0}
        try:
            with open(f"{cls.CPU_GOVERNOR_PATH}/scaling_cur_freq", "r") as f:
                result["current"] = int(f.read().strip()) // 1000  # kHz to MHz
            with open(f"{cls.CPU_GOVERNOR_PATH}/scaling_max_freq", "r") as f:
                result["max"] = int(f.read().strip()) // 1000
        except (OSError, ValueError) as e:
            logger.debug("Failed to read CPU frequency: %s", e)
        return result

    # ==================== GPU MODE ====================

    @classmethod
    def is_hybrid_gpu(cls) -> bool:
        """Check if this is a hybrid GPU laptop (NVIDIA Optimus, AMD Switchable)."""
        # Check for NVIDIA
        nvidia_present = os.path.exists("/proc/driver/nvidia") or \
            shutil.which("nvidia-smi") is not None

        # Check for integrated GPU as well
        intel_present = any("intel" in p.lower() for p in glob.glob("/sys/class/drm/card*/device/vendor"))
        amd_igpu = os.path.exists("/sys/class/drm/card0/device/driver/module/drivers/pci:amdgpu")

        return nvidia_present and (intel_present or amd_igpu)

    @classmethod
    def get_gpu_mode(cls) -> str:
        """
        Get current GPU mode.
        Returns: 'integrated', 'hybrid', 'nvidia', or 'unknown'
        """
        # Check envycontrol first
        if shutil.which("envycontrol"):
            try:
                result = subprocess.run(
                    ["envycontrol", "--query"],
                    capture_output=True, text=True, check=False, timeout=10
                )
                output = result.stdout.lower()
                if "integrated" in output:
                    return "integrated"
                elif "hybrid" in output:
                    return "hybrid"
                elif "nvidia" in output:
                    return "nvidia"
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("envycontrol query failed: %s", e)

        # Check supergfxctl (ASUS)
        if shutil.which("supergfxctl"):
            try:
                result = subprocess.run(
                    ["supergfxctl", "-g"],
                    capture_output=True, text=True, check=False, timeout=10
                )
                return result.stdout.strip().lower()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("supergfxctl query failed: %s", e)

        return "unknown"

    @classmethod
    def set_gpu_mode(cls, mode: str) -> tuple:
        """
        Set GPU mode. Requires logout/reboot.

        Args:
            mode: 'integrated', 'hybrid', or 'nvidia'

        Returns:
            (success: bool, message: str)
        """
        valid_modes = ["integrated", "hybrid", "nvidia"]
        if mode not in valid_modes:
            return (False, f"Invalid mode. Choose from: {valid_modes}")

        # Try envycontrol
        if shutil.which("envycontrol"):
            try:
                result = subprocess.run(
                    ["pkexec", "envycontrol", "--switch", mode],
                    capture_output=True, text=True, check=False, timeout=30
                )
                if result.returncode == 0:
                    return (True, f"GPU mode set to '{mode}'. Logout/reboot required.")
                else:
                    return (False, result.stderr)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                return (False, str(e))

        # Try supergfxctl
        if shutil.which("supergfxctl"):
            mode_map = {"integrated": "Integrated", "hybrid": "Hybrid", "nvidia": "Dedicated"}
            try:
                result = subprocess.run(
                    ["pkexec", "supergfxctl", "-m", mode_map.get(mode, mode)],
                    capture_output=True, text=True, check=False, timeout=30
                )
                if result.returncode == 0:
                    return (True, f"GPU mode set to '{mode}'. Logout/reboot required.")
                else:
                    return (False, result.stderr)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                return (False, str(e))

        return (False, "No GPU switching tool found. Install 'envycontrol' or 'supergfxctl'.")

    @classmethod
    def get_available_gpu_tools(cls) -> list:
        """Get list of available GPU switching tools."""
        tools = []
        if shutil.which("envycontrol"):
            tools.append("envycontrol")
        if shutil.which("supergfxctl"):
            tools.append("supergfxctl")
        return tools

    # ==================== FAN CONTROL ====================

    @classmethod
    def is_nbfc_available(cls) -> bool:
        """Check if nbfc-linux is installed."""
        return shutil.which("nbfc") is not None

    @classmethod
    def get_nbfc_profiles(cls) -> list:
        """Get available NBFC fan profiles."""
        if not cls.is_nbfc_available():
            return []

        try:
            result = subprocess.run(
                ["nbfc", "config", "-l"],
                capture_output=True, text=True, check=False, timeout=10
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list NBFC profiles: %s", e)
        return []

    @classmethod
    def get_current_nbfc_config(cls) -> Optional[str]:
        """Get currently active NBFC config."""
        if not cls.is_nbfc_available():
            return None

        try:
            result = subprocess.run(
                ["nbfc", "status", "-a"],
                capture_output=True, text=True, check=False, timeout=10
            )
            for line in result.stdout.split("\n"):
                if "Selected Config" in line or "Config" in line:
                    return line.split(":")[-1].strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get NBFC config: %s", e)
        return None

    @classmethod
    def set_nbfc_profile(cls, profile: str) -> bool:
        """Set NBFC fan profile."""
        if not cls.is_nbfc_available():
            return False

        try:
            result = subprocess.run(
                ["pkexec", "nbfc", "config", "-s", profile],
                capture_output=True, text=True, check=False, timeout=30
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to set NBFC profile: %s", e)
            return False

    @classmethod
    def set_fan_speed(cls, speed: int) -> bool:
        """
        Set fan speed percentage (0-100).
        Use -1 for auto mode.
        """
        if not cls.is_nbfc_available():
            return False

        try:
            if speed < 0:
                # Auto mode
                result = subprocess.run(
                    ["pkexec", "nbfc", "set", "-a"],
                    capture_output=True, text=True, check=False, timeout=30
                )
            else:
                # Manual speed
                result = subprocess.run(
                    ["pkexec", "nbfc", "set", "-s", str(min(100, max(0, speed)))],
                    capture_output=True, text=True, check=False, timeout=30
                )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to set fan speed: %s", e)
            return False

    @classmethod
    def get_fan_status(cls) -> dict:
        """Get current fan status (speed, temperature)."""
        status = {"speed": -1, "temperature": -1, "mode": "unknown"}

        if not cls.is_nbfc_available():
            return status

        try:
            result = subprocess.run(
                ["nbfc", "status", "-a"],
                capture_output=True, text=True, check=False, timeout=10
            )
            for line in result.stdout.split("\n"):
                if "Current Speed" in line or "Speed" in line:
                    try:
                        status["speed"] = float(line.split(":")[-1].strip().replace("%", ""))
                    except ValueError:
                        pass
                if "Temperature" in line:
                    try:
                        status["temperature"] = float(line.split(":")[-1].strip().replace("°C", "").replace("C", ""))
                    except ValueError:
                        pass
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get fan status: %s", e)

        return status

    # ==================== THERMAL / POWER PROFILES ====================

    @classmethod
    def is_power_profiles_available(cls) -> bool:
        """Check if power-profiles-daemon is available."""
        return shutil.which("powerprofilesctl") is not None

    @classmethod
    def get_power_profile(cls) -> str:
        """Get current power profile."""
        if not cls.is_power_profiles_available():
            return "unknown"

        try:
            result = subprocess.run(
                ["powerprofilesctl", "get"],
                capture_output=True, text=True, check=False, timeout=10
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to get power profile: %s", e)
            return "unknown"

    @classmethod
    def set_power_profile(cls, profile: str) -> bool:
        """
        Set power profile.
        Valid profiles: power-saver, balanced, performance
        """
        if not cls.is_power_profiles_available():
            return False

        valid = ["power-saver", "balanced", "performance"]
        if profile not in valid:
            return False

        try:
            result = subprocess.run(
                ["powerprofilesctl", "set", profile],
                capture_output=True, text=True, check=False, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to set power profile: %s", e)
            return False

    @classmethod
    def get_available_power_profiles(cls) -> list:
        """Get available power profiles."""
        if not cls.is_power_profiles_available():
            return []

        try:
            result = subprocess.run(
                ["powerprofilesctl", "list"],
                capture_output=True, text=True, check=False, timeout=10
            )
            profiles = []
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith("*"):
                    # Parse profile name
                    if ":" in line:
                        profiles.append(line.split(":")[0].strip().replace("*", "").strip())
                    elif line in ["power-saver", "balanced", "performance"]:
                        profiles.append(line)
            return profiles if profiles else ["power-saver", "balanced", "performance"]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to list power profiles: %s", e)
            return ["power-saver", "balanced", "performance"]

    # ==================== AI HARDWARE ACCELERATION ====================

    @classmethod
    def get_ai_capabilities(cls) -> dict:
        """
        Detect hardware acceleration support for AI workloads.

        Returns a dict with:
            - cuda: bool - NVIDIA CUDA GPU detected
            - rocm: bool - AMD ROCm GPU detected
            - npu_intel: bool - Intel NPU (Meteor Lake/Arrow Lake) detected
            - npu_amd: bool - AMD Ryzen AI NPU detected
            - details: dict - Additional hardware details
        """
        caps: dict[str, Any] = {
            "cuda": False,
            "rocm": False,
            "npu_intel": False,
            "npu_amd": False,
            "details": {}
        }

        # 1. Check NVIDIA CUDA
        if shutil.which("nvidia-smi"):
            try:
                result = subprocess.run(
                    ["nvidia-smi", "-L"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and "GPU" in result.stdout:
                    caps["cuda"] = True
                    # Extract GPU name
                    lines = result.stdout.strip().split("\n")
                    if lines:
                        caps["details"]["nvidia_gpu"] = lines[0].strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("nvidia-smi check failed: %s", e)

        # 2. Check AMD ROCm
        if shutil.which("rocminfo"):
            try:
                result = subprocess.run(
                    ["rocminfo"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result.returncode == 0 and "Agent" in result.stdout:
                    caps["rocm"] = True
                    caps["details"]["rocm_available"] = True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("rocminfo check failed: %s", e)

        # Alternative AMD check via hip
        if not caps["rocm"] and shutil.which("hipconfig"):
            try:
                result = subprocess.run(
                    ["hipconfig", "--platform"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and "amd" in result.stdout.lower():
                    caps["rocm"] = True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("hipconfig check failed: %s", e)

        # 3. Check Intel NPU (Core Ultra / Meteor Lake)
        # NPUs appear in /dev/accel/ on newer kernels (6.5+)
        try:
            accel_devices = glob.glob("/dev/accel/*")
            if accel_devices:
                caps["npu_intel"] = True
                caps["details"]["npu_devices"] = accel_devices
        except OSError as e:
            logger.debug("NPU device check failed: %s", e)

        # Alternative Intel NPU check via sysfs
        npu_path = "/sys/class/misc/intel_vpu"
        if os.path.exists(npu_path):
            caps["npu_intel"] = True

        # 4. Check AMD Ryzen AI NPU (XDNA)
        xdna_path = "/sys/class/amdxdna"
        if os.path.exists(xdna_path):
            caps["npu_amd"] = True
            caps["details"]["amd_xdna"] = True

        # Check for NPU driver module
        try:
            result = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "intel_vpu" in result.stdout:
                caps["npu_intel"] = True
            if "amdxdna" in result.stdout:
                caps["npu_amd"] = True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("lsmod NPU check failed: %s", e)

        return caps

    @classmethod
    def get_ai_summary(cls) -> str:
        """
        Get a human-readable summary of AI capabilities.
        """
        caps = cls.get_ai_capabilities()

        parts = []
        if caps["cuda"]:
            gpu_name = caps["details"].get("nvidia_gpu", "NVIDIA GPU")
            parts.append(f"✅ CUDA ({gpu_name})")
        if caps["rocm"]:
            parts.append("✅ ROCm (AMD GPU)")
        if caps["npu_intel"]:
            parts.append("✅ Intel NPU")
        if caps["npu_amd"]:
            parts.append("✅ AMD Ryzen AI NPU")

        if not parts:
            return "❌ No AI hardware acceleration detected (CPU-only mode)"

        return "AI Hardware: " + ", ".join(parts)
