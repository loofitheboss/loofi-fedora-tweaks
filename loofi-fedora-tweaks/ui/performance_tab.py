"""
Performance Tab — GUI for the Auto-Tuner engine.
Part of v17.0 "Atlas".

Displays current workload detection, kernel tunables, recommendations,
and tuning history. Uses AutoTuner from utils/auto_tuner.py.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QGroupBox,
    QGridLayout, QTableWidget, QHeaderView,
    QWidget
)
from PyQt6.QtCore import QTimer
from ui.base_tab import BaseTab
from utils.auto_tuner import AutoTuner, WorkloadProfile, TuningRecommendation, TuningHistoryEntry
import time
from core.plugins.metadata import PluginMetadata
from utils.log import get_logger

logger = get_logger(__name__)


class PerformanceTab(BaseTab):
    """Performance auto-tuner tab with workload detection and tuning."""

    _METADATA = PluginMetadata(
        id="performance",
        name="Performance",
        description="Auto-tuner engine for workload detection, kernel tunables, and performance recommendations.",
        category="Hardware",
        icon="🚀",
        badge="advanced",
        order=20,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._current_workload: WorkloadProfile | None = None
        self._current_rec: TuningRecommendation | None = None
        self.init_ui()

        # Auto-refresh workload every 30s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._detect_workload)
        self._timer.start(30_000)

        # Initial load
        QTimer.singleShot(200, self._detect_workload)

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel(self.tr("Performance Auto-Tuner"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)

        # ==================== Workload Detection ====================
        workload_group = QGroupBox(self.tr("Current Workload"))
        wl_layout = QGridLayout()
        workload_group.setLayout(wl_layout)

        self.lbl_workload = QLabel("—")
        self.lbl_workload.setStyleSheet("font-size: 16px; font-weight: bold;")
        wl_layout.addWidget(QLabel(self.tr("Profile:")), 0, 0)
        wl_layout.addWidget(self.lbl_workload, 0, 1)

        self.lbl_cpu = QLabel("—")
        wl_layout.addWidget(QLabel(self.tr("CPU:")), 1, 0)
        wl_layout.addWidget(self.lbl_cpu, 1, 1)

        self.lbl_memory = QLabel("—")
        wl_layout.addWidget(QLabel(self.tr("Memory:")), 2, 0)
        wl_layout.addWidget(self.lbl_memory, 2, 1)

        self.lbl_iowait = QLabel("—")
        wl_layout.addWidget(QLabel(self.tr("I/O Wait:")), 3, 0)
        wl_layout.addWidget(self.lbl_iowait, 3, 1)

        btn_refresh = QPushButton(self.tr("🔄 Re-detect Workload"))
        btn_refresh.setAccessibleName(self.tr("Re-detect workload"))
        btn_refresh.clicked.connect(self._detect_workload)
        wl_layout.addWidget(btn_refresh, 4, 0, 1, 2)

        layout.addWidget(workload_group)

        # ==================== Current Settings ====================
        settings_group = QGroupBox(self.tr("Current Kernel Settings"))
        sl_layout = QGridLayout()
        settings_group.setLayout(sl_layout)

        self.lbl_governor = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("CPU Governor:")), 0, 0)
        sl_layout.addWidget(self.lbl_governor, 0, 1)

        self.lbl_swappiness = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Swappiness:")), 1, 0)
        sl_layout.addWidget(self.lbl_swappiness, 1, 1)

        self.lbl_io_sched = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("I/O Scheduler:")), 2, 0)
        sl_layout.addWidget(self.lbl_io_sched, 2, 1)

        self.lbl_thp = QLabel("—")
        sl_layout.addWidget(QLabel(self.tr("Transparent Hugepages:")), 3, 0)
        sl_layout.addWidget(self.lbl_thp, 3, 1)

        layout.addWidget(settings_group)

        # ==================== Recommendation ====================
        rec_group = QGroupBox(self.tr("Recommendation"))
        rec_layout = QVBoxLayout()
        rec_group.setLayout(rec_layout)

        self.lbl_rec_summary = QLabel(self.tr("Detect a workload first…"))
        self.lbl_rec_summary.setWordWrap(True)
        rec_layout.addWidget(self.lbl_rec_summary)

        self.lbl_rec_details = QLabel("")
        self.lbl_rec_details.setWordWrap(True)
        self.lbl_rec_details.setStyleSheet("color: #9da7bf;")
        rec_layout.addWidget(self.lbl_rec_details)

        btn_apply = QPushButton(self.tr("⚡ Apply Recommendation"))
        btn_apply.setAccessibleName(self.tr("Apply recommendation"))
        btn_apply.clicked.connect(self._apply_recommendation)
        rec_layout.addWidget(btn_apply)

        layout.addWidget(rec_group)

        # ==================== History ====================
        history_group = QGroupBox(self.tr("Tuning History"))
        hl_layout = QVBoxLayout()
        history_group.setLayout(hl_layout)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            self.tr("Time"), self.tr("Workload"), self.tr("Applied"), self.tr("Settings")
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setMaximumHeight(180)
        BaseTab.configure_table(self.history_table)
        hl_layout.addWidget(self.history_table)

        layout.addWidget(history_group)

        # Output area from BaseTab
        layout.addWidget(self.output_area)
        layout.addStretch()

    # ============================================================
    # Actions
    # ============================================================

    def _detect_workload(self):
        """Detect current workload and update UI."""
        try:
            workload = AutoTuner.detect_workload()
            self._current_workload = workload

            self.lbl_workload.setText(workload.name.upper())
            self.lbl_cpu.setText(f"{workload.cpu_percent:.1f}%")
            self.lbl_memory.setText(f"{workload.memory_percent:.1f}%")
            self.lbl_iowait.setText(f"{workload.io_wait:.1f}%")

            # Update current settings
            settings = AutoTuner.get_current_settings()
            self.lbl_governor.setText(settings.get("governor", "unknown"))
            self.lbl_swappiness.setText(str(settings.get("swappiness", "?")))
            self.lbl_io_sched.setText(settings.get("io_scheduler", "unknown"))
            self.lbl_thp.setText(settings.get("thp", "unknown"))

            # Generate recommendation
            rec = AutoTuner.recommend(workload)
            self._current_rec = rec
            self.lbl_rec_summary.setText(
                f"Recommended for <b>{rec.workload}</b>: {rec.reason}"
            )
            self.lbl_rec_details.setText(
                f"Governor: {rec.governor} | Swappiness: {rec.swappiness} | "
                f"I/O: {rec.io_scheduler} | THP: {rec.thp}"
            )

            # Refresh history
            self._refresh_history()
        except Exception as exc:
            self.append_output(f"Detection error: {exc}\n")

    def _apply_recommendation(self):
        """Apply the current auto-tuner recommendation."""
        if not self._current_rec:
            self.append_output("No recommendation to apply. Detect workload first.\n")
            return

        rec = self._current_rec
        binary, args, desc = AutoTuner.apply_recommendation(rec)
        self.run_command(binary, args, desc)

        # Log to history
        entry = TuningHistoryEntry(
            timestamp=time.time(),
            workload=rec.workload,
            recommendations={
                "governor": rec.governor,
                "swappiness": rec.swappiness,
                "io_scheduler": rec.io_scheduler,
                "thp": rec.thp,
            },
            applied=True,
        )
        try:
            AutoTuner.save_tuning_entry(entry)
        except Exception:
            logger.debug("Failed to save tuning history entry", exc_info=True)

    def _refresh_history(self):
        """Update the history table."""
        try:
            history = AutoTuner.get_tuning_history()
            self.history_table.clearSpans()
            self.history_table.setRowCount(0)
            recent = list(reversed(history[-10:]))
            if not recent:
                self.set_table_empty_state(self.history_table, self.tr("No tuning history yet"))
                return

            for entry in recent:
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)

                from datetime import datetime
                ts = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d %H:%M")
                self.history_table.setItem(row, 0, self.make_table_item(ts))
                self.history_table.setItem(row, 1, self.make_table_item(entry.workload))
                self.history_table.setItem(row, 2, self.make_table_item(
                    "✅" if entry.applied else "❌"
                ))
                recs = entry.recommendations
                summary = f"gov={recs.get('governor', '?')}, swap={recs.get('swappiness', '?')}"
                self.history_table.setItem(row, 3, self.make_table_item(summary))
        except Exception:
            self.set_table_empty_state(self.history_table, self.tr("Failed to load tuning history"), color="#e8556d")
