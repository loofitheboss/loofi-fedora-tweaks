"""
Developer Tools management utilities.
Part of v7.1 "Developer" update.

Handles installation of version managers:
- PyEnv for Python
- NVM for Node.js
- Rustup for Rust
"""

import logging
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Operation result with message."""

    success: bool
    message: str
    data: Optional[dict] = None


class DevToolsManager:
    """
    Manages developer version managers installation.

    These tools allow developers to manage multiple versions of languages
    without interfering with system packages.
    """

    # Installation scripts (official sources)
    INSTALLERS: dict[str, dict[str, Any]] = {
        "pyenv": {
            "name": "PyEnv",
            "check_cmd": "pyenv",
            "install_script": "https://pyenv.run",
            "shell_config": """
# PyEnv configuration
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
""",
            "description": "Python version manager - install multiple Python versions",
        },
        "nvm": {
            "name": "NVM",
            "check_cmd": None,  # NVM is a shell function, not a binary
            "check_dir": ".nvm",
            "install_script": "https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh",
            "shell_config": r"""
# NVM configuration
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
""",
            "description": "Node Version Manager - install multiple Node.js versions",
        },
        "rustup": {
            "name": "Rustup",
            "check_cmd": "rustup",
            "install_script": "https://sh.rustup.rs",
            "shell_config": """
# Rust/Cargo configuration
. "$HOME/.cargo/env"
""",
            "description": "Rust toolchain installer - manage Rust versions and targets",
        },
    }

    @classmethod
    def get_tool_status(cls, tool: str) -> tuple[bool, str]:
        """
        Check if a dev tool is installed.

        Args:
            tool: Tool key (pyenv, nvm, rustup)

        Returns:
            Tuple of (installed, version_string)
        """
        info = cls.INSTALLERS.get(tool)
        if not info:
            return False, "Unknown tool"

        # Check by command
        if info.get("check_cmd"):
            if shutil.which(info["check_cmd"]):
                try:
                    result = subprocess.run(
                        [info["check_cmd"], "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    version = result.stdout.strip().split("\n")[0]
                    return True, version
                except Exception as e:
                    logger.debug("Failed to get version for %s: %s", tool, e)
                    return True, "installed"

        # Check by directory (for NVM)
        if info.get("check_dir"):
            check_path = Path.home() / info["check_dir"]
            if check_path.exists():
                return True, "installed"

        return False, "not installed"

    @classmethod
    def get_all_status(cls) -> dict[str, tuple[bool, str]]:
        """
        Get installation status of all dev tools.

        Returns:
            Dict mapping tool key to (installed, version) tuple.
        """
        return {tool: cls.get_tool_status(tool) for tool in cls.INSTALLERS}

    @classmethod
    def install_pyenv(cls, python_version: str = "3.12") -> Result:
        """
        Install PyEnv and optionally a Python version.

        Args:
            python_version: Python version to install (e.g., "3.12", "3.11.8")

        Returns:
            Result with success status and message.
        """
        installed, _ = cls.get_tool_status("pyenv")
        if installed:
            return Result(True, "PyEnv is already installed.")

        # Check for required build dependencies
        required_deps = [
            "gcc",
            "make",
            "zlib-devel",
            "bzip2-devel",
            "readline-devel",
            "sqlite-devel",
            "openssl-devel",
            "libffi-devel",
            "xz-devel",
        ]

        try:
            # Install build dependencies first
            binary, args, desc = PrivilegedCommand.dnf("install", *required_deps)
            subprocess.run([binary] + args, check=True, timeout=300)

            # Install pyenv via official script
            subprocess.run(
                ["bash", "-c", "curl -fsSL https://pyenv.run | bash"],
                check=True,
                timeout=300,
            )

            # Add to shell config
            cls._add_shell_config(cls.INSTALLERS["pyenv"]["shell_config"])

            return Result(
                True,
                f"PyEnv installed successfully!\n"
                f"Restart your terminal, then run:\n"
                f"  pyenv install {python_version}\n"
                f"  pyenv global {python_version}",
            )

        except subprocess.CalledProcessError as e:
            return Result(False, f"Installation failed: {e}")
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def install_nvm(cls, node_version: str = "lts") -> Result:
        """
        Install NVM and optionally Node.js.

        Args:
            node_version: Node version to install ("lts", "latest", or specific version)

        Returns:
            Result with success status and message.
        """
        installed, _ = cls.get_tool_status("nvm")
        if installed:
            return Result(True, "NVM is already installed.")

        try:
            # Install NVM via official script
            subprocess.run(
                [
                    "bash",
                    "-c",
                    "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash",
                ],
                check=True,
                timeout=120,
            )

            return Result(
                True,
                f"NVM installed successfully!\n"
                f"Restart your terminal, then run:\n"
                f"  nvm install --{node_version}\n"
                if node_version in ["lts", "latest"]
                else f"  nvm install {node_version}\n",
            )

        except subprocess.CalledProcessError as e:
            return Result(False, f"Installation failed: {e}")
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def install_rustup(cls) -> Result:
        """
        Install Rustup (Rust toolchain manager).

        Returns:
            Result with success status and message.
        """
        installed, _ = cls.get_tool_status("rustup")
        if installed:
            return Result(True, "Rustup is already installed.")

        try:
            # Install rustup non-interactively
            subprocess.run(
                [
                    "bash",
                    "-c",
                    "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
                ],
                check=True,
                timeout=300,
            )

            # Add to shell config
            cls._add_shell_config(cls.INSTALLERS["rustup"]["shell_config"])

            return Result(
                True,
                "Rustup installed successfully!\n"
                "Restart your terminal to use `rustc`, `cargo`, and `rustup`.",
            )

        except subprocess.CalledProcessError as e:
            return Result(False, f"Installation failed: {e}")
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def _add_shell_config(cls, config: str):
        """
        Add configuration to shell RC files.

        Appends to both .bashrc and .zshrc if they exist.
        """
        home = Path.home()

        for rc_file in [".bashrc", ".zshrc"]:
            rc_path = home / rc_file
            if rc_path.exists():
                content = rc_path.read_text()
                # Avoid duplicates
                if config.strip() not in content:
                    with open(rc_path, "a") as f:
                        f.write(f"\n{config.strip()}\n")

    @classmethod
    def get_available_tools(cls) -> list[dict]:
        """
        Get list of available tools with their status.

        Returns:
            List of dicts with tool info and status.
        """
        tools = []
        for key, info in cls.INSTALLERS.items():
            installed, version = cls.get_tool_status(key)
            tools.append(
                {
                    "key": key,
                    "name": info["name"],
                    "description": info["description"],
                    "installed": installed,
                    "version": version,
                }
            )
        return tools
