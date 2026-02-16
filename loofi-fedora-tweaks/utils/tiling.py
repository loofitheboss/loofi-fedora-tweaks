"""
Tiling Manager - Window management utilities.
Part of v9.0 "Director" update.

Provides configuration helpers for:
- Hyprland (Wayland tiling compositor)
- Sway (i3-compatible Wayland compositor)
- Workspace templates
"""

import logging
import subprocess
import shutil
import os
from dataclasses import dataclass
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Operation result."""

    success: bool
    message: str
    data: Optional[dict] = None


class TilingManager:
    """
    Manages tiling window manager configurations.
    Supports Hyprland and Sway.
    """

    # Common tiling layouts
    LAYOUTS = {
        "dwindle": {
            "name": "Dwindle (Fibonacci)",
            "desc": "New windows take half of remaining space",
            "hyprland": "dwindle",
            "sway": "splitv",
        },
        "master": {
            "name": "Master-Stack",
            "desc": "One large master, others stacked",
            "hyprland": "master",
            "sway": "splith",
        },
        "columns": {
            "name": "Columns",
            "desc": "Equal width columns",
            "hyprland": "dwindle",
            "sway": "splitv",
        },
    }

    # Workspace templates
    WORKSPACE_TEMPLATES: dict[str, dict[str, Any]] = {
        "development": {
            "name": "Development",
            "workspaces": {
                1: {"name": "Code", "apps": ["code", "terminal"]},
                2: {"name": "Browser", "apps": ["firefox"]},
                3: {"name": "Docs", "apps": ["evince", "obsidian"]},
                4: {"name": "Terminal", "apps": ["terminal"]},
            },
        },
        "creative": {
            "name": "Creative",
            "workspaces": {
                1: {"name": "Design", "apps": ["gimp", "inkscape"]},
                2: {"name": "Reference", "apps": ["firefox"]},
                3: {"name": "Files", "apps": ["nautilus"]},
                4: {"name": "Music", "apps": ["spotify"]},
            },
        },
        "gaming": {
            "name": "Gaming",
            "workspaces": {
                1: {"name": "Game", "apps": ["steam"]},
                2: {"name": "Chat", "apps": ["discord"]},
                3: {"name": "Browser", "apps": ["firefox"]},
                4: {"name": "System", "apps": ["terminal"]},
            },
        },
    }

    @classmethod
    def is_hyprland(cls) -> bool:
        """Check if running Hyprland."""
        session = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        return "hyprland" in session or shutil.which("hyprctl") is not None

    @classmethod
    def is_sway(cls) -> bool:
        """Check if running Sway."""
        session = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        return "sway" in session or shutil.which("swaymsg") is not None

    @classmethod
    def get_compositor(cls) -> str:
        """Detect current compositor."""
        if cls.is_hyprland():
            return "hyprland"
        elif cls.is_sway():
            return "sway"
        else:
            return "unknown"

    @classmethod
    def get_config_path(cls) -> Path:
        """Get config path for current compositor."""
        if cls.is_hyprland():
            return Path.home() / ".config/hypr/hyprland.conf"
        elif cls.is_sway():
            return Path.home() / ".config/sway/config"
        else:
            return Path.home() / ".config"

    @classmethod
    def get_keybindings(cls) -> list[dict]:
        """Get current keybindings from compositor config."""
        bindings: list[dict[str, str]] = []
        config_path = cls.get_config_path()

        if not config_path.exists():
            return bindings

        try:
            with open(config_path, "r") as f:
                content = f.read()

            if cls.is_hyprland():
                # Parse Hyprland binds
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("bind = "):
                        parts = line.replace("bind = ", "").split(",")
                        if len(parts) >= 4:
                            bindings.append(
                                {
                                    "mods": parts[0].strip(),
                                    "key": parts[1].strip(),
                                    "action": parts[2].strip(),
                                    "args": ",".join(parts[3:]).strip(),
                                }
                            )
            elif cls.is_sway():
                # Parse Sway bindsym
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("bindsym "):
                        parts = line.replace("bindsym ", "").split(" ", 1)
                        if len(parts) == 2:
                            bindings.append({"key": parts[0], "action": parts[1]})
        except (OSError, IOError) as e:
            logger.debug("Failed to parse keybindings from config: %s", e)

        return bindings

    @classmethod
    def add_keybinding(cls, mods: str, key: str, action: str, args: str = "") -> Result:
        """Add a keybinding to compositor config."""
        config_path = cls.get_config_path()

        if not config_path.exists():
            return Result(False, f"Config not found: {config_path}")

        try:
            # Create backup
            backup_path = config_path.with_suffix(".conf.bak")
            shutil.copy2(config_path, backup_path)

            with open(config_path, "a") as f:
                if cls.is_hyprland():
                    f.write(f"\nbind = {mods}, {key}, {action}, {args}\n")
                elif cls.is_sway():
                    f.write(f"\nbindsym {mods}+{key} {action} {args}\n")

            return Result(
                True,
                "Keybinding added. Reload config to apply.",
                {"backup": str(backup_path)},
            )
        except (OSError, IOError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def reload_config(cls) -> Result:
        """Reload compositor configuration."""
        try:
            if cls.is_hyprland():
                result = subprocess.run(
                    ["hyprctl", "reload"], capture_output=True, text=True, timeout=10
                )
            elif cls.is_sway():
                result = subprocess.run(
                    ["swaymsg", "reload"], capture_output=True, text=True, timeout=10
                )
            else:
                return Result(False, "Unknown compositor")

            if result.returncode == 0:
                return Result(True, "Configuration reloaded")
            else:
                return Result(False, f"Reload failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def generate_workspace_template(cls, template_name: str) -> Result:
        """
        Generate config for a workspace template.

        Returns the config snippet to add.
        """
        if template_name not in cls.WORKSPACE_TEMPLATES:
            return Result(False, f"Unknown template: {template_name}")

        template = cls.WORKSPACE_TEMPLATES[template_name]
        config_lines = []

        config_lines.append(f"# Workspace Template: {template['name']}")
        config_lines.append("# Generated by Loofi Fedora Tweaks")
        config_lines.append("")

        if cls.is_hyprland():
            for ws_num, ws_config in template["workspaces"].items():  # type: ignore[union-attr]
                config_lines.append(f"# Workspace {ws_num}: {ws_config['name']}")
                for app in ws_config["apps"]:
                    config_lines.append(
                        f"windowrulev2 = workspace {ws_num} silent, class:^({app})$"
                    )
            config_lines.append("")
        elif cls.is_sway():
            for ws_num, ws_config in template["workspaces"].items():  # type: ignore[union-attr]
                config_lines.append(f"# Workspace {ws_num}: {ws_config['name']}")
                for app in ws_config["apps"]:
                    config_lines.append(f'assign [app_id="{app}"] workspace {ws_num}')
            config_lines.append("")

        return Result(True, "Template generated", {"config": "\n".join(config_lines)})

    @classmethod
    def move_window_to_workspace(cls, workspace: int) -> Result:
        """Move focused window to workspace."""
        try:
            if cls.is_hyprland():
                result = subprocess.run(
                    ["hyprctl", "dispatch", "movetoworkspacesilent", str(workspace)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif cls.is_sway():
                result = subprocess.run(
                    ["swaymsg", "move", "container", "to", "workspace", str(workspace)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            else:
                return Result(False, "Unknown compositor")

            if result.returncode == 0:
                return Result(True, f"Moved to workspace {workspace}")
            else:
                return Result(False, f"Move failed: {result.stderr}")
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")


class DotfileManager:
    """
    Manages dotfile synchronization.
    Useful for keeping configs in sync across machines.
    """

    # Common dotfile paths
    DOTFILES = {
        "hyprland": ".config/hypr",
        "sway": ".config/sway",
        "waybar": ".config/waybar",
        "kitty": ".config/kitty",
        "alacritty": ".config/alacritty",
        "fish": ".config/fish",
        "zsh": ".zshrc",
        "nvim": ".config/nvim",
        "bash": ".bashrc",
    }

    @classmethod
    def create_dotfile_repo(cls, repo_path: Path) -> Result:
        """
        Create a dotfiles repository structure.
        """
        try:
            repo_path.mkdir(parents=True, exist_ok=True)

            # Create directories
            (repo_path / "config").mkdir(exist_ok=True)
            (repo_path / "scripts").mkdir(exist_ok=True)

            # Create install script
            install_script = repo_path / "install.sh"
            install_script.write_text("""#!/bin/bash
