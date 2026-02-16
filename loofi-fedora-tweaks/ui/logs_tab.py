"""
Logs Tab — GUI for the Smart Log Viewer.
Part of v17.0 "Atlas".

Structured journal browsing with pattern detection, error summary,
and log export. Uses SmartLogViewer from utils/smart_logs.py.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTableWidget,
    QHeaderView,
    QComboBox,
    QSpinBox,
    QFileDialog,
    QGridLayout,
    QTextEdit,
    QWidget,
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from ui.base_tab import BaseTab
from utils.smart_logs import SmartLogViewer
from core.plugins.metadata import PluginMetadata
from utils.log import get_logger

logger = get_logger(__name__)


class LogsTab(BaseTab):
    """Smart log viewer tab with pattern detection."""

    _METADATA = PluginMetadata(
        id="logs",
        name="Logs",
        description="Smart log viewer with pattern detection, error summary, and log export.",
        category="Health & Logs",
        icon="📋",
        badge="advanced",
        order=20,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self._poll_live_logs)
        self._live_cursor = None
        self._live_row_count = 0
        self.init_ui()
        QTimer.singleShot(200, self._load_summary)

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self.tr("Smart Log Viewer"))
        header.setObjectName("logsHeader")
        layout.addWidget(header)

        # ==================== Error Summary ====================
        summary_group = QGroupBox(self.tr("Error Summary (last 24h)"))
        sg_layout = QGridLayout()
        summary_group.setLayout(sg_layout)

        self.lbl_total = QLabel("—")
        sg_layout.addWidget(QLabel(self.tr("Total entries:")), 0, 0)
        sg_layout.addWidget(self.lbl_total, 0, 1)

        self.lbl_critical = QLabel("—")
        self.lbl_critical.setObjectName("logsCritical")
        sg_layout.addWidget(QLabel(self.tr("Critical:")), 0, 2)
        sg_layout.addWidget(self.lbl_critical, 0, 3)

        self.lbl_warning = QLabel("—")
        self.lbl_warning.setObjectName("logsWarning")
        sg_layout.addWidget(QLabel(self.tr("Warnings:")), 1, 0)
        sg_layout.addWidget(self.lbl_warning, 1, 1)

        self.lbl_errors = QLabel("—")
        self.lbl_errors.setObjectName("logsErrors")
        sg_layout.addWidget(QLabel(self.tr("Errors:")), 1, 2)
        sg_layout.addWidget(self.lbl_errors, 1, 3)

        btn_refresh_summary = QPushButton(self.tr("🔄 Refresh Summary"))
        btn_refresh_summary.setAccessibleName(self.tr("Refresh Summary"))
        btn_refresh_summary.clicked.connect(self._load_summary)
        sg_layout.addWidget(btn_refresh_summary, 2, 0, 1, 4)

        layout.addWidget(summary_group)

        # ==================== Detected Patterns ====================
        pattern_group = QGroupBox(self.tr("Detected Patterns"))
        pg_layout = QVBoxLayout()
        pattern_group.setLayout(pg_layout)

        self.pattern_table = QTableWidget()
        self.pattern_table.setAccessibleName(self.tr("Detected Patterns"))
        self.pattern_table.setColumnCount(2)
        self.pattern_table.setHorizontalHeaderLabels(
            [self.tr("Pattern"), self.tr("Count")]
        )
        self.pattern_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.pattern_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pattern_table.setMaximumHeight(150)
        BaseTab.configure_table(self.pattern_table)
        pg_layout.addWidget(self.pattern_table)

        layout.addWidget(pattern_group)

        # ==================== Live Log Panel ====================
        live_group = QGroupBox(self.tr("Live Log Panel"))
        lg_layout = QVBoxLayout()
        live_group.setLayout(lg_layout)

        live_controls = QHBoxLayout()
        self.btn_live_toggle = QPushButton(self.tr("▶ Start Live"))
        self.btn_live_toggle.setAccessibleName(self.tr("Start Live"))
        self.btn_live_toggle.clicked.connect(self._toggle_live)
        live_controls.addWidget(self.btn_live_toggle)

        live_controls.addWidget(QLabel(self.tr("Every (sec):")))
        self.live_interval_spin = QSpinBox()
        self.live_interval_spin.setAccessibleName(self.tr("Live interval seconds"))
        self.live_interval_spin.setRange(1, 30)
        self.live_interval_spin.setValue(2)
        live_controls.addWidget(self.live_interval_spin)

        live_controls.addWidget(QLabel(self.tr("Buffer rows:")))
        self.live_buffer_spin = QSpinBox()
        self.live_buffer_spin.setAccessibleName(self.tr("Buffer rows"))
        self.live_buffer_spin.setRange(50, 2000)
        self.live_buffer_spin.setValue(300)
        live_controls.addWidget(self.live_buffer_spin)
        live_controls.addStretch()
        lg_layout.addLayout(live_controls)

        self.live_text = QTextEdit()
        self.live_text.setAccessibleName(self.tr("Live log output"))
        self.live_text.setReadOnly(True)
        self.live_text.setMaximumHeight(180)
        lg_layout.addWidget(self.live_text)
        layout.addWidget(live_group)

        # ==================== Log Browser ====================
        browse_group = QGroupBox(self.tr("Browse Logs"))
        bl_layout = QVBoxLayout()
        browse_group.setLayout(bl_layout)

        # Filters
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel(self.tr("Unit:")))
        self.unit_combo = QComboBox()
        self.unit_combo.setAccessibleName(self.tr("Unit filter"))
        self.unit_combo.setEditable(True)
        self.unit_combo.setMinimumWidth(180)
        self.unit_combo.addItem(self.tr("(all)"))
        filter_layout.addWidget(self.unit_combo)

        filter_layout.addWidget(QLabel(self.tr("Priority:")))
        self.priority_combo = QComboBox()
        self.priority_combo.setAccessibleName(self.tr("Priority filter"))
        self.priority_combo.addItems(
            [
                "0 (emerg)",
                "1 (alert)",
                "2 (crit)",
                "3 (err)",
                "4 (warn)",
                "5 (notice)",
                "6 (info)",
                "7 (debug)",
            ]
        )
        self.priority_combo.setCurrentIndex(4)  # Default: warning and above
        filter_layout.addWidget(self.priority_combo)

        filter_layout.addWidget(QLabel(self.tr("Lines:")))
        self.lines_spin = QSpinBox()
        self.lines_spin.setAccessibleName(self.tr("Lines to fetch"))
        self.lines_spin.setRange(10, 1000)
        self.lines_spin.setValue(100)
        filter_layout.addWidget(self.lines_spin)

        bl_layout.addLayout(filter_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_fetch = QPushButton(self.tr("📋 Fetch Logs"))
        btn_fetch.setAccessibleName(self.tr("Fetch Logs"))
        btn_fetch.clicked.connect(self._fetch_logs)
        btn_layout.addWidget(btn_fetch)

        btn_export = QPushButton(self.tr("💾 Export Logs"))
        btn_export.setAccessibleName(self.tr("Export Logs"))
        btn_export.clicked.connect(self._export_logs)
        btn_layout.addWidget(btn_export)

        bl_layout.addLayout(btn_layout)

        # Log table
        self.log_table = QTableWidget()
        self.log_table.setAccessibleName(self.tr("Log entries"))
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels(
            [self.tr("Time"), self.tr("Unit"), self.tr("Priority"), self.tr("Message")]
        )
        hdr = self.log_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.log_table)
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
            self.pattern_table.clearSpans()
            self.pattern_table.setRowCount(0)
            if not summary.detected_patterns:
                self.set_table_empty_state(
                    self.pattern_table, self.tr("No known log patterns detected")
                )
            else:
                for pattern_name, count in summary.detected_patterns:
                    row = self.pattern_table.rowCount()
                    self.pattern_table.insertRow(row)
                    self.pattern_table.setItem(
                        row, 0, self.make_table_item(pattern_name)
                    )
                    self.pattern_table.setItem(row, 1, self.make_table_item(str(count)))
                normalize = getattr(BaseTab, "ensure_table_row_heights", None)
                if callable(normalize):
                    normalize(self.pattern_table)

            # Populate unit combo from top units
            current_text = self.unit_combo.currentText()
            self.unit_combo.clear()
            self.unit_combo.addItem(self.tr("(all)"))
            try:
                units = SmartLogViewer.get_unit_list()
                for unit in units[:50]:
                    self.unit_combo.addItem(unit)
            except (RuntimeError, OSError, ValueError) as e:
                logger.debug("Failed to load systemd unit list: %s", e)
            # Restore selection
            idx = self.unit_combo.findText(current_text)
            if idx >= 0:
                self.unit_combo.setCurrentIndex(idx)

        except (RuntimeError, OSError, ValueError) as exc:
            self.set_table_empty_state(
                self.pattern_table,
                self.tr("Failed to load log summary"),
                color="#e8556d",
            )
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
                unit=unit, priority=priority, lines=lines, since="24h ago"
            )

            self.log_table.clearSpans()
            self.log_table.setRowCount(0)
            if not entries:
                self.set_table_empty_state(
                    self.log_table, self.tr("No log entries for current filters")
                )
            for entry in entries:
                row = self.log_table.rowCount()
                self.log_table.insertRow(row)

                self.log_table.setItem(row, 0, self.make_table_item(entry.timestamp))

                unit_item = self.make_table_item(entry.unit)
                self.log_table.setItem(row, 1, unit_item)

                prio_item = self.make_table_item(entry.priority_label)
                if entry.priority <= 2:
                    prio_item.setForeground(QColor("#e8556d"))
                elif entry.priority <= 4:
                    prio_item.setForeground(QColor("#e89840"))
                self.log_table.setItem(row, 2, prio_item)

                msg_item = self.make_table_item(entry.message[:200])
                if entry.pattern_match:
                    msg_item.setForeground(QColor("#e8556d"))
                    msg_item.setToolTip(f"Pattern: {entry.pattern_match}")
                self.log_table.setItem(row, 3, msg_item)
            normalize = getattr(BaseTab, "ensure_table_row_heights", None)
            if callable(normalize):
                normalize(self.log_table)

            self.append_output(f"Fetched {len(entries)} log entries\n")
        except (RuntimeError, OSError, ValueError) as exc:
            self.set_table_empty_state(
                self.log_table, self.tr("Failed to fetch logs"), color="#e8556d"
            )
            self.append_output(f"Error fetching logs: {exc}\n")

    def _export_logs(self):
        """Export current logs to a file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Logs"),
            "loofi-logs.txt",
            self.tr("Text Files (*.txt);;JSON Files (*.json)"),
        )
        if not path:
            return

        try:
            fmt = "json" if path.endswith(".json") else "text"
            entries = SmartLogViewer.get_logs(
                since="24h ago",
                lines=self.lines_spin.value(),
            )
            SmartLogViewer.export_logs(entries, path, format=fmt)
            self.append_output(f"Logs exported to {path}\n")
        except (OSError, RuntimeError, ValueError) as exc:
            self.append_output(f"Export error: {exc}\n")

    def _toggle_live(self):
        """Start/stop live polling."""
        if self._live_timer.isActive():
            self._stop_live()
        else:
            self._start_live()

    def _start_live(self):
        """Begin live log polling."""
        interval_ms = self.live_interval_spin.value() * 1000
        self._live_cursor = None
        self._live_row_count = 0
        self.live_text.clear()
        self._live_timer.start(interval_ms)
        self.btn_live_toggle.setText(self.tr("■ Stop Live"))
        self.append_output("Live log panel started\n")
        self._poll_live_logs()

    def _stop_live(self):
        """Stop live log polling."""
        self._live_timer.stop()
        self.btn_live_toggle.setText(self.tr("▶ Start Live"))
        self.append_output("Live log panel stopped\n")

    def _poll_live_logs(self):
        """Poll incremental log updates and append them to the live panel."""
        try:
            unit = self.unit_combo.currentText()
            if unit == self.tr("(all)"):
                unit = None
            priority = self.priority_combo.currentIndex()

            entries, next_cursor = SmartLogViewer.get_logs_incremental(
                self._live_cursor,
                unit=unit,
                priority=priority,
                lines=max(100, self.lines_spin.value()),
                since="2 minutes ago",
                max_entries=200,
            )
            self._live_cursor = next_cursor
            if not entries:
                return

            for entry in entries:
                marker = f" ({entry.pattern_match})" if entry.pattern_match else ""
                line = f"{entry.timestamp} [{entry.priority_label}] {entry.unit}: {entry.message}{marker}"
                self.live_text.append(line)
                self._live_row_count += 1

            self._trim_live_buffer()
        except (RuntimeError, OSError, ValueError) as exc:
            self.append_output(f"Live log error: {exc}\n")

    def _trim_live_buffer(self):
        """Trim live panel to configured max rows."""
        max_rows = self.live_buffer_spin.value()
        if self._live_row_count <= max_rows:
            return

        doc = self.live_text.document()
        while self._live_row_count > max_rows and doc.blockCount() > 0:
            cursor = self.live_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
            self._live_row_count -= 1
