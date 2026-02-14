"""Tests for ui/extensions_tab.py — ExtensionsTab source-level checks."""

import os
import unittest


class TestExtensionsTabSource(unittest.TestCase):
    """Ensure ExtensionsTab has required widgets and methods."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'extensions_tab.py'
        )
        with open(path, 'r', encoding='utf-8') as fh:
            cls.source = fh.read()

    def test_inherits_base_tab(self):
        self.assertIn("class ExtensionsTab(BaseTab)", self.source)

    def test_has_metadata(self):
        self.assertIn("_METADATA", self.source)
        self.assertIn('"extensions"', self.source)

    def test_has_search_bar(self):
        self.assertIn("QLineEdit", self.source)
        self.assertIn("search", self.source.lower())

    def test_has_extensions_table(self):
        self.assertIn("QTableWidget", self.source)

    def test_has_enable_disable(self):
        self.assertIn("Enable", self.source)
        self.assertIn("Disable", self.source)

    def test_has_install_remove(self):
        self.assertIn("Install", self.source)
        self.assertIn("Remove", self.source)

    def test_uses_extension_manager(self):
        self.assertIn("ExtensionManager", self.source)

    def test_has_load_method(self):
        self.assertIn("def _load_extensions", self.source)

    def test_has_show_event(self):
        self.assertIn("def showEvent", self.source)


class TestBackupTabSource(unittest.TestCase):
    """Ensure BackupTab has required widgets and methods."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), '..', 'loofi-fedora-tweaks', 'ui', 'backup_tab.py'
        )
        with open(path, 'r', encoding='utf-8') as fh:
            cls.source = fh.read()

    def test_inherits_base_tab(self):
        self.assertIn("class BackupTab(BaseTab)", self.source)

    def test_has_metadata(self):
        self.assertIn("_METADATA", self.source)
        self.assertIn('"backup"', self.source)

    def test_has_stacked_widget(self):
        self.assertIn("QStackedWidget", self.source)

    def test_has_wizard_pages(self):
        # Detect, Configure, Manage pages
        self.assertIn("_create_detect_page", self.source)
        self.assertIn("_create_configure_page", self.source)
        self.assertIn("_create_manage_page", self.source)

    def test_uses_backup_wizard(self):
        self.assertIn("BackupWizard", self.source)

    def test_has_create_snapshot(self):
        self.assertIn("_create_snapshot", self.source)

    def test_has_restore(self):
        self.assertIn("restore", self.source.lower())

    def test_has_navigation_buttons(self):
        self.assertIn("Back", self.source)
        self.assertIn("Next", self.source)


if __name__ == '__main__':
    unittest.main()
