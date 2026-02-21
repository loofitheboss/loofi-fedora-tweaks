"""Tests for quick actions bar."""
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

# Mock PyQt6 before importing the module under test
_orig_pyqt6 = sys.modules.get("PyQt6")
_orig_qtwidgets = sys.modules.get("PyQt6.QtWidgets")
_orig_qtcore = sys.modules.get("PyQt6.QtCore")
_orig_qtgui = sys.modules.get("PyQt6.QtGui")

sys.modules["PyQt6"] = MagicMock()
sys.modules["PyQt6.QtWidgets"] = MagicMock()
sys.modules["PyQt6.QtCore"] = MagicMock()
sys.modules["PyQt6.QtGui"] = MagicMock()

from ui.quick_actions import QuickAction, QuickActionRegistry, register_default_actions  # noqa: E402

# Restore originals so other tests are not polluted
for _mod, _orig in [("PyQt6", _orig_pyqt6), ("PyQt6.QtWidgets", _orig_qtwidgets),
                     ("PyQt6.QtCore", _orig_qtcore), ("PyQt6.QtGui", _orig_qtgui)]:
    if _orig is not None:
        sys.modules[_mod] = _orig
    else:
        sys.modules.pop(_mod, None)


class TestQuickAction(unittest.TestCase):
    """Tests for the QuickAction dataclass."""

    def test_create(self):
        """Verify all fields are stored correctly."""
        def cb():
            return None
        action = QuickAction(
            name="Test",
            category="Cat",
            callback=cb,
            description="A test action",
            icon="🔧",
            keywords=["test", "demo"],
        )
        self.assertEqual(action.name, "Test")
        self.assertEqual(action.category, "Cat")
        self.assertIs(action.callback, cb)
        self.assertEqual(action.description, "A test action")
        self.assertEqual(action.icon, "🔧")
        self.assertEqual(action.keywords, ["test", "demo"])

    def test_callback_callable(self):
        """Verify the callback can be invoked."""
        result = []
        action = QuickAction(
            name="Run",
            category="Cat",
            callback=lambda: result.append(1),
            description="desc",
            icon="⚙️",
        )
        action.callback()
        self.assertEqual(result, [1])

    def test_keywords_list(self):
        """Verify keywords is stored as a list."""
        action = QuickAction(
            name="KW",
            category="Cat",
            callback=lambda: None,
            description="desc",
            icon="📦",
            keywords=["alpha", "beta"],
        )
        self.assertIsInstance(action.keywords, list)
        self.assertEqual(len(action.keywords), 2)

    def test_default_keywords(self):
        """Verify keywords defaults to an empty list."""
        action = QuickAction(
            name="NoKW",
            category="Cat",
            callback=lambda: None,
            description="desc",
            icon="📦",
        )
        self.assertEqual(action.keywords, [])


