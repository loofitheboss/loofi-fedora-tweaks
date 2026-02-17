"""Tests for command palette quick command integration (v47.0)."""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestCommandPaletteQuickCommands(unittest.TestCase):
    """Tests for command palette action execution support."""

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_registry_includes_quick_commands_with_handlers(self):
        """Quick commands with action handlers should appear in feature registry."""
        from utils.quick_commands import QuickCommandRegistry, QuickCommand
        QuickCommandRegistry.reset()
        registry = QuickCommandRegistry.instance()
        registry.register(QuickCommand(
            id="test-cmd",
            name="Test Command",
            description="A test command",
            category="Test",
            keywords=["test"],
            action=lambda: None,
        ))
        from ui.command_palette import _build_feature_registry
        features = _build_feature_registry()
        execute_features = [f for f in features if f.get("type") == "execute"]
        self.assertGreater(len(execute_features), 0)
        QuickCommandRegistry.reset()

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_quick_commands_have_execute_handler(self):
        """Quick command entries should have callable execute handler."""
        from utils.quick_commands import QuickCommandRegistry, QuickCommand
        QuickCommandRegistry.reset()
        registry = QuickCommandRegistry.instance()
        registry.register(QuickCommand(
            id="test-exec", name="Exec Test", description="d",
            category="Test", keywords=["t"], action=lambda: None,
        ))
        from ui.command_palette import _build_feature_registry
        features = _build_feature_registry()
        for f in features:
            if f.get("type") == "execute":
                self.assertTrue(callable(f.get("execute")), f"Missing handler for {f['name']}")
        QuickCommandRegistry.reset()

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_quick_commands_have_category(self):
        """Quick command entries should have a category."""
        from utils.quick_commands import QuickCommandRegistry, QuickCommand
        QuickCommandRegistry.reset()
        registry = QuickCommandRegistry.instance()
        registry.register(QuickCommand(
            id="test-cat", name="Cat Test", description="d",
            category="TestCat", keywords=["t"], action=lambda: None,
        ))
        from ui.command_palette import _build_feature_registry
        features = _build_feature_registry()
        for f in features:
            if f.get("type") == "execute":
                self.assertTrue(f.get("category"), f"Missing category for {f['name']}")
        QuickCommandRegistry.reset()

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_quick_commands_names_have_icon_prefix(self):
        """Quick command names should have the ⚡ prefix."""
        from utils.quick_commands import QuickCommandRegistry, QuickCommand
        QuickCommandRegistry.reset()
        registry = QuickCommandRegistry.instance()
        registry.register(QuickCommand(
            id="test-icon", name="Icon Test", description="d",
            category="Test", keywords=["t"], action=lambda: None,
        ))
        from ui.command_palette import _build_feature_registry
        features = _build_feature_registry()
        for f in features:
            if f.get("type") == "execute":
                self.assertTrue(f["name"].startswith("⚡"), f"Missing icon prefix: {f['name']}")
        QuickCommandRegistry.reset()

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_navigate_features_still_present(self):
        """Standard navigation features should still exist."""
        from ui.command_palette import _build_feature_registry
        features = _build_feature_registry()
        nav_features = [f for f in features if f.get("type", "navigate") == "navigate"]
        self.assertGreater(len(nav_features), 50)

    @patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
    def test_match_score_for_quick_command(self):
        """Quick command entries should be matchable by search."""
        from ui.command_palette import CommandPalette
        entry = {
            "name": "⚡ System Cleanup",
            "category": "Maintenance",
            "keywords": ["cleanup", "cache"],
            "action": "",
            "type": "execute",
        }
        score = CommandPalette._match_score(entry, "cleanup")
        self.assertGreater(score, 0)


if __name__ == '__main__':
    unittest.main()
