"""
Performance Tab - Live performance graphs with real-time system metrics.
Shows CPU, Memory, Network I/O, and Disk I/O as animated area charts.
Part of the v9.2 Pulse Update.
"""

import os
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QGroupBox,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient

from utils.performance import PerformanceCollector


class MiniGraph(QWidget):
    """
    A compact area-chart widget that draws a filled line graph.

    Stores the last 60 values and renders them as a smooth area chart
    using QPainter. Designed for embedding inside performance cards.
    """

    MAX_POINTS = 60

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._values: deque = deque(maxlen=self.MAX_POINTS)
        self._max_value: float = 100.0
        self.setFixedHeight(80)
        self.setMinimumWidth(200)

    def set_max_value(self, max_val: float):
        """Set the maximum expected value for Y-axis scaling."""
        self._max_value = max(max_val, 1.0)

    def add_value(self, value: float):
        """Append a new data point and trigger a repaint."""
        self._values.append(value)
        self.update()

    def paintEvent(self, event):
        """Draw the area chart with gradient fill."""
        if not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e2e"))

        # Draw subtle horizontal grid lines
        grid_pen = QPen(QColor("#45475a"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(0, y, w, y)

        values = list(self._values)
        count = len(values)
        if count < 2:
            # Single point: draw a horizontal line at that value
            y_pos = h - (values[0] / self._max_value) * h
            y_pos = max(0, min(h, y_pos))
            line_pen = QPen(self._color)
            line_pen.setWidth(2)
            painter.setPen(line_pen)
            painter.drawLine(0, int(y_pos), w, int(y_pos))
            painter.end()
            return

        # Build the path for the line
        step = w / (self.MAX_POINTS - 1)
        # Offset so the latest point is at the right edge
        x_offset = (self.MAX_POINTS - count) * step

        path = QPainterPath()
        fill_path = QPainterPath()

        for i, val in enumerate(values):
            clamped = max(0.0, min(val, self._max_value))
            x = x_offset + i * step
            y = h - (clamped / self._max_value) * (h - 4)  # 4px top padding
            y = max(2, min(h - 2, y))
            if i == 0:
                path.moveTo(x, y)
                fill_path.moveTo(x, h)
                fill_path.lineTo(x, y)
            else:
                path.lineTo(x, y)
                fill_path.lineTo(x, y)

        # Close fill path along the bottom
        last_x = x_offset + (count - 1) * step
        fill_path.lineTo(last_x, h)
        fill_path.closeSubpath()

        # Gradient fill under the line
        gradient = QLinearGradient(0, 0, 0, h)
        fill_color = QColor(self._color)
        fill_color.setAlpha(80)
        gradient.setColorAt(0.0, fill_color)
        fill_color_bottom = QColor(self._color)
        fill_color_bottom.setAlpha(10)
        gradient.setColorAt(1.0, fill_color_bottom)
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(fill_path)

        # Draw the line itself
        line_pen = QPen(self._color)
        line_pen.setWidth(2)
        painter.setPen(line_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.end()


class DualMiniGraph(QWidget):
    """
    An area-chart widget that draws two overlapping line graphs.

    Used for network (send/recv) and disk (read/write) where two
    metrics need to be shown on the same axes.
    """

    MAX_POINTS = 60

    def __init__(self, color_a: str, color_b: str, parent=None):
        super().__init__(parent)
        self._color_a = QColor(color_a)
        self._color_b = QColor(color_b)
        self._values_a: deque = deque(maxlen=self.MAX_POINTS)
        self._values_b: deque = deque(maxlen=self.MAX_POINTS)
        self._max_value: float = 1024.0  # Auto-scales
        self.setFixedHeight(80)
        self.setMinimumWidth(200)

    def add_values(self, value_a: float, value_b: float):
        """Append data points for both series and trigger repaint."""
        self._values_a.append(value_a)
        self._values_b.append(value_b)
        # Auto-scale: use the max of recent values with a floor
        all_vals = list(self._values_a) + list(self._values_b)
        if all_vals:
            peak = max(all_vals)
            self._max_value = max(peak * 1.2, 1024.0)
        self.update()

    def _draw_series(self, painter: QPainter, values: list, color: QColor,
                     w: int, h: int):
        """Draw a single series as a filled area chart."""
        count = len(values)
        if count < 2:
            return

        step = w / (self.MAX_POINTS - 1)
        x_offset = (self.MAX_POINTS - count) * step

        path = QPainterPath()
        fill_path = QPainterPath()

        for i, val in enumerate(values):
            clamped = max(0.0, min(val, self._max_value))
            x = x_offset + i * step
            y = h - (clamped / self._max_value) * (h - 4)
            y = max(2, min(h - 2, y))
            if i == 0:
                path.moveTo(x, y)
                fill_path.moveTo(x, h)
                fill_path.lineTo(x, y)
            else:
                path.lineTo(x, y)
                fill_path.lineTo(x, y)

        last_x = x_offset + (count - 1) * step
        fill_path.lineTo(last_x, h)
        fill_path.closeSubpath()

        # Gradient fill
        gradient = QLinearGradient(0, 0, 0, h)
        fill_color = QColor(color)
        fill_color.setAlpha(50)
        gradient.setColorAt(0.0, fill_color)
        fill_color_bottom = QColor(color)
        fill_color_bottom.setAlpha(5)
        gradient.setColorAt(1.0, fill_color_bottom)
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(fill_path)

        # Line
        line_pen = QPen(color)
        line_pen.setWidth(2)
        painter.setPen(line_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def paintEvent(self, event):
        """Draw both series overlapping."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e2e"))

        # Grid lines
        grid_pen = QPen(QColor("#45475a"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(0, y, w, y)

        # Draw series B first (behind), then A (in front)
        self._draw_series(painter, list(self._values_b), self._color_b, w, h)
        self._draw_series(painter, list(self._values_a), self._color_a, w, h)

        painter.end()


class PerformanceTab(QWidget):
    """
    Live performance graphs tab.

    Displays real-time CPU, memory, network, and disk I/O metrics
    as animated area charts with current-value labels, updated
    every second via QTimer.
    """

    def __init__(self):
        super().__init__()
        self.collector = PerformanceCollector()
        self.init_ui()

        # Collection timer - fires every 1000ms
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_tick)
        self.refresh_timer.start(1000)

        # Collect an initial baseline so first real tick has data
        self.collector.collect_all()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("Performance Monitor"))
        header.setObjectName("header")
        layout.addWidget(header)

        # 2x2 Grid of performance cards
        grid = QGridLayout()
        grid.setSpacing(20)

        # CPU Card
        cpu_card = self._create_cpu_card()
        grid.addWidget(cpu_card, 0, 0)

        # Memory Card
        memory_card = self._create_memory_card()
        grid.addWidget(memory_card, 0, 1)

        # Network Card
        network_card = self._create_network_card()
        grid.addWidget(network_card, 1, 0)

        # Disk I/O Card
        disk_card = self._create_disk_card()
        grid.addWidget(disk_card, 1, 1)

        layout.addLayout(grid)
        layout.addStretch()

    # ==================== CARD BUILDERS ====================

    def _create_card(self, title: str, icon: str) -> QGroupBox:
        """Create a styled card group box matching the Catppuccin Mocha theme."""
        card = QGroupBox(f"{icon} {title}")
        card.setStyleSheet("""
            QGroupBox {
                background-color: #313244;
                border-radius: 12px;
                padding: 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                padding: 10px;
            }
        """)
        return card

    def _create_cpu_card(self) -> QGroupBox:
        """Build the CPU usage card with graph and labels."""
        card = self._create_card(self.tr("CPU Usage"), "\U0001f7e2")
        card_layout = QVBoxLayout(card)

        # Line graph for overall CPU %
        self.cpu_graph = MiniGraph("#a6e3a1")
        self.cpu_graph.set_max_value(100.0)
        card_layout.addWidget(self.cpu_graph)

        # Per-core bar container
        self.cpu_core_layout = QHBoxLayout()
        self.cpu_core_layout.setSpacing(2)
        self.cpu_core_bars: list = []
        # Bars are created dynamically on first data
        card_layout.addLayout(self.cpu_core_layout)

        # Status label
        self.lbl_cpu = QLabel(self.tr("CPU: --% | Cores: --"))
        self.lbl_cpu.setStyleSheet("color: #a6adc8; font-size: 12px;")
        card_layout.addWidget(self.lbl_cpu)

        return card

    def _create_memory_card(self) -> QGroupBox:
        """Build the memory usage card with graph and labels."""
        card = self._create_card(self.tr("Memory Usage"), "\U0001f535")
        card_layout = QVBoxLayout(card)

        self.mem_graph = MiniGraph("#89b4fa")
        self.mem_graph.set_max_value(100.0)
        card_layout.addWidget(self.mem_graph)

        self.lbl_mem = QLabel(self.tr("Memory: --% | --/--"))
        self.lbl_mem.setStyleSheet("color: #a6adc8; font-size: 12px;")
        card_layout.addWidget(self.lbl_mem)

        return card

    def _create_network_card(self) -> QGroupBox:
        """Build the network I/O card with dual-line graph and labels."""
        card = self._create_card(self.tr("Network I/O"), "\U0001f7e3")
        card_layout = QVBoxLayout(card)

        # Two-line graph: send (lighter purple) and recv (purple)
        self.net_graph = DualMiniGraph("#cba6f7", "#b4befe")
        card_layout.addWidget(self.net_graph)

        # Legend
        legend_layout = QHBoxLayout()
        recv_dot = QLabel("\u25cf")
        recv_dot.setStyleSheet("color: #cba6f7; font-size: 10px;")
        legend_layout.addWidget(recv_dot)
        legend_layout.addWidget(QLabel(self.tr("Recv")))
        send_dot = QLabel("\u25cf")
        send_dot.setStyleSheet("color: #b4befe; font-size: 10px;")
        legend_layout.addWidget(send_dot)
        legend_layout.addWidget(QLabel(self.tr("Send")))
        legend_layout.addStretch()
        card_layout.addLayout(legend_layout)

        self.lbl_net = QLabel(self.tr("Net: -- | --"))
        self.lbl_net.setStyleSheet("color: #a6adc8; font-size: 12px;")
        card_layout.addWidget(self.lbl_net)

        return card

    def _create_disk_card(self) -> QGroupBox:
        """Build the disk I/O card with dual-line graph and labels."""
        card = self._create_card(self.tr("Disk I/O"), "\U0001f7e1")
        card_layout = QVBoxLayout(card)

        # Two-line graph: read (yellow) and write (peach/orange)
        self.disk_graph = DualMiniGraph("#f9e2af", "#fab387")
        card_layout.addWidget(self.disk_graph)

        # Legend
        legend_layout = QHBoxLayout()
        read_dot = QLabel("\u25cf")
        read_dot.setStyleSheet("color: #f9e2af; font-size: 10px;")
        legend_layout.addWidget(read_dot)
        legend_layout.addWidget(QLabel(self.tr("Read")))
        write_dot = QLabel("\u25cf")
        write_dot.setStyleSheet("color: #fab387; font-size: 10px;")
        legend_layout.addWidget(write_dot)
        legend_layout.addWidget(QLabel(self.tr("Write")))
        legend_layout.addStretch()
        card_layout.addLayout(legend_layout)

        self.lbl_disk = QLabel(self.tr("Disk: -- | --"))
        self.lbl_disk.setStyleSheet("color: #a6adc8; font-size: 12px;")
        card_layout.addWidget(self.lbl_disk)

        return card

    # ==================== PER-CORE BARS ====================

    def _ensure_core_bars(self, core_count: int):
        """Create per-core bar widgets if not yet initialized."""
        if len(self.cpu_core_bars) == core_count:
            return

        # Clear existing bars
        for bar in self.cpu_core_bars:
            bar.setParent(None)
            bar.deleteLater()
        self.cpu_core_bars.clear()

        for i in range(core_count):
            bar = _CoreBar()
            self.cpu_core_layout.addWidget(bar)
            self.cpu_core_bars.append(bar)

    # ==================== TIMER CALLBACK ====================

    def _on_tick(self):
        """Called every second to collect metrics and update graphs."""
        results = self.collector.collect_all()

        # --- CPU ---
        cpu_sample = results.get("cpu")
        if cpu_sample is not None:
            self.cpu_graph.add_value(cpu_sample.percent)
            core_count = len(cpu_sample.per_core)
            self._ensure_core_bars(core_count)
            for i, pct in enumerate(cpu_sample.per_core):
                if i < len(self.cpu_core_bars):
                    self.cpu_core_bars[i].set_value(pct)
            self.lbl_cpu.setText(
                self.tr("CPU: {pct}% | Cores: {cores}").format(
                    pct=cpu_sample.percent, cores=core_count
                )
            )

        # --- Memory ---
        mem_sample = results.get("memory")
        if mem_sample is not None:
            self.mem_graph.add_value(mem_sample.percent)
            used_h = PerformanceCollector.bytes_to_human(mem_sample.used_bytes)
            total_h = PerformanceCollector.bytes_to_human(mem_sample.total_bytes)
            self.lbl_mem.setText(
                self.tr("Memory: {pct}% | {used}/{total}").format(
                    pct=mem_sample.percent, used=used_h, total=total_h
                )
            )

        # --- Network ---
        net_sample = results.get("network")
        if net_sample is not None:
            self.net_graph.add_values(net_sample.recv_rate, net_sample.send_rate)
            recv_h = PerformanceCollector.bytes_to_human(int(net_sample.recv_rate))
            send_h = PerformanceCollector.bytes_to_human(int(net_sample.send_rate))
            self.lbl_net.setText(
                self.tr("Recv: {recv}/s | Send: {send}/s").format(
                    recv=recv_h, send=send_h
                )
            )

        # --- Disk I/O ---
        disk_sample = results.get("disk_io")
        if disk_sample is not None:
            self.disk_graph.add_values(disk_sample.read_rate, disk_sample.write_rate)
            read_h = PerformanceCollector.bytes_to_human(int(disk_sample.read_rate))
            write_h = PerformanceCollector.bytes_to_human(int(disk_sample.write_rate))
            self.lbl_disk.setText(
                self.tr("Read: {read}/s | Write: {write}/s").format(
                    read=read_h, write=write_h
                )
            )


class _CoreBar(QWidget):
    """
    Tiny vertical bar representing a single CPU core's usage.

    Drawn as a small green rectangle whose fill height reflects
    the core's current utilization percentage.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value: float = 0.0
        self.setFixedHeight(24)
        self.setMinimumWidth(6)
        self.setMaximumWidth(20)

    def set_value(self, percent: float):
        """Set core usage percentage (0-100) and repaint."""
        self._value = max(0.0, min(100.0, percent))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background slot
        painter.fillRect(0, 0, w, h, QColor("#1e1e2e"))

        # Filled portion from bottom
        fill_h = int(h * self._value / 100.0)
        if fill_h > 0:
            # Color shifts from green to yellow to red based on value
            if self._value < 60:
                color = QColor("#a6e3a1")
            elif self._value < 85:
                color = QColor("#f9e2af")
            else:
                color = QColor("#f38ba8")
            painter.fillRect(0, h - fill_h, w, fill_h, color)

        painter.end()
