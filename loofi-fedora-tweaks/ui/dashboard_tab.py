"""
Dashboard Tab v2 — Live system overview with graphs.
Part of v16.0 "Horizon".

Features:
- Welcome header with system variant badge
- Live CPU & RAM sparkline graphs (refreshed every 2s)
- Storage breakdown per mount point
- Network speed indicator (upload/download)
- Top 5 processes by CPU
- Recent actions feed from HistoryManager
- Quick Actions grid (Clean Cache, Update All, Power Profile, Gaming Mode)
"""

from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QProgressBar, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient

import subprocess

from utils.system import SystemManager
from utils.disk import DiskManager
from utils.monitor import SystemMonitor
from utils.history import HistoryManager


# ---------------------------------------------------------------------------
# Sparkline widget (compact, self-contained)
# ---------------------------------------------------------------------------

class SparkLine(QWidget):
    """Tiny area-chart widget for embedding in dashboard cards."""

    MAX_POINTS = 30

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._values: deque = deque(maxlen=self.MAX_POINTS)
        self._max_value: float = 100.0
        self.setFixedHeight(48)
        self.setMinimumWidth(160)

    def set_max_value(self, v: float):
        self._max_value = max(v, 1.0)

    def add_value(self, v: float):
        self._values.append(v)
        self.update()

    @property
    def latest(self) -> float:
        return self._values[-1] if self._values else 0.0

    def paintEvent(self, event):
        if not self._values:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e2e"))

        values = list(self._values)
        count = len(values)
        if count < 2:
            painter.end()
            return

        step = w / (self.MAX_POINTS - 1)
        x_off = (self.MAX_POINTS - count) * step

        path = QPainterPath()
        first_y = h - (values[0] / self._max_value) * h
        path.moveTo(x_off, max(0, min(h, first_y)))
        for i in range(1, count):
            x = x_off + i * step
            y = h - (values[i] / self._max_value) * h
            path.lineTo(x, max(0, min(h, y)))

        # Fill
        fill_path = QPainterPath(path)
        fill_path.lineTo(x_off + (count - 1) * step, h)
        fill_path.lineTo(x_off, h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        fill_color = QColor(self._color)
        fill_color.setAlpha(60)
        grad.setColorAt(0, fill_color)
        fill_color.setAlpha(10)
        grad.setColorAt(1, fill_color)
        painter.fillPath(fill_path, grad)

        # Line
        pen = QPen(self._color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()


# ---------------------------------------------------------------------------
# Dashboard Tab v2
# ---------------------------------------------------------------------------

class DashboardTab(QWidget):
    """Overhauled dashboard with live graphs and richer information."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # Data for network speed calculation
        self._prev_rx = 0
        self._prev_tx = 0

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self._inner = QVBoxLayout(container)
        self._inner.setContentsMargins(30, 20, 30, 20)
        self._inner.setSpacing(16)

        self._build_header()
        self._build_live_metrics()
        self._build_storage_section()
        self._build_top_processes()
        self._build_recent_actions()
        self._build_quick_actions()
        self._inner.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Timers
        self._fast_timer = QTimer(self)
        self._fast_timer.timeout.connect(self._tick_fast)
        self._fast_timer.start(2000)

        self._slow_timer = QTimer(self)
        self._slow_timer.timeout.connect(self._tick_slow)
        self._slow_timer.start(10000)

        # Initial data load
        self._tick_fast()
        self._tick_slow()

    # ==================================================================
    # Header
    # ==================================================================

    def _build_header(self):
        row = QHBoxLayout()

        header = QLabel(self.tr("Welcome back, Loofi! 👋"))
        header.setObjectName("header")
        row.addWidget(header)

        row.addStretch()

        variant = SystemManager.get_variant_name()
        pkg_mgr = SystemManager.get_package_manager()
        badge = QLabel(f"💻 {variant} ({pkg_mgr})")
        badge.setStyleSheet(
            "color: #89b4fa; font-weight: bold; font-size: 13px; "
            "background: #1e1e2e; padding: 4px 10px; border-radius: 8px;"
        )
        row.addWidget(badge)
        self._inner.addLayout(row)

        # Reboot banner (Atomic only)
        self.reboot_banner = QFrame()
        self.reboot_banner.setStyleSheet(
            "QFrame { background-color: #f9e2af; border-radius: 8px; padding: 10px; }"
        )
        rb_layout = QHBoxLayout(self.reboot_banner)
        lbl = QLabel(self.tr("⚠️ Pending changes require reboot!"))
        lbl.setStyleSheet("color: #1e1e2e; font-weight: bold;")
        rb_layout.addWidget(lbl)
        rb_layout.addStretch()
        reboot_btn = QPushButton(self.tr("🔁 Reboot Now"))
        reboot_btn.setStyleSheet(
            "background-color: #1e1e2e; color: #f9e2af; padding: 5px 10px; border-radius: 5px;"
        )
        reboot_btn.clicked.connect(self._reboot)
        rb_layout.addWidget(reboot_btn)
        self._inner.addWidget(self.reboot_banner)
        self.reboot_banner.setVisible(SystemManager.has_pending_deployment())

    # ==================================================================
    # Live Metrics Row (CPU graph + RAM graph + Network speed)
    # ==================================================================

    def _build_live_metrics(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        # CPU card
        cpu_card = self._card()
        cpu_inner = QVBoxLayout(cpu_card)
        self.lbl_cpu = QLabel("🔥 CPU: —")
        self.lbl_cpu.setStyleSheet("font-weight: bold; font-size: 13px;")
        cpu_inner.addWidget(self.lbl_cpu)
        self.spark_cpu = SparkLine("#f38ba8")
        cpu_inner.addWidget(self.spark_cpu)
        row.addWidget(cpu_card)

        # RAM card
        ram_card = self._card()
        ram_inner = QVBoxLayout(ram_card)
        self.lbl_ram = QLabel("🧠 RAM: —")
        self.lbl_ram.setStyleSheet("font-weight: bold; font-size: 13px;")
        ram_inner.addWidget(self.lbl_ram)
        self.spark_ram = SparkLine("#89b4fa")
        ram_inner.addWidget(self.spark_ram)
        row.addWidget(ram_card)

        # Network card
        net_card = self._card()
        net_inner = QVBoxLayout(net_card)
        self.lbl_net = QLabel("🌐 Network: —")
        self.lbl_net.setStyleSheet("font-weight: bold; font-size: 13px;")
        net_inner.addWidget(self.lbl_net)
        self.lbl_net_detail = QLabel("↓ 0 B/s   ↑ 0 B/s")
        self.lbl_net_detail.setStyleSheet("color: #a6adc8; font-size: 12px;")
        net_inner.addWidget(self.lbl_net_detail)
        net_inner.addStretch()
        row.addWidget(net_card)

        self._inner.addLayout(row)

    # ==================================================================
    # Storage Breakdown
    # ==================================================================

    def _build_storage_section(self):
        self.storage_card = self._card()
        self.storage_inner = QVBoxLayout(self.storage_card)
        title = QLabel(self.tr("💿 Storage"))
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 4px;")
        self.storage_inner.addWidget(title)
        self.storage_bars: list = []
        self._inner.addWidget(self.storage_card)

    def _refresh_storage(self):
        for lbl, bar in self.storage_bars:
            self.storage_inner.removeWidget(lbl)
            self.storage_inner.removeWidget(bar)
            lbl.deleteLater()
            bar.deleteLater()
        self.storage_bars.clear()

        mounts = self._get_mount_points()
        for mp in mounts:
            usage = DiskManager.get_disk_usage(mp)
            if not usage:
                continue
            percent = usage.percent_used if hasattr(usage, 'percent_used') else 0
            free = usage.free_human if hasattr(usage, 'free_human') else "?"
            total = usage.total_human if hasattr(usage, 'total_human') else "?"

            lbl = QLabel(f"{mp}  —  {free} free / {total}")
            lbl.setStyleSheet("font-size: 12px; color: #cdd6f4;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(percent))
            bar.setFixedHeight(14)
            bar.setTextVisible(False)
            if percent >= 90:
                color = "#f38ba8"
            elif percent >= 75:
                color = "#f9e2af"
            else:
                color = "#a6e3a1"
            bar.setStyleSheet(
                f"QProgressBar {{ background: #313244; border-radius: 7px; }}"
                f"QProgressBar::chunk {{ background: {color}; border-radius: 7px; }}"
            )
            self.storage_inner.addWidget(lbl)
            self.storage_inner.addWidget(bar)
            self.storage_bars.append((lbl, bar))

    # ==================================================================
    # Top Processes
    # ==================================================================

    def _build_top_processes(self):
        card = self._card()
        inner = QVBoxLayout(card)
        title = QLabel(self.tr("🔝 Top Processes"))
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 4px;")
        inner.addWidget(title)
        self.process_labels: list = []
        for _ in range(5):
            lbl = QLabel("—")
            lbl.setStyleSheet("font-size: 12px; color: #cdd6f4; font-family: monospace;")
            inner.addWidget(lbl)
            self.process_labels.append(lbl)
        self._inner.addWidget(card)

    def _refresh_processes(self):
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid,pcpu,pmem,comm", "--sort=-pcpu", "--no-headers"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().splitlines()[:5]
            for i, lbl in enumerate(self.process_labels):
                if i < len(lines):
                    parts = lines[i].split()
                    if len(parts) >= 4:
                        pid, cpu, mem = parts[0], parts[1], parts[2]
                        name = " ".join(parts[3:])[:30]
                        lbl.setText(
                            f"  {name:<30}  CPU {cpu:>5}%  MEM {mem:>5}%  PID {pid}"
                        )
                    else:
                        lbl.setText(lines[i].strip())
                else:
                    lbl.setText("—")
        except Exception:
            pass

    # ==================================================================
    # Recent Actions
    # ==================================================================

    def _build_recent_actions(self):
        card = self._card()
        inner = QVBoxLayout(card)
        title = QLabel(self.tr("📋 Recent Actions"))
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 4px;")
        inner.addWidget(title)
        self.history_labels: list = []
        for _ in range(5):
            lbl = QLabel("—")
            lbl.setStyleSheet("font-size: 12px; color: #a6adc8;")
            inner.addWidget(lbl)
            self.history_labels.append(lbl)
        self._inner.addWidget(card)

    def _refresh_history(self):
        try:
            hm = HistoryManager()
            history = hm._load_history()
            entries = history[:5] if history else []
            for i, lbl in enumerate(self.history_labels):
                if i < len(entries):
                    entry = entries[i]
                    ts = entry.get("timestamp", "")[:16]
                    action = entry.get("action", "Unknown")
                    lbl.setText(f"  {ts}  —  {action}")
                else:
                    lbl.setText("—")
        except Exception:
            pass

    # ==================================================================
    # Quick Actions
    # ==================================================================

    def _build_quick_actions(self):
        section_label = QLabel(self.tr("Quick Actions"))
        section_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-top: 12px;"
        )
        self._inner.addWidget(section_label)

        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(
            self._action_btn(self.tr("Clean Cache"), "🧹", "#f9e2af",
                             self._go_maintenance), 0, 0)
        grid.addWidget(
            self._action_btn(self.tr("Update All"), "🔄", "#89b4fa",
                             self._go_maintenance), 0, 1)
        grid.addWidget(
            self._action_btn(self.tr("Power Profile"), "🔋", "#a6e3a1",
                             self._go_hardware), 1, 0)
        grid.addWidget(
            self._action_btn(self.tr("Gaming Mode"), "🎮", "#f38ba8",
                             self._go_gaming), 1, 1)

        self._inner.addLayout(grid)

    # ==================================================================
    # Timer callbacks
    # ==================================================================

    def _tick_fast(self):
        """Update live graphs (every 2s)."""
        cpu = SystemMonitor.get_cpu_info()
        if cpu:
            pct = cpu.load_percent
            self.spark_cpu.add_value(pct)
            color = "#f38ba8" if pct >= 80 else "#f9e2af" if pct >= 50 else "#a6e3a1"
            self.lbl_cpu.setText(f"🔥 CPU: {pct:.0f}%")
            self.lbl_cpu.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {color};"
            )

        mem = SystemMonitor.get_memory_info()
        if mem:
            pct = mem.percent_used
            self.spark_ram.add_value(pct)
            color = "#f38ba8" if pct >= 85 else "#f9e2af" if pct >= 65 else "#a6e3a1"
            self.lbl_ram.setText(
                f"🧠 RAM: {mem.used_human} / {mem.total_human} ({pct:.0f}%)"
            )
            self.lbl_ram.setStyleSheet(
                f"font-weight: bold; font-size: 13px; color: {color};"
            )

        self._refresh_network()

    def _tick_slow(self):
        """Update slower sections (every 10s)."""
        self._refresh_storage()
        self._refresh_processes()
        self._refresh_history()

    # ==================================================================
    # Network
    # ==================================================================

    def _refresh_network(self):
        try:
            rx, tx = self._get_network_bytes()
            if self._prev_rx > 0:
                dl = (rx - self._prev_rx) / 2
                ul = (tx - self._prev_tx) / 2
                self.lbl_net.setText("🌐 Network")
                self.lbl_net_detail.setText(
                    f"↓ {self._human_speed(dl)}   ↑ {self._human_speed(ul)}"
                )
            self._prev_rx = rx
            self._prev_tx = tx
        except Exception:
            pass

    @staticmethod
    def _get_network_bytes():
        rx_total = 0
        tx_total = 0
        try:
            with open("/proc/net/dev", "r") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    iface, data = line.split(":", 1)
                    if iface.strip() == "lo":
                        continue
                    parts = data.split()
                    if len(parts) >= 9:
                        rx_total += int(parts[0])
                        tx_total += int(parts[8])
        except OSError:
            pass
        return rx_total, tx_total

    @staticmethod
    def _human_speed(bps: float) -> str:
        if bps < 1024:
            return f"{bps:.0f} B/s"
        elif bps < 1024 ** 2:
            return f"{bps / 1024:.1f} KB/s"
        elif bps < 1024 ** 3:
            return f"{bps / (1024 ** 2):.1f} MB/s"
        return f"{bps / (1024 ** 3):.2f} GB/s"

    # ==================================================================
    # Quick Action callbacks
    # ==================================================================

    def _go_maintenance(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Maintenance")

    def _go_hardware(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Hardware")

    def _go_gaming(self):
        if hasattr(self.main_window, "switch_to_tab"):
            self.main_window.switch_to_tab("Gaming")

    # ==================================================================
    # Helpers
    # ==================================================================

    def _reboot(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, self.tr("Reboot Now?"),
            self.tr("Reboot now to apply pending changes?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            subprocess.run(["systemctl", "reboot"])

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #313244; border-radius: 12px; padding: 12px; }"
        )
        return card

    @staticmethod
    def _action_btn(text: str, icon: str, color: str, callback) -> QPushButton:
        btn = QPushButton(f"{icon}  {text}")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e2e;
                border: 2px solid {color};
                color: {color};
                border-radius: 12px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: #1e1e2e;
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    @staticmethod
    def _get_mount_points() -> list:
        mounts = ["/"]
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 3:
                        continue
                    device, mp, fstype = parts[0], parts[1], parts[2]
                    if fstype in ("ext4", "btrfs", "xfs", "f2fs", "vfat", "ntfs"):
                        if mp not in mounts and not mp.startswith("/snap"):
                            mounts.append(mp)
        except OSError:
            pass
        return mounts[:6]
