"""Tests for core.plugins.scanner — PluginScanner external plugin discovery."""
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.scanner import PluginScanner
from core.plugins.package import PluginManifest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_plugin_dir(base_dir: Path, plugin_id: str, manifest_data: dict = None):
    """Create a plugin directory with manifest.json."""
    plugin_dir = base_dir / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    if manifest_data is None:
        manifest_data = {
            "id": plugin_id,
            "name": plugin_id.replace("-", " ").title(),
            "version": "1.0.0",
            "description": f"Test plugin {plugin_id}",
            "author": "Test Author",
            "entrypoint": "plugin.py",
            "permissions": ["network"]
        }
    
    manifest_path = plugin_dir / "plugin.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f)
    
    # Create dummy plugin.py
    plugin_py = plugin_dir / "plugin.py"
    plugin_py.write_text("# Plugin code")
    
    return plugin_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginScannerInitialization:
    """Tests for PluginScanner construction."""

    def test_scanner_uses_default_plugins_dir(self):
        """Scanner uses ~/.config/loofi-fedora-tweaks/plugins/ by default."""
        scanner = PluginScanner()
        expected = Path.home() / ".config" / "loofi-fedora-tweaks" / "plugins"
        assert scanner.plugins_dir == expected

    def test_scanner_accepts_custom_plugins_dir(self):
        """Scanner accepts custom plugins directory."""
        custom_dir = Path("/tmp/custom-plugins")
        scanner = PluginScanner(plugins_dir=custom_dir)
        assert scanner.plugins_dir == custom_dir

    def test_scanner_creates_plugins_dir_if_missing(self):
        """Scanner creates plugins directory on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            assert not plugins_dir.exists()
            
            PluginScanner(plugins_dir=plugins_dir)
            assert plugins_dir.exists()

    def test_scanner_sets_state_file_path(self):
        """Scanner sets correct state file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "plugins"
            scanner = PluginScanner(plugins_dir=plugins_dir)
            expected_state = Path(tmpdir) / "plugins.json"
            assert scanner.state_file == expected_state


class TestPluginScannerScan:
    """Tests for PluginScanner.scan() discovery."""

    def test_scan_returns_empty_list_if_no_plugins(self):
        """scan() returns empty list when no plugins exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = PluginScanner(plugins_dir=Path(tmpdir))
            results = scanner.scan()
            assert results == []

    def test_scan_discovers_single_valid_plugin(self):
        """scan() discovers a single valid plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "test-plugin")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1
            plugin_dir, manifest = results[0]
            assert manifest.id == "test-plugin"
            assert manifest.name == "Test Plugin"

    def test_scan_discovers_multiple_plugins(self):
        """scan() discovers multiple valid plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "plugin-one")
            _create_plugin_dir(base_dir, "plugin-two")
            _create_plugin_dir(base_dir, "plugin-three")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 3
            plugin_ids = {manifest.id for _, manifest in results}
            assert plugin_ids == {"plugin-one", "plugin-two", "plugin-three"}

    def test_scan_skips_files_in_plugins_dir(self):
        """scan() ignores files, only scans directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "valid-plugin")
            
            # Create a file (not directory)
            (base_dir / "readme.txt").write_text("Not a plugin")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1
            assert results[0][1].id == "valid-plugin"

    def test_scan_skips_plugins_without_manifest(self):
        """scan() skips directories without plugin.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            # Valid plugin
            _create_plugin_dir(base_dir, "valid-plugin")
            
            # Invalid plugin (no manifest)
            invalid_dir = base_dir / "invalid-plugin"
            invalid_dir.mkdir()
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1
            assert results[0][1].id == "valid-plugin"

    def test_scan_returns_path_and_manifest_tuples(self):
        """scan() returns list of (Path, PluginManifest) tuples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "test-plugin")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1
            plugin_dir, manifest = results[0]
            assert isinstance(plugin_dir, Path)
            assert isinstance(manifest, PluginManifest)


