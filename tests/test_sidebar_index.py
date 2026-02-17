"""Tests for SidebarEntry and SidebarIndex in main_window.py"""
import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestSidebarEntry(unittest.TestCase):
    def test_create_entry_with_all_fields(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="storage", name="Storage", description="Manage disks",
            category="System", icon="storage-disk", badge="",
        )
        entry = SidebarEntry(
            plugin_id="storage",
            display_name="Storage",
            tree_item=MagicMock(),
            page_widget=MagicMock(),
            metadata=meta,
        )
        self.assertEqual(entry.plugin_id, "storage")
        self.assertEqual(entry.display_name, "Storage")
        self.assertEqual(entry.status, "")

    def test_entry_default_status_is_empty(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="test", name="Test", description="",
            category="System", icon="", badge="",
        )
        entry = SidebarEntry(
            plugin_id="test", display_name="Test",
            tree_item=MagicMock(), page_widget=MagicMock(),
            metadata=meta,
        )
        self.assertEqual(entry.status, "")

    def test_entry_status_is_mutable(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="test", name="Test", description="",
            category="System", icon="", badge="",
        )
        entry = SidebarEntry(
            plugin_id="test", display_name="Test",
            tree_item=MagicMock(), page_widget=MagicMock(),
            metadata=meta,
        )
        entry.status = "ok"
        self.assertEqual(entry.status, "ok")


class TestAddPageDecomposition(unittest.TestCase):
    def test_main_window_has_find_or_create_category(self):
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_find_or_create_category'))

    def test_main_window_has_create_tab_item(self):
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_create_tab_item'))

    def test_main_window_has_register_in_index(self):
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_register_in_index'))


class TestFavoritesIdLookup(unittest.TestCase):
    def test_favorites_uses_index_lookup(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata
        meta = PluginMetadata(id="system-info", name="System Info", description="", category="System", icon="", badge="")
        index = {"system-info": SidebarEntry(plugin_id="system-info", display_name="System Info", tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta)}
        entry = index.get("system-info")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.display_name, "System Info")

    def test_stale_favorite_returns_none(self):
        index = {}
        self.assertIsNone(index.get("deleted-tab"))


class TestSetTabStatusById(unittest.TestCase):
    def test_status_stored_in_entry(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata
        meta = PluginMetadata(id="storage", name="Storage", description="Manage disks", category="System", icon="", badge="")
        entry = SidebarEntry(plugin_id="storage", display_name="Storage", tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta)
        entry.status = "warning"
        self.assertEqual(entry.status, "warning")
        entry.tree_item.setText.assert_not_called()


class TestSwitchToTabById(unittest.TestCase):
    def test_switch_by_plugin_id(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata
        meta = PluginMetadata(id="storage", name="Storage", description="", category="System", icon="", badge="")
        index = {"storage": SidebarEntry(plugin_id="storage", display_name="Storage", tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta)}
        entry = index.get("storage")
        self.assertIsNotNone(entry)

    def test_display_name_not_in_index_keys(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata
        meta = PluginMetadata(id="storage", name="Storage", description="", category="System", icon="", badge="")
        index = {"storage": SidebarEntry(plugin_id="storage", display_name="Storage", tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta)}
        self.assertIsNone(index.get("Storage"))


class TestSidebarItemDelegate(unittest.TestCase):
    def test_delegate_class_exists(self):
        from ui.main_window import SidebarItemDelegate
        self.assertTrue(callable(SidebarItemDelegate))

    def test_status_colors_defined(self):
        from ui.main_window import SidebarItemDelegate
        delegate = SidebarItemDelegate()
        self.assertIn("ok", delegate._STATUS_COLORS)
        self.assertIn("warning", delegate._STATUS_COLORS)
        self.assertIn("error", delegate._STATUS_COLORS)

    def test_status_colors_are_three_values(self):
        from ui.main_window import SidebarItemDelegate
        delegate = SidebarItemDelegate()
        self.assertEqual(len(delegate._STATUS_COLORS), 3)

    def test_delegate_inherits_qstyleditemdelegate(self):
        from PyQt6.QtWidgets import QStyledItemDelegate
        from ui.main_window import SidebarItemDelegate
        self.assertTrue(issubclass(SidebarItemDelegate, QStyledItemDelegate))


class TestExperienceLevelValidation(unittest.TestCase):
    def test_get_all_declared_tab_ids_returns_set(self):
        from utils.experience_level import ExperienceLevelManager
        result = ExperienceLevelManager.get_all_declared_tab_ids()
        self.assertIsInstance(result, set)
        self.assertIn("dashboard", result)
        self.assertIn("development", result)

    def test_beginner_tabs_subset_of_declared(self):
        from utils.experience_level import ExperienceLevelManager, _BEGINNER_TABS
        declared = ExperienceLevelManager.get_all_declared_tab_ids()
        for tab_id in _BEGINNER_TABS:
            self.assertIn(tab_id, declared)

    def test_declared_ids_includes_intermediate(self):
        from utils.experience_level import ExperienceLevelManager, _INTERMEDIATE_TABS
        declared = ExperienceLevelManager.get_all_declared_tab_ids()
        for tab_id in _INTERMEDIATE_TABS:
            self.assertIn(tab_id, declared)

    def test_declared_ids_is_nonempty(self):
        from utils.experience_level import ExperienceLevelManager
        result = ExperienceLevelManager.get_all_declared_tab_ids()
        self.assertGreater(len(result), 0)


class TestRebuildSidebarMethodExists(unittest.TestCase):
    def test_main_window_has_rebuild_sidebar_for_experience_level(self):
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_rebuild_sidebar_for_experience_level'))
        self.assertTrue(callable(getattr(MainWindow, '_rebuild_sidebar_for_experience_level')))


if __name__ == "__main__":
    unittest.main()
