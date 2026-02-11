"""
Automation Profiles - Event-triggered actions for system automation.
Manages profiles that react to power, network, and monitor events.
"""

import json
import logging
import shlex
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Available automation triggers."""
    ON_BATTERY = "on_battery"
    ON_AC = "on_ac"
    ON_PUBLIC_WIFI = "on_public_wifi"
    ON_HOME_WIFI = "on_home_wifi"
    ON_ULTRAWIDE = "on_ultrawide"
    ON_LAPTOP_ONLY = "on_laptop_only"
    ON_STARTUP = "on_startup"


class ActionType(Enum):
    """Available automation actions."""
    SET_POWER_PROFILE = "set_power_profile"
    SET_CPU_GOVERNOR = "set_cpu_governor"
    ENABLE_VPN = "enable_vpn"
    DISABLE_VPN = "disable_vpn"
    ENABLE_TILING = "enable_tiling"
    DISABLE_TILING = "disable_tiling"
    SET_THEME = "set_theme"
    RUN_COMMAND = "run_command"
    ENABLE_FOCUS_MODE = "enable_focus_mode"
    DISABLE_FOCUS_MODE = "disable_focus_mode"


@dataclass
class AutomationRule:
    """A single automation rule."""
    id: str
    name: str
    trigger: str  # TriggerType value
    action: str   # ActionType value
    action_params: Dict[str, Any]
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationRule":
        return cls(**data)


class AutomationProfiles:
    """
    Manages event-triggered automation rules.
    All methods return dicts for v10.0 API compatibility.
    """

    CONFIG_DIR = Path.home() / ".config" / "loofi-fedora-tweaks"
    CONFIG_FILE = CONFIG_DIR / "automation.json"

    @classmethod
    def ensure_config(cls):
        """Ensure config directory and default rules exist."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not cls.CONFIG_FILE.exists():
            default_config = {
                "enabled": True,
                "home_wifi_ssids": [],
                "rules": []
            }
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=2)

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """Load automation configuration."""
        cls.ensure_config()
        try:
            with open(cls.CONFIG_FILE, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to load automation config: %s", e)
            return {"enabled": True, "rules": []}

    @classmethod
    def save_config(cls, config: Dict[str, Any]):
        """Save automation configuration."""
        cls.ensure_config()
        with open(cls.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if automation system is enabled."""
        return cls.load_config().get("enabled", True)

    @classmethod
    def set_enabled(cls, enabled: bool):
        """Enable or disable automation system."""
        config = cls.load_config()
        config["enabled"] = enabled
        cls.save_config(config)

    # -------------------------------------------------------------------------
    # Rule Management
    # -------------------------------------------------------------------------

    @classmethod
    def list_rules(cls) -> List[Dict[str, Any]]:
        """
        Get all automation rules.

        Returns:
            List of rule dicts
        """
        config = cls.load_config()
        return config.get("rules", [])

    @classmethod
    def get_rule(cls, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific rule by ID.

        Returns:
            Rule dict or None
        """
        for rule in cls.list_rules():
            if rule.get("id") == rule_id:
                return rule
        return None

    @classmethod
    def add_rule(cls, rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new automation rule.

        Returns:
            Dict with 'success' and 'message'
        """
        try:
            validation = cls.validate_rule(rule)
            if not validation["success"]:
                return validation
            config = cls.load_config()
            if "rules" not in config:
                config["rules"] = []

            # Generate ID if not provided
            if "id" not in rule:
                import uuid
                rule["id"] = str(uuid.uuid4())[:8]

            config["rules"].append(rule)
            cls.save_config(config)

            return {"success": True, "message": f"Rule '{rule.get('name', 'unnamed')}' added", "id": rule["id"]}
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to add automation rule: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def update_rule(cls, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing rule.

        Returns:
            Dict with 'success' and 'message'
        """
        try:
            config = cls.load_config()
            for i, rule in enumerate(config.get("rules", [])):
                if rule.get("id") == rule_id:
                    merged = dict(rule)
                    merged.update(updates)
                    validation = cls.validate_rule(merged)
                    if not validation["success"]:
                        return validation
                    config["rules"][i].update(updates)
                    cls.save_config(config)
                    return {"success": True, "message": "Rule updated"}
            return {"success": False, "message": "Rule not found"}
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to update automation rule: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def delete_rule(cls, rule_id: str) -> Dict[str, Any]:
        """
        Delete an automation rule.

        Returns:
            Dict with 'success' and 'message'
        """
        try:
            config = cls.load_config()
            original_count = len(config.get("rules", []))
            config["rules"] = [r for r in config.get("rules", []) if r.get("id") != rule_id]

            if len(config["rules"]) < original_count:
                cls.save_config(config)
                return {"success": True, "message": "Rule deleted"}
            return {"success": False, "message": "Rule not found"}
        except (OSError, json.JSONDecodeError) as e:
            logger.debug("Failed to delete automation rule: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def enable_rule(cls, rule_id: str, enabled: bool) -> Dict[str, Any]:
        """Enable or disable a specific rule."""
        return cls.update_rule(rule_id, {"enabled": enabled})

    # -------------------------------------------------------------------------
    # Rule Matching
    # -------------------------------------------------------------------------

    @classmethod
    def get_rules_for_trigger(cls, trigger: str) -> List[Dict[str, Any]]:
        """
        Get all enabled rules matching a trigger.

        Returns:
            List of matching rule dicts
        """
        return [
            rule for rule in cls.list_rules()
            if rule.get("trigger") == trigger and rule.get("enabled", True)
        ]

    @classmethod
    def set_home_wifi_ssids(cls, ssids: List[str]):
        """Set list of home Wi-Fi network SSIDs."""
        config = cls.load_config()
        config["home_wifi_ssids"] = ssids
        cls.save_config(config)

    @classmethod
    def get_home_wifi_ssids(cls) -> List[str]:
        """Get list of home Wi-Fi network SSIDs."""
        return cls.load_config().get("home_wifi_ssids", [])

    # -------------------------------------------------------------------------
    # Validation & Simulation
    # -------------------------------------------------------------------------

    @classmethod
    def validate_rule(cls, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a rule definition without executing it."""
        errors = []
        warnings = []

        trigger = rule.get("trigger")
        action = rule.get("action")
        params = rule.get("action_params", {})

        if trigger not in [t.value for t in TriggerType]:
            errors.append(f"Invalid trigger: {trigger}")

        if action not in [a.value for a in ActionType]:
            errors.append(f"Invalid action: {action}")

        if action == ActionType.SET_POWER_PROFILE.value:
            if params.get("profile") not in ("power-saver", "balanced", "performance"):
                warnings.append("Power profile should be one of: power-saver, balanced, performance")
        if action == ActionType.SET_CPU_GOVERNOR.value and not params.get("governor"):
            errors.append("Missing action_params.governor")
        if action in (ActionType.ENABLE_VPN.value, ActionType.DISABLE_VPN.value):
            if params.get("vpn_name") is None:
                warnings.append("vpn_name not set; first available VPN will be used")
        if action in (ActionType.ENABLE_TILING.value, ActionType.DISABLE_TILING.value):
            if not params.get("script"):
                warnings.append("script not set; default 'polonium' will be used")
        if action == ActionType.SET_THEME.value:
            if params.get("theme") not in ("light", "dark"):
                warnings.append("Theme should be 'light' or 'dark'")
        if action == ActionType.RUN_COMMAND.value and not params.get("command"):
            errors.append("Missing action_params.command")

        if errors:
            return {"success": False, "message": "Validation failed", "errors": errors, "warnings": warnings}
        return {"success": True, "message": "Validation OK", "errors": [], "warnings": warnings}

    @classmethod
    def dry_run_action(cls, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Describe what an action would do without executing it."""
        if action == ActionType.SET_POWER_PROFILE.value:
            profile = params.get("profile", "balanced")
            return {"success": True, "message": f"Would set power profile to '{profile}'"}
        if action == ActionType.SET_CPU_GOVERNOR.value:
            governor = params.get("governor", "schedutil")
            return {"success": True, "message": f"Would set CPU governor to '{governor}'"}
        if action == ActionType.ENABLE_VPN.value:
            name = params.get("vpn_name", "<auto>")
            return {"success": True, "message": f"Would enable VPN '{name}'"}
        if action == ActionType.DISABLE_VPN.value:
            return {"success": True, "message": "Would disable active VPN connections"}
        if action == ActionType.ENABLE_TILING.value:
            script = params.get("script", "polonium")
            return {"success": True, "message": f"Would enable tiling script '{script}'"}
        if action == ActionType.DISABLE_TILING.value:
            script = params.get("script", "polonium")
            return {"success": True, "message": f"Would disable tiling script '{script}'"}
        if action == ActionType.SET_THEME.value:
            theme = params.get("theme", "dark")
            return {"success": True, "message": f"Would set theme to '{theme}'"}
        if action == ActionType.RUN_COMMAND.value:
            cmd = params.get("command", "")
            return {"success": True, "message": f"Would run command: {cmd}"}
        if action == ActionType.ENABLE_FOCUS_MODE.value:
            profile = params.get("profile", "default")
            return {"success": True, "message": f"Would enable Focus Mode (profile: {profile})"}
        if action == ActionType.DISABLE_FOCUS_MODE.value:
            return {"success": True, "message": "Would disable Focus Mode"}
        return {"success": False, "message": f"Unknown action: {action}"}

    @classmethod
    def simulate_rules_for_trigger(cls, trigger: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Dry-run all rules for a trigger."""
        rules = cls.get_rules_for_trigger(trigger)
        results = []
        for rule in rules:
            results.append({
                "rule_id": rule.get("id"),
                "rule_name": rule.get("name"),
                "result": cls.dry_run_action(rule.get("action"), rule.get("action_params", {}))
            })
        return {
            "success": True,
            "message": f"Simulated {len(results)} rules for trigger '{trigger}'",
            "results": results
        }

    # -------------------------------------------------------------------------
    # Action Execution
    # -------------------------------------------------------------------------

    @classmethod
    def execute_rules_for_trigger(cls, trigger: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute all matching rules for a trigger.

        Args:
            trigger: TriggerType value
            context: Optional context dict (e.g., SSID, monitor info)

        Returns:
            Dict with results for each rule
        """
        if not cls.is_enabled():
            return {"success": True, "message": "Automation disabled", "results": []}

        rules = cls.get_rules_for_trigger(trigger)
        results = []

        for rule in rules:
            result = cls.execute_action(rule.get("action"), rule.get("action_params", {}))
            results.append({
                "rule_id": rule.get("id"),
                "rule_name": rule.get("name"),
                "result": result
            })

        return {
            "success": True,
            "message": f"Executed {len(results)} rules for trigger '{trigger}'",
            "results": results
        }

    @classmethod
    def execute_action(cls, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single automation action.

        Args:
            action: ActionType value
            params: Action-specific parameters

        Returns:
            Dict with 'success' and 'message'
        """
        action_handlers = {
            ActionType.SET_POWER_PROFILE.value: cls._action_set_power_profile,
            ActionType.SET_CPU_GOVERNOR.value: cls._action_set_cpu_governor,
            ActionType.ENABLE_VPN.value: cls._action_enable_vpn,
            ActionType.DISABLE_VPN.value: cls._action_disable_vpn,
            ActionType.ENABLE_TILING.value: cls._action_enable_tiling,
            ActionType.DISABLE_TILING.value: cls._action_disable_tiling,
            ActionType.SET_THEME.value: cls._action_set_theme,
            ActionType.RUN_COMMAND.value: cls._action_run_command,
            ActionType.ENABLE_FOCUS_MODE.value: cls._action_enable_focus_mode,
            ActionType.DISABLE_FOCUS_MODE.value: cls._action_disable_focus_mode,
        }

        handler = action_handlers.get(action)
        if handler:
            try:
                return handler(params)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError, ImportError) as e:
                logger.debug("Action execution failed: %s", e)
                return {"success": False, "message": str(e)}

        return {"success": False, "message": f"Unknown action: {action}"}

    # -------------------------------------------------------------------------
    # Action Implementations
    # -------------------------------------------------------------------------

    @classmethod
    def _action_set_power_profile(cls, params: Dict) -> Dict[str, Any]:
        """Set power profile (power-saver, balanced, performance)."""
        profile = params.get("profile", "balanced")
        try:
            result = subprocess.run(
                ["powerprofilesctl", "set", profile],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Power profile set to '{profile}'"}
            return {"success": False, "message": result.stderr or "Command failed"}
        except FileNotFoundError:
            return {"success": False, "message": "power-profiles-daemon not installed"}
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to set power profile: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def _action_set_cpu_governor(cls, params: Dict) -> Dict[str, Any]:
        """Set CPU governor for all cores."""
        governor = params.get("governor", "schedutil")
        try:
            from utils.hardware import HardwareManager
            return HardwareManager.set_governor(governor)
        except ImportError:
            # Fallback implementation
            try:
                result = subprocess.run(
                    ["pkexec", "bash", "-c",
                     f"for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo '{governor}' > $cpu; done"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    return {"success": True, "message": f"CPU governor set to '{governor}'"}
                return {"success": False, "message": "Failed to set governor"}
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to set CPU governor: %s", e)
                return {"success": False, "message": str(e)}

    @classmethod
    def _action_enable_vpn(cls, params: Dict) -> Dict[str, Any]:
        """Enable VPN connection."""
        vpn_name = params.get("vpn_name")
        try:
            if vpn_name:
                cmd = ["nmcli", "connection", "up", vpn_name]
            else:
                # Try to find and connect to first VPN
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "NAME,TYPE", "connection"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.splitlines():
                    name, conn_type = line.split(":", 1)
                    if "vpn" in conn_type.lower():
                        vpn_name = name
                        break

                if not vpn_name:
                    return {"success": False, "message": "No VPN connection found"}
                cmd = ["nmcli", "connection", "up", vpn_name]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"success": True, "message": f"VPN '{vpn_name}' connected"}
            return {"success": False, "message": result.stderr or "VPN connection failed"}
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError, ValueError) as e:
            logger.debug("Failed to enable VPN: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def _action_disable_vpn(cls, params: Dict) -> Dict[str, Any]:
        """Disable active VPN connections."""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,STATE", "connection", "show", "--active"],
                capture_output=True, text=True, timeout=10
            )
            disconnected = []
            for line in result.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 2 and "vpn" in parts[1].lower():
                    name = parts[0]
                    subprocess.run(
                        ["nmcli", "connection", "down", name],
                        capture_output=True, timeout=10
                    )
                    disconnected.append(name)

            if disconnected:
                return {"success": True, "message": f"Disconnected VPNs: {', '.join(disconnected)}"}
            return {"success": True, "message": "No active VPN connections"}
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to disable VPN: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def _action_enable_tiling(cls, params: Dict) -> Dict[str, Any]:
        """Enable tiling window manager scripts."""
        script_name = params.get("script", "polonium")
        try:
            from utils.kwin_tiling import KWinTiling
            return KWinTiling.enable_script(script_name)
        except ImportError:
            # Fallback: try kwriteconfig5
            try:
                subprocess.run([
                    "kwriteconfig5", "--file", "kwinrc",
                    "--group", "Plugins",
                    "--key", f"{script_name}Enabled", "true"
                ], capture_output=True, text=True, timeout=10)

                subprocess.run(["qdbus", "org.kde.KWin", "/KWin", "reconfigure"],
                               capture_output=True, timeout=10)

                return {"success": True, "message": f"Tiling script '{script_name}' enabled"}
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to enable tiling: %s", e)
                return {"success": False, "message": str(e)}

    @classmethod
    def _action_disable_tiling(cls, params: Dict) -> Dict[str, Any]:
        """Disable tiling window manager scripts."""
        script_name = params.get("script", "polonium")
        try:
            from utils.kwin_tiling import KWinTiling
            return KWinTiling.disable_script(script_name)
        except ImportError:
            try:
                subprocess.run([
                    "kwriteconfig5", "--file", "kwinrc",
                    "--group", "Plugins",
                    "--key", f"{script_name}Enabled", "false"
                ], capture_output=True, text=True, timeout=10)

                subprocess.run(["qdbus", "org.kde.KWin", "/KWin", "reconfigure"],
                               capture_output=True, timeout=10)

                return {"success": True, "message": f"Tiling script '{script_name}' disabled"}
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug("Failed to disable tiling: %s", e)
                return {"success": False, "message": str(e)}

    @classmethod
    def _action_set_theme(cls, params: Dict) -> Dict[str, Any]:
        """Set desktop theme (light/dark)."""
        theme = params.get("theme", "dark")
        try:
            # Try KDE Plasma
            if theme == "dark":
                result = subprocess.run([
                    "plasma-apply-colorscheme", "BreezeDark"
                ], capture_output=True, text=True, timeout=10)
            else:
                result = subprocess.run([
                    "plasma-apply-colorscheme", "BreezeLight"
                ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return {"success": True, "message": f"Theme set to '{theme}'"}

            # Try GNOME
            gsettings_value = "prefer-dark" if theme == "dark" else "default"
            result = subprocess.run([
                "gsettings", "set", "org.gnome.desktop.interface",
                "color-scheme", gsettings_value
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return {"success": True, "message": f"Theme set to '{theme}'"}

            return {"success": False, "message": "Could not set theme"}
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            logger.debug("Failed to set theme: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def _action_run_command(cls, params: Dict) -> Dict[str, Any]:
        """Run a custom shell command."""
        command = params.get("command")
        if not command:
            return {"success": False, "message": "No command specified"}

        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True, text=True, timeout=60
            )
            return {
                "success": result.returncode == 0,
                "message": result.stdout or result.stderr or "Command executed",
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Command timed out"}
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            logger.debug("Failed to run command: %s", e)
            return {"success": False, "message": str(e)}

    @classmethod
    def _action_enable_focus_mode(cls, params: Dict) -> Dict[str, Any]:
        """Enable focus mode."""
        profile = params.get("profile", "default")
        try:
            from utils.focus_mode import FocusMode
            return FocusMode.enable(profile)
        except ImportError:
            return {"success": False, "message": "Focus mode module not available"}

    @classmethod
    def _action_disable_focus_mode(cls, params: Dict) -> Dict[str, Any]:
        """Disable focus mode."""
        try:
            from utils.focus_mode import FocusMode
            return FocusMode.disable()
        except ImportError:
            return {"success": False, "message": "Focus mode module not available"}

    # -------------------------------------------------------------------------
    # Quick Presets
    # -------------------------------------------------------------------------

    @classmethod
    def create_battery_saver_preset(cls) -> Dict[str, Any]:
        """Create common battery saver rules."""
        rules = [
            {
                "name": "Battery Power Saver",
                "trigger": TriggerType.ON_BATTERY.value,
                "action": ActionType.SET_POWER_PROFILE.value,
                "action_params": {"profile": "power-saver"},
                "enabled": True
            },
            {
                "name": "AC Performance Mode",
                "trigger": TriggerType.ON_AC.value,
                "action": ActionType.SET_POWER_PROFILE.value,
                "action_params": {"profile": "balanced"},
                "enabled": True
            }
        ]

        for rule in rules:
            cls.add_rule(rule)

        return {"success": True, "message": f"Created {len(rules)} battery saver rules"}

    @classmethod
    def create_tiling_preset(cls) -> Dict[str, Any]:
        """Create auto-tiling rules based on monitor setup."""
        rules = [
            {
                "name": "Ultrawide Tiling",
                "trigger": TriggerType.ON_ULTRAWIDE.value,
                "action": ActionType.ENABLE_TILING.value,
                "action_params": {"script": "polonium"},
                "enabled": True
            },
            {
                "name": "Laptop No Tiling",
                "trigger": TriggerType.ON_LAPTOP_ONLY.value,
                "action": ActionType.DISABLE_TILING.value,
                "action_params": {"script": "polonium"},
                "enabled": True
            }
        ]

        for rule in rules:
            cls.add_rule(rule)

        return {"success": True, "message": f"Created {len(rules)} tiling rules"}