# Dotfiles installer - Generated by Loofi Fedora Tweaks

DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing dotfiles from $DOTFILES_DIR"

# Symlink configs
for config in "$DOTFILES_DIR/config/"*; do
    name=$(basename "$config")
    target="$HOME/.config/$name"

    if [ -e "$target" ]; then
        echo "Backing up $target"
        mv "$target" "$target.backup"
    fi

    ln -sf "$config" "$target"
    echo "Linked $name"
done

echo "Done!"
""")
            os.chmod(install_script, 0o755)

            # Create README
            readme = repo_path / "README.md"
            readme.write_text("""# Dotfiles

Generated by Loofi Fedora Tweaks.

## Installation

```bash
./install.sh
```

## Structure

- `config/` - Config files to symlink to ~/.config/
- `scripts/` - Utility scripts
""")

            # Initialize git
            subprocess.run(
                ["git", "init"], cwd=repo_path, capture_output=True, timeout=10
            )

            return Result(
                True, f"Dotfiles repo created at {repo_path}", {"path": str(repo_path)}
            )
        except (subprocess.SubprocessError, OSError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def sync_dotfile(cls, name: str, repo_path: Path) -> Result:
        """
        Copy a dotfile to the repo.
        """
        if name not in cls.DOTFILES:
            return Result(False, f"Unknown dotfile: {name}")

        source = Path.home() / cls.DOTFILES[name]

        if not source.exists():
            return Result(False, f"Source not found: {source}")

        try:
            dest = repo_path / "config" / name

            if source.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, dest)

            return Result(True, f"Synced {name} to dotfiles repo")
        except (OSError, IOError) as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def list_managed_dotfiles(cls, repo_path: Path) -> list[str]:
        """List dotfiles in the repo."""
        config_dir = repo_path / "config"

        if not config_dir.exists():
            return []

        return [f.name for f in config_dir.iterdir()]
