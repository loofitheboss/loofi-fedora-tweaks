"""
core.plugins — Plugin architecture for Loofi Fedora Tweaks.

Public API:
    PluginInterface  — ABC for all plugins
    PluginMetadata   — frozen dataclass for plugin metadata
    CompatStatus     — dataclass for compatibility check results
    PluginRegistry   — singleton registry
    PluginLoader     — built-in plugin loader
    CompatibilityDetector — system compatibility checker
"""

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata, CompatStatus
from core.plugins.registry import PluginRegistry
from core.plugins.loader import PluginLoader
from core.plugins.compat import CompatibilityDetector

__all__ = [
    "PluginInterface",
    "PluginMetadata",
    "CompatStatus",
    "PluginRegistry",
    "PluginLoader",
    "CompatibilityDetector",
]
