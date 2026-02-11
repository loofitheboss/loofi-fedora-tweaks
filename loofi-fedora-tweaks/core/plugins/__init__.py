"""
core.plugins — Plugin architecture for Loofi Fedora Tweaks.

Public API:
    PluginInterface  — ABC for all plugins
    PluginMetadata   — frozen dataclass for plugin metadata
    CompatStatus     — dataclass for compatibility check results
    PluginRegistry   — singleton registry
    PluginLoader     — built-in plugin loader
    CompatibilityDetector — system compatibility checker
    PluginAdapter    — adapter for legacy LoofiPlugin (v26.0+)
    PluginManifest   — plugin.json manifest data (v26.0+)
    PluginPackage    — .loofi-plugin archive format (v26.0+)
    PluginSandbox    — runtime permission enforcement (v26.0+)
    RestrictedImporter — custom import hook for sandbox (v26.0+)
    PluginScanner    — external plugin discovery (v26.0+)
    create_sandbox   — factory function for PluginSandbox (v26.0+)
    IntegrityVerifier — SHA256 + GPG verification (v26.0 Phase 1 T6)
    VerificationResult — integrity verification result (v26.0 Phase 1 T6)
    DependencyResolver — dependency resolution with version constraints (v26.0 Phase 1 T8)
    ResolverResult   — dependency resolution result (v26.0 Phase 1 T8)
"""

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata, CompatStatus
from core.plugins.registry import PluginRegistry
from core.plugins.loader import PluginLoader
from core.plugins.compat import CompatibilityDetector
from core.plugins.adapter import PluginAdapter
from core.plugins.package import PluginManifest, PluginPackage
from core.plugins.sandbox import PluginSandbox, RestrictedImporter, create_sandbox
from core.plugins.scanner import PluginScanner
from core.plugins.integrity import IntegrityVerifier, VerificationResult
from core.plugins.resolver import DependencyResolver, ResolverResult

__all__ = [
    "PluginInterface",
    "PluginMetadata",
    "CompatStatus",
    "PluginRegistry",
    "PluginLoader",
    "CompatibilityDetector",
    "PluginAdapter",
    "PluginManifest",
    "PluginPackage",
    "PluginSandbox",
    "RestrictedImporter",
    "PluginScanner",
    "create_sandbox",
    "IntegrityVerifier",
    "VerificationResult",
    "DependencyResolver",
    "ResolverResult",
]
