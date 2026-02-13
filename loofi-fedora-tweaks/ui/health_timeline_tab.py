"""
Health Timeline Tab - View system health metrics over time.
Part of v13.0 "Nexus Update".

Provides:
- Summary view of recent metrics (CPU temp, RAM, disk, load)
- Button to record a snapshot
- Button to export data
- Table showing recent metrics
- Output log for operation feedback
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QSpinBox,
    QFileDialog, QMessageBox,
)

from ui.base_tab import BaseTab
from ui.tab_utils import CONTENT_MARGINS
from utils.health_timeline import HealthTimeline
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class HealthTimelineTab(QWidget, PluginInterface):
    """Health Timeline tab for viewing system metrics over time."""

    _METADATA = PluginMetadata(
        id="health",
        name="Health",
        description="System health metrics timeline for tracking CPU, RAM, disk, and thermal trends.",
        category="Health & Logs",
        icon="📈",
        badge="",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.timeline = HealthTimeline()
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
        header = QLabel(self.tr("Health Timeline"))
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #a277ff;"
        )
        layout.addWidget(header)

        description = QLabel(self.tr(
            "Track system health metrics over time including CPU temperature, "
            "RAM usage, disk space, and load average. Record snapshots and "
            "export data for analysis."
        ))
        description.setWordWrap(True)
        description.setStyleSheet("color: #9da7bf; font-size: 12px;")
        layout.addWidget(description)

        # Summary section
        summary_group = QGroupBox(self.tr("Recent Metrics Summary (24h)"))
        summary_layout = QVBoxLayout(summary_group)
        self.summary_label = QLabel(self.tr("Loading..."))
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "font-size: 12px; padding: 8px; background: #0b0e14; "
            "border-radius: 4px; color: #e6edf3;"
        )
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(summary_group)

        # Action buttons
        actions_group = QGroupBox(self.tr("Actions"))
        btn_layout = QHBoxLayout(actions_group)

        snapshot_btn = QPushButton(self.tr("Record Snapshot"))
        snapshot_btn.clicked.connect(self._record_snapshot)
        btn_layout.addWidget(snapshot_btn)

        export_btn = QPushButton(self.tr("Export Data"))
        export_btn.clicked.connect(self._export_data)
        btn_layout.addWidget(export_btn)

        prune_btn = QPushButton(self.tr("Prune Old Data"))
        prune_btn.clicked.connect(self._prune_data)
        btn_layout.addWidget(prune_btn)

        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(self._refresh_data)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addWidget(actions_group)

        # View controls
        view_group = QGroupBox(self.tr("View Options"))
        view_layout = QHBoxLayout(view_group)

        view_layout.addWidget(QLabel(self.tr("Metric Type:")))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "cpu_temp", "ram_usage", "disk_usage", "load_avg"
        ])
        self.metric_combo.currentTextChanged.connect(self._refresh_table)
        view_layout.addWidget(self.metric_combo)

        view_layout.addWidget(QLabel(self.tr("Hours:")))
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(1, 168)
        self.hours_spin.setValue(24)
        self.hours_spin.valueChanged.connect(self._refresh_table)
        view_layout.addWidget(self.hours_spin)

        view_layout.addStretch()
        layout.addWidget(view_group)

        # Metrics table
        table_group = QGroupBox(self.tr("Recent Metrics"))
        table_layout = QVBoxLayout(table_group)
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(4)
        self.metrics_table.setHorizontalHeaderLabels([
            self.tr("Timestamp"),
            self.tr("Value"),
            self.tr("Unit"),
            self.tr("ID"),
        ])
        self.metrics_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.metrics_table.setMaximumHeight(250)
        BaseTab.configure_table(self.metrics_table)
        table_layout.addWidget(self.metrics_table)
        layout.addWidget(table_group)

        # Anomaly detection section
        anomaly_group = QGroupBox(self.tr("Anomaly Detection"))
        anomaly_layout = QVBoxLayout(anomaly_group)
        self.anomaly_label = QLabel(self.tr("No anomalies detected."))
        self.anomaly_label.setWordWrap(True)
        self.anomaly_label.setStyleSheet(
            "font-size: 12px; padding: 8px; background: #0b0e14; "
            "border-radius: 4px; color: #e6edf3;"
        )
        anomaly_layout.addWidget(self.anomaly_label)

        detect_btn = QPushButton(self.tr("Detect Anomalies"))
        detect_btn.clicked.connect(self._detect_anomalies)
        anomaly_layout.addWidget(detect_btn)
        layout.addWidget(anomaly_group)

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
        self._refresh_data()

    # ==================== SLOTS ====================

    def _refresh_data(self):
        """Refresh all data displays."""
        self._refresh_summary()
        self._refresh_table()
        self.log(self.tr("Data refreshed."))

    def _refresh_summary(self):
        """Refresh the summary section."""
        summary = self.timeline.get_summary(hours=24)
        if not summary:
            self.summary_label.setText(self.tr(
                "No metrics recorded in the last 24 hours. "
                "Click 'Record Snapshot' to capture current system state."
            ))
            return

        lines = []
        metric_labels = {
            "cpu_temp": ("CPU Temp", "C"),
            "ram_usage": ("RAM Usage", "%"),
            "disk_usage": ("Disk Usage", "%"),
            "load_avg": ("Load Avg", ""),
        }

        for metric_type, data in summary.items():
            label, unit = metric_labels.get(metric_type, (metric_type, ""))
            lines.append(
                f"{label}: min={data['min']:.1f}{unit}, "
                f"max={data['max']:.1f}{unit}, "
                f"avg={data['avg']:.1f}{unit} "
                f"({data['count']} samples)"
            )

        self.summary_label.setText("\n".join(lines) if lines else self.tr("No data"))

    def _refresh_table(self):
        """Refresh the metrics table."""
        metric_type = self.metric_combo.currentText()
        hours = self.hours_spin.value()
        metrics = self.timeline.get_metrics(metric_type, hours)

        self.metrics_table.setRowCount(len(metrics))
        for row, m in enumerate(metrics):
            self.metrics_table.setItem(row, 0, QTableWidgetItem(m["timestamp"]))
            self.metrics_table.setItem(row, 1, QTableWidgetItem(f"{m['value']:.2f}"))
            self.metrics_table.setItem(row, 2, QTableWidgetItem(m["unit"]))
            self.metrics_table.setItem(row, 3, QTableWidgetItem(str(m["id"])))

    def _record_snapshot(self):
        """Record a system health snapshot."""
        self.log(self.tr("Recording system snapshot..."))
        result = self.timeline.record_snapshot()
        self.log(result.message)
        if result.success:
            self._refresh_data()

    def _export_data(self):
        """Export metrics to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Metrics"),
            "health_metrics.json",
            self.tr("JSON Files (*.json);;CSV Files (*.csv)"),
        )
        if not file_path:
            return

        # Determine format from extension
        if file_path.lower().endswith(".csv"):
            format_type = "csv"
        else:
            format_type = "json"

        self.log(self.tr("Exporting to {}...").format(file_path))
        result = self.timeline.export_metrics(file_path, format=format_type)
        self.log(result.message)

        if result.success:
            QMessageBox.information(
                self,
                self.tr("Export Complete"),
                self.tr("Metrics exported to:\n{}").format(file_path),
            )

    def _prune_data(self):
        """Prune old metrics data."""
        reply = QMessageBox.question(
            self,
            self.tr("Prune Data"),
            self.tr(
                "Delete metrics older than 30 days?\n"
                "This action cannot be undone."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log(self.tr("Pruning old data..."))
        result = self.timeline.prune_old_data()
        self.log(result.message)
        if result.success:
            self._refresh_data()

    def _detect_anomalies(self):
        """Detect anomalies in the selected metric type."""
        metric_type = self.metric_combo.currentText()
        hours = self.hours_spin.value()

        self.log(self.tr("Detecting anomalies in {}...").format(metric_type))
        anomalies = self.timeline.detect_anomalies(metric_type, hours)

        if not anomalies:
            self.anomaly_label.setText(self.tr(
                "No anomalies detected in {} (last {} hours).".format(
                    metric_type, hours
                )
            ))
            self.log(self.tr("No anomalies detected."))
            return

        lines = [
            self.tr("Found {} anomalies in {}:").format(len(anomalies), metric_type)
        ]
        for a in anomalies[:10]:  # Limit display
            lines.append(
                f"  {a['timestamp']}: {a['value']:.2f} "
                f"({a['deviation']:.1f} std devs from mean {a['mean']:.2f})"
            )
        if len(anomalies) > 10:
            lines.append(self.tr("  ... and {} more").format(len(anomalies) - 10))

        self.anomaly_label.setText("\n".join(lines))
        self.log(self.tr("Found {} anomalies.").format(len(anomalies)))

    # ==================== LOG HELPER ====================

    def log(self, message: str):
        """Append a message to the output log."""
        self.output_text.append(message)
