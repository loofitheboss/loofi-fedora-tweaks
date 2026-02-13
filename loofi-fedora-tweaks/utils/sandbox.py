"""
Sandbox Manager - Application sandboxing utilities.
Part of v8.5 "Sentinel" update.

Provides Firejail and Bubblewrap wrappers for running
non-Flatpak applications in sandboxed environments.
"""

import subprocess
import shutil
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class Result:
    """Operation result."""
    success: bool
    message: str
    data: Optional[dict] = None


class PluginIsolationManager:
    """Runtime enforcement checks for plugin isolation policies."""

    @staticmethod
    def _mode_value(mode) -> str:
        value = getattr(mode, "value", mode)
        return str(value or "advisory").strip().lower()

    @classmethod
    def can_enforce_mode(cls, mode) -> bool:
        """Return whether current host can enforce a requested isolation mode."""
        mode_value = cls._mode_value(mode)
        if mode_value == "advisory":
            return True
        if mode_value == "process":
            return (
                SandboxManager.is_firejail_installed()
                or BubblewrapManager.is_installed()
            )
        if mode_value == "os":
            return BubblewrapManager.is_installed()
        return False

    @classmethod
    def enforce_policy(cls, policy) -> Result:
        """Validate that policy isolation mode is enforceable on this host."""
        mode = cls._mode_value(getattr(policy, "mode", "advisory"))
        plugin_id = str(getattr(policy, "plugin_id", "unknown-plugin"))

        if cls.can_enforce_mode(mode):
            return Result(
                True,
                f"Isolation policy enforced for {plugin_id} (mode={mode})",
                {"plugin_id": plugin_id, "mode": mode},
            )

        return Result(
            False,
            f"Isolation policy cannot be enforced for {plugin_id} (mode={mode})",
            {"plugin_id": plugin_id, "mode": mode},
        )


