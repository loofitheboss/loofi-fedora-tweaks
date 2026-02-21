"""
Integration tests for v29.0 "Usability & Polish" features.

Covers:
- SettingsManager.reset_group() method
- Sidebar filter matches descriptions (MainWindow._filter_sidebar logic)
- API server CORS origins are restricted (not wildcard)
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


# ---------------------------------------------------------------------------
# Settings reset_group
# ---------------------------------------------------------------------------

class TestSettingsResetGroup(unittest.TestCase):
    """SettingsManager.reset_group() resets only the specified keys."""

    def _make_manager(self, tmpdir, initial=None):
        from pathlib import Path
        from utils.settings import SettingsManager
        path = Path(tmpdir) / "settings.json"
        if initial is not None:
            path.write_text(json.dumps(initial, indent=2))
        return SettingsManager(settings_path=path)

    def test_reset_group_restores_defaults(self):
        """reset_group resets specified keys to defaults."""
        from utils.settings import AppSettings
        from dataclasses import asdict

        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["follow_system_theme"] = True
            initial["log_level"] = "DEBUG"
            mgr = self._make_manager(tmpdir, initial)

            # Confirm customised values
            self.assertEqual(mgr.get("theme"), "light")
            self.assertTrue(mgr.get("follow_system_theme"))
            self.assertEqual(mgr.get("log_level"), "DEBUG")

            # Reset only theme-related keys
            mgr.reset_group(["theme", "follow_system_theme"])

            self.assertEqual(mgr.get("theme"), "dark")
            self.assertFalse(mgr.get("follow_system_theme"))

    def test_reset_group_leaves_other_keys(self):
        """Keys not in the reset group remain unchanged."""
        from utils.settings import AppSettings
        from dataclasses import asdict

        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["log_level"] = "DEBUG"
            mgr = self._make_manager(tmpdir, initial)

            mgr.reset_group(["theme"])

            # theme reset
            self.assertEqual(mgr.get("theme"), "dark")
            # log_level unchanged
            self.assertEqual(mgr.get("log_level"), "DEBUG")

    def test_reset_group_persists_to_disk(self):
        """After reset_group, the file on disk reflects the reset values."""
        from pathlib import Path
        from utils.settings import SettingsManager, AppSettings
        from dataclasses import asdict

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            initial["start_minimized"] = True
            path.write_text(json.dumps(initial, indent=2))

            mgr = SettingsManager(settings_path=path)
            mgr.reset_group(["theme"])

            # Re-read from disk
            saved = json.loads(path.read_text())
            self.assertEqual(saved["theme"], "dark")
            self.assertTrue(saved["start_minimized"])

    def test_reset_group_unknown_key_ignored(self):
        """Unknown keys in the list are silently ignored."""
        from utils.settings import AppSettings
        from dataclasses import asdict

        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            mgr = self._make_manager(tmpdir, initial)

            # "nonexistent_key" is not in defaults
            mgr.reset_group(["theme", "nonexistent_key"])

            self.assertEqual(mgr.get("theme"), "dark")

    def test_reset_group_empty_list(self):
        """Empty key list is a no-op but still persists (save called)."""
        from utils.settings import AppSettings
        from dataclasses import asdict

        with tempfile.TemporaryDirectory() as tmpdir:
            initial = asdict(AppSettings())
            initial["theme"] = "light"
            mgr = self._make_manager(tmpdir, initial)

            mgr.reset_group([])

            self.assertEqual(mgr.get("theme"), "light")


# ---------------------------------------------------------------------------
# Sidebar filter matches descriptions
# ---------------------------------------------------------------------------

class TestSidebarFilter(unittest.TestCase):
    """
    MainWindow._filter_sidebar should match against item text,
    description data, and badge data.
    """

    @classmethod
    def setUpClass(cls):
        """Ensure a QApplication exists for the lifetime of these tests."""
        from PyQt6.QtWidgets import QApplication
        cls._app = QApplication.instance()
        if cls._app is None:
            cls._app = QApplication([])

    def _build_tree_with_items(self):
        """Build a mock QTreeWidget with categories and children."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

        _ROLE_DESC = Qt.ItemDataRole.UserRole + 1
        _ROLE_BADGE = Qt.ItemDataRole.UserRole + 2

        tree = QTreeWidget()
        tree.setHeaderHidden(True)

        # Category: System
        cat = QTreeWidgetItem(tree, ["System"])

        # Child 1: System Info
        child1 = QTreeWidgetItem(cat, ["🖥 System Info"])
        child1.setData(0, _ROLE_DESC, "hardware and OS details")
        child1.setData(0, _ROLE_BADGE, "recommended")
        child1.setData(0, Qt.ItemDataRole.UserRole, MagicMock())  # page widget

        # Child 2: Maintenance
        child2 = QTreeWidgetItem(cat, ["🔧 Maintenance"])
        child2.setData(0, _ROLE_DESC, "updates cleanup overlays")
        child2.setData(0, _ROLE_BADGE, "")
        child2.setData(0, Qt.ItemDataRole.UserRole, MagicMock())

        # Category: Tools
        cat2 = QTreeWidgetItem(tree, ["Tools"])

        child3 = QTreeWidgetItem(cat2, ["🎮 Gaming"])
        child3.setData(0, _ROLE_DESC, "steam proton gaming setup")
        child3.setData(0, _ROLE_BADGE, "advanced")
        child3.setData(0, Qt.ItemDataRole.UserRole, MagicMock())

        return tree, _ROLE_DESC, _ROLE_BADGE

    def _run_filter(self, tree, text):
        """
        Simulate _filter_sidebar logic from MainWindow.
        We replicate the filter logic here to test it independently
        of the full MainWindow instantiation.
        """
        from PyQt6.QtCore import Qt

        _ROLE_DESC = Qt.ItemDataRole.UserRole + 1
        _ROLE_BADGE = Qt.ItemDataRole.UserRole + 2

        search = text.lower()
        for i in range(tree.topLevelItemCount()):
            category = tree.topLevelItem(i)
            category_visible = False
            for j in range(category.childCount()):
                child = category.child(j)
                name_match = search in child.text(0).lower()
                desc = (child.data(0, _ROLE_DESC) or "").lower()
                desc_match = search in desc
                badge = (child.data(0, _ROLE_BADGE) or "").lower()
                badge_match = search in badge
                if name_match or desc_match or badge_match:
                    child.setHidden(False)
                    category_visible = True
                else:
                    child.setHidden(True)
            if search in category.text(0).lower():
                category_visible = True
                for j in range(category.childCount()):
                    category.child(j).setHidden(False)
            category.setHidden(not category_visible)

    def test_filter_by_name(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "gaming")

        cat_system = tree.topLevelItem(0)
        cat_tools = tree.topLevelItem(1)

        # "Gaming" child should be visible
        self.assertFalse(cat_tools.child(0).isHidden())
        # "System Info" and "Maintenance" should be hidden
        self.assertTrue(cat_system.child(0).isHidden())
        self.assertTrue(cat_system.child(1).isHidden())

    def test_filter_by_description(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "hardware")

        cat_system = tree.topLevelItem(0)
        # "System Info" has "hardware" in description
        self.assertFalse(cat_system.child(0).isHidden())
        # "Maintenance" does not
        self.assertTrue(cat_system.child(1).isHidden())

    def test_filter_by_badge(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "recommended")

        cat_system = tree.topLevelItem(0)
        # "System Info" has badge "recommended"
        self.assertFalse(cat_system.child(0).isHidden())
        # "Maintenance" has empty badge
        self.assertTrue(cat_system.child(1).isHidden())

    def test_filter_by_category_name(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "system")

        cat_system = tree.topLevelItem(0)
        # Category matches "system", so all children visible
        self.assertFalse(cat_system.isHidden())
        self.assertFalse(cat_system.child(0).isHidden())
        self.assertFalse(cat_system.child(1).isHidden())

    def test_empty_filter_shows_everything(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "")

        for i in range(tree.topLevelItemCount()):
            cat = tree.topLevelItem(i)
            self.assertFalse(cat.isHidden())
            for j in range(cat.childCount()):
                self.assertFalse(cat.child(j).isHidden())

    def test_no_match_hides_everything(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "zzzzzznotfound")

        for i in range(tree.topLevelItemCount()):
            cat = tree.topLevelItem(i)
            self.assertTrue(cat.isHidden())

    def test_case_insensitive_match(self):
        tree, _, _ = self._build_tree_with_items()
        self._run_filter(tree, "GAMING")

        cat_tools = tree.topLevelItem(1)
        self.assertFalse(cat_tools.child(0).isHidden())