class TestPluginScannerValidation:
    """Tests for plugin validation during scan."""

    def test_scan_validates_required_manifest_fields(self):
        """scan() validates manifest has required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            # Missing required fields
            invalid_manifest = {
                "id": "incomplete-plugin",
                "name": "Incomplete"
                # Missing version, description, author, entrypoint
            }
            plugin_dir = base_dir / "incomplete-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text(json.dumps(invalid_manifest))
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            # Should skip invalid plugin
            assert len(results) == 0

    def test_scan_accepts_complete_manifest(self):
        """scan() accepts manifest with all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            complete_manifest = {
                "id": "complete-plugin",
                "name": "Complete Plugin",
                "version": "1.0.0",
                "description": "A complete plugin",
                "author": "Test Author",
                "entrypoint": "plugin.py",
                "permissions": ["network"]
            }
            _create_plugin_dir(base_dir, "complete-plugin", complete_manifest)
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1
            assert results[0][1].id == "complete-plugin"

    def test_scan_handles_malformed_json(self):
        """scan() gracefully handles malformed JSON in manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            plugin_dir = base_dir / "bad-json-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text("{ invalid json }")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            # Should skip plugin with bad JSON
            assert len(results) == 0


class TestPluginScannerStateManagement:
    """Tests for plugin enabled/disabled state."""

    def test_scan_respects_disabled_plugins_in_state(self):
        """scan() skips plugins marked as disabled in state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            state_file = Path(tmpdir) / "plugins.json"
            
            _create_plugin_dir(base_dir, "enabled-plugin")
            _create_plugin_dir(base_dir, "disabled-plugin")
            
            # Create state file with one disabled
            state = {
                "enabled-plugin": {"enabled": True},
                "disabled-plugin": {"enabled": False}
            }
            state_file.write_text(json.dumps(state))
            
            scanner = PluginScanner(plugins_dir=base_dir)
            scanner.state_file = state_file
            results = scanner.scan()
            
            # Should only find enabled plugin
            assert len(results) == 1
            assert results[0][1].id == "enabled-plugin"

    def test_scan_assumes_enabled_if_not_in_state(self):
        """scan() treats plugins as enabled if not in state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "new-plugin")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            # New plugin should be discovered (enabled by default)
            assert len(results) == 1
            assert results[0][1].id == "new-plugin"

    def test_scan_handles_missing_state_file(self):
        """scan() works correctly when state file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "test-plugin")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1


class TestPluginScannerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_scan_handles_nonexistent_plugins_dir(self):
        """scan() handles gracefully when plugins directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "does-not-exist"
            scanner = PluginScanner(plugins_dir=nonexistent)
            
            # scan() should handle this without crashing
            results = scanner.scan()
            assert results == []

    def test_scan_handles_permission_errors(self):
        """scan() handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "test-plugin")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            
            # Mock permission error
            with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
                results = scanner.scan()
                # Should handle error and return empty or partial results
                assert isinstance(results, list)

    def test_scan_handles_unicode_plugin_names(self):
        """scan() handles plugin IDs with unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            manifest = {
                "id": "unicode-plugin",
                "name": "Unicode Plugin 🔌",
                "version": "1.0.0",
                "description": "Supports émojis",
                "author": "Test",
                "entrypoint": "plugin.py"
            }
            _create_plugin_dir(base_dir, "unicode-plugin", manifest)
            
            scanner = PluginScanner(plugins_dir=base_dir)
            results = scanner.scan()
            
            assert len(results) == 1
            assert "Unicode Plugin" in results[0][1].name


class TestPluginScannerIntegration:
    """Integration tests for full scan workflow."""

    def test_full_scan_workflow_with_mixed_plugins(self):
        """Test complete scan with valid, invalid, and disabled plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            state_file = Path(tmpdir) / "plugins.json"
            
            # Create plugins
            _create_plugin_dir(base_dir, "plugin-valid-1")
            _create_plugin_dir(base_dir, "plugin-valid-2")
            _create_plugin_dir(base_dir, "plugin-disabled")
            
            # Invalid plugin (no manifest)
            (base_dir / "plugin-invalid").mkdir()
            
            # State file
            state = {"plugin-disabled": {"enabled": False}}
            state_file.write_text(json.dumps(state))
            
            scanner = PluginScanner(plugins_dir=base_dir)
            scanner.state_file = state_file
            results = scanner.scan()
            
            # Should find 2 valid enabled plugins
            assert len(results) == 2
            plugin_ids = {manifest.id for _, manifest in results}
            assert plugin_ids == {"plugin-valid-1", "plugin-valid-2"}

    def test_scanner_reusability(self):
        """Scanner can be reused for multiple scans."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            _create_plugin_dir(base_dir, "plugin-1")
            
            scanner = PluginScanner(plugins_dir=base_dir)
            
            # First scan
            results1 = scanner.scan()
            assert len(results1) == 1
            
            # Add another plugin
            _create_plugin_dir(base_dir, "plugin-2")
            
            # Second scan should find both
            results2 = scanner.scan()
            assert len(results2) == 2
