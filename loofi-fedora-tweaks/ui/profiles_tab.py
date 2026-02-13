"""
Profiles Tab - System profile quick-switch UI.
Part of v13.0 "Nexus Update".

Provides:
- Profile cards grid showing built-in and custom profiles
- Active profile indicator at the top
- Create Custom Profile dialog
- Apply profile with one click
- Output log for operation feedback
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QGridLayout, QTextEdit, QScrollArea,
    QFrame, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QComboBox, QFileDialog,
)

from ui.tab_utils import CONTENT_MARGINS
from utils.profiles import ProfileManager
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class ProfilesTab(QWidget, PluginInterface):
    """System Profiles tab for quick-switching system configurations."""

    _METADATA = PluginMetadata(
        id="profiles",
        name="Profiles",
        description="System profile quick-switch for applying and managing configuration profiles.",
        category="Personalize",
        icon="👤",
        badge="",
        order=20,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the UI layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("System Profiles"))
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #a277ff;"
        )
        layout.addWidget(header)

        description = QLabel(self.tr(
            "Quick-switch between optimised system configurations. "
            "Select a profile to adjust CPU governor, services, "
            "notifications, and more."
        ))
        description.setWordWrap(True)
        description.setStyleSheet("color: #9da7bf; font-size: 12px;")
        layout.addWidget(description)

        # Active profile indicator
        self.active_label = QLabel(self.tr("Active profile: None"))
        self.active_label.setStyleSheet(
            "font-size: 13px; padding: 8px; background: #0b0e14; "
            "border-radius: 4px; color: #e6edf3;"
        )
        layout.addWidget(self.active_label)

        # Profile cards grid
        cards_group = QGroupBox(self.tr("Available Profiles"))
        self.cards_layout = QGridLayout(cards_group)
        self.cards_layout.setSpacing(10)
        layout.addWidget(cards_group)

        # Action buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(self._refresh_profiles)
        btn_layout.addWidget(refresh_btn)

        create_btn = QPushButton(self.tr("Create Custom Profile"))
        create_btn.clicked.connect(self._show_create_dialog)
        btn_layout.addWidget(create_btn)

        capture_btn = QPushButton(self.tr("Capture Current State"))
        capture_btn.clicked.connect(self._capture_current)
        btn_layout.addWidget(capture_btn)

        export_all_btn = QPushButton(self.tr("Export All"))
        export_all_btn.clicked.connect(self._export_all_profiles)
        btn_layout.addWidget(export_all_btn)

        import_all_btn = QPushButton(self.tr("Import Bundle"))
        import_all_btn.clicked.connect(self._import_bundle)
        btn_layout.addWidget(import_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Output log
        log_group = QGroupBox(self.tr("Output Log"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        layout.addWidget(log_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*CONTENT_MARGINS)
        main_layout.addWidget(scroll)

        # Initial data load
        self._refresh_profiles()

    # ==================== PROFILE CARDS ====================

    def _refresh_profiles(self):
        """Reload profile cards and the active profile indicator."""
        # Update active profile label
        active = ProfileManager.get_active_profile()
        if active:
            profile = ProfileManager.get_profile(active)
            display = profile.get("name", active) if profile else active
            self.active_label.setText(
                self.tr("Active profile: {}").format(display)
            )
        else:
            self.active_label.setText(self.tr("Active profile: None"))

        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Populate cards
        profiles = ProfileManager.list_profiles()
        for index, profile in enumerate(profiles):
            card = self._create_profile_card(profile)
            row = index // 3
            col = index % 3
            self.cards_layout.addWidget(card, row, col)

        self.log(self.tr("Profiles refreshed ({} available).").format(len(profiles)))

    def _create_profile_card(self, profile: dict) -> QFrame:
        """Create a visual card widget for a single profile."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame { background: #0b0e14; border-radius: 8px; padding: 10px; }"
        )

        layout = QVBoxLayout(card)

        # Icon + Name
        title = QLabel(f"{profile.get('icon', '')}  {profile.get('name', 'Unknown')}")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)

        # Description
        desc = QLabel(profile.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf; font-size: 11px;")
        layout.addWidget(desc)

        # Type badge
        badge_text = self.tr("Built-in") if profile.get("builtin") else self.tr("Custom")
        badge = QLabel(badge_text)
        badge.setStyleSheet("color: #a277ff; font-size: 10px;")
        layout.addWidget(badge)

        # Buttons
        btn_layout = QHBoxLayout()

        apply_btn = QPushButton(self.tr("Apply"))
        profile_key = profile.get("key", "")
        apply_btn.clicked.connect(lambda checked, k=profile_key: self._apply_profile(k))
        btn_layout.addWidget(apply_btn)

        if not profile.get("builtin"):
            delete_btn = QPushButton(self.tr("Delete"))
            delete_btn.clicked.connect(
                lambda checked, k=profile_key: self._delete_profile(k)
            )
            btn_layout.addWidget(delete_btn)

        export_btn = QPushButton(self.tr("Export"))
        export_btn.clicked.connect(
            lambda checked, k=profile_key: self._export_profile(k)
        )
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return card

    # ==================== SLOTS ====================

    def _apply_profile(self, name: str):
        """Apply the selected profile."""
        profile = ProfileManager.get_profile(name)
        if not profile:
            self.log(self.tr("Profile '{}' not found.").format(name))
            return

        reply = QMessageBox.question(
            self,
            self.tr("Apply Profile"),
            self.tr("Apply the '{}' profile? This will change system settings.").format(
                profile.get("name", name)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log(self.tr("Applying profile '{}'...").format(profile.get("name", name)))
        result = ProfileManager.apply_profile(name, create_snapshot=True)
        self.log(result.message)
        self._refresh_profiles()

    def _delete_profile(self, name: str):
        """Delete a custom profile with confirmation."""
        reply = QMessageBox.question(
            self,
            self.tr("Delete Profile"),
            self.tr("Delete custom profile '{}'?").format(name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        result = ProfileManager.delete_custom_profile(name)
        self.log(result.message)
        if result.success:
            self._refresh_profiles()

    def _export_profile(self, name: str):
        """Export a single profile to JSON."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Profile"),
            f"{name}.json",
            self.tr("JSON Files (*.json)"),
        )
        if not path:
            return

        result = ProfileManager.export_profile_json(name, path)
        self.log(result.message)

    def _export_all_profiles(self):
        """Export all custom profiles to a bundle file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Profile Bundle"),
            "profiles-bundle.json",
            self.tr("JSON Files (*.json)"),
        )
        if not path:
            return

        result = ProfileManager.export_bundle_json(path, include_builtins=False)
        self.log(result.message)

    def _import_bundle(self):
        """Import profiles from a JSON file (single or bundle)."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Profile JSON"),
            "",
            self.tr("JSON Files (*.json)"),
        )
        if not path:
            return

        # Try bundle first, then fall back to single profile import.
        result = ProfileManager.import_bundle_json(path, overwrite=False)
        if not result.success:
            result = ProfileManager.import_profile_json(path, overwrite=False)

        self.log(result.message)
        if result.success:
            self._refresh_profiles()

    def _show_create_dialog(self):
        """Open a dialog to create a custom profile."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Create Custom Profile"))
        dialog.setMinimumWidth(400)
        form = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText(self.tr("My Custom Profile"))
        form.addRow(self.tr("Name:"), name_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText(self.tr("Description of this profile"))
        form.addRow(self.tr("Description:"), desc_edit)

        governor_combo = QComboBox()
        governor_combo.addItems(["performance", "powersave", "schedutil", "ondemand", "conservative"])
        form.addRow(self.tr("CPU Governor:"), governor_combo)

        compositor_combo = QComboBox()
        compositor_combo.addItems(["enabled", "disabled", "reduced"])
        form.addRow(self.tr("Compositor:"), compositor_combo)

        notif_combo = QComboBox()
        notif_combo.addItems(["all", "critical", "dnd"])
        form.addRow(self.tr("Notifications:"), notif_combo)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton(self.tr("Save"))
        cancel_btn = QPushButton(self.tr("Cancel"))
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        form.addRow(btn_layout)

        cancel_btn.clicked.connect(dialog.reject)

        def do_save():
            pname = name_edit.text().strip()
            if not pname:
                QMessageBox.warning(
                    dialog, self.tr("Error"),
                    self.tr("Please enter a profile name."),
                )
                return
            settings = {
                "description": desc_edit.text().strip(),
                "governor": governor_combo.currentText(),
                "compositor": compositor_combo.currentText(),
                "notifications": notif_combo.currentText(),
            }
            result = ProfileManager.create_custom_profile(pname, settings)
            self.log(result.message)
            if result.success:
                dialog.accept()
                self._refresh_profiles()
            else:
                QMessageBox.warning(
                    dialog, self.tr("Error"), result.message,
                )

        save_btn.clicked.connect(do_save)
        dialog.exec()

    def _capture_current(self):
        """Capture the current system state as a profile."""
        name, ok = self._prompt_for_name()
        if not ok or not name:
            return

        self.log(self.tr("Capturing current system state..."))
        result = ProfileManager.capture_current_as_profile(name)
        self.log(result.message)
        if result.success:
            self._refresh_profiles()

    def _prompt_for_name(self):
        """Quick input dialog for profile name."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Profile Name"))
        layout = QVBoxLayout(dialog)

        label = QLabel(self.tr("Enter a name for the captured profile:"))
        layout.addWidget(label)

        name_edit = QLineEdit()
        layout.addWidget(name_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(self.tr("OK"))
        cancel_btn = QPushButton(self.tr("Cancel"))
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        cancel_btn.clicked.connect(dialog.reject)
        ok_btn.clicked.connect(dialog.accept)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return name_edit.text().strip(), True
        return "", False

    # ==================== LOG HELPER ====================

    def log(self, message: str):
        """Append a message to the output log."""
        self.output_text.append(message)