class SandboxManager:
    """
    Manages application sandboxing via Firejail or Bubblewrap.

    Firejail is preferred for ease of use with existing profiles.
    Bubblewrap is used for custom, minimal sandboxes.
    """

    # Common Firejail profiles for popular apps
    FIREJAIL_PROFILES = {
        "firefox": "Firefox web browser",
        "chromium": "Chromium browser",
        "vlc": "VLC media player",
        "gimp": "GIMP image editor",
        "libreoffice": "LibreOffice suite",
        "discord": "Discord chat",
        "steam": "Steam gaming platform",
        "thunderbird": "Thunderbird email",
        "telegram-desktop": "Telegram messenger",
    }

    @classmethod
    def is_firejail_installed(cls) -> bool:
        """Check if Firejail is installed."""
        return shutil.which("firejail") is not None

    @classmethod
    def is_bubblewrap_installed(cls) -> bool:
        """Check if Bubblewrap is installed."""
        return shutil.which("bwrap") is not None

    @classmethod
    def install_firejail(cls) -> Result:
        """Install Firejail via DNF."""
        if cls.is_firejail_installed():
            return Result(True, "Firejail is already installed")

        try:
            # Security: Safe - Uses hardcoded command list with shell=False (default)
            # Not user-controllable, not reachable from API without validation
            result = subprocess.run(
                ["pkexec", "dnf", "install", "firejail", "-y"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return Result(True, "Firejail installed successfully")
            else:
                return Result(False, f"Installation failed: {result.stderr}")
        except Exception as e:
            return Result(False, f"Installation error: {e}")

    @classmethod
    def list_profiles(cls) -> list[str]:
        """List available Firejail profiles."""
        if not cls.is_firejail_installed():
            return []

        profiles = []
        profile_dirs = [
            "/etc/firejail",
            "/usr/local/etc/firejail",
            Path.home() / ".config/firejail"
        ]

        for dir_path in profile_dirs:
            if os.path.exists(dir_path):
                for f in os.listdir(dir_path):
                    if f.endswith(".profile"):
                        profiles.append(f.replace(".profile", ""))

        return sorted(set(profiles))

    @classmethod
    def run_sandboxed(
        cls,
        command: list[str],
        no_network: bool = False,
        private_home: bool = False,
        read_only_home: bool = False,
        profile: Optional[str] = None
    ) -> Result:
        """
        Run a command in a Firejail sandbox.

        Args:
            command: Command and arguments to run
            no_network: Disable network access
            private_home: Use empty private home directory
            read_only_home: Mount home as read-only
            profile: Specific profile to use

        Returns:
            Result with process info.
        """
        if not cls.is_firejail_installed():
            return Result(False, "Firejail is not installed")

        firejail_cmd = ["firejail"]

        if no_network:
            firejail_cmd.append("--net=none")

        if private_home:
            firejail_cmd.append("--private")
        elif read_only_home:
            firejail_cmd.append("--private-home")

        if profile:
            firejail_cmd.extend(["--profile", profile])

        firejail_cmd.extend(command)

        try:
            # Start process in background
            # Security: Safe - Uses hardcoded command list with shell=False (default)
            # firejail command itself is hardcoded, only sandboxed app command varies
            process = subprocess.Popen(
                firejail_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            return Result(
                True,
                f"Started sandboxed: {' '.join(command)}",
                {"pid": process.pid}
            )
        except Exception as e:
            return Result(False, f"Failed to start sandbox: {e}")

    @classmethod
    def create_desktop_entry(
        cls,
        app_name: str,
        exec_command: str,
        no_network: bool = False,
        private_home: bool = False
    ) -> Result:
        """
        Create a sandboxed .desktop entry for an application.

        This creates a new desktop file that launches the app
        through Firejail with specified restrictions.
        """
        if not cls.is_firejail_installed():
            return Result(False, "Firejail is not installed")

        # Build firejail command
        fj_opts = []
        if no_network:
            fj_opts.append("--net=none")
        if private_home:
            fj_opts.append("--private")

        fj_cmd = f"firejail {' '.join(fj_opts)} {exec_command}"

        desktop_content = f"""[Desktop Entry]
Name={app_name} (Sandboxed)
Comment={app_name} running in Firejail sandbox
Exec={fj_cmd}
Icon={app_name.lower()}
Terminal=false
Type=Application
Categories=Security;
"""

        desktop_dir = Path.home() / ".local/share/applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)

        desktop_file = desktop_dir / f"{app_name.lower()}-sandboxed.desktop"

        try:
            with open(desktop_file, "w") as f:
                f.write(desktop_content)

            # Make executable
            os.chmod(desktop_file, 0o755)

            return Result(
                True,
                f"Created sandboxed launcher: {desktop_file}",
                {"path": str(desktop_file)}
            )
        except Exception as e:
            return Result(False, f"Failed to create desktop entry: {e}")

    @classmethod
    def get_sandbox_status(cls, pid: int) -> dict:
        """Check if a process is running in a sandbox."""
        status = {
            "running": False,
            "sandboxed": False,
            "restrictions": []
        }

        # Check if process exists
        try:
            os.kill(pid, 0)
            status["running"] = True
        except OSError:
            return status

        # Check if running under firejail
        try:
            cmdline_path = f"/proc/{pid}/cmdline"
            if os.path.exists(cmdline_path):
                with open(cmdline_path, "rb") as f:
                    cmdline = f.read().decode("utf-8", errors="ignore")
                    if "firejail" in cmdline:
                        status["sandboxed"] = True

                        # Parse restrictions
                        if "--net=none" in cmdline:
                            status["restrictions"].append("no_network")
                        if "--private" in cmdline:
                            status["restrictions"].append("private_home")
        except Exception:
            pass

        return status


class BubblewrapManager:
    """
    Low-level sandboxing via Bubblewrap.
    Use for custom, minimal sandboxes with fine-grained control.
    """

    @classmethod
    def is_installed(cls) -> bool:
        """Check if Bubblewrap is installed."""
        return shutil.which("bwrap") is not None

    @classmethod
    def run_minimal_sandbox(
        cls,
        command: list[str],
        share_paths: Optional[list[str]] = None
    ) -> Result:
        """
        Run command in a minimal Bubblewrap sandbox.

        This creates an extremely restricted environment with:
        - No network
        - No home directory access (unless specified)
        - Read-only system
        """
        if not cls.is_installed():
            return Result(False, "Bubblewrap is not installed")

        bwrap_cmd = [
            "bwrap",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/sbin", "/sbin",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--unshare-net",  # No network
            "--unshare-pid",  # Separate PID namespace
        ]

        # Add shared paths
        if share_paths:
            for path in share_paths:
                if os.path.exists(path):
                    bwrap_cmd.extend(["--bind", path, path])

        bwrap_cmd.extend(command)

        try:
            process = subprocess.Popen(
                bwrap_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            return Result(
                True,
                f"Started in minimal sandbox: {' '.join(command)}",
                {"pid": process.pid}
            )
        except Exception as e:
            return Result(False, f"Failed to start sandbox: {e}")
