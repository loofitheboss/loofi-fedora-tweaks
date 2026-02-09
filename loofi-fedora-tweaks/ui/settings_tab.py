"""
Settings Tab - User-facing preferences UI.
Part of v13.5 "UX Polish" update.

Three sub-tabs inside an internal QTabWidget:
  Appearance  - theme selector, follow-system toggle
  Behavior    - startup, notifications, confirm-dangerous
  Advanced    - reset-to-defaults, log-level
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox,
    QLabel, QPushButton, QComboBox, QCheckBox, QFormLayout,
    QScrollArea, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt

from utils.settings import SettingsManager
from ui.tab_utils import configure_top_tabs, CONTENT_MARGINS


class SettingsTab(QWidget):
    """Application settings tab with Appearance / Behavior / Advanced sub-tabs."""

    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._mgr = SettingsManager.instance()
        self._init_ui()

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(*CONTENT_MARGINS)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("Settings"))
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #a277ff;"
        )
        layout.addWidget(header)

        desc = QLabel(self.tr(
            "Configure appearance, behavior, and advanced options. "
            "Changes are saved automatically."
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc)

        # Internal sub-tabs
        tabs = QTabWidget()
        configure_top_tabs(tabs)
        tabs.addTab(self._build_appearance_tab(), self.tr("Appearance"))
        tabs.addTab(self._build_behavior_tab(), self.tr("Behavior"))
        tabs.addTab(self._build_advanced_tab(), self.tr("Advanced"))
        layout.addWidget(tabs)

        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    # --------------------------------------------------------- Appearance --

    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setSpacing(12)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self._mgr.get("theme"))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        form.addRow(self.tr("Theme:"), self.theme_combo)

        # Follow system theme
        self.follow_system_cb = QCheckBox(self.tr("Follow system theme"))
        self.follow_system_cb.setChecked(self._mgr.get("follow_system_theme"))
        self.follow_system_cb.toggled.connect(self._on_follow_system_toggled)
        form.addRow("", self.follow_system_cb)

        return page

    # ----------------------------------------------------------- Behavior --

    def _build_behavior_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setSpacing(12)

        self.start_minimized_cb = QCheckBox(self.tr("Start minimized to tray"))
        self.start_minimized_cb.setChecked(self._mgr.get("start_minimized"))
        self.start_minimized_cb.toggled.connect(
            lambda v: self._toggle_setting("start_minimized", v)
        )
        form.addRow("", self.start_minimized_cb)

        self.notifications_cb = QCheckBox(self.tr("Show desktop notifications"))
        self.notifications_cb.setChecked(self._mgr.get("show_notifications"))
        self.notifications_cb.toggled.connect(
            lambda v: self._toggle_setting("show_notifications", v)
        )
        form.addRow("", self.notifications_cb)

        self.confirm_cb = QCheckBox(self.tr("Confirm dangerous actions"))
        self.confirm_cb.setChecked(self._mgr.get("confirm_dangerous_actions"))
        self.confirm_cb.toggled.connect(
            lambda v: self._toggle_setting("confirm_dangerous_actions", v)
        )
        form.addRow("", self.confirm_cb)

        self.restore_tab_cb = QCheckBox(self.tr("Restore last active tab on start"))
        self.restore_tab_cb.setChecked(self._mgr.get("restore_last_tab"))
        self.restore_tab_cb.toggled.connect(
            lambda v: self._toggle_setting("restore_last_tab", v)
        )
        form.addRow("", self.restore_tab_cb)

        return page

    # ----------------------------------------------------------- Advanced --

    def _build_advanced_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Log level
        log_group = QGroupBox(self.tr("Logging"))
        log_form = QFormLayout(log_group)
        self.log_combo = QComboBox()
        self.log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_combo.setCurrentText(self._mgr.get("log_level"))
        self.log_combo.currentTextChanged.connect(self._on_log_level_changed)
        log_form.addRow(self.tr("Log level:"), self.log_combo)
        layout.addWidget(log_group)

        # Update checking
        self.updates_cb = QCheckBox(self.tr("Check for updates on start"))
        self.updates_cb.setChecked(self._mgr.get("check_updates_on_start"))
        self.updates_cb.toggled.connect(
            lambda v: self._toggle_setting("check_updates_on_start", v)
        )
        layout.addWidget(self.updates_cb)

        # Reset
        reset_group = QGroupBox(self.tr("Reset"))
        reset_layout = QVBoxLayout(reset_group)
        reset_btn = QPushButton(self.tr("Reset All Settings to Defaults"))
        reset_btn.setObjectName("dangerAction")
        reset_btn.clicked.connect(self._on_reset)
        reset_layout.addWidget(reset_btn)
        layout.addWidget(reset_group)

        layout.addStretch()
        return page

    # ------------------------------------------------------------ Slots --

    def _on_theme_changed(self, theme_name: str):
        self._mgr.set("theme", theme_name)
        self._mgr.save()
        if self._main_window and hasattr(self._main_window, "load_theme"):
            self._main_window.load_theme(theme_name)

    def _on_follow_system_toggled(self, checked: bool):
        self._mgr.set("follow_system_theme", checked)
        self._mgr.save()
        if checked and self._main_window and hasattr(self._main_window, "detect_system_theme"):
            system_theme = self._main_window.detect_system_theme()
            self.theme_combo.setCurrentText(system_theme)

    def _toggle_setting(self, key: str, value: bool):
        self._mgr.set(key, value)
        self._mgr.save()

    def _on_log_level_changed(self, level: str):
        self._mgr.set("log_level", level)
        self._mgr.save()

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            self.tr("Reset Settings"),
            self.tr(
                "This will restore all settings to their default values. Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._mgr.reset()

        # Refresh widgets to reflect defaults
        self.theme_combo.setCurrentText(self._mgr.get("theme"))
        self.follow_system_cb.setChecked(self._mgr.get("follow_system_theme"))
        self.start_minimized_cb.setChecked(self._mgr.get("start_minimized"))
        self.notifications_cb.setChecked(self._mgr.get("show_notifications"))
        self.confirm_cb.setChecked(self._mgr.get("confirm_dangerous_actions"))
        self.restore_tab_cb.setChecked(self._mgr.get("restore_last_tab"))
        self.log_combo.setCurrentText(self._mgr.get("log_level"))
        self.updates_cb.setChecked(self._mgr.get("check_updates_on_start"))

        if self._main_window and hasattr(self._main_window, "load_theme"):
            self._main_window.load_theme(self._mgr.get("theme"))
