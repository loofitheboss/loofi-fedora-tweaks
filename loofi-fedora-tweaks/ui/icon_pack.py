"""Icon pack helpers for resolving bundled Loofi icon assets."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from PyQt6.QtGui import QIcon

_ICON_SIZES = {16, 20, 24, 32}
_ICON_NAMES = (
    "appearance-theme",
    "cleanup",
    "cpu-performance",
    "developer-tools",
    "hardware-performance",
    "home",
    "info",
    "install",
    "logs",
    "maintenance-health",
    "memory-ram",
    "network-connectivity",
    "network-traffic",
    "notifications",
    "overview-dashboard",
    "packages-software",
    "restart",
    "search",
    "security-shield",
    "settings",
    "status-ok",
    "storage-disk",
    "terminal-console",
    "update",
)

_ICON_ALIASES: dict[str, str] = {
    "appearance": "appearance-theme",
    "cleanup": "cleanup",
    "cpu": "cpu-performance",
    "developer": "developer-tools",
    "hardware": "hardware-performance",
    "home": "home",
    "info": "info",
    "install": "install",
    "logs": "logs",
    "maintenance": "maintenance-health",
    "memory": "memory-ram",
    "network": "network-connectivity",
    "notifications": "notifications",
    "overview": "overview-dashboard",
    "packages": "packages-software",
    "restart": "restart",
    "search": "search",
    "security": "security-shield",
    "settings": "settings",
    "status": "status-ok",
    "storage": "storage-disk",
    "terminal": "terminal-console",
    "update": "update",
    "⚙": "settings",
    "⚙️": "settings",
    "⚡": "hardware-performance",
    "⏰": "settings",
    "ℹ": "info",
    "ℹ️": "info",
    "🌍": "network-connectivity",
    "🌐": "network-connectivity",
    "🎨": "appearance-theme",
    "🎮": "developer-tools",
    "🏠": "home",
    "👤": "settings",
    "💾": "storage-disk",
    "📈": "maintenance-health",
    "📊": "overview-dashboard",
    "📋": "logs",
    "📜": "logs",
    "📡": "network-traffic",
    "📦": "packages-software",
    "📌": "status-ok",
    "📸": "logs",
    "🔄": "update",
    "🔁": "restart",
    "🔋": "hardware-performance",
    "🔍": "search",
    "🔔": "notifications",
    "🔗": "network-connectivity",
    "🔧": "maintenance-health",
    "🔭": "maintenance-health",
    "🔥": "security-shield",
    "🛠": "developer-tools",
    "🛠️": "developer-tools",
    "🛡": "security-shield",
    "🛡️": "security-shield",
    "🧠": "cpu-performance",
    "🧹": "cleanup",
    "🧩": "developer-tools",
    "🤖": "developer-tools",
    "🚀": "cpu-performance",
}


_ICON_GROUPS: dict[str, str] = {
    "overview-dashboard": "system",
    "home": "system",
    "info": "system",
    "terminal-console": "tools",
    "logs": "tools",
    "search": "network",
    "notifications": "network",
    "network-connectivity": "network",
    "network-traffic": "network",
    "packages-software": "packages",
    "install": "packages",
    "update": "packages",
    "hardware-performance": "hardware",
    "cpu-performance": "hardware",
    "memory-ram": "hardware",
    "storage-disk": "hardware",
    "maintenance-health": "maintenance",
    "cleanup": "maintenance",
    "restart": "maintenance",
    "status-ok": "maintenance",
    "security-shield": "security",
    "appearance-theme": "appearance",
    "developer-tools": "tools",
    "settings": "tools",
}


_LIGHT_ICON_TINTS: dict[str, str] = {
    "overview-dashboard": "#4D6F9E",
    "home": "#4A78A8",
    "info": "#4B7E98",
    "terminal-console": "#636F7F",
    "logs": "#677487",
    "search": "#3D7E90",
    "notifications": "#3E8699",
    "network-connectivity": "#3E889D",
    "network-traffic": "#3A8094",
    "packages-software": "#A4782F",
    "install": "#A6813A",
    "update": "#A2752D",
    "hardware-performance": "#2F8A66",
    "cpu-performance": "#32856B",
    "memory-ram": "#3B826D",
    "storage-disk": "#3C8764",
    "maintenance-health": "#5B8E3B",
    "cleanup": "#5A8A35",
    "restart": "#648E3D",
    "status-ok": "#4F8C44",
    "security-shield": "#9A6664",
    "appearance-theme": "#3F8178",
    "developer-tools": "#5F7289",
    "settings": "#5E7687",
}


_DARK_ICON_TINTS: dict[str, str] = {
    "overview-dashboard": "#9CB8E8",
    "home": "#A4C1ED",
    "info": "#9FD0E4",
    "terminal-console": "#C1CDDD",
    "logs": "#C5D1E2",
    "search": "#9CD9E6",
    "notifications": "#A0E0ED",
    "network-connectivity": "#9DDDEA",
    "network-traffic": "#95D4E3",
    "packages-software": "#E5C188",
    "install": "#E7C993",
    "update": "#E1BA7B",
    "hardware-performance": "#8EE0BD",
    "cpu-performance": "#86D8BE",
    "memory-ram": "#9AE1CA",
    "storage-disk": "#93D8B4",
    "maintenance-health": "#B3D87C",
    "cleanup": "#A9D06E",
    "restart": "#B8DA85",
    "status-ok": "#9ED37E",
    "security-shield": "#E1ACAA",
    "appearance-theme": "#87D4C6",
    "developer-tools": "#BECBE0",
    "settings": "#BDD4E1",
}


_LIGHT_PALETTE: dict[str, str] = {
    "appearance": "#357A73",
    "hardware": "#2A8B66",
    "maintenance": "#4A8C2F",
    "network": "#2D7893",
    "packages": "#A27114",
    "security": "#9B5E5E",
    "system": "#466A9E",
    "tools": "#5E6D84",
}


_DARK_PALETTE: dict[str, str] = {
    "appearance": "#61CFC1",
    "hardware": "#74D5A6",
    "maintenance": "#9BCF5F",
    "network": "#79D2E3",
    "packages": "#E0B267",
    "security": "#E19A9A",
    "system": "#8FB0E4",
    "tools": "#B0BED5",
}


def icon_tint(icon_value: str) -> str:
    """Return the base theme-aware tint for an icon token."""
    icon_name = resolve_icon_name(icon_value)
    if not icon_name:
        return _DARK_PALETTE["tools"] if _is_dark_theme() else _LIGHT_PALETTE["tools"]
    return _default_tint(icon_name)


def icon_tint_variant(icon_value: str, selected: bool = False) -> str:
    """Return a selected/unselected tint variant to improve hierarchy."""
    base_hex = icon_tint(icon_value)
    try:
        from PyQt6.QtGui import QColor

        color = QColor(base_hex)
        if selected:
            color = color.lighter(120 if _is_dark_theme() else 108)
            color.setAlpha(255)
        else:
            color = color.darker(100 if _is_dark_theme() else 104)
            color.setAlpha(212 if _is_dark_theme() else 194)
        return color.name(QColor.NameFormat.HexArgb)
    except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return base_hex


def _icon_roots() -> list[Path]:
    """Return candidate locations for the icon-pack root."""
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent.parent
    package_root = module_dir.parent
    return [
        project_root / "assets" / "icons",
        package_root / "assets" / "icons",
    ]


@lru_cache(maxsize=1)
def icon_root() -> Path | None:
    """Return the first existing icon-pack root directory."""
    for root in _icon_roots():
        if (root / "svg").is_dir():
            return root
    return None


@lru_cache(maxsize=1)
def icon_map() -> dict[str, str]:
    """Load semantic icon mapping from icon-map.json (with fallback)."""
    for root in _icon_roots():
        map_path = root / "icon-map.json"
        if not map_path.is_file():
            continue
        try:
            with open(map_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                return {
                    str(key): str(value)
                    for key, value in loaded.items()
                    if isinstance(key, str) and isinstance(value, str)
                }
        except (OSError, json.JSONDecodeError, ValueError):
            continue

    return {name: f"assets/icons/svg/{name}.svg" for name in _ICON_NAMES}


def resolve_icon_name(icon_value: str) -> str:
    """Resolve an input icon token (semantic id or legacy emoji) to a semantic id."""
    if not icon_value:
        return ""

    value = icon_value.strip()
    if not value:
        return ""

    mapped = icon_map()
    if value in mapped:
        return value
    if value.lower() in mapped:
        return value.lower()
    if value in _ICON_ALIASES:
        return _ICON_ALIASES[value]
    lowered = value.lower()
    if lowered in _ICON_ALIASES:
        return _ICON_ALIASES[lowered]
    return ""


def resolve_icon_path(icon_value: str, size: int = 24) -> str | None:
    """Return an existing icon file path for the given icon token."""
    name = resolve_icon_name(icon_value)
    if not name:
        return None

    root = icon_root()
    if root is None:
        return None

    svg_path = root / "svg" / f"{name}.svg"
    if svg_path.is_file():
        return str(svg_path)

    if size in _ICON_SIZES:
        png_path = root / "png" / str(size) / f"{name}.png"
        if png_path.is_file():
            return str(png_path)

    return None


def _is_dark_theme() -> bool:
    """Best-effort theme detection based on application palette lightness."""
    try:
        from PyQt6.QtGui import QPalette
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return True
        base_color = app.palette().color(QPalette.ColorRole.Base)
        return base_color.lightness() < 128
    except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return True


def _default_tint(icon_name: str) -> str:
    """Return a subtle group tint color for icon integration."""
    dark_theme = _is_dark_theme()
    if dark_theme:
        if icon_name in _DARK_ICON_TINTS:
            return _DARK_ICON_TINTS[icon_name]
    else:
        if icon_name in _LIGHT_ICON_TINTS:
            return _LIGHT_ICON_TINTS[icon_name]

    group = _ICON_GROUPS.get(icon_name, "tools")
    palette = _DARK_PALETTE if dark_theme else _LIGHT_PALETTE
    return palette.get(group, palette["tools"])


def _tinted_icon(path: str, size: int, tint: str) -> QIcon | None:
    """Build a tinted icon pixmap from source path."""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor, QPainter, QPixmap

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(tint))
        painter.end()
        return QIcon(pixmap)
    except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return None


def get_qicon(icon_value: str, size: int = 24, tint: str | None = None) -> QIcon:
    """Return a QIcon for semantic ids or legacy emoji icon tokens."""
    path = resolve_icon_path(icon_value, size=size)
    if not path:
        return QIcon()

    icon_name = resolve_icon_name(icon_value)
    icon = _tinted_icon(path, size, tint or _default_tint(icon_name))
    if icon is not None:
        return icon
    return QIcon(path)