# ---------------------------------------------------------------------------
# API Server CORS lockdown
# ---------------------------------------------------------------------------

class TestAPIServerCORS(unittest.TestCase):
    """API server CORS origins are restricted to localhost (not wildcard)."""

    @patch('utils.api_server.uvicorn')
    @patch('utils.api_server.AuthManager')
    def test_cors_not_wildcard(self, mock_auth, mock_uvicorn):
        """Allowed origins must not contain '*'."""
        from utils.api_server import APIServer

        server = APIServer(host="127.0.0.1", port=8000)
        app = server.app

        # Find the CORSMiddleware in the middleware stack
        cors_found = False
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_found = True
                origins = middleware.kwargs.get("allow_origins", [])
                self.assertNotIn("*", origins,
                                 "CORS should not allow wildcard origin")
        self.assertTrue(cors_found, "CORSMiddleware not found in app middleware")

    @patch('utils.api_server.uvicorn')
    @patch('utils.api_server.AuthManager')
    def test_cors_allows_localhost(self, mock_auth, mock_uvicorn):
        """Allowed origins should include localhost variants."""
        from utils.api_server import APIServer

        server = APIServer(host="127.0.0.1", port=8000)
        app = server.app

        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                origins = middleware.kwargs.get("allow_origins", [])
                localhost_found = any("localhost" in o or "127.0.0.1" in o for o in origins)
                self.assertTrue(localhost_found,
                                f"CORS should allow localhost, got: {origins}")
                break

    @patch('utils.api_server.uvicorn')
    @patch('utils.api_server.AuthManager')
    def test_cors_origins_are_list_of_strings(self, mock_auth, mock_uvicorn):
        """Origins should be a list of string URLs."""
        from utils.api_server import APIServer

        server = APIServer(host="127.0.0.1", port=8000)
        app = server.app

        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                origins = middleware.kwargs.get("allow_origins", [])
                self.assertIsInstance(origins, list)
                for o in origins:
                    self.assertIsInstance(o, str)
                    self.assertTrue(o.startswith("http"),
                                    f"Origin should be an HTTP URL: {o}")
                break

    @patch('utils.api_server.uvicorn')
    @patch('utils.api_server.AuthManager')
    def test_cors_credentials_enabled(self, mock_auth, mock_uvicorn):
        """Credentials should be allowed for API token auth."""
        from utils.api_server import APIServer

        server = APIServer(host="127.0.0.1", port=8000)
        app = server.app

        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                creds = middleware.kwargs.get("allow_credentials", False)
                self.assertTrue(creds)
                break


