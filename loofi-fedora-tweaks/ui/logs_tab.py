"""
Logs Tab — GUI for the Smart Log Viewer.
Part of v17.0 "Atlas".

Structured journal browsing with pattern detection, error summary,
and log export. Uses SmartLogViewer from utils/smart_logs.py.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QLineEdit, QFileDialog, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from ui.base_tab import BaseTab
from utils.smart_logs import SmartLogViewer


class LogsTab(BaseTab):
    """Smart log viewer tab with pattern detection."""

    def __init__(self):
        super().__init__()
        self.init_ui()
        QTimer.singleShot(200, self._load_summary)

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self.tr("Smart Log Viewer"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)

        # ==================== Error Summary ====================
        summary_group = QGroupBox(self.tr("Error Summary (last 24h)"))
        sg_layout = QGridLayout()
        summary_group.setLayout(sg_layout)

        self.lbl_total = QLabel("—")
        sg_layout.addWidget(QLabel(self.tr("Total entries:")), 0, 0)
        sg_layout.addWidget(self.lbl_total, 0, 1)

        self.lbl_critical = QLabel("—")
        self.lbl_critical.setStyleSheet("color: #f38ba8; font-weight: bold;")
        sg_layout.addWidget(QLabel(self.tr("Critical:")), 0, 2)
        sg_layout.addWidget(self.lbl_critical, 0, 3)

        self.lbl_warning = QLabel("—")
        self.lbl_warning.setStyleSheet("color: #fab387;")
        sg_layout.addWidget(QLabel(self.tr("Warnings:")), 1, 0)
        sg_layout.addWidget(self.lbl_warning, 1, 1)

        self.lbl_errors = QLabel("—")
        self.lbl_errors.setStyleSheet("color: #f38ba8;")
        sg_layout.addWidget(QLabel(self.tr("Errors:")), 1, 2)
        sg_layout.addWidget(self.lbl_errors, 1, 3)

        btn_refresh_summary = QPushButton(self.tr("🔄 Refresh Summary"))
        btn_refresh_summary.clicked.connect(self._load_summary)
        sg_layout.addWidget(btn_refresh_summary, 2, 0, 1, 4)

        layout.addWidget(summary_group)

        # ==================== Detected Patterns ====================
        pattern_group = QGroupBox(self.tr("Detected Patterns"))
        pg_layout = QVBoxLayout()
        pattern_group.setLayout(pg_layout)

        self.pattern_table = QTableWidget()
        self.pattern_table.setColumnCount(2)
        self.pattern_table.setHorizontalHeaderLabels([
            self.tr("Pattern"), self.tr("Count")
        ])
        self.pattern_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.pattern_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pattern_table.setMaximumHeight(150)
        pg_layout.addWidget(self.pattern_table)

        layout.addWidget(pattern_group)

        # ==================== Log Browser ====================
        browse_group = QGroupBox(self.tr("Browse Logs"))
        bl_layout = QVBoxLayout()
        browse_group.setLayout(bl_layout)

        # Filters
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel(self.tr("Unit:")))
        self.unit_combo = QComboBox()
        self.unit_combo.setEditable(True)
        self.unit_combo.setMinimumWidth(180)
        self.unit_combo.addItem(self.tr("(all)"))
        filter_layout.addWidget(self.unit_combo)

        filter_layout.addWidget(QLabel(self.tr("Priority:")))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems([
            "0 (emerg)", "1 (alert)", "2 (crit)", "3 (err)",
            "4 (warn)", "5 (notice)", "6 (info)", "7 (debug)"
        ])
        self.priority_combo.setCurrentIndex(4)  # Default: warning and above
        filter_layout.addWidget(self.priority_combo)

        filter_layout.addWidget(QLabel(self.tr("Lines:")))
        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(10, 1000)
        self.lines_spin.setValue(100)
        filter_layout.addWidget(self.lines_spin)

        bl_layout.addLayout(filter_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_fetch = QPushButton(self.tr("📋 Fetch Logs"))
        btn_fetch.clicked.connect(self._fetch_logs)
        btn_layout.addWidget(btn_fetch)

        btn_export = QPushButton(self.tr("💾 Export Logs"))
        btn_export.clicked.connect(self._export_logs)
        btn_layout.addWidget(btn_export)

        bl_layout.addLayout(btn_layout)

        # Log table
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels([
            self.tr("Time"), self.tr("Unit"), self.tr("Priority"), self.tr("Message")
        ])
        hdr = self.log_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        bl_layout.addWidget(self.log_table)

        layout.addWidget(browse_group)

        # Output area from BaseTab
        layout.addWidget(self.output_area)

    # ============================================================
    # Actions
    # ============================================================

    def _load_summary(self):
        """Load error summary and pattern stats."""
        try:
            summary = SmartLogViewer.get_error_summary("24h ago")
            self.lbl_total.setText(str(summary.total_entries))
            self.lbl_critical.setText(str(summary.critical_count))
            self.lbl_warning.setText(str(summary.warning_count))
            self.lbl_errors.setText(str(summary.error_count))

            # Patterns
            self.pattern_table.setRowCount(0)
            for pattern_name, count in summary.detected_patterns:
                row = self.pattern_table.rowCount()
                self.pattern_table.insertRow(row)
                self.pattern_table.setItem(row, 0, QTableWidgetItem(pattern_name))
                self.pattern_table.setItem(row, 1, QTableWidgetItem(str(count)))

            # Populate unit combo from top units
            current_text = self.unit_combo.currentText()
            self.unit_combo.clear()
            self.unit_combo.addItem(self.tr("(all)"))
            try:
                units = SmartLogViewer.get_unit_list()
                for unit in units[:50]:
                    self.unit_combo.addItem(unit)
            except Exception:
                pass
            # Restore selection
            idx = self.unit_combo.findText(current_text)
            if idx >= 0:
                self.unit_combo.setCurrentIndex(idx)

        except Exception as exc:
            self.append_output(f"Error loading summary: {exc}\n")

    def _fetch_logs(self):
        """Fetch and display journal logs with current filters."""
        try:
            unit = self.unit_combo.currentText()
            if unit == self.tr("(all)"):
                unit = None

            priority = self.priority_combo.currentIndex()
            lines = self.lines_spin.value()

            entries = SmartLogViewer.get_logs(
                unit=unit,
                priority=priority,
                lines=lines,
                since="24h ago"
            )

            self.log_table.setRowCount(0)
            for entry in entries:
                row = self.log_table.rowCount()
                self.log_table.insertRow(row)

                self.log_table.setItem(row, 0, QTableWidgetItem(entry.timestamp))

                unit_item = QTableWidgetItem(entry.unit)
                self.log_table.setItem(row, 1, unit_item)

                prio_item = QTableWidgetItem(entry.priority_label)
                if entry.priority <= 2:
                    prio_item.setForeground(QColor("#f38ba8"))
                elif entry.priority <= 4:
                    prio_item.setForeground(QColor("#fab387"))
                self.log_table.setItem(row, 2, prio_item)

                msg_item = QTableWidgetItem(entry.message[:200])
                if entry.pattern_match:
                    msg_item.setForeground(QColor("#f38ba8"))
                    msg_item.setToolTip(f"Pattern: {entry.pattern_match}")
                self.log_table.setItem(row, 3, msg_item)

            self.append_output(f"Fetched {len(entries)} log entries\n")
        except Exception as exc:
            self.append_output(f"Error fetching logs: {exc}\n")

    def _export_logs(self):
        """Export current logs to a file."""
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export Logs"),
            "loofi-logs.txt",
            self.tr("Text Files (*.txt);;JSON Files (*.json)")
        )
        if not path:
            return

        try:
            fmt = "json" if path.endswith(".json") else "text"
            SmartLogViewer.export_logs(path, fmt=fmt)
            self.append_output(f"Logs exported to {path}\n")
        except Exception as exc:
            self.append_output(f"Export error: {exc}\n")
