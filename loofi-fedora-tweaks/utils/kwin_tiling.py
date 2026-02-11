"""
KWin Tiling Manager - KDE Plasma window management.
Part of v9.0 "Director" update.

Provides:
- KWin quick tiling integration
- Custom KWin scripts for tiling layouts
- Window rules management
"""

import subprocess
import shutil
import os
import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class Result:
    """Operation result."""
    success: bool
    message: str
    data: Optional[dict] = None


class KWinManager:
    """
    Manages KWin tiling and window rules for KDE Plasma.

    Uses kwriteconfig5/kwriteconfig6 and dbus for configuration.
    """

    # Quick tile positions
    TILE_POSITIONS = {
        "left": "Quick Tile Window to the Left",
        "right": "Quick Tile Window to the Right",
        "top": "Quick Tile Window to the Top",
        "bottom": "Quick Tile Window to the Bottom",
        "top_left": "Quick Tile Window to the Top Left",
        "top_right": "Quick Tile Window to the Top Right",
        "bottom_left": "Quick Tile Window to the Bottom Left",
        "bottom_right": "Quick Tile Window to the Bottom Right",
        "maximize": "Maximize Window",
    }

    # Default keybindings for tiling
    DEFAULT_BINDINGS = {
        "Meta+Left": "left",
        "Meta+Right": "right",
        "Meta+Up": "maximize",
        "Meta+Down": "minimize",
        "Meta+H": "left",
        "Meta+L": "right",
        "Meta+K": "top",
        "Meta+J": "bottom",
    }

    @classmethod
    def is_kde(cls) -> bool:
        """Check if running KDE Plasma."""
        session = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        return "kde" in session or "plasma" in session

    @classmethod
    def is_wayland(cls) -> bool:
        """Check if running Wayland session."""
        return os.environ.get("XDG_SESSION_TYPE", "") == "wayland"

    @classmethod
    def get_kwriteconfig(cls) -> Optional[str]:
        """Get appropriate kwriteconfig command."""
        for cmd in ["kwriteconfig6", "kwriteconfig5"]:
            if shutil.which(cmd):
                return cmd
        return None

    @classmethod
    def get_kreadconfig(cls) -> Optional[str]:
        """Get appropriate kreadconfig command."""
        for cmd in ["kreadconfig6", "kreadconfig5"]:
            if shutil.which(cmd):
                return cmd
        return None

    @classmethod
    def enable_quick_tiling(cls) -> Result:
        """Enable KWin quick tiling feature."""
        kwrite = cls.get_kwriteconfig()
        if not kwrite:
            return Result(False, "kwriteconfig not found")

        try:
            # Enable quick tiling in kwinrc
            result = subprocess.run(
                [kwrite, "--file", "kwinrc", "--group", "Windows",
                 "--key", "ElectricBorders", "1"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return Result(False, f"Failed: {result.stderr}")

            return Result(True, "Quick tiling enabled. Restart KWin to apply.")
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def set_keybinding(cls, shortcut: str, action: str) -> Result:
        """
        Set a KWin keybinding.

        Args:
            shortcut: Key combo like "Meta+H"
            action: Action name from TILE_POSITIONS
        """
        if action not in cls.TILE_POSITIONS:
            return Result(False, f"Unknown action: {action}")

        kwrite = cls.get_kwriteconfig()
        if not kwrite:
            return Result(False, "kwriteconfig not found")

        action_name = cls.TILE_POSITIONS[action]

        try:
            result = subprocess.run(
                [kwrite, "--file", "kglobalshortcutsrc",
                 "--group", "kwin",
                 "--key", action_name, shortcut],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return Result(False, f"Failed: {result.stderr}")

            return Result(True, f"Bound {shortcut} to {action_name}")
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def apply_tiling_preset(cls, preset: str = "vim") -> Result:
        """
        Apply a tiling keybinding preset.

        Presets:
        - vim: H/J/K/L style navigation
        - arrows: Arrow key navigation
        """
        if preset == "vim":
            bindings = {
                "Meta+H": "left",
                "Meta+L": "right",
                "Meta+K": "top",
                "Meta+J": "bottom",
                "Meta+Shift+H": "top_left",
                "Meta+Shift+L": "top_right",
                "Meta+Shift+J": "bottom_left",
                "Meta+Shift+K": "bottom_right",
                "Meta+M": "maximize",
            }
        elif preset == "arrows":
            bindings = {
                "Meta+Left": "left",
                "Meta+Right": "right",
                "Meta+Up": "maximize",
                "Meta+Down": "bottom",
                "Meta+Shift+Left": "top_left",
                "Meta+Shift+Right": "top_right",
                "Meta+Ctrl+Left": "bottom_left",
                "Meta+Ctrl+Right": "bottom_right",
            }
        else:
            return Result(False, f"Unknown preset: {preset}")

        errors = []
        for shortcut, action in bindings.items():
            result = cls.set_keybinding(shortcut, action)
            if not result.success:
                errors.append(f"{shortcut}: {result.message}")

        if errors:
            return Result(False, f"Some bindings failed: {', '.join(errors)}")

        return Result(
            True,
            f"Applied '{preset}' preset. Restart KWin to apply.",
            {"bindings": bindings}
        )

    @classmethod
    def reconfigure_kwin(cls) -> Result:
        """Reconfigure KWin to apply changes."""
        try:
            # Use dbus to reconfigure
            result = subprocess.run(
                ["qdbus", "org.kde.KWin", "/KWin", "reconfigure"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return Result(True, "KWin reconfigured")

            # Try dbus-send as fallback
            result = subprocess.run(
                ["dbus-send", "--type=signal", "--dest=org.kde.KWin",
                 "/KWin", "org.kde.KWin.reloadConfig"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return Result(True, "KWin reconfigured")
            else:
                return Result(False, "Failed to reconfigure KWin")
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def add_window_rule(
        cls,
        window_class: str,
        workspace: Optional[int] = None,
        maximized: bool = False,
        position: Optional[str] = None
    ) -> Result:
        """
        Add a KWin window rule.

        Args:
            window_class: Window class to match
            workspace: Workspace to place window on
            maximized: Start maximized
            position: Tile position
        """
        Path.home() / ".config/kwinrulesrc"

        try:
            # Read existing rules count
            kread = cls.get_kreadconfig()
            count = 0

            if kread:
                result = subprocess.run(
                    [kread, "--file", "kwinrulesrc", "--group", "General",
                     "--key", "count"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    count = int(result.stdout.strip())

            # Add new rule
            new_rule_num = count + 1
            kwrite = cls.get_kwriteconfig()

            if not kwrite:
                return Result(False, "kwriteconfig not found")

            # Set rule properties
            commands = [
                [kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                 "--key", "Description", f"Loofi Rule: {window_class}"],
                [kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                 "--key", "wmclass", window_class],
                [kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                 "--key", "wmclassmatch", "1"],  # Exact match
            ]

            if workspace:
                commands.append([
                    kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                    "--key", "desktops", str(workspace)
                ])
                commands.append([
                    kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                    "--key", "desktopsrule", "2"  # Force
                ])

            if maximized:
                commands.append([
                    kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                    "--key", "maximizehoriz", "true"
                ])
                commands.append([
                    kwrite, "--file", "kwinrulesrc", "--group", f"{new_rule_num}",
                    "--key", "maximizevert", "true"
                ])

            # Update count
            commands.append([
                kwrite, "--file", "kwinrulesrc", "--group", "General",
                "--key", "count", str(new_rule_num)
            ])

            for cmd in commands:
                subprocess.run(cmd, capture_output=True, timeout=10)

            return Result(
                True,
                f"Window rule added for {window_class}",
                {"rule_number": new_rule_num}
            )
        except Exception as e:
            return Result(False, f"Error: {e}")

    @classmethod
    def get_window_list(cls) -> list[dict]:
        """Get list of open windows."""
        windows = []

        try:
            result = subprocess.run(
                ["qdbus", "org.kde.KWin", "/KWin", "queryWindowInfo"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return windows

            # Simple parsing (actual format may vary)
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    windows.append({"info": line.strip()})

            return windows
        except Exception:
            return windows

    @classmethod
    def install_tiling_script(cls) -> Result:
        """
        Install a KWin tiling script for advanced layouts.
        """
        scripts_dir = Path.home() / ".local/share/kwin/scripts/LoofiTiling"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # Create main.js
        main_js = scripts_dir / "main.js"
        main_js.write_text("""/*
 * Loofi Tiling Script for KWin
 * Generated by Loofi Fedora Tweaks
 *
 * Provides basic tiling functionality.
 */

// Grid tiling helper
function tileToGrid(client, col, row, cols, rows) {
    var area = workspace.clientArea(0, client.screen, workspace.currentDesktop);
    var cellWidth = area.width / cols;
    var cellHeight = area.height / rows;

    client.geometry = {
        x: area.x + (cellWidth * col),
        y: area.y + (cellHeight * row),
        width: cellWidth,
        height: cellHeight
    };
}

// Register shortcuts
registerShortcut("Loofi: Tile Left Third", "Tile to left third", "Meta+1", function() {
    var client = workspace.activeClient;
    if (client) {
        tileToGrid(client, 0, 0, 3, 1);
    }
});

registerShortcut("Loofi: Tile Center Third", "Tile to center third", "Meta+2", function() {
    var client = workspace.activeClient;
    if (client) {
        tileToGrid(client, 1, 0, 3, 1);
    }
});

registerShortcut("Loofi: Tile Right Third", "Tile to right third", "Meta+3", function() {
    var client = workspace.activeClient;
    if (client) {
        tileToGrid(client, 2, 0, 3, 1);
    }
});

console.log("Loofi Tiling Script loaded");
""")

        # Create metadata.json
        metadata = scripts_dir / "metadata.json"
        metadata.write_text(json.dumps({
            "KPlugin": {
                "Name": "Loofi Tiling",
                "Description": "Basic tiling script from Loofi Fedora Tweaks",
                "Icon": "preferences-system-windows-effect-fadedesktop",
                "Authors": [{"Name": "Loofi Fedora Tweaks"}],
                "Id": "loofi-tiling",
                "Version": "1.0",
                "License": "GPL-3.0"
            },
            "X-Plasma-API": "javascript",
            "X-Plasma-MainScript": "main.js"
        }, indent=2))

        return Result(
            True,
            f"Tiling script installed to {scripts_dir}. Enable in System Settings → Window Management → KWin Scripts.",
            {"path": str(scripts_dir)}
        )
