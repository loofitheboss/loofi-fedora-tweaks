"""
Storage Tab — disk information, SMART health, and filesystem management.
Part of v17.0 "Atlas".

Uses StorageManager from utils/storage.py for lsblk, smartctl, df, and fsck.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGridLayout, QWidget
)
from PyQt6.QtCore import QTimer
from ui.base_tab import BaseTab
from utils.storage import StorageManager
from core.plugins.metadata import PluginMetadata


class StorageTab(BaseTab):
    """Storage and disk management tab."""

    _METADATA = PluginMetadata(
        id="storage",
        name="Storage",
        description="Disk information, SMART health monitoring, and filesystem management.",
        category="Manage",
        icon="💾",
        badge="",
        order=40,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.init_ui()
        QTimer.singleShot(200, self._refresh_all)

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self.tr("Storage & Disks"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)

        # ==================== Disks ====================
        disk_group = QGroupBox(self.tr("Physical Disks"))
        dl_layout = QVBoxLayout()
        disk_group.setLayout(dl_layout)

        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(5)
        self.disk_table.setHorizontalHeaderLabels([
            self.tr("Device"), self.tr("Model"), self.tr("Size"),
            self.tr("Type"), self.tr("Removable")
        ])
        self.disk_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.disk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.disk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.disk_table.setMaximumHeight(140)
        BaseTab.configure_table(self.disk_table)
        self.set_table_empty_state(self.disk_table, self.tr("Loading disks..."))
        dl_layout.addWidget(self.disk_table)

        disk_btn_layout = QHBoxLayout()
        btn_smart = QPushButton(self.tr("🔍 SMART Health"))
        btn_smart.clicked.connect(self._check_smart)
        disk_btn_layout.addWidget(btn_smart)

        btn_refresh_disks = QPushButton(self.tr("🔄 Refresh"))
        btn_refresh_disks.clicked.connect(self._refresh_all)
        disk_btn_layout.addWidget(btn_refresh_disks)
        dl_layout.addLayout(disk_btn_layout)

        layout.addWidget(disk_group)

        # ==================== Partitions & Mount Points ====================
        mount_group = QGroupBox(self.tr("Mount Points"))
        ml_layout = QVBoxLayout()
        mount_group.setLayout(ml_layout)

        self.mount_table = QTableWidget()
        self.mount_table.setColumnCount(6)
        self.mount_table.setHorizontalHeaderLabels([
            self.tr("Device"), self.tr("Mount Point"), self.tr("Filesystem"),
            self.tr("Size"), self.tr("Used"), self.tr("Usage")
        ])
        self.mount_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.mount_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.mount_table)
        self.set_table_empty_state(self.mount_table, self.tr("Loading mount points..."))
        ml_layout.addWidget(self.mount_table)

        layout.addWidget(mount_group)

        # ==================== Actions ====================
        action_group = QGroupBox(self.tr("Actions"))
        al_layout = QHBoxLayout()
        action_group.setLayout(al_layout)

        btn_trim = QPushButton(self.tr("✂️ Trim SSDs"))
        btn_trim.clicked.connect(self._trim_ssd)
        al_layout.addWidget(btn_trim)

        btn_fsck = QPushButton(self.tr("🔧 Check Filesystem"))
        btn_fsck.clicked.connect(self._check_filesystem)
        al_layout.addWidget(btn_fsck)

        layout.addWidget(action_group)

        # ==================== SMART Details ====================
        smart_group = QGroupBox(self.tr("SMART Health Details"))
        sl_layout = QGridLayout()
        smart_group.setLayout(sl_layout)

        self.lbl_smart_model = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Model:")), 0, 0)
        sl_layout.addWidget(self.lbl_smart_model, 0, 1)

        self.lbl_smart_serial = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Serial:")), 0, 2)
        sl_layout.addWidget(self.lbl_smart_serial, 0, 3)

        self.lbl_smart_health = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Health:")), 1, 0)
        sl_layout.addWidget(self.lbl_smart_health, 1, 1)

        self.lbl_smart_temp = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Temperature:")), 1, 2)
        sl_layout.addWidget(self.lbl_smart_temp, 1, 3)

        self.lbl_smart_hours = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Power-On Hours:")), 2, 0)
        sl_layout.addWidget(self.lbl_smart_hours, 2, 1)

        self.lbl_smart_realloc = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Reallocated Sectors:")), 2, 2)
        sl_layout.addWidget(self.lbl_smart_realloc, 2, 3)

        layout.addWidget(smart_group)

        # Output area from BaseTab
        layout.addWidget(self.output_area)
        layout.addStretch()

    # ============================================================
    # Actions
    # ============================================================

    def _refresh_all(self):
        """Refresh disk and mount tables."""
        self._refresh_disks()
        self._refresh_mounts()

    def _refresh_disks(self):
        """Refresh physical disk table."""
        try:
            disks = StorageManager.list_disks()
            self.disk_table.clearSpans()
            self.disk_table.setRowCount(0)

            if not disks:
                self.set_table_empty_state(self.disk_table, self.tr("No disks detected"))
                return

            for disk in disks:
                row = self.disk_table.rowCount()
                self.disk_table.insertRow(row)
                self.disk_table.setItem(row, 0, self.make_table_item(disk.path))
                self.disk_table.setItem(row, 1, self.make_table_item(disk.model or "—"))
                self.disk_table.setItem(row, 2, self.make_table_item(disk.size))
                self.disk_table.setItem(row, 3, self.make_table_item(
                    "NVMe" if "nvme" in disk.name else "SATA/USB"
                ))
                self.disk_table.setItem(row, 4, self.make_table_item(
                    "Yes" if disk.rm else "No"
                ))
        except Exception as exc:
            self.set_table_empty_state(self.disk_table, self.tr("Failed to load disks"), color="#e8556d")
            self.append_output(f"Error listing disks: {exc}\n")

    def _refresh_mounts(self):
        """Refresh mount point table."""
        try:
            mounts = StorageManager.list_mounts()
            self.mount_table.clearSpans()
            self.mount_table.setRowCount(0)

            if not mounts:
                self.set_table_empty_state(self.mount_table, self.tr("No mount points found"))
                return

            for mount in mounts:
                row = self.mount_table.rowCount()
                self.mount_table.insertRow(row)
                self.mount_table.setItem(row, 0, self.make_table_item(mount.source))
                self.mount_table.setItem(row, 1, self.make_table_item(mount.target))
                self.mount_table.setItem(row, 2, self.make_table_item(mount.fstype))
                self.mount_table.setItem(row, 3, self.make_table_item(mount.size))
                self.mount_table.setItem(row, 4, self.make_table_item(mount.used))
                self.mount_table.setItem(row, 5, self.make_table_item(mount.use_percent))
        except Exception as exc:
            self.set_table_empty_state(self.mount_table, self.tr("Failed to load mount points"), color="#e8556d")
            self.append_output(f"Error listing mounts: {exc}\n")

    def _check_smart(self):
        """Check SMART health for selected disk."""
        row = self.disk_table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, self.tr("No Selection"),
                self.tr("Select a disk to check SMART health.")
            )
            return

        device = self.disk_table.item(row, 0).text()
        self.append_output(f"Checking SMART for {device}...\n")

        try:
            health = StorageManager.get_smart_health(device)
            self.lbl_smart_model.setText(health.model or "—")
            self.lbl_smart_serial.setText(health.serial or "—")

            if health.health_passed:
                self.lbl_smart_health.setText("✅ PASSED")
                self.lbl_smart_health.setStyleSheet("color: #3dd68c; font-weight: bold;")
            else:
                self.lbl_smart_health.setText("❌ FAILED")
                self.lbl_smart_health.setStyleSheet("color: #e8556d; font-weight: bold;")

            self.lbl_smart_temp.setText(
                f"{health.temperature_c}°C" if health.temperature_c else "—"
            )
            self.lbl_smart_hours.setText(
                f"{health.power_on_hours:,}" if health.power_on_hours else "—"
            )

            realloc = health.reallocated_sectors
            self.lbl_smart_realloc.setText(str(realloc))
            if realloc > 0:
                self.lbl_smart_realloc.setStyleSheet("color: #e89840; font-weight: bold;")
            else:
                self.lbl_smart_realloc.setStyleSheet("")

            self.append_output(f"SMART check complete for {device}\n")
        except Exception as exc:
            self.append_output(f"SMART error: {exc}\n")

    def _trim_ssd(self):
        """Run fstrim on all SSDs."""
        confirm = QMessageBox.question(
            self, self.tr("Trim SSDs"),
            self.tr("Run fstrim on all mounted filesystems?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.append_output("Running SSD trim...\n")
        try:
            result = StorageManager.trim_ssd()
            icon = "✅" if result.success else "❌"
            self.append_output(f"{icon} {result.message}\n")
        except Exception as exc:
            self.append_output(f"Trim error: {exc}\n")

    def _check_filesystem(self):
        """Check filesystem on selected mount."""
        row = self.mount_table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, self.tr("No Selection"),
                self.tr("Select a mount point to check.")
            )
            return

        device = self.mount_table.item(row, 0).text()
        target = self.mount_table.item(row, 1).text()

        QMessageBox.information(
            self, self.tr("Filesystem Check"),
            self.tr(f"Running read-only check on {device} ({target}).\n"
                    "For a full repair, unmount first.")
        )

        self.append_output(f"Checking {device}...\n")
        try:
            result = StorageManager.check_filesystem(device)
            icon = "✅" if result.success else "⚠️"
            self.append_output(f"{icon} {result.message}\n")
        except Exception as exc:
            self.append_output(f"Check error: {exc}\n")
