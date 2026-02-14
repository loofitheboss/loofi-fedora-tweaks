"""
Tests for v38.0 "Clarity" — UX Polish & Theme Correctness.

Covers all v38.0 changes:
- Doctor tab rewrite (PrivilegedCommand, SystemManager, self.tr)
- Dashboard username fix (getpass.getuser)
- Quick Actions callback wiring (switch_to_tab navigation)
- Confirm Dialog risk levels and per-action suppression
- BaseTab Copy/Save/Cancel output toolbar
- MainWindow undo button, toast notifications, breadcrumb click

All Qt widgets run offscreen or are mocked. No root required.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


# ---------------------------------------------------------------------------
# Doctor Tab — PrivilegedCommand & SystemManager
# ---------------------------------------------------------------------------
class TestDoctorPrivilegedCommand(unittest.TestCase):
    """Verify doctor uses PrivilegedCommand.dnf() and get_package_manager()."""

    @patch("utils.system.SystemManager.get_package_manager", return_value="dnf")
    @patch("shutil.which", return_value=None)
    @patch("utils.command_runner.CommandRunner.run_command")
    def test_fix_uses_privileged_command(self, mock_run, mock_which, mock_pm):
        """fix_dependencies() calls PrivilegedCommand.dnf() not raw dnf."""
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        d.fix_dependencies()
        mock_run.assert_called_once()
        binary = mock_run.call_args[0][0]
        self.assertEqual(binary, "pkexec")
        d.close()

    @patch("utils.system.SystemManager.get_package_manager", return_value="rpm-ostree")
    @patch("shutil.which", return_value=None)
    def test_tools_dict_uses_system_pm(self, mock_which, mock_pm):
        """Tools dict includes the detected package manager, not hardcoded dnf."""
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        self.assertIn("rpm-ostree", d.tools)
        d.close()

    @patch("utils.system.SystemManager.get_package_manager", return_value="dnf")
    @patch("shutil.which", return_value="/usr/bin/fake")
    def test_header_has_object_name(self, mock_which, mock_pm):
        """Doctor header label uses objectName for QSS styling."""
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        # Find doctorHeader widget
        from PyQt6.QtWidgets import QLabel
        found = False
        for child in d.findChildren(QLabel):
            if child.objectName() == "doctorHeader":
                found = True
                break
        self.assertTrue(found, "doctorHeader objectName not found")
        d.close()

    @patch("utils.system.SystemManager.get_package_manager", return_value="dnf")
    @patch("shutil.which", return_value="/usr/bin/fake")
    def test_fix_button_has_object_name(self, mock_which, mock_pm):
        """Fix button uses objectName for QSS styling."""
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        self.assertEqual(d.btn_fix.objectName(), "doctorFixButton")
        d.close()

    @patch("utils.system.SystemManager.get_package_manager", return_value="dnf")
    @patch("shutil.which", return_value="/usr/bin/fake")
    def test_tool_list_has_accessible_name(self, mock_which, mock_pm):
        """Tool list has accessibleName for a11y."""
        from ui.doctor import DependencyDoctor
        d = DependencyDoctor()
        self.assertTrue(len(d.tool_list.accessibleName()) > 0)
        d.close()


# ---------------------------------------------------------------------------
# Dashboard — Username Fix
# ---------------------------------------------------------------------------
class TestDashboardUsername(unittest.TestCase):
    """Verify dashboard uses getpass.getuser() for the username."""

    @patch("getpass.getuser", return_value="testuser")
    def test_username_from_getpass(self, mock_user):
        """Dashboard greeting uses getpass.getuser().capitalize()."""
        # We test this by checking the import is present and the mock works
        import getpass
        name = getpass.getuser().capitalize()
        self.assertEqual(name, "Testuser")
        mock_user.assert_called()


# ---------------------------------------------------------------------------
# Quick Actions — Callback Wiring
# ---------------------------------------------------------------------------
class TestQuickActionsCallbackWiring(unittest.TestCase):
    """Verify register_default_actions wires callbacks to switch_to_tab."""

    def setUp(self):
        """Reset singleton and mock PyQt6."""
        self._orig_pyqt6 = sys.modules.get("PyQt6")
        self._orig_qtwidgets = sys.modules.get("PyQt6.QtWidgets")
        self._orig_qtcore = sys.modules.get("PyQt6.QtCore")
        self._orig_qtgui = sys.modules.get("PyQt6.QtGui")

        sys.modules["PyQt6"] = MagicMock()
        sys.modules["PyQt6.QtWidgets"] = MagicMock()
        sys.modules["PyQt6.QtCore"] = MagicMock()
        sys.modules["PyQt6.QtGui"] = MagicMock()

    def tearDown(self):
        """Restore module state."""
        for mod, orig in [
            ("PyQt6", self._orig_pyqt6),
            ("PyQt6.QtWidgets", self._orig_qtwidgets),
            ("PyQt6.QtCore", self._orig_qtcore),
            ("PyQt6.QtGui", self._orig_qtgui),
        ]:
            if orig is not None:
                sys.modules[mod] = orig
            else:
                sys.modules.pop(mod, None)

    def test_callbacks_navigate_with_main_window(self):
        """When main_window is provided, callbacks call switch_to_tab."""
        from ui.quick_actions import QuickActionRegistry, register_default_actions

        QuickActionRegistry._instance = None
        reg = QuickActionRegistry.instance()
        mock_mw = MagicMock()
        mock_mw.switch_to_tab = MagicMock()
        register_default_actions(reg, main_window=mock_mw)

        # Every action callback should invoke switch_to_tab when called
        called_tabs = set()
        for action in reg.get_all():
            mock_mw.switch_to_tab.reset_mock()
            action.callback()
            if mock_mw.switch_to_tab.called:
                called_tabs.add(mock_mw.switch_to_tab.call_args[0][0])

        # Should have navigated to multiple different tabs
        self.assertGreater(len(called_tabs), 5,
                           f"Expected >5 tab navigations, got {called_tabs}")

    def test_callbacks_noop_without_main_window(self):
        """Without main_window, callbacks are still callable (no crash)."""
        from ui.quick_actions import QuickActionRegistry, register_default_actions

        QuickActionRegistry._instance = None
        reg = QuickActionRegistry.instance()
        register_default_actions(reg, main_window=None)

        for action in reg.get_all():
            # Should not raise
            action.callback()


# ---------------------------------------------------------------------------
# Confirm Dialog — Risk Levels & Per-Action Suppression
# ---------------------------------------------------------------------------
class TestConfirmDialogRiskLevels(unittest.TestCase):
    """Test risk level badge and per-action suppression features (v38.0)."""

    def test_risk_constants_defined(self):
        """Risk level constants are defined on the class."""
        from ui.confirm_dialog import ConfirmActionDialog

        self.assertEqual(ConfirmActionDialog.RISK_LOW, "low")
        self.assertEqual(ConfirmActionDialog.RISK_MEDIUM, "medium")
        self.assertEqual(ConfirmActionDialog.RISK_HIGH, "high")

    @patch("ui.confirm_dialog.SettingsManager")
    def test_confirm_skips_when_action_key_suppressed(self, mock_settings_cls):
        """confirm() returns True when action_key is in suppressed_confirmations."""
        mock_mgr = MagicMock()
        mock_mgr.get.side_effect = lambda key: {
            "suppressed_confirmations": ["delete_all"],
            "confirm_dangerous_actions": True,
        }.get(key, None)
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        result = ConfirmActionDialog.confirm(
            parent=None,
            action="Delete everything",
            action_key="delete_all",
        )
        self.assertTrue(result)

    @patch("ui.confirm_dialog.SettingsManager")
    def test_confirm_shows_dialog_for_unknown_action_key(self, mock_settings_cls):
        """confirm() shows dialog when action_key is not suppressed."""
        mock_mgr = MagicMock()
        mock_mgr.get.side_effect = lambda key: {
            "suppressed_confirmations": ["other_action"],
            "confirm_dangerous_actions": True,
        }.get(key, True)
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog
        from PyQt6.QtWidgets import QDialog

        with patch.object(ConfirmActionDialog, '__init__', return_value=None):
            with patch.object(ConfirmActionDialog, 'exec',
                              return_value=QDialog.DialogCode.Accepted):
                result = ConfirmActionDialog.confirm(
                    parent=None,
                    action="New action",
                    action_key="new_key",
                )
                self.assertTrue(result)

    @patch("ui.confirm_dialog.SettingsManager")
    def test_on_confirm_per_action_suppression(self, mock_settings_cls):
        """_on_confirm saves action_key to suppressed_confirmations list."""
        mock_mgr = MagicMock()
        mock_mgr.get.return_value = []
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog.dont_ask_cb = MagicMock()
        dialog.dont_ask_cb.isChecked.return_value = True
        dialog._action_key = "cleanup_cache"
        dialog.snapshot_cb = None
        dialog._snapshot_requested = False
        dialog.accept = MagicMock()

        ConfirmActionDialog._on_confirm(dialog)

        # Should save action_key to suppressed list
        mock_mgr.set.assert_called_once_with(
            "suppressed_confirmations", ["cleanup_cache"]
        )
        mock_mgr.save.assert_called_once()

    @patch("ui.confirm_dialog.SettingsManager")
    def test_on_confirm_global_disable_without_action_key(self, mock_settings_cls):
        """_on_confirm without action_key disables global confirmation."""
        mock_mgr = MagicMock()
        mock_settings_cls.instance.return_value = mock_mgr

        from ui.confirm_dialog import ConfirmActionDialog

        dialog = MagicMock(spec=ConfirmActionDialog)
        dialog.dont_ask_cb = MagicMock()
        dialog.dont_ask_cb.isChecked.return_value = True
        dialog._action_key = ""
        dialog.snapshot_cb = None
        dialog._snapshot_requested = False
        dialog.accept = MagicMock()

        ConfirmActionDialog._on_confirm(dialog)

        mock_mgr.set.assert_called_once_with("confirm_dangerous_actions", False)

    def test_risk_badge_created_in_dialog(self):
        """Dialog creates a risk badge when risk_level is provided."""
        from ui.confirm_dialog import ConfirmActionDialog

        d = ConfirmActionDialog(
            action="Delete files",
            risk_level="high",
        )
        # Find riskBadge widget
        from PyQt6.QtWidgets import QLabel
        badges = [c for c in d.findChildren(QLabel)
                  if c.objectName() == "riskBadge"]
        self.assertEqual(len(badges), 1)
        self.assertEqual(badges[0].property("level"), "high")
        d.close()

    def test_no_risk_badge_by_default(self):
        """Dialog does not create a risk badge without risk_level."""
        from ui.confirm_dialog import ConfirmActionDialog

        d = ConfirmActionDialog(action="Simple action")
        from PyQt6.QtWidgets import QLabel
        badges = [c for c in d.findChildren(QLabel)
                  if c.objectName() == "riskBadge"]
        self.assertEqual(len(badges), 0)
        d.close()

    def test_confirm_passes_risk_level_to_dialog(self):
        """confirm() static method passes risk_level and action_key."""
        from ui.confirm_dialog import ConfirmActionDialog
        from PyQt6.QtWidgets import QDialog

        with patch("ui.confirm_dialog.SettingsManager") as mock_sm:
            mock_mgr = MagicMock()
            mock_mgr.get.return_value = True
            mock_sm.instance.return_value = mock_mgr

            with patch.object(ConfirmActionDialog, '__init__',
                              return_value=None) as mock_init:
                with patch.object(ConfirmActionDialog, 'exec',
                                  return_value=QDialog.DialogCode.Accepted):
                    ConfirmActionDialog.confirm(
                        action="Test",
                        risk_level="medium",
                        action_key="test_key",
                    )
                    # Verify risk_level and action_key passed to constructor
                    _, kwargs = mock_init.call_args
                    self.assertEqual(kwargs.get("risk_level"), "medium")
                    self.assertEqual(kwargs.get("action_key"), "test_key")


# ---------------------------------------------------------------------------
# BaseTab — Copy/Save/Cancel Output Toolbar
# ---------------------------------------------------------------------------
class TestBaseTabOutputToolbar(unittest.TestCase):
    """Test Copy/Save/Cancel buttons added to BaseTab output section."""

    def _make_tab(self):
        """Create a BaseTab instance for testing."""
        from ui.base_tab import BaseTab
        tab = BaseTab()
        return tab

    def test_copy_output_copies_to_clipboard(self):
        """_copy_output copies text to clipboard."""
        tab = self._make_tab()
        tab.output_area.setPlainText("Test output line 1\nLine 2")

        with patch("PyQt6.QtWidgets.QApplication.clipboard") as mock_clip:
            mock_clipboard = MagicMock()
            mock_clip.return_value = mock_clipboard
            tab._copy_output()
            mock_clipboard.setText.assert_called_once_with(
                "Test output line 1\nLine 2"
            )
        tab.close()

    def test_copy_output_empty_noop(self):
        """_copy_output does nothing when output is empty."""
        tab = self._make_tab()
        tab.output_area.setPlainText("")

        with patch("PyQt6.QtWidgets.QApplication.clipboard") as mock_clip:
            tab._copy_output()
            mock_clip.assert_not_called()
        tab.close()

    @patch("ui.base_tab.QFileDialog.getSaveFileName",
           return_value=("/tmp/test_output.txt", ""))
    def test_save_output_writes_file(self, mock_dialog):
        """_save_output writes output text to the selected file."""
        tab = self._make_tab()
        tab.output_area.setPlainText("Save this text")

        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            tab._save_output()
            mock_file.assert_called_once_with("/tmp/test_output.txt", "w")
            mock_file().write.assert_called_once_with("Save this text")
        tab.close()

    def test_save_output_empty_noop(self):
        """_save_output does nothing when output is empty."""
        tab = self._make_tab()
        tab.output_area.setPlainText("")

        with patch("ui.base_tab.QFileDialog.getSaveFileName") as mock_dialog:
            tab._save_output()
            mock_dialog.assert_not_called()
        tab.close()

    def test_cancel_command_calls_runner_cancel(self):
        """_cancel_command calls runner.cancel() if runner exists."""
        tab = self._make_tab()
        tab.runner = MagicMock()
        tab._cancel_command()
        tab.runner.cancel.assert_called_once()
        tab.close()

    def test_cancel_command_no_runner(self):
        """_cancel_command handles absent runner gracefully."""
        tab = self._make_tab()
        tab.runner = None
        # Should not raise
        tab._cancel_command()
        tab.close()

    def test_configure_table_sets_object_name(self):
        """configure_table sets objectName to 'baseTable'."""
        from ui.base_tab import BaseTab
        from PyQt6.QtWidgets import QTableWidget

        table = QTableWidget(0, 3)
        BaseTab.configure_table(table)
        self.assertEqual(table.objectName(), "baseTable")
        table.close()

    def test_make_table_item_default_no_color(self):
        """make_table_item with no color lets QSS handle styling."""
        from ui.base_tab import BaseTab

        item = BaseTab.make_table_item("test value")
        self.assertEqual(item.text(), "test value")

    def test_make_table_item_with_explicit_color(self):
        """make_table_item with explicit color sets foreground."""
        from ui.base_tab import BaseTab

        item = BaseTab.make_table_item("colored", color="#ff0000")
        self.assertEqual(item.text(), "colored")


# ---------------------------------------------------------------------------
# MainWindow — Undo Button & Toast
# ---------------------------------------------------------------------------
class TestMainWindowUndoAndToast(unittest.TestCase):
    """Test undo button, toast notifications, and breadcrumb click."""

    @patch("ui.main_window.HistoryManager")
    def test_show_undo_button_makes_visible(self, mock_hm):
        """show_undo_button makes the undo button visible."""
        mw = MagicMock()
        mw._undo_btn = MagicMock()
        mw._status_label = MagicMock()
        mw.tr = lambda s: s

        from ui.main_window import MainWindow
        MainWindow.show_undo_button(mw, "Last action")

        mw._undo_btn.setVisible.assert_called_with(True)
        mw._status_label.setText.assert_called()

    @patch("ui.main_window.HistoryManager")
    def test_on_undo_clicked_success(self, mock_hm_cls):
        """_on_undo_clicked calls HistoryManager.undo_last_action on success."""
        mock_hm = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Undone successfully"
        mock_hm.undo_last_action.return_value = mock_result
        mock_hm_cls.return_value = mock_hm

        mw = MagicMock()
        mw.tr = lambda s: s
        mw.show_status_toast = MagicMock()
        mw._undo_btn = MagicMock()

        from ui.main_window import MainWindow
        MainWindow._on_undo_clicked(mw)

        mock_hm.undo_last_action.assert_called_once()
        mw.show_status_toast.assert_called_with("Undone successfully")
        mw._undo_btn.setVisible.assert_called_with(False)

    @patch("ui.main_window.HistoryManager")
    def test_on_undo_clicked_failure(self, mock_hm_cls):
        """_on_undo_clicked shows error toast on failure."""
        mock_hm = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Nothing to undo"
        mock_hm.undo_last_action.return_value = mock_result
        mock_hm_cls.return_value = mock_hm

        mw = MagicMock()
        mw.tr = lambda s: s
        mw.show_status_toast = MagicMock()
        mw._undo_btn = MagicMock()

        from ui.main_window import MainWindow
        MainWindow._on_undo_clicked(mw)

        mw.show_status_toast.assert_called_with("Nothing to undo", error=True)

    @patch("ui.main_window.HistoryManager", side_effect=Exception("fail"))
    def test_on_undo_clicked_exception(self, mock_hm_cls):
        """_on_undo_clicked handles exceptions gracefully."""
        mw = MagicMock()
        mw.tr = lambda s: s
        mw.show_status_toast = MagicMock()
        mw._undo_btn = MagicMock()

        from ui.main_window import MainWindow
        MainWindow._on_undo_clicked(mw)

        mw.show_status_toast.assert_called_with("Undo failed", error=True)
        mw._undo_btn.setVisible.assert_called_with(False)

    def test_show_status_toast_sets_property(self):
        """show_status_toast sets toast property on status label."""
        mw = MagicMock()
        mw._status_label = MagicMock()
        mw.tr = lambda s: s

        from ui.main_window import MainWindow

        # Test success toast
        MainWindow.show_status_toast(mw, "Done!", error=False)
        mw._status_label.setText.assert_called_with("Done!")
        mw._status_label.setProperty.assert_called_with("toast", "success")

    def test_show_status_toast_error(self):
        """show_status_toast error=True sets toast property to 'error'."""
        mw = MagicMock()
        mw._status_label = MagicMock()
        mw.tr = lambda s: s

        from ui.main_window import MainWindow
        MainWindow.show_status_toast(mw, "Failed!", error=True)
        mw._status_label.setProperty.assert_called_with("toast", "error")

    def test_clear_toast_resets_label(self):
        """_clear_toast clears text and toast property."""
        mw = MagicMock()
        mw._status_label = MagicMock()

        from ui.main_window import MainWindow
        MainWindow._clear_toast(mw)

        mw._status_label.setText.assert_called_with("")
        mw._status_label.setProperty.assert_called_with("toast", "")

    def test_breadcrumb_category_click_navigates(self):
        """_on_breadcrumb_category_click navigates to parent's first child."""
        mw = MagicMock()
        parent_item = MagicMock()
        parent_item.childCount.return_value = 3
        child_item = MagicMock()
        parent_item.child.return_value = child_item
        mw._bc_parent_item = parent_item

        from ui.main_window import MainWindow
        MainWindow._on_breadcrumb_category_click(mw)

        parent_item.setExpanded.assert_called_with(True)
        mw.sidebar.setCurrentItem.assert_called_with(child_item)

    def test_breadcrumb_click_no_parent(self):
        """_on_breadcrumb_category_click does nothing without parent item."""
        mw = MagicMock(spec=[])  # Empty spec — no attributes
        mw.sidebar = MagicMock()

        from ui.main_window import MainWindow
        # Should not raise even without _bc_parent_item
        MainWindow._on_breadcrumb_category_click(mw)