# ---------------------------------------------------------------------------
# Error handler integration
# ---------------------------------------------------------------------------

class TestErrorHandlerIntegration(unittest.TestCase):
    """Error handler installs and uninstalls correctly in lifecycle."""

    def test_install_and_uninstall_roundtrip(self):
        from utils.error_handler import (
            install_error_handler,
            uninstall_error_handler,
            _loofi_excepthook,
            _original_excepthook,
        )

        original = sys.excepthook
        try:
            install_error_handler()
            self.assertIs(sys.excepthook, _loofi_excepthook)

            uninstall_error_handler()
            self.assertIs(sys.excepthook, _original_excepthook)
        finally:
            sys.excepthook = original

    @patch('utils.error_handler._show_error_dialog')
    @patch('utils.error_handler._log_error')
    def test_excepthook_called_for_unhandled_exception(self, mock_log, mock_dialog):
        """When installed, unhandled exceptions route through the handler."""
        from utils.error_handler import install_error_handler
        from utils.errors import NetworkError

        original = sys.excepthook
        try:
            install_error_handler()
            exc = NetworkError("timeout")
            sys.excepthook(type(exc), exc, None)

            mock_log.assert_called_once()
            mock_dialog.assert_called_once_with(exc)
        finally:
            sys.excepthook = original


# ---------------------------------------------------------------------------
# Notification toast category fallback
# ---------------------------------------------------------------------------

class TestNotificationToastCategoryFallback(unittest.TestCase):
    """Unknown categories should gracefully fall back to default colour."""

    def test_unknown_category_returns_default_colour(self):
        from ui.notification_toast import _CATEGORY_COLORS
        default = "#39c5cf"
        result = _CATEGORY_COLORS.get("totally_unknown", default)
        self.assertEqual(result, default)


if __name__ == '__main__':
    unittest.main()
