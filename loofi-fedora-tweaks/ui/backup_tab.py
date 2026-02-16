"""
Backup Tab — Guided system backup wizard.
Part of v37.0.0 "Pinnacle" — T9.

Multi-step wizard flow using QStackedWidget:
Step 1: Detect backup tool
Step 2: Configure snapshot
Step 3: Create snapshot
Step 4: View results + existing snapshots
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QStackedWidget, QGroupBox, QTableWidget, QHeaderView,
    QAbstractItemView,
)

from ui.base_tab import BaseTab
from core.plugins.metadata import PluginMetadata

logger = logging.getLogger(__name__)

CONTENT_MARGINS = (16, 16, 16, 16)


class BackupTab(BaseTab):
    """System backup wizard with step-by-step flow."""

    _METADATA = PluginMetadata(
        id="backup",
        name="Backup",
        description="Create, manage, and restore system snapshots via Timeshift or Snapper.",
        category="Maintain",
        icon="💾",
        badge="new",
        order=15,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._loaded = False
        self.init_ui()

    def init_ui(self):
        """Build the backup wizard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*CONTENT_MARGINS)

        # --- Header ---
        title = QLabel(self.tr("System Backup Wizard"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # --- Wizard Stack ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Page 0: Detection
        self.stack.addWidget(self._create_detect_page())
        # Page 1: Configure
        self.stack.addWidget(self._create_configure_page())
        # Page 2: Snapshot list + manage
        self.stack.addWidget(self._create_manage_page())

        # --- Navigation ---
        nav = QHBoxLayout()
        self.back_btn = QPushButton(self.tr("← Back"))
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setEnabled(False)
        nav.addWidget(self.back_btn)

        nav.addStretch()

        self.next_btn = QPushButton(self.tr("Next →"))
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        # --- Output ---
        self.add_output_section(layout)

    # ================================================================
    # PAGES
    # ================================================================

    def _create_detect_page(self) -> QWidget:
        """Page 0: Detect available backup tools."""
        page = QWidget()
        layout = QVBoxLayout(page)

        info = QLabel(self.tr(
            "This wizard helps you create and manage system snapshots.\n"
            "Supported tools: Timeshift, Snapper."
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        # Tool status
        self.tool_status = QLabel()
        self.tool_status.setObjectName("toolStatus")
        layout.addWidget(self.tool_status)

        self.detect_btn = QPushButton(self.tr("Detect Backup Tools"))
        self.detect_btn.clicked.connect(self._detect_tools)
        layout.addWidget(self.detect_btn)

        layout.addStretch()
        return page

    def _create_configure_page(self) -> QWidget:
        """Page 1: Configure snapshot creation."""
        page = QWidget()
        layout = QVBoxLayout(page)

        group = QGroupBox(self.tr("Create Snapshot"))
        group_layout = QVBoxLayout(group)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel(self.tr("Description:")))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(self.tr("Loofi backup"))
        self.desc_input.setText("Loofi backup")
        desc_row.addWidget(self.desc_input)
        group_layout.addLayout(desc_row)

        self.tool_info = QLabel()
        group_layout.addWidget(self.tool_info)

        self.create_btn = QPushButton(self.tr("Create Snapshot"))
        self.create_btn.clicked.connect(self._create_snapshot)
        group_layout.addWidget(self.create_btn)

        layout.addWidget(group)
        layout.addStretch()
        return page

    def _create_manage_page(self) -> QWidget:
        """Page 2: List and manage existing snapshots."""
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QHBoxLayout()
        header.addWidget(QLabel(self.tr("Existing Snapshots")))
        header.addStretch()

        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(self._load_snapshots)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Snapshot table
        self.snap_table = QTableWidget(0, 4)
        self.snap_table.setHorizontalHeaderLabels([
            self.tr("ID"),
            self.tr("Date"),
            self.tr("Description"),
            self.tr("Tool"),
        ])
        h_header = self.snap_table.horizontalHeader()
        assert h_header is not None
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.snap_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        BaseTab.configure_table(self.snap_table)
        layout.addWidget(self.snap_table)

        # Action buttons
        actions = QHBoxLayout()
        self.restore_btn = QPushButton(self.tr("Restore Selected"))
        self.restore_btn.clicked.connect(self._restore_selected)
        actions.addWidget(self.restore_btn)

        self.delete_btn = QPushButton(self.tr("Delete Selected"))
        self.delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(self.delete_btn)

        actions.addStretch()
        layout.addLayout(actions)

        return page

    # ================================================================
    # NAVIGATION
    # ================================================================

    def _go_back(self):
        """Go to previous wizard page."""
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
        self.back_btn.setEnabled(self.stack.currentIndex() > 0)
        self.next_btn.setText(
            self.tr("Finish") if self.stack.currentIndex() == self.stack.count() - 1
            else self.tr("Next →")
        )

    def _go_next(self):
        """Go to next wizard page."""
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            if idx == 0:
                self._setup_configure_page()
            if idx + 1 == 2:
                self._load_snapshots()
        self.back_btn.setEnabled(self.stack.currentIndex() > 0)
        self.next_btn.setText(
            self.tr("Finish") if self.stack.currentIndex() == self.stack.count() - 1
            else self.tr("Next →")
        )

    def showEvent(self, event):
        """Auto-detect on first show."""
        super().showEvent(event)
        if not self._loaded:
            self._detect_tools()
            self._loaded = True

    # ================================================================
    # ACTIONS
    # ================================================================

    def _detect_tools(self):
        """Detect available backup tools."""
        try:
            from utils.backup_wizard import BackupWizard
            tool = BackupWizard.detect_backup_tool()
            available = BackupWizard.get_available_tools()

            if tool == "none":
                self.tool_status.setText(self.tr(
                    "⚠ No backup tool found.\n"
                    "Install timeshift or snapper:\n"
                    "  sudo dnf install timeshift\n"
                    "  sudo dnf install snapper"
                ))
                self.next_btn.setEnabled(False)
            else:
                tools_str = ", ".join(available)
                self.tool_status.setText(self.tr(
                    "✓ Backup tool detected: {}\n"
                    "Available tools: {}"
                ).format(tool, tools_str))
                self.next_btn.setEnabled(True)
                self._detected_tool = tool

            self.append_output(self.tr("Tool detection complete: {}\n").format(tool))
        except (RuntimeError, OSError, ValueError) as e:
            logger.error("Tool detection failed: %s", e)
            self.tool_status.setText(self.tr("Detection failed: {}").format(e))

    def _setup_configure_page(self):
        """Prepare configure page with detected tool info."""
        tool = getattr(self, "_detected_tool", "none")
        self.tool_info.setText(self.tr("Using backup tool: {}").format(tool))

    def _create_snapshot(self):
        """Create a system snapshot."""
        try:
            from utils.backup_wizard import BackupWizard
            desc = self.desc_input.text().strip() or "Loofi backup"
            tool = getattr(self, "_detected_tool", None)
            binary, args, description = BackupWizard.create_snapshot(tool=tool, description=desc)
            self.run_command(binary, args, description)
        except (RuntimeError, OSError, ValueError) as e:
            self.append_output(f"[ERROR] {e}\n")

    def _load_snapshots(self):
        """Load existing snapshots into the table."""
        try:
            from utils.backup_wizard import BackupWizard
            tool = getattr(self, "_detected_tool", None)
            snapshots = BackupWizard.list_snapshots(tool=tool)
            self.snap_table.setRowCount(len(snapshots))

            for row, snap in enumerate(snapshots):
                self.snap_table.setItem(row, 0, BaseTab.make_table_item(snap.id))
                self.snap_table.setItem(row, 1, BaseTab.make_table_item(snap.date))
                self.snap_table.setItem(row, 2, BaseTab.make_table_item(snap.description))
                self.snap_table.setItem(row, 3, BaseTab.make_table_item(snap.tool))

            if not snapshots:
                BaseTab.set_table_empty_state(self.snap_table, self.tr("No snapshots found"))

            self.append_output(self.tr("Found {} snapshots.\n").format(len(snapshots)))
        except (RuntimeError, OSError, ValueError) as e:
            logger.error("Failed to load snapshots: %s", e)
            self.append_output(f"[ERROR] {e}\n")

    def _restore_selected(self):
        """Restore selected snapshot."""
        row = self.snap_table.currentRow()
        if row < 0:
            self.append_output(self.tr("Select a snapshot to restore.\n"))
            return

        snap_id = self.snap_table.item(row, 0)
        tool_item = self.snap_table.item(row, 3)
        if not snap_id:
            return

        try:
            from utils.backup_wizard import BackupWizard
            tool = tool_item.text() if tool_item else None
            binary, args, desc = BackupWizard.restore_snapshot(snap_id.text(), tool=tool)
            self.run_command(binary, args, desc)
        except (RuntimeError, OSError, ValueError) as e:
            self.append_output(f"[ERROR] {e}\n")

    def _delete_selected(self):
        """Delete selected snapshot."""
        row = self.snap_table.currentRow()
        if row < 0:
            self.append_output(self.tr("Select a snapshot to delete.\n"))
            return

        snap_id = self.snap_table.item(row, 0)
        tool_item = self.snap_table.item(row, 3)
        if not snap_id:
            return

        try:
            from utils.backup_wizard import BackupWizard
            tool = tool_item.text() if tool_item else None
            binary, args, desc = BackupWizard.delete_snapshot(snap_id.text(), tool=tool)
            self.run_command(binary, args, desc)
        except (RuntimeError, OSError, ValueError) as e:
            self.append_output(f"[ERROR] {e}\n")
