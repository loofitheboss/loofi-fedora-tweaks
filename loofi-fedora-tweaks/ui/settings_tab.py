"""
Settings Tab - User-facing preferences UI.
Part of v13.5 "UX Polish" update.

Three sub-tabs inside an internal QTabWidget:
  Appearance  - theme selector, follow-system toggle
  Behavior    - startup, notifications, confirm-dangerous
  Advanced    - reset-to-defaults, log-level
"""

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from utils.settings import SettingsManager

from ui.tab_utils import CONTENT_MARGINS, configure_top_tabs


class SettingsTab(QWidget, PluginInterface):
    """Application settings tab with Appearance / Behavior / Advanced sub-tabs."""

    _METADATA = PluginMetadata(
        id="settings",
        name="Settings",
        description="Configure appearance, behavior, and advanced application options.",
        category="Appearance",
        icon="⚙️",
        badge="",
        order=100,
    )

    def __init__(self):
        super().__init__()
        self._main_window = None
        self._mgr = SettingsManager.instance()
        self._ui_initialized = False
        # Guard against headless/non-Qt execution paths that import tabs without a QApplication.
        if QApplication.instance() is not None:
            self._init_ui()

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def set_context(self, context: dict) -> None:
        self._main_window = context.get("main_window")
        if not self._ui_initialized:
            self._init_ui()

    # ------------------------------------------------------------------ UI --

    def _init_ui(self):
        if self._ui_initialized:
            return
        self._ui_initialized = True

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
        header.setObjectName("settingsHeader")
        layout.addWidget(header)

        desc = QLabel(self.tr(
            "Configure appearance, behavior, and advanced options. "
            "Changes are saved automatically."
        ))
        desc.setWordWrap(True)
        desc.setObjectName("settingsDesc")
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

        # Help text (v47.0)
        help_label = QLabel(self.tr(
            "Choose your visual theme. 'Follow system theme' auto-detects your desktop preference."
        ))
        help_label.setWordWrap(True)
        help_label.setObjectName("settingsHelpText")
        form.addRow(help_label)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName(self.tr("Theme selector"))
        self.theme_combo.addItems(["dark", "light", "highcontrast"])
        self.theme_combo.setCurrentText(self._mgr.get("theme"))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        form.addRow(self.tr("Theme:"), self.theme_combo)

        # Follow system theme
        self.follow_system_cb = QCheckBox(self.tr("Follow system theme"))
        self.follow_system_cb.setAccessibleName(self.tr("Follow system theme"))
        self.follow_system_cb.setChecked(self._mgr.get("follow_system_theme"))
        self.follow_system_cb.toggled.connect(self._on_follow_system_toggled)
        form.addRow("", self.follow_system_cb)

        # v29.0: Reset appearance to defaults
        reset_appearance_btn = QPushButton(self.tr("↩ Reset Appearance"))
        reset_appearance_btn.setAccessibleName(self.tr("Reset Appearance"))
        reset_appearance_btn.setToolTip(self.tr("Reset theme settings to defaults"))
        reset_appearance_btn.clicked.connect(self._reset_appearance)
        form.addRow("", reset_appearance_btn)

        return page

    # ----------------------------------------------------------- Behavior --

    def _build_behavior_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setSpacing(12)

        # Experience Level selector (v47.0)
        from utils.experience_level import ExperienceLevelManager
        self.experience_combo = QComboBox()
        self.experience_combo.setAccessibleName(self.tr("Experience level"))
        self.experience_combo.addItems(["Beginner", "Intermediate", "Advanced"])
        current_level = ExperienceLevelManager.get_level()
        level_index = {"beginner": 0, "intermediate": 1, "advanced": 2}
        self.experience_combo.setCurrentIndex(level_index.get(current_level.value, 0))
        self.experience_combo.currentIndexChanged.connect(self._on_experience_level_changed)
        form.addRow(self.tr("Experience Level:"), self.experience_combo)

        self._experience_desc = QLabel(self._experience_description(current_level))
        self._experience_desc.setWordWrap(True)
        self._experience_desc.setObjectName("settingsHelpText")
        form.addRow("", self._experience_desc)

        self.start_minimized_cb = QCheckBox(self.tr("Start minimized to tray"))
        self.start_minimized_cb.setAccessibleName(self.tr("Start minimized to tray"))
        self.start_minimized_cb.setChecked(self._mgr.get("start_minimized"))
        self.start_minimized_cb.toggled.connect(
            lambda v: self._toggle_setting("start_minimized", v)
        )
        form.addRow("", self.start_minimized_cb)

        self.notifications_cb = QCheckBox(self.tr("Show desktop notifications"))
        self.notifications_cb.setAccessibleName(self.tr("Show desktop notifications"))
        self.notifications_cb.setChecked(self._mgr.get("show_notifications"))
        self.notifications_cb.toggled.connect(
            lambda v: self._toggle_setting("show_notifications", v)
        )
        form.addRow("", self.notifications_cb)

        self.confirm_cb = QCheckBox(self.tr("Confirm dangerous actions"))
        self.confirm_cb.setAccessibleName(self.tr("Confirm dangerous actions"))
        self.confirm_cb.setChecked(self._mgr.get("confirm_dangerous_actions"))
        self.confirm_cb.toggled.connect(
            lambda v: self._toggle_setting("confirm_dangerous_actions", v)
        )
        form.addRow("", self.confirm_cb)

        self.restore_tab_cb = QCheckBox(self.tr("Restore last active tab on start"))
        self.restore_tab_cb.setAccessibleName(self.tr("Restore last active tab on start"))
        self.restore_tab_cb.setChecked(self._mgr.get("restore_last_tab"))
        self.restore_tab_cb.toggled.connect(
            lambda v: self._toggle_setting("restore_last_tab", v)
        )
        form.addRow("", self.restore_tab_cb)

        # v29.0: Reset behavior to defaults
        reset_behavior_btn = QPushButton(self.tr("↩ Reset Behavior"))
        reset_behavior_btn.setAccessibleName(self.tr("Reset Behavior"))
        reset_behavior_btn.setToolTip(self.tr("Reset behavior settings to defaults"))
        reset_behavior_btn.clicked.connect(self._reset_behavior)
        form.addRow("", reset_behavior_btn)

        return page

    # ----------------------------------------------------------- Advanced --

    def _build_advanced_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Help text (v47.0)
        help_label = QLabel(self.tr(
            "Advanced settings for debugging and maintenance. "
            "Only change these if you know what you're doing."
        ))
        help_label.setWordWrap(True)
        help_label.setObjectName("settingsHelpText")
        layout.addWidget(help_label)

        # Log level
        log_group = QGroupBox(self.tr("Logging"))
        log_form = QFormLayout(log_group)
        self.log_combo = QComboBox()
        self.log_combo.setAccessibleName(self.tr("Log level selector"))
        self.log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_combo.setCurrentText(self._mgr.get("log_level"))
        self.log_combo.currentTextChanged.connect(self._on_log_level_changed)
        log_form.addRow(self.tr("Log level:"), self.log_combo)
        layout.addWidget(log_group)

        # Update checking
        self.updates_cb = QCheckBox(self.tr("Check for updates on start"))
        self.updates_cb.setAccessibleName(self.tr("Check for updates on start"))
        self.updates_cb.setChecked(self._mgr.get("check_updates_on_start"))
        self.updates_cb.toggled.connect(
            lambda v: self._toggle_setting("check_updates_on_start", v)
        )
        layout.addWidget(self.updates_cb)

        # Reset
        reset_group = QGroupBox(self.tr("Reset"))
        reset_layout = QVBoxLayout(reset_group)
        reset_btn = QPushButton(self.tr("Reset All Settings to Defaults"))
        reset_btn.setAccessibleName(self.tr("Reset All Settings to Defaults"))
        reset_btn.setObjectName("dangerAction")
        reset_btn.clicked.connect(self._on_reset)
        reset_layout.addWidget(reset_btn)
        layout.addWidget(reset_group)

        layout.addStretch()
        return page

    # ------------------------------------------------------------ Slots --

    def _experience_description(self, level) -> str:
        """Return a user-friendly description for the experience level."""
        from utils.experience_level import ExperienceLevel
        descriptions = {
            ExperienceLevel.BEGINNER: self.tr(
                "Simplified view with essential tools — ideal for new Fedora users."
            ),
            ExperienceLevel.INTERMEDIATE: self.tr(
                "Core tools plus development and customization options."
            ),
            ExperienceLevel.ADVANCED: self.tr(
                "Full access to all tabs and features."
            ),
        }
        return descriptions.get(level, "")

    def _on_experience_level_changed(self, index: int):
        """Handle experience level combo box change."""
        from utils.experience_level import ExperienceLevel, ExperienceLevelManager
        level_map = {0: ExperienceLevel.BEGINNER, 1: ExperienceLevel.INTERMEDIATE, 2: ExperienceLevel.ADVANCED}
        level = level_map.get(index, ExperienceLevel.BEGINNER)
        ExperienceLevelManager.set_level(level)
        self._experience_desc.setText(self._experience_description(level))

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

    # ---------------------------------------- v29.0 Reset per group --

    def _reset_appearance(self):
        """Reset appearance settings to defaults."""
        self._mgr.reset_group(["theme", "follow_system_theme"])
        self.theme_combo.setCurrentText(self._mgr.get("theme"))
        self.follow_system_cb.setChecked(self._mgr.get("follow_system_theme"))
        if self._main_window and hasattr(self._main_window, "load_theme"):
            self._main_window.load_theme(self._mgr.get("theme"))

    def _reset_behavior(self):
        """Reset behavior settings to defaults."""
        self._mgr.reset_group([
            "start_minimized", "show_notifications",
            "confirm_dangerous_actions", "restore_last_tab", "last_tab_index",
        ])
        self.start_minimized_cb.setChecked(self._mgr.get("start_minimized"))
        self.notifications_cb.setChecked(self._mgr.get("show_notifications"))
        self.confirm_cb.setChecked(self._mgr.get("confirm_dangerous_actions"))
        self.restore_tab_cb.setChecked(self._mgr.get("restore_last_tab"))
