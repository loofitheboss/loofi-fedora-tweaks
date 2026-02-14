"""
Extensions Tab — Desktop shell extension management.
Part of v37.0.0 "Pinnacle" — T8.

Provides a UI for browsing, installing, enabling, disabling, and
removing GNOME Shell and KDE Plasma extensions.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget,
    QHeaderView, QAbstractItemView,
)

from ui.base_tab import BaseTab
from core.plugins.metadata import PluginMetadata

logger = logging.getLogger(__name__)

CONTENT_MARGINS = (16, 16, 16, 16)


class ExtensionsTab(BaseTab):
    """Desktop shell extension manager — GNOME and KDE."""

    _METADATA = PluginMetadata(
        id="extensions",
        name="Extensions",
        description="Manage GNOME Shell and KDE Plasma desktop extensions.",
        category="Personalize",
        icon="🧩",
        badge="new",
        order=15,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._extensions_loaded = False
        self.init_ui()

    def init_ui(self):
        """Build the extensions management UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*CONTENT_MARGINS)

        # --- Header ---
        header = QHBoxLayout()
        title = QLabel(self.tr("Desktop Extensions"))
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self.de_label = QLabel()
        self.de_label.setObjectName("deLabel")
        header.addWidget(self.de_label)
        layout.addLayout(header)

        # --- Search + Filter ---
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Search extensions..."))
        self.search_input.textChanged.connect(self._filter_table)
        filter_row.addWidget(self.search_input)

        self.status_filter = QComboBox()
        self.status_filter.addItems([
            self.tr("All"),
            self.tr("Enabled"),
            self.tr("Disabled"),
        ])
        self.status_filter.currentIndexChanged.connect(self._filter_table)
        filter_row.addWidget(self.status_filter)

        self.refresh_btn = QPushButton(self.tr("Refresh"))
        self.refresh_btn.clicked.connect(self._load_extensions)
        filter_row.addWidget(self.refresh_btn)

        layout.addLayout(filter_row)

        # --- Extensions Table ---
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            self.tr("Extension"),
            self.tr("Status"),
            self.tr("Desktop"),
            self.tr("Actions"),
        ])
        h_header = self.table.horizontalHeader()
        assert h_header is not None
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        BaseTab.configure_table(self.table)
        layout.addWidget(self.table)

        # --- Action Buttons ---
        actions = QHBoxLayout()
        self.install_btn = QPushButton(self.tr("Install Extension"))
        self.install_btn.clicked.connect(self._install_extension)
        actions.addWidget(self.install_btn)

        self.remove_btn = QPushButton(self.tr("Remove Selected"))
        self.remove_btn.clicked.connect(self._remove_selected)
        actions.addWidget(self.remove_btn)

        actions.addStretch()
        layout.addLayout(actions)

        # --- Output ---
        self.add_output_section(layout)

        # Detect desktop and load
        self._detect_desktop()

    def showEvent(self, event):
        """Load extensions on first show."""
        super().showEvent(event)
        if not self._extensions_loaded:
            self._load_extensions()
            self._extensions_loaded = True

    def _detect_desktop(self):
        """Detect and display current desktop environment."""
        try:
            from utils.extension_manager import ExtensionManager
            de = ExtensionManager.detect_desktop()
            labels = {"gnome": "GNOME Shell", "kde": "KDE Plasma", "unknown": "Unknown"}
            self.de_label.setText(self.tr("Desktop: {}").format(labels.get(de.value, de.value)))

            if not ExtensionManager.is_supported():
                self.install_btn.setEnabled(False)
                self.remove_btn.setEnabled(False)
                self.append_output(self.tr("Extension management not supported on this desktop.\n"))
        except Exception as e:
            logger.warning("Desktop detection failed: %s", e)
            self.de_label.setText(self.tr("Desktop: Unknown"))

    def _load_extensions(self):
        """Load installed extensions into the table."""
        try:
            from utils.extension_manager import ExtensionManager
            extensions = ExtensionManager.list_installed()
            self.table.setRowCount(len(extensions))

            for row, ext in enumerate(extensions):
                # Name
                self.table.setItem(row, 0, BaseTab.make_table_item(
                    ext.name or ext.uuid
                ))
                # Status
                status = self.tr("Enabled") if ext.enabled else self.tr("Disabled")
                color = "#4caf50" if ext.enabled else "#ff9800"
                self.table.setItem(row, 1, BaseTab.make_table_item(status, color=color))
                # Desktop
                self.table.setItem(row, 2, BaseTab.make_table_item(ext.desktop.upper()))
                # Action buttons
                action_widget = self._create_action_buttons(ext)
                self.table.setCellWidget(row, 3, action_widget)

            if not extensions:
                BaseTab.set_table_empty_state(self.table, self.tr("No extensions found"))

            self.append_output(self.tr("Loaded {} extensions.\n").format(len(extensions)))
        except Exception as e:
            logger.error("Failed to load extensions: %s", e)
            self.append_output(self.tr("[ERROR] Failed to load extensions: {}\n").format(e))

    def _create_action_buttons(self, ext) -> QWidget:
        """Create enable/disable toggle button for an extension row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)

        if ext.enabled:
            btn = QPushButton(self.tr("Disable"))
            btn.clicked.connect(lambda checked, u=ext.uuid: self._toggle_extension(u, False))
        else:
            btn = QPushButton(self.tr("Enable"))
            btn.clicked.connect(lambda checked, u=ext.uuid: self._toggle_extension(u, True))

        layout.addWidget(btn)
        return widget

    def _toggle_extension(self, uuid: str, enable: bool):
        """Enable or disable an extension."""
        try:
            from utils.extension_manager import ExtensionManager
            if enable:
                binary, args, desc = ExtensionManager.enable(uuid)
            else:
                binary, args, desc = ExtensionManager.disable(uuid)
            self.run_command(binary, args, desc)
        except Exception as e:
            self.append_output(f"[ERROR] {e}\n")

    def _install_extension(self):
        """Install an extension by UUID from search input."""
        uuid = self.search_input.text().strip()
        if not uuid:
            self.append_output(self.tr("Enter an extension UUID to install.\n"))
            return
        try:
            from utils.extension_manager import ExtensionManager
            binary, args, desc = ExtensionManager.install(uuid)
            self.run_command(binary, args, desc)
        except Exception as e:
            self.append_output(f"[ERROR] {e}\n")

    def _remove_selected(self):
        """Remove selected extension."""
        row = self.table.currentRow()
        if row < 0:
            self.append_output(self.tr("Select an extension to remove.\n"))
            return
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        try:
            from utils.extension_manager import ExtensionManager
            binary, args, desc = ExtensionManager.remove(name_item.text())
            self.run_command(binary, args, desc)
        except Exception as e:
            self.append_output(f"[ERROR] {e}\n")

    def _filter_table(self):
        """Filter table rows by search text and status."""
        query = self.search_input.text().lower()
        status_idx = self.status_filter.currentIndex()

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            status_item = self.table.item(row, 1)
            if not name_item:
                continue

            name_match = query in name_item.text().lower()
            status_match = True
            if status_idx == 1 and status_item:
                status_match = "enabled" in status_item.text().lower()
            elif status_idx == 2 and status_item:
                status_match = "disabled" in status_item.text().lower()

            self.table.setRowHidden(row, not (name_match and status_match))
