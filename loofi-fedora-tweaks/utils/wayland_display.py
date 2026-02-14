"""
Wayland Display Configuration Manager.
Part of v37.0.0 "Pinnacle" — T5.

GNOME uses gsettings for scaling and mutter experimental features.
KDE uses kscreen-doctor for output configuration.
Gated by $XDG_SESSION_TYPE == "wayland".
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

CommandTuple = Tuple[str, List[str], str]


@dataclass
class DisplayInfo:
    """Describes a connected display."""
    name: str
    resolution: str = ""
    scale: float = 1.0
    position: Tuple[int, int] = (0, 0)
    refresh_rate: float = 60.0
    primary: bool = False
    enabled: bool = True
    make: str = ""
    model: str = ""


class WaylandDisplayManager:
    """Wayland-aware display configuration for GNOME and KDE.

    All methods are ``@staticmethod``.
    Wayland-only features gated by ``$XDG_SESSION_TYPE``.
    GNOME: gsettings + mutter experimental features.
    KDE: kscreen-doctor output queries and changes.
    """

    # -----------------------------------------------------------------
    # Session checks
    # -----------------------------------------------------------------

    @staticmethod
    def is_wayland() -> bool:
        """Return True if the current session is Wayland."""
        return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

    @staticmethod
    def _detect_de() -> str:
        """Detect desktop environment. Returns 'gnome', 'kde', or 'unknown'."""
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        if "GNOME" in desktop:
            return "gnome"
        if "KDE" in desktop or "PLASMA" in desktop:
            return "kde"
        return "unknown"

    # -----------------------------------------------------------------
    # Display listing
    # -----------------------------------------------------------------

    @staticmethod
    def get_displays() -> List[DisplayInfo]:
        """List connected displays with resolution, scale, and position.

        GNOME: parse ``gnome-randr`` or ``xrandr`` or gsettings.
        KDE: parse ``kscreen-doctor --outputs``.
        X11 session: returns empty list with log warning.

        Returns:
            List of :class:`DisplayInfo`.
        """
        if not WaylandDisplayManager.is_wayland():
            logger.warning("Not a Wayland session — display config limited")
            # Still attempt basic detection via xrandr fallback
            return WaylandDisplayManager._get_displays_xrandr()

        de = WaylandDisplayManager._detect_de()
        if de == "gnome":
            return WaylandDisplayManager._get_displays_gnome()
        elif de == "kde":
            return WaylandDisplayManager._get_displays_kde()
        else:
            logger.info("Unknown DE for Wayland display listing")
            return []

    @staticmethod
    def _get_displays_gnome() -> List[DisplayInfo]:
        """Get display info on GNOME via gsettings and mutter."""
        displays: List[DisplayInfo] = []
        try:
            # Use gnome-monitor-config or DBus to query monitor state
            result = subprocess.run(
                ["gnome-monitor-config", "list"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                displays = WaylandDisplayManager._parse_gnome_monitors(result.stdout)
            else:
                # Fallback: try gsettings for basic scaling info
                scale_result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "text-scaling-factor"],
                    capture_output=True, text=True, timeout=5,
                )
                if scale_result.returncode == 0:
                    try:
                        scale = float(scale_result.stdout.strip())
                    except ValueError:
                        scale = 1.0
                    displays.append(DisplayInfo(
                        name="primary",
                        scale=scale,
                        primary=True,
                    ))
        except subprocess.TimeoutExpired:
            logger.warning("Timeout querying GNOME displays")
        except FileNotFoundError:
            logger.debug("gnome-monitor-config not found")
        return displays

    @staticmethod
    def _parse_gnome_monitors(output: str) -> List[DisplayInfo]:
        """Parse gnome-monitor-config list output."""
        displays: List[DisplayInfo] = []
        current: Optional[DisplayInfo] = None
        for line in output.splitlines():
            stripped = line.strip()
            # Monitor lines start with a connector name like "DP-1", "HDMI-1"
            if not stripped.startswith(" ") and stripped and ":" not in stripped:
                # Likely a section header — save previous
                if stripped.startswith("Monitor"):
                    continue
            if "connector:" in stripped.lower() or stripped.startswith("DP-") or stripped.startswith("HDMI-") or stripped.startswith("eDP-"):
                if current:
                    displays.append(current)
                name = stripped.replace(":", "").strip()
                current = DisplayInfo(name=name)
            elif current:
                if "resolution" in stripped.lower() or "mode" in stripped.lower():
                    # Try to extract resolution like "1920x1080"
                    parts = stripped.split()
                    for part in parts:
                        if "x" in part and part.replace("x", "").replace("@", "").replace(".", "").isdigit():
                            current.resolution = part.split("@")[0]
                            if "@" in part:
                                try:
                                    current.refresh_rate = float(part.split("@")[1])
                                except ValueError:
                                    pass
                elif "scale" in stripped.lower():
                    parts = stripped.split()
                    for part in parts:
                        try:
                            current.scale = float(part)
                            break
                        except ValueError:
                            continue
                elif "primary" in stripped.lower():
                    current.primary = True
                elif "position" in stripped.lower():
                    parts = stripped.split()
                    nums = [p for p in parts if p.isdigit()]
                    if len(nums) >= 2:
                        current.position = (int(nums[0]), int(nums[1]))
        if current:
            displays.append(current)
        return displays

    @staticmethod
    def _get_displays_kde() -> List[DisplayInfo]:
        """Get display info on KDE via kscreen-doctor."""
        displays: List[DisplayInfo] = []
        if not shutil.which("kscreen-doctor"):
            logger.debug("kscreen-doctor not found")
            return displays
        try:
            result = subprocess.run(
                ["kscreen-doctor", "--outputs"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                displays = WaylandDisplayManager._parse_kscreen_outputs(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout querying KDE displays")
        except FileNotFoundError:
            pass
        return displays

    @staticmethod
    def _parse_kscreen_outputs(output: str) -> List[DisplayInfo]:
        """Parse kscreen-doctor --outputs output."""
        displays: List[DisplayInfo] = []
        current: Optional[DisplayInfo] = None
        for line in output.splitlines():
            stripped = line.strip()
            # Output sections start with "Output: N"
            if stripped.startswith("Output:"):
                if current:
                    displays.append(current)
                parts = stripped.split()
                idx = parts[1] if len(parts) > 1 else "unknown"
                current = DisplayInfo(name=idx)
            elif current:
                lower = stripped.lower()
                if lower.startswith("name:"):
                    current.name = stripped.split(":", 1)[1].strip()
                elif lower.startswith("enabled:"):
                    current.enabled = "true" in lower
                elif lower.startswith("priority:") and "1" in stripped:
                    current.primary = True
                elif lower.startswith("scale:"):
                    try:
                        current.scale = float(stripped.split(":")[1].strip())
                    except ValueError:
                        pass
                elif "mode:" in lower or "resolution:" in lower:
                    for part in stripped.split():
                        if "x" in part and part.replace("x", "").isdigit():
                            current.resolution = part
                elif lower.startswith("pos:") or lower.startswith("position:"):
                    coords = stripped.split(":", 1)[1].strip()
                    parts = coords.replace(",", " ").split()
                    nums = [p for p in parts if p.lstrip("-").isdigit()]
                    if len(nums) >= 2:
                        current.position = (int(nums[0]), int(nums[1]))
        if current:
            displays.append(current)
        return displays

    @staticmethod
    def _get_displays_xrandr() -> List[DisplayInfo]:
        """Fallback: get basic display info via xrandr (X11)."""
        displays: List[DisplayInfo] = []
        if not shutil.which("xrandr"):
            return displays
        try:
            result = subprocess.run(
                ["xrandr", "--query"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if " connected" in line:
                        parts = line.split()
                        name = parts[0]
                        primary = "primary" in parts
                        # Resolution like 1920x1080+0+0
                        res = ""
                        for p in parts:
                            if "x" in p and "+" in p:
                                res = p.split("+")[0]
                                break
                        displays.append(DisplayInfo(
                            name=name,
                            resolution=res,
                            primary=primary,
                        ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return displays

    # -----------------------------------------------------------------
    # Scaling
    # -----------------------------------------------------------------

    @staticmethod
    def set_scaling(display: str, factor: float) -> CommandTuple:
        """Set display scaling factor.

        GNOME: gsettings for text-scaling-factor (integer scaling via mutter).
        KDE: kscreen-doctor output.<name>.scale <factor>.

        Args:
            display: Display name/identifier.
            factor: Scale factor (1.0, 1.25, 1.5, 2.0).

        Returns:
            Command tuple for execution.
        """
        de = WaylandDisplayManager._detect_de()
        if de == "gnome":
            return WaylandDisplayManager._set_scaling_gnome(display, factor)
        elif de == "kde":
            return WaylandDisplayManager._set_scaling_kde(display, factor)
        return ("echo", ["Unsupported desktop for scaling"], "Scaling not supported")

    @staticmethod
    def _set_scaling_gnome(display: str, factor: float) -> CommandTuple:
        """Set GNOME scaling via gsettings."""
        # Integer scaling via gsettings
        return (
            "gsettings",
            ["set", "org.gnome.desktop.interface", "text-scaling-factor", str(factor)],
            f"Setting GNOME text scaling to {factor}",
        )

    @staticmethod
    def _set_scaling_kde(display: str, factor: float) -> CommandTuple:
        """Set KDE scaling via kscreen-doctor."""
        return (
            "kscreen-doctor",
            [f"output.{display}.scale.{factor}"],
            f"Setting KDE display {display} scale to {factor}",
        )

    # -----------------------------------------------------------------
    # Fractional scaling
    # -----------------------------------------------------------------

    @staticmethod
    def enable_fractional_scaling() -> CommandTuple:
        """Enable fractional scaling on GNOME via mutter experimental features.

        KDE supports fractional scaling natively via kscreen-doctor.

        Returns:
            Command tuple for execution.
        """
        de = WaylandDisplayManager._detect_de()
        if de == "gnome":
            return (
                "gsettings",
                ["set", "org.gnome.mutter", "experimental-features",
                 "['scale-monitor-framebuffer']"],
                "Enabling GNOME fractional scaling",
            )
        elif de == "kde":
            return (
                "echo",
                ["KDE supports fractional scaling natively — no extra config needed"],
                "KDE fractional scaling is native",
            )
        return ("echo", ["Unsupported desktop"], "Fractional scaling not supported")

    @staticmethod
    def disable_fractional_scaling() -> CommandTuple:
        """Disable fractional scaling on GNOME."""
        de = WaylandDisplayManager._detect_de()
        if de == "gnome":
            return (
                "gsettings",
                ["set", "org.gnome.mutter", "experimental-features", "[]"],
                "Disabling GNOME fractional scaling",
            )
        return ("echo", ["No action needed"], "Fractional scaling not applicable")

    # -----------------------------------------------------------------
    # Position
    # -----------------------------------------------------------------

    @staticmethod
    def set_position(display: str, x: int, y: int) -> CommandTuple:
        """Set display position for multi-monitor layout.

        Args:
            display: Display name/identifier.
            x: Horizontal position.
            y: Vertical position.

        Returns:
            Command tuple for execution.
        """
        de = WaylandDisplayManager._detect_de()
        if de == "gnome":
            # gnome-monitor-config set for position
            return (
                "gnome-monitor-config",
                ["set", "-LpM", display, "-x", str(x), "-y", str(y)],
                f"Setting GNOME display {display} position to ({x}, {y})",
            )
        elif de == "kde":
            return (
                "kscreen-doctor",
                [f"output.{display}.position.{x},{y}"],
                f"Setting KDE display {display} position to ({x}, {y})",
            )
        return ("echo", ["Unsupported desktop for positioning"], "Position setting not supported")

    # -----------------------------------------------------------------
    # Session info
    # -----------------------------------------------------------------

    @staticmethod
    def get_session_info() -> dict:
        """Return session type and desktop environment info.

        Returns:
            Dict with session_type, desktop, wayland, compositor.
        """
        session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")
        wayland_display = os.environ.get("WAYLAND_DISPLAY", "")

        compositor = "unknown"
        if "GNOME" in desktop.upper():
            compositor = "mutter"
        elif "KDE" in desktop.upper() or "PLASMA" in desktop.upper():
            compositor = "kwin"

        return {
            "session_type": session_type,
            "desktop": desktop,
            "wayland": bool(wayland_display) or session_type == "wayland",
            "compositor": compositor,
            "wayland_display": wayland_display,
        }
