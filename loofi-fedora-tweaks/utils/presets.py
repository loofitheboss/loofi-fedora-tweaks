import logging
import os
import json
import subprocess
import shutil

logger = logging.getLogger(__name__)


class PresetManager:
    PRESETS_DIR = os.path.expanduser("~/.config/loofi-fedora-tweaks/presets")

    def __init__(self):
        os.makedirs(self.PRESETS_DIR, exist_ok=True)

    def list_presets(self):
        """Returns a list of preset names."""
        if not os.path.exists(self.PRESETS_DIR):
            return []
        files = [f for f in os.listdir(self.PRESETS_DIR) if f.endswith(".json")]
        return [os.path.splitext(f)[0] for f in files]

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize preset name to prevent path traversal."""
        # Strip directory separators and dangerous characters
        safe = os.path.basename(name)
        safe = safe.replace("..", "").replace("/", "").replace("\\", "")
        if not safe:
            safe = "unnamed_preset"
        return safe

    def save_preset(self, name):
        """Captures current system state and saves as JSON."""
        data = {
            "name": name,
            "theme": self._get_gsettings("org.gnome.desktop.interface", "gtk-theme"),
            "icon_theme": self._get_gsettings(
                "org.gnome.desktop.interface", "icon-theme"
            ),
            "cursor_theme": self._get_gsettings(
                "org.gnome.desktop.interface", "cursor-theme"
            ),
            "color_scheme": self._get_gsettings(
                "org.gnome.desktop.interface", "color-scheme"
            ),
            "battery_limit": self._get_battery_limit(),
            "power_profile": self._get_power_profile(),
        }

        safe_name = self._sanitize_name(name)
        path = os.path.join(self.PRESETS_DIR, f"{safe_name}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        return True

    def load_preset(self, name):
        """Loads a preset and applies settings."""
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.PRESETS_DIR, f"{safe_name}.json")
        if not os.path.exists(path):
            return False

        with open(path, "r") as f:
            data = json.load(f)

        # Apply GSettings
        self._set_gsettings(
            "org.gnome.desktop.interface", "gtk-theme", data.get("theme")
        )
        self._set_gsettings(
            "org.gnome.desktop.interface", "icon-theme", data.get("icon_theme")
        )
        self._set_gsettings(
            "org.gnome.desktop.interface", "cursor-theme", data.get("cursor_theme")
        )
        self._set_gsettings(
            "org.gnome.desktop.interface", "color-scheme", data.get("color_scheme")
        )

        # Apply Battery Limit (Requires PKEXEC if changed)
        # We can implement a signal or callback, or just run valid commands here if possible.
        # Since we are in a utility, we might need to return specific actions for the UI to handle,
        # OR we use our BatteryManager if we can trust it.
        # For now, let's return a dict of complex actions for the UI to perform if needed.
        return data

    def delete_preset(self, name):
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.PRESETS_DIR, f"{safe_name}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def save_preset_data(self, name, data):
        """Save preset from provided data (for community presets)."""
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.PRESETS_DIR, f"{safe_name}.json")
        try:
            with open(path, "w") as f:
                json.dump({"name": name, **data}, f, indent=4)
            return True
        except Exception as e:
            logger.debug("Failed to save preset data: %s", e)
            return False

    # --- Helpers ---
    def _get_gsettings(self, schema, key):
        if not shutil.which("gsettings"):
            return None
        try:
            return (
                subprocess.check_output(
                    ["gsettings", "get", schema, key], text=True, timeout=15
                )
                .strip()
                .strip("'")
            )
        except subprocess.CalledProcessError:
            return None

    def _set_gsettings(self, schema, key, value):
        if value and shutil.which("gsettings"):
            try:
                subprocess.run(
                    ["gsettings", "set", schema, key, value], check=False, timeout=15
                )
            except Exception as e:
                logger.debug("Failed to set gsettings %s %s: %s", schema, key, e)

    def _get_battery_limit(self):
        # Read from config file primarily
        try:
            with open("/etc/loofi-fedora-tweaks/battery.conf", "r") as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 100

    def _get_power_profile(self):
        if not shutil.which("powerprofilesctl"):
            return "balanced"
        try:
            return subprocess.check_output(
                ["powerprofilesctl", "get"], text=True, timeout=60
            ).strip()
        except subprocess.CalledProcessError:
            return "balanced"