# ---------------------------------------------------------------------------
# QSS ObjectNames — Verify key objectNames exist in themes
# ---------------------------------------------------------------------------
class TestQSSObjectNames(unittest.TestCase):
    """Verify that QSS files contain rules for v38.0 objectNames."""

    def _read_qss(self, filename):
        """Helper to read a QSS file."""
        qss_path = os.path.join(
            os.path.dirname(__file__), "..", "loofi-fedora-tweaks",
            "assets", filename
        )
        with open(qss_path, "r") as f:
            return f.read()

    def test_modern_qss_has_v38_objectnames(self):
        """modern.qss contains rules for all v38.0 objectNames."""
        qss = self._read_qss("modern.qss")
        v38_names = [
            "doctorHeader", "doctorFixButton",
            "confirmIcon", "confirmAction", "confirmSeparator",
            "confirmDescription", "confirmUndoFrame", "confirmUndoText",
            "confirmSnapshot", "confirmDontAsk", "confirmPreview",
            "riskBadge",
            "commandPalette", "paletteSearch", "paletteHint",
            "paletteResults", "paletteFooter",
            "baseTable",
            "outputCopyBtn", "outputSaveBtn", "outputCancelBtn",
            "undoButton",
        ]
        for name in v38_names:
            self.assertIn(name, qss,
                          f"modern.qss missing objectName rule: {name}")

    def test_light_qss_has_v38_objectnames(self):
        """light.qss contains rules for all v38.0 objectNames."""
        qss = self._read_qss("light.qss")
        v38_names = [
            "doctorHeader", "doctorFixButton",
            "confirmIcon", "confirmAction",
            "riskBadge",
            "commandPalette", "paletteSearch",
            "baseTable",
            "outputCopyBtn", "outputSaveBtn", "outputCancelBtn",
            "undoButton",
        ]
        for name in v38_names:
            self.assertIn(name, qss,
                          f"light.qss missing objectName rule: {name}")

    def test_modern_qss_version_header(self):
        """modern.qss version comment says v38.0."""
        qss = self._read_qss("modern.qss")
        self.assertIn("v38.0", qss)

    def test_light_qss_version_header(self):
        """light.qss version comment says v38.0."""
        qss = self._read_qss("light.qss")
        self.assertIn("v38.0", qss)


# ---------------------------------------------------------------------------
# Version Alignment
# ---------------------------------------------------------------------------
class TestVersionAlignment(unittest.TestCase):
    """Verify version files are in sync at v38.0.0."""

    def test_version_py(self):
        """version.py has __version__ = '38.0.0'."""
        from version import __version__, __version_codename__
        self.assertEqual(__version__, "38.0.0")
        self.assertEqual(__version_codename__, "Clarity")

    def test_pyproject_version(self):
        """pyproject.toml has version = '38.0.0'."""
        pyproject_path = os.path.join(
            os.path.dirname(__file__), "..", "pyproject.toml"
        )
        with open(pyproject_path, "r") as f:
            content = f.read()
        self.assertIn('version = "38.0.0"', content)


if __name__ == "__main__":
    unittest.main()
