"""
Snapshot Tab — GUI for the Snapshot Timeline manager.
Part of v17.0 "Atlas".

Unified snapshot management across Timeshift, Snapper, and Btrfs backends.
Uses SnapshotManager from utils/snapshot_manager.py.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTableWidget,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QGridLayout,
    QWidget,
)
from PyQt6.QtCore import QTimer
from ui.base_tab import BaseTab
from utils.snapshot_manager import SnapshotManager
from datetime import datetime
from core.plugins.metadata import PluginMetadata


class SnapshotTab(BaseTab):
    """Snapshot timeline management tab."""

    _METADATA = PluginMetadata(
        id="snapshots",
        name="Snapshots",
        description="Unified snapshot management across Timeshift, Snapper, and Btrfs backends.",
        category="Packages",
        icon="📸",
        badge="advanced",
        order=30,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.init_ui()
        QTimer.singleShot(200, self._refresh_backends)

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self.tr("System Snapshots"))
        header.setObjectName("snapHeader")
        layout.addWidget(header)

        # ==================== Backend Status ====================
        backend_group = QGroupBox(self.tr("Backends"))
        bg_layout = QGridLayout()
        backend_group.setLayout(bg_layout)

        self.backend_labels: list = []
        for i, name in enumerate(["Snapper", "Timeshift", "Btrfs"]):
            label = QLabel(f"{name}:")
            status = QLabel("—")
            bg_layout.addWidget(label, i, 0)
            bg_layout.addWidget(status, i, 1)
            self.backend_labels.append((name.lower(), status))

        layout.addWidget(backend_group)

        # ==================== Actions ====================
        action_layout = QHBoxLayout()

        btn_create = QPushButton(self.tr("📸 Create Snapshot"))
        btn_create.setAccessibleName(self.tr("Create Snapshot"))
        btn_create.clicked.connect(self._create_snapshot)
        action_layout.addWidget(btn_create)

        btn_delete = QPushButton(self.tr("🗑️ Delete Selected"))
        btn_delete.setAccessibleName(self.tr("Delete Selected"))
        btn_delete.clicked.connect(self._delete_snapshot)
        action_layout.addWidget(btn_delete)

        btn_refresh = QPushButton(self.tr("🔄 Refresh"))
        btn_refresh.setAccessibleName(self.tr("Refresh"))
        btn_refresh.clicked.connect(self._refresh_all)
        action_layout.addWidget(btn_refresh)

        layout.addLayout(action_layout)

        # ==================== Snapshot Timeline ====================
        snap_group = QGroupBox(self.tr("Snapshot Timeline"))
        sl_layout = QVBoxLayout()
        snap_group.setLayout(sl_layout)

        self.snap_table = QTableWidget()
        self.snap_table.setAccessibleName(self.tr("Snapshot Timeline"))
        self.snap_table.setColumnCount(5)
        self.snap_table.setHorizontalHeaderLabels(
            [
                self.tr("ID"),
                self.tr("Label"),
                self.tr("Backend"),
                self.tr("Time"),
                self.tr("Size"),
            ]
        )
        self.snap_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.snap_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.snap_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.snap_table.setProperty("maxVisibleRows", 4)
        BaseTab.configure_table(self.snap_table)
        self.set_table_empty_state(
            self.snap_table,
            self.tr("Click Refresh to load snapshots (authentication may be required)"),
        )
        sl_layout.addWidget(self.snap_table)

        layout.addWidget(snap_group)

        # Output area from BaseTab
        layout.addWidget(self.output_area)
        layout.addStretch()

    # ============================================================
    # Actions
    # ============================================================

    def _refresh_all(self):
        """Refresh backends and snapshot list (explicit user action)."""
        self._refresh_backends()
        self._refresh_snapshots()

    def _refresh_backends(self):
        """Update backend status labels."""
        try:
            backends = SnapshotManager.detect_backends()
            backend_map = {b.name: b for b in backends}
            for name, label in self.backend_labels:
                b = backend_map.get(name)
                if b and b.available:
                    label.setText(f"✅ {b.version or 'installed'}")
                    label.setObjectName("snapBackendAvail")
                else:
                    label.setText("❌ Not found")
                    label.setObjectName("snapBackendMissing")
                if label.style() is not None:
                    label.style().unpolish(label)
                    label.style().polish(label)
        except (RuntimeError, OSError, ValueError) as exc:
            self.append_output(f"Backend check failed: {exc}\n")

    def _refresh_snapshots(self):
        """Reload the snapshot table."""
        try:
            snapshots = SnapshotManager.list_snapshots()
            self.snap_table.clearSpans()
            self.snap_table.setRowCount(0)

            if not snapshots:
                self.set_table_empty_state(
                    self.snap_table, self.tr("No snapshots found")
                )
                self.append_output("Found 0 snapshot(s)\n")
                return

            for snap in snapshots:
                row = self.snap_table.rowCount()
                self.snap_table.insertRow(row)
                self.snap_table.setItem(row, 0, self.make_table_item(snap.id))
                self.snap_table.setItem(row, 1, self.make_table_item(snap.label))
                self.snap_table.setItem(row, 2, self.make_table_item(snap.backend))

                ts_str = (
                    datetime.fromtimestamp(snap.timestamp).strftime("%Y-%m-%d %H:%M")
                    if snap.timestamp
                    else "—"
                )
                self.snap_table.setItem(row, 3, self.make_table_item(ts_str))
                self.snap_table.setItem(row, 4, self.make_table_item(snap.size_str))
            normalize = getattr(BaseTab, "ensure_table_row_heights", None)
            if callable(normalize):
                normalize(self.snap_table)

            count = self.snap_table.rowCount()
            self.append_output(f"Found {count} snapshot(s)\n")
        except (RuntimeError, OSError, ValueError) as exc:
            self.set_table_empty_state(
                self.snap_table, self.tr("Failed to load snapshots"), color="#e8556d"
            )
            self.append_output(f"Error listing snapshots: {exc}\n")

    def _create_snapshot(self):
        """Create a new snapshot."""
        label, ok = QInputDialog.getText(
            self, self.tr("Create Snapshot"), self.tr("Snapshot label:")
        )
        if not ok or not label.strip():
            return

        try:
            binary, args, desc = SnapshotManager.create_snapshot(label.strip())
            self.run_command(binary, args, desc)
            QTimer.singleShot(3000, self._refresh_snapshots)
        except (RuntimeError, OSError, ValueError) as exc:
            self.append_output(f"Error creating snapshot: {exc}\n")

    def _delete_snapshot(self):
        """Delete the selected snapshot."""
        row = self.snap_table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, self.tr("No Selection"), self.tr("Select a snapshot to delete.")
            )
            return

        snap_id = self.snap_table.item(row, 0).text()
        backend = self.snap_table.item(row, 2).text()

        confirm = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr(f"Delete snapshot '{snap_id}' from {backend}?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            binary, args, desc = SnapshotManager.delete_snapshot(snap_id, backend)
            self.run_command(binary, args, desc)
            QTimer.singleShot(3000, self._refresh_snapshots)
        except (RuntimeError, OSError, ValueError) as exc:
            self.append_output(f"Error deleting snapshot: {exc}\n")