class TestQuickActionRegistry(unittest.TestCase):
    """Tests for QuickActionRegistry singleton and query methods."""

    def setUp(self):
        """Reset singleton between tests."""
        QuickActionRegistry._instance = None

    def _make_action(self, name="Act", category="General", **kwargs):
        """Helper to create a QuickAction with defaults."""
        defaults = dict(
            callback=lambda: None,
            description=f"{name} description",
            icon="🔧",
            keywords=[],
        )
        defaults.update(kwargs)
        return QuickAction(name=name, category=category, **defaults)

    # -- singleton ------------------------------------------------------

    def test_singleton(self):
        """instance() returns the same object on repeated calls."""
        a = QuickActionRegistry.instance()
        b = QuickActionRegistry.instance()
        self.assertIs(a, b)

    # -- register / unregister ------------------------------------------

    def test_register(self):
        """A registered action appears in get_all()."""
        reg = QuickActionRegistry.instance()
        action = self._make_action("MyAction")
        reg.register(action)
        self.assertIn(action, reg.get_all())

    def test_register_multiple(self):
        """Multiple registered actions all appear."""
        reg = QuickActionRegistry.instance()
        actions = [self._make_action(f"A{i}") for i in range(5)]
        for a in actions:
            reg.register(a)
        self.assertEqual(len(reg.get_all()), 5)
        for a in actions:
            self.assertIn(a, reg.get_all())

    def test_register_no_duplicates(self):
        """Registering an action with the same name twice only stores one."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("Dup"))
        reg.register(self._make_action("Dup"))
        self.assertEqual(len(reg.get_all()), 1)

    def test_unregister(self):
        """Unregistering removes the action from get_all()."""
        reg = QuickActionRegistry.instance()
        action = self._make_action("Gone")
        reg.register(action)
        reg.unregister("Gone")
        self.assertEqual(reg.get_all(), [])

    def test_unregister_nonexistent(self):
        """Unregistering a name that doesn't exist does not crash."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("Keep"))
        reg.unregister("DoesNotExist")
        self.assertEqual(len(reg.get_all()), 1)

    # -- get_by_category ------------------------------------------------

    def test_get_by_category(self):
        """get_by_category returns only matching actions."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("A1", category="Maintenance"))
        reg.register(self._make_action("A2", category="Security"))
        reg.register(self._make_action("A3", category="Maintenance"))

        results = reg.get_by_category("Maintenance")
        self.assertEqual(len(results), 2)
        names = [a.name for a in results]
        self.assertIn("A1", names)
        self.assertIn("A3", names)

    def test_get_by_category_empty(self):
        """get_by_category returns empty list for unknown category."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("X", category="Maintenance"))
        self.assertEqual(reg.get_by_category("Nonexistent"), [])

    def test_get_by_category_case_insensitive(self):
        """get_by_category matching is case-insensitive."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("X", category="Maintenance"))
        self.assertEqual(len(reg.get_by_category("maintenance")), 1)
        self.assertEqual(len(reg.get_by_category("MAINTENANCE")), 1)

    # -- search ---------------------------------------------------------

    def test_search_by_name(self):
        """search finds actions by name substring."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("Update System"))
        reg.register(self._make_action("Clean Cache"))

        results = reg.search("Update")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Update System")

    def test_search_by_description(self):
        """search finds actions by description substring."""
        reg = QuickActionRegistry.instance()
        reg.register(
            self._make_action("A", description="Optimize disk performance")
        )
        reg.register(self._make_action("B", description="Check network"))

        results = reg.search("disk")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "A")

    def test_search_by_keyword(self):
        """search finds actions by keyword match."""
        reg = QuickActionRegistry.instance()
        reg.register(
            self._make_action("Trim", keywords=["ssd", "fstrim"])
        )
        reg.register(self._make_action("Other"))

        results = reg.search("fstrim")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Trim")

    def test_search_case_insensitive(self):
        """search is case-insensitive."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("CPU Governor"))

        self.assertEqual(len(reg.search("cpu")), 1)
        self.assertEqual(len(reg.search("CPU")), 1)
        self.assertEqual(len(reg.search("Cpu Governor")), 1)

    def test_search_empty_query(self):
        """search with empty query returns all actions."""
        reg = QuickActionRegistry.instance()
        for i in range(5):
            reg.register(self._make_action(f"Act{i}"))

        self.assertEqual(len(reg.search("")), 5)


class TestRecentActions(unittest.TestCase):
    """Tests for the recent-actions tracking in QuickActionRegistry."""

    def setUp(self):
        QuickActionRegistry._instance = None

    def _make_action(self, name="Act", category="General", **kwargs):
        defaults = dict(
            callback=lambda: None,
            description=f"{name} description",
            icon="🔧",
            keywords=[],
        )
        defaults.update(kwargs)
        return QuickAction(name=name, category=category, **defaults)

    def test_mark_used(self):
        """mark_used adds the name to the recent list."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("A1"))
        reg.mark_used("A1")

        recents = reg.get_recent()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0].name, "A1")

    def test_mark_used_promotes(self):
        """mark_used moves name to front (most recent first)."""
        reg = QuickActionRegistry.instance()
        for name in ["A1", "A2", "A3"]:
            reg.register(self._make_action(name))

        reg.mark_used("A1")
        reg.mark_used("A2")
        reg.mark_used("A3")
        # A3 was marked last, so it should be first
        self.assertEqual(reg.get_recent()[0].name, "A3")

        # Now promote A1 again
        reg.mark_used("A1")
        self.assertEqual(reg.get_recent()[0].name, "A1")
        # A1 should not appear twice
        names = [a.name for a in reg.get_recent()]
        self.assertEqual(names.count("A1"), 1)

    def test_recent_max_10(self):
        """Recent list is capped at 10 entries."""
        reg = QuickActionRegistry.instance()
        for i in range(15):
            name = f"R{i}"
            reg.register(self._make_action(name))
            reg.mark_used(name)

        self.assertLessEqual(len(reg.get_recent()), 10)

    def test_get_recent(self):
        """get_recent returns QuickAction objects in order."""
        reg = QuickActionRegistry.instance()
        reg.register(self._make_action("X"))
        reg.register(self._make_action("Y"))
        reg.mark_used("X")
        reg.mark_used("Y")

        recents = reg.get_recent()
        self.assertIsInstance(recents[0], QuickAction)
        # Y was marked last, so first
        self.assertEqual(recents[0].name, "Y")
        self.assertEqual(recents[1].name, "X")

    def test_search_recent_first(self):
        """Recent actions appear before non-recent ones in search results."""
        reg = QuickActionRegistry.instance()
        # Register several actions in the same category & keyword space
        for name in ["Alpha Tool", "Beta Tool", "Gamma Tool"]:
            reg.register(self._make_action(name, keywords=["tool"]))

        # Mark Beta as recently used
        reg.mark_used("Beta Tool")

        results = reg.search("Tool")
        self.assertEqual(results[0].name, "Beta Tool")
        # The rest should be alphabetical
        remaining = [a.name for a in results[1:]]
        self.assertEqual(remaining, sorted(remaining))


class TestRegisterDefaults(unittest.TestCase):
    """Tests for the register_default_actions helper."""

    def setUp(self):
        QuickActionRegistry._instance = None

    def test_registers_actions(self):
        """register_default_actions populates the registry."""
        reg = QuickActionRegistry.instance()
        register_default_actions(reg)
        self.assertGreater(len(reg.get_all()), 0)

    def test_default_count(self):
        """At least 15 actions are registered by default."""
        reg = QuickActionRegistry.instance()
        register_default_actions(reg)
        self.assertGreaterEqual(len(reg.get_all()), 15)

    def test_default_categories(self):
        """At least 4 expected categories are present."""
        reg = QuickActionRegistry.instance()
        register_default_actions(reg)

        categories = {a.category for a in reg.get_all()}
        for expected in ["Maintenance", "Security", "Hardware", "Network"]:
            self.assertIn(expected, categories)

    def test_default_actions_have_callbacks(self):
        """Every default action has a callable callback."""
        reg = QuickActionRegistry.instance()
        register_default_actions(reg)

        for action in reg.get_all():
            self.assertTrue(
                callable(action.callback),
                f"{action.name} callback is not callable",
            )


if __name__ == "__main__":
    unittest.main()
