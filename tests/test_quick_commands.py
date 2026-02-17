"""Tests for utils/quick_commands.py"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.quick_commands import QuickCommand, QuickCommandRegistry


class TestQuickCommand(unittest.TestCase):
    """Tests for QuickCommand dataclass."""

    def test_creation(self):
        """Test QuickCommand can be created with all fields."""
        cmd = QuickCommand(
            id="test-cmd",
            name="Test Command",
            description="A test command",
            category="System",
            keywords=["test", "demo"],
            action=lambda: None,
        )
        self.assertEqual(cmd.id, "test-cmd")
        self.assertEqual(cmd.name, "Test Command")
        self.assertEqual(cmd.category, "System")
        self.assertEqual(len(cmd.keywords), 2)

    def test_creation_without_action(self):
        """Test QuickCommand can be created without an action."""
        cmd = QuickCommand(
            id="test-cmd",
            name="Test",
            description="Test",
            category="System",
            keywords=[],
        )
        self.assertIsNone(cmd.action)


class TestQuickCommandRegistryBasic(unittest.TestCase):
    """Tests for QuickCommandRegistry basic operations."""

    def setUp(self):
        """Reset singleton before each test."""
        QuickCommandRegistry.reset()

    def tearDown(self):
        """Reset singleton after each test."""
        QuickCommandRegistry.reset()

    def test_singleton(self):
        """Test registry is a singleton."""
        r1 = QuickCommandRegistry.instance()
        r2 = QuickCommandRegistry.instance()
        self.assertIs(r1, r2)

    def test_register_command(self):
        """Test registering a command."""
        registry = QuickCommandRegistry.instance()
        cmd = QuickCommand(
            id="test-cmd", name="Test", description="Test",
            category="System", keywords=["test"],
        )

        registry.register(cmd)

        self.assertIsNotNone(registry.get("test-cmd"))

    def test_register_duplicate_raises(self):
        """Test that registering a duplicate ID raises ValueError."""
        registry = QuickCommandRegistry.instance()
        cmd1 = QuickCommand(id="dup", name="A", description="A", category="S", keywords=[])
        cmd2 = QuickCommand(id="dup", name="B", description="B", category="S", keywords=[])

        registry.register(cmd1)
        with self.assertRaises(ValueError):
            registry.register(cmd2)

    def test_unregister_command(self):
        """Test unregistering a command."""
        registry = QuickCommandRegistry.instance()
        cmd = QuickCommand(id="rm-me", name="Remove", description="R", category="S", keywords=[])
        registry.register(cmd)

        registry.unregister("rm-me")

        self.assertIsNone(registry.get("rm-me"))

    def test_unregister_nonexistent(self):
        """Test unregistering a non-existent command is a no-op."""
        registry = QuickCommandRegistry.instance()
        registry.unregister("does-not-exist")  # Should not raise

    def test_get_nonexistent(self):
        """Test getting a non-existent command returns None."""
        registry = QuickCommandRegistry.instance()
        self.assertIsNone(registry.get("nonexistent"))


class TestQuickCommandRegistryListing(unittest.TestCase):
    """Tests for QuickCommandRegistry listing operations."""

    def setUp(self):
        QuickCommandRegistry.reset()
        self.registry = QuickCommandRegistry.instance()
        self.registry.register(QuickCommand(
            id="alpha", name="Alpha", description="First",
            category="System", keywords=["a"],
        ))
        self.registry.register(QuickCommand(
            id="beta", name="Beta", description="Second",
            category="Tools", keywords=["b"],
        ))
        self.registry.register(QuickCommand(
            id="gamma", name="Gamma", description="Third",
            category="System", keywords=["c"],
        ))

    def tearDown(self):
        QuickCommandRegistry.reset()

    def test_list_all(self):
        """Test listing all commands."""
        all_cmds = self.registry.list_all()
        self.assertEqual(len(all_cmds), 3)

    def test_list_all_sorted_by_name(self):
        """Test list_all returns commands sorted by name."""
        all_cmds = self.registry.list_all()
        names = [c.name for c in all_cmds]
        self.assertEqual(names, sorted(names))

    def test_list_by_category(self):
        """Test listing commands filtered by category."""
        system_cmds = self.registry.list_by_category("System")
        self.assertEqual(len(system_cmds), 2)

        tools_cmds = self.registry.list_by_category("Tools")
        self.assertEqual(len(tools_cmds), 1)

    def test_list_by_nonexistent_category(self):
        """Test listing commands for a non-existent category."""
        cmds = self.registry.list_by_category("Nonexistent")
        self.assertEqual(len(cmds), 0)


class TestQuickCommandRegistrySearch(unittest.TestCase):
    """Tests for QuickCommandRegistry.search()."""

    def setUp(self):
        QuickCommandRegistry.reset()
        self.registry = QuickCommandRegistry.instance()
        self.registry.register(QuickCommand(
            id="focus", name="Toggle Focus Mode", description="Enable focus",
            category="System", keywords=["focus", "zen", "concentrate"],
        ))
        self.registry.register(QuickCommand(
            id="cleanup", name="Run System Cleanup", description="Clean temp files",
            category="Maintenance", keywords=["clean", "cache", "temp"],
        ))

    def tearDown(self):
        QuickCommandRegistry.reset()

    def test_search_by_name(self):
        """Test searching by name substring."""
        results = self.registry.search("Focus")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "focus")

    def test_search_by_keyword(self):
        """Test searching by keyword."""
        results = self.registry.search("zen")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "focus")

    def test_search_by_description(self):
        """Test searching by description."""
        results = self.registry.search("temp files")
        self.assertGreater(len(results), 0)

    def test_search_empty_returns_all(self):
        """Test empty search returns all commands."""
        results = self.registry.search("")
        self.assertEqual(len(results), 2)

    def test_search_no_match(self):
        """Test search with no match returns empty list."""
        results = self.registry.search("xyznonexistent")
        self.assertEqual(len(results), 0)

    def test_search_case_insensitive(self):
        """Test search is case-insensitive."""
        results1 = self.registry.search("FOCUS")
        results2 = self.registry.search("focus")
        self.assertEqual(len(results1), len(results2))

    def test_search_exact_match_scored_highest(self):
        """Test exact name match scores highest."""
        self.registry.register(QuickCommand(
            id="exact", name="zen", description="Exact match",
            category="System", keywords=[],
        ))

        results = self.registry.search("zen")
        # The exact name match ("zen") should rank above keyword match
        self.assertGreater(len(results), 1)


class TestQuickCommandRegistryExecution(unittest.TestCase):
    """Tests for QuickCommandRegistry.execute()."""

    def setUp(self):
        QuickCommandRegistry.reset()
        self.registry = QuickCommandRegistry.instance()

    def tearDown(self):
        QuickCommandRegistry.reset()

    def test_execute_success(self):
        """Test successful command execution."""
        mock_action = MagicMock()
        self.registry.register(QuickCommand(
            id="exec-test", name="Exec", description="Test",
            category="System", keywords=[], action=mock_action,
        ))

        result = self.registry.execute("exec-test")

        self.assertTrue(result)
        mock_action.assert_called_once()

    def test_execute_nonexistent(self):
        """Test executing a non-existent command returns False."""
        result = self.registry.execute("nonexistent")
        self.assertFalse(result)

    def test_execute_no_action(self):
        """Test executing a command with no action returns False."""
        self.registry.register(QuickCommand(
            id="no-action", name="No Action", description="Test",
            category="System", keywords=[],
        ))

        result = self.registry.execute("no-action")
        self.assertFalse(result)

    def test_execute_error_handled(self):
        """Test that execution errors are handled gracefully."""
        def failing_action():
            raise RuntimeError("Action failed")

        self.registry.register(QuickCommand(
            id="fail-test", name="Fail", description="Test",
            category="System", keywords=[], action=failing_action,
        ))

        result = self.registry.execute("fail-test")
        self.assertFalse(result)


class TestQuickCommandRegistryBuiltins(unittest.TestCase):
    """Tests for QuickCommandRegistry.get_builtin_commands()."""

    def test_builtin_count(self):
        """Test that built-in commands list has expected count."""
        builtins = QuickCommandRegistry.get_builtin_commands()
        self.assertEqual(len(builtins), 10)

    def test_builtin_ids_unique(self):
        """Test all built-in command IDs are unique."""
        builtins = QuickCommandRegistry.get_builtin_commands()
        ids = [c.id for c in builtins]
        self.assertEqual(len(ids), len(set(ids)))

    def test_builtin_actions_none(self):
        """Test built-in commands have None actions (need UI wiring)."""
        builtins = QuickCommandRegistry.get_builtin_commands()
        for cmd in builtins:
            self.assertIsNone(cmd.action, f"Builtin {cmd.id} should have None action")

    def test_builtin_fields_populated(self):
        """Test all built-in commands have non-empty required fields."""
        builtins = QuickCommandRegistry.get_builtin_commands()
        for cmd in builtins:
            self.assertTrue(cmd.id, f"Command missing id")
            self.assertTrue(cmd.name, f"Command {cmd.id} missing name")
            self.assertTrue(cmd.description, f"Command {cmd.id} missing description")
            self.assertTrue(cmd.category, f"Command {cmd.id} missing category")
            self.assertGreater(len(cmd.keywords), 0, f"Command {cmd.id} has no keywords")


if __name__ == '__main__':
    unittest.main()
