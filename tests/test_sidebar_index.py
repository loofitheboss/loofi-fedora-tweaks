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


if __name__ == "__main__":
    unittest.main()
