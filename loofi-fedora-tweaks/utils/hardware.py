"""
Hardware Manager - Central hardware control abstraction.
Handles CPU governors, GPU modes, fan control, and thermal management.
"""

import os
import glob
import subprocess
import shutil
from typing import Optional


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
        except Exception:
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
                capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except Exception:
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
        except Exception:
            pass
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
                    capture_output=True, text=True, check=False
                )
                output = result.stdout.lower()
                if "integrated" in output:
                    return "integrated"
                elif "hybrid" in output:
                    return "hybrid"
                elif "nvidia" in output:
                    return "nvidia"
            except Exception:
                pass
        
        # Check supergfxctl (ASUS)
        if shutil.which("supergfxctl"):
            try:
                result = subprocess.run(
                    ["supergfxctl", "-g"],
                    capture_output=True, text=True, check=False
                )
                return result.stdout.strip().lower()
            except Exception:
                pass
        
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
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    return (True, f"GPU mode set to '{mode}'. Logout/reboot required.")
                else:
                    return (False, result.stderr)
            except Exception as e:
                return (False, str(e))
        
        # Try supergfxctl
        if shutil.which("supergfxctl"):
            mode_map = {"integrated": "Integrated", "hybrid": "Hybrid", "nvidia": "Dedicated"}
            try:
                result = subprocess.run(
                    ["pkexec", "supergfxctl", "-m", mode_map.get(mode, mode)],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    return (True, f"GPU mode set to '{mode}'. Logout/reboot required.")
                else:
                    return (False, result.stderr)
            except Exception as e:
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
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except Exception:
            pass
        return []
    
    @classmethod
    def get_current_nbfc_config(cls) -> Optional[str]:
        """Get currently active NBFC config."""
        if not cls.is_nbfc_available():
            return None
        
        try:
            result = subprocess.run(
                ["nbfc", "status", "-a"],
                capture_output=True, text=True, check=False
            )
            for line in result.stdout.split("\n"):
                if "Selected Config" in line or "Config" in line:
                    return line.split(":")[-1].strip()
        except Exception:
            pass
        return None
    
    @classmethod
    def set_nbfc_profile(cls, profile: str) -> bool:
        """Set NBFC fan profile."""
        if not cls.is_nbfc_available():
            return False
        
        try:
            result = subprocess.run(
                ["pkexec", "nbfc", "config", "-s", profile],
                capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except Exception:
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
                    capture_output=True, text=True, check=False
                )
            else:
                # Manual speed
                result = subprocess.run(
                    ["pkexec", "nbfc", "set", "-s", str(min(100, max(0, speed)))],
                    capture_output=True, text=True, check=False
                )
            return result.returncode == 0
        except Exception:
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
                capture_output=True, text=True, check=False
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
        except Exception:
            pass
        
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
                capture_output=True, text=True, check=False
            )
            return result.stdout.strip()
        except Exception:
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
                capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @classmethod
    def get_available_power_profiles(cls) -> list:
        """Get available power profiles."""
        if not cls.is_power_profiles_available():
            return []
        
        try:
            result = subprocess.run(
                ["powerprofilesctl", "list"],
                capture_output=True, text=True, check=False
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
        except Exception:
            return ["power-saver", "balanced", "performance"]
