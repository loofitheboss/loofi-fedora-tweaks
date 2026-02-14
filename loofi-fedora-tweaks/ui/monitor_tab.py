"""
Monitor Tab - Consolidated tab merging Performance and Processes.
Part of v11.0 "Aurora Update".

Uses QTabWidget for sub-navigation to preserve all features from the
original PerformanceTab and ProcessesTab.

Does NOT inherit BaseTab because both sub-tabs have their own
refresh timers and custom rendering logic rather than CommandRunner
based execution.
"""

import os
from collections import deque

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox,
    QInputDialog, QFrame, QHeaderView, QGridLayout, QGroupBox,
    QTabWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QPainterPath, QLinearGradient, QBrush
)

from utils.performance import PerformanceCollector
from services.system import ProcessManager
from ui.tab_utils import configure_top_tabs
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata
from utils.log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Performance graph widgets
# ---------------------------------------------------------------------------

class MiniGraph(QWidget):
    """Compact area-chart widget that draws a filled line graph.

    Stores the last 60 values and renders them as a smooth area chart
    using QPainter.  Designed for embedding inside performance cards.
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
        painter.fillRect(0, 0, w, h, QColor("#0b0e14"))

        # Subtle horizontal grid lines
        grid_pen = QPen(QColor("#2d3348"))
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
    """Area-chart widget that draws two overlapping line graphs.

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
        painter.fillRect(0, 0, w, h, QColor("#0b0e14"))

        # Grid lines
        grid_pen = QPen(QColor("#2d3348"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = int(h * i / 4)
            painter.drawLine(0, y, w, y)

        # Draw series B first (behind), then A (in front)
        self._draw_series(painter, list(self._values_b), self._color_b, w, h)
        self._draw_series(painter, list(self._values_a), self._color_a, w, h)

        painter.end()


class _CoreBar(QWidget):
    """Tiny vertical bar representing a single CPU core's usage.

    Drawn as a small coloured rectangle whose fill height reflects
    the core's current utilisation percentage.
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
        painter.fillRect(0, 0, w, h, QColor("#0b0e14"))

        # Filled portion from bottom
        fill_h = int(h * self._value / 100.0)
        if fill_h > 0:
            if self._value < 60:
                color = QColor("#3dd68c")
            elif self._value < 85:
                color = QColor("#e8b84d")
            else:
                color = QColor("#e8556d")
            painter.fillRect(0, h - fill_h, w, fill_h, color)

        painter.end()


# ---------------------------------------------------------------------------
# Sub-tab: Performance
# ---------------------------------------------------------------------------

class _PerformanceSubTab(QWidget):
    """Sub-tab with live performance graphs.

    Preserves every feature from the original PerformanceTab:
    - Real-time CPU usage graph with per-core bars
    - Memory usage graph with used/total labels
    - Network I/O dual-line graph (send/recv)
    - Disk I/O dual-line graph (read/write)
    - 1-second QTimer refresh cycle
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

        cpu_card = self._create_cpu_card()
        grid.addWidget(cpu_card, 0, 0)

        memory_card = self._create_memory_card()
        grid.addWidget(memory_card, 0, 1)

        network_card = self._create_network_card()
        grid.addWidget(network_card, 1, 0)

        disk_card = self._create_disk_card()
        grid.addWidget(disk_card, 1, 1)

        layout.addLayout(grid)
        layout.addStretch()

    # ==================== CARD BUILDERS ====================

    def _create_card(self, title: str, icon: str) -> QGroupBox:
        """Create a styled card group box matching the Catppuccin Mocha theme."""
        card = QGroupBox(f"{icon} {title}")
        card.setObjectName("monitorCard")
        return card

    def _create_cpu_card(self) -> QGroupBox:
        """Build the CPU usage card with graph and labels."""
        card = self._create_card(self.tr("CPU Usage"), "\U0001f7e2")
        card_layout = QVBoxLayout(card)

        self.cpu_graph = MiniGraph("#3dd68c")
        self.cpu_graph.set_max_value(100.0)
        card_layout.addWidget(self.cpu_graph)

        # Per-core bar container
        self.cpu_core_layout = QHBoxLayout()
        self.cpu_core_layout.setSpacing(2)
        self.cpu_core_bars: list = []
        card_layout.addLayout(self.cpu_core_layout)

        self.lbl_cpu = QLabel(self.tr("CPU: --% | Cores: --"))
        self.lbl_cpu.setObjectName("monitorCpuLabel")
        card_layout.addWidget(self.lbl_cpu)

        return card

    def _create_memory_card(self) -> QGroupBox:
        """Build the memory usage card with graph and labels."""
        card = self._create_card(self.tr("Memory Usage"), "\U0001f535")
        card_layout = QVBoxLayout(card)

        self.mem_graph = MiniGraph("#39c5cf")
        self.mem_graph.set_max_value(100.0)
        card_layout.addWidget(self.mem_graph)

        self.lbl_mem = QLabel(self.tr("Memory: --% | --/--"))
        self.lbl_mem.setObjectName("monitorMemLabel")
        card_layout.addWidget(self.lbl_mem)

        return card

    def _create_network_card(self) -> QGroupBox:
        """Build the network I/O card with dual-line graph and labels."""
        card = self._create_card(self.tr("Network I/O"), "\U0001f7e3")
        card_layout = QVBoxLayout(card)

        self.net_graph = DualMiniGraph("#b78eff", "#4dd9e3")
        card_layout.addWidget(self.net_graph)

        # Legend
        legend_layout = QHBoxLayout()
        recv_dot = QLabel("\u25cf")
        recv_dot.setObjectName("monitorNetRecvDot")
        legend_layout.addWidget(recv_dot)
        legend_layout.addWidget(QLabel(self.tr("Recv")))
        send_dot = QLabel("\u25cf")
        send_dot.setObjectName("monitorNetSendDot")
        legend_layout.addWidget(send_dot)
        legend_layout.addWidget(QLabel(self.tr("Send")))
        legend_layout.addStretch()
        card_layout.addLayout(legend_layout)

        self.lbl_net = QLabel(self.tr("Net: -- | --"))
        self.lbl_net.setObjectName("monitorNetLabel")
        card_layout.addWidget(self.lbl_net)

        return card

    def _create_disk_card(self) -> QGroupBox:
        """Build the disk I/O card with dual-line graph and labels."""
        card = self._create_card(self.tr("Disk I/O"), "\U0001f7e1")
        card_layout = QVBoxLayout(card)

        self.disk_graph = DualMiniGraph("#e8b84d", "#e89840")
        card_layout.addWidget(self.disk_graph)

        # Legend
        legend_layout = QHBoxLayout()
        read_dot = QLabel("\u25cf")
        read_dot.setObjectName("monitorDiskReadDot")
        legend_layout.addWidget(read_dot)
        legend_layout.addWidget(QLabel(self.tr("Read")))
        write_dot = QLabel("\u25cf")
        write_dot.setObjectName("monitorDiskWriteDot")
        legend_layout.addWidget(write_dot)
        legend_layout.addWidget(QLabel(self.tr("Write")))
        legend_layout.addStretch()
        card_layout.addLayout(legend_layout)

        self.lbl_disk = QLabel(self.tr("Disk: -- | --"))
        self.lbl_disk.setObjectName("monitorDiskLabel")
        card_layout.addWidget(self.lbl_disk)

        return card

    # ==================== PER-CORE BARS ====================

    def _ensure_core_bars(self, core_count: int):
        """Create per-core bar widgets if not yet initialised."""
        if len(self.cpu_core_bars) == core_count:
            return

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
            total_h = PerformanceCollector.bytes_to_human(
                mem_sample.total_bytes
            )
            self.lbl_mem.setText(
                self.tr("Memory: {pct}% | {used}/{total}").format(
                    pct=mem_sample.percent, used=used_h, total=total_h
                )
            )

        # --- Network ---
        net_sample = results.get("network")
        if net_sample is not None:
            self.net_graph.add_values(
                net_sample.recv_rate, net_sample.send_rate
            )
            recv_h = PerformanceCollector.bytes_to_human(
                int(net_sample.recv_rate)
            )
            send_h = PerformanceCollector.bytes_to_human(
                int(net_sample.send_rate)
            )
            self.lbl_net.setText(
                self.tr("Recv: {recv}/s | Send: {send}/s").format(
                    recv=recv_h, send=send_h
                )
            )

        # --- Disk I/O ---
        disk_sample = results.get("disk_io")
        if disk_sample is not None:
            self.disk_graph.add_values(
                disk_sample.read_rate, disk_sample.write_rate
            )
            read_h = PerformanceCollector.bytes_to_human(
                int(disk_sample.read_rate)
            )
            write_h = PerformanceCollector.bytes_to_human(
                int(disk_sample.write_rate)
            )
            self.lbl_disk.setText(
                self.tr("Read: {read}/s | Write: {write}/s").format(
                    read=read_h, write=write_h
                )
            )


# ---------------------------------------------------------------------------
# Sub-tab: Processes
# ---------------------------------------------------------------------------

class _ProcessesSubTab(QWidget):
    """Sub-tab with real-time process table and management controls.

    Preserves every feature from the original ProcessesTab:
    - Process table with PID, Name, User, CPU%, Memory%, Memory, State, Nice
    - Sort by CPU / Memory / Name / PID
    - My Processes filter toggle
    - Auto-refresh (3-second timer)
    - Right-click context menu: Kill (SIGTERM), Force Kill (SIGKILL), Renice
    - Summary bar with total / running / sleeping / zombie counts
    - Catppuccin Mocha colour coding (zombies red, high-CPU yellow)
    """

    # Catppuccin Mocha colour constants
    COLOR_BASE = "#0b0e14"
    COLOR_SURFACE0 = "#1c2030"
    COLOR_SURFACE1 = "#2d3348"
    COLOR_SUBTEXT0 = "#9da7bf"
    COLOR_TEXT = "#e6edf3"
    COLOR_BLUE = "#39c5cf"
    COLOR_GREEN = "#3dd68c"
    COLOR_RED = "#e8556d"
    COLOR_YELLOW = "#e8b84d"
    COLOR_MAUVE = "#b78eff"
    COLOR_PEACH = "#e89840"

    def __init__(self):
        super().__init__()
        self._show_all = True  # True = all processes, False = my only
        self._current_sort = "cpu"
        self._current_user = self._get_current_username()
        self.init_ui()

        # Auto-refresh timer (3 seconds)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_processes)
        self.refresh_timer.start(3000)

        # Initial load
        QTimer.singleShot(100, self.refresh_processes)

    @staticmethod
    def _get_current_username() -> str:
        """Get the current user's username."""
        try:
            return os.getlogin()
        except OSError:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_name

    def init_ui(self):
        """Initialise the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("Process Monitor"))
        header.setObjectName("header")
        layout.addWidget(header)

        # Summary bar
        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("monitorSummaryFrame")
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(15, 8, 15, 8)

        self.lbl_summary = QLabel(
            self.tr("Total: 0 | Running: 0 | Sleeping: 0 | Zombie: 0")
        )
        self.lbl_summary.setObjectName("monitorSummaryLabel")
        summary_layout.addWidget(self.lbl_summary)
        summary_layout.addStretch()
        layout.addWidget(self.summary_frame)

        # Controls bar
        controls_layout = QHBoxLayout()

        # Sort controls
        controls_layout.addWidget(QLabel(self.tr("Sort by:")))
        self.sort_combo = QComboBox()
        self.sort_combo.setAccessibleName(self.tr("Process sort order"))
        self.sort_combo.addItem(self.tr("CPU"), "cpu")
        self.sort_combo.addItem(self.tr("Memory"), "memory")
        self.sort_combo.addItem(self.tr("Name"), "name")
        self.sort_combo.addItem(self.tr("PID"), "pid")
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.sort_combo.setObjectName("monitorSortCombo")
        controls_layout.addWidget(self.sort_combo)

        controls_layout.addStretch()

        # Show All / My Processes toggle
        self.btn_toggle_filter = QPushButton(self.tr("My Processes"))
        self.btn_toggle_filter.setAccessibleName(self.tr("My Processes"))
        self.btn_toggle_filter.setCheckable(True)
        self.btn_toggle_filter.setChecked(False)
        self.btn_toggle_filter.setObjectName("monitorFilterToggle")
        self.btn_toggle_filter.toggled.connect(self._on_filter_toggled)
        controls_layout.addWidget(self.btn_toggle_filter)

        # Refresh button
        btn_refresh = QPushButton(self.tr("Refresh"))
        btn_refresh.setAccessibleName(self.tr("Refresh"))
        btn_refresh.setObjectName("monitorRefreshBtn")
        btn_refresh.clicked.connect(self.refresh_processes)
        controls_layout.addWidget(btn_refresh)

        layout.addLayout(controls_layout)

        # Process tree / table
        self.process_tree = QTreeWidget()
        self.process_tree.setHeaderLabels([
            self.tr("PID"),
            self.tr("Name"),
            self.tr("User"),
            self.tr("CPU%"),
            self.tr("Memory%"),
            self.tr("Memory"),
            self.tr("State"),
            self.tr("Nice"),
        ])
        self.process_tree.setRootIsDecorated(False)
        self.process_tree.setAlternatingRowColors(True)
        self.process_tree.setSortingEnabled(False)
        self.process_tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.process_tree.customContextMenuRequested.connect(
            self._show_context_menu
        )

        # Column widths
        self.process_tree.setColumnWidth(0, 70)   # PID
        self.process_tree.setColumnWidth(1, 200)  # Name
        self.process_tree.setColumnWidth(2, 100)  # User
        self.process_tree.setColumnWidth(3, 70)   # CPU%
        self.process_tree.setColumnWidth(4, 80)   # Memory%
        self.process_tree.setColumnWidth(5, 90)   # Memory
        self.process_tree.setColumnWidth(6, 60)   # State
        self.process_tree.setColumnWidth(7, 50)   # Nice

        # Stretch the Name column
        tree_header = self.process_tree.header()
        tree_header.setStretchLastSection(False)
        tree_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.process_tree.setObjectName("monitorProcessTree")

        layout.addWidget(self.process_tree)

    # -- Slot handlers -----------------------------------------------------

    def _on_sort_changed(self, index: int):
        """Handle sort dropdown change."""
        self._current_sort = self.sort_combo.currentData()
        self.refresh_processes()

    def _on_filter_toggled(self, checked: bool):
        """Handle the Show All / My Processes toggle."""
        self._show_all = not checked
        if checked:
            self.btn_toggle_filter.setText(self.tr("My Processes"))
        else:
            self.btn_toggle_filter.setText(self.tr("My Processes"))
        self.refresh_processes()

    # -- Data refresh ------------------------------------------------------

    def refresh_processes(self):
        """Refresh the process list and summary bar."""
        counts = ProcessManager.get_process_count()
        self.lbl_summary.setText(
            self.tr(
                "Total: {total} | Running: {running} | "
                "Sleeping: {sleeping} | Zombie: {zombie}"
            ).format(
                total=counts["total"],
                running=counts["running"],
                sleeping=counts["sleeping"],
                zombie=counts["zombie"],
            )
        )

        processes = ProcessManager.get_all_processes()

        # Filter if "My Processes" is toggled
        if not self._show_all:
            processes = [p for p in processes if p.user == self._current_user]

        # Sort
        if self._current_sort == "cpu":
            processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        elif self._current_sort == "memory":
            processes.sort(key=lambda p: p.memory_bytes, reverse=True)
        elif self._current_sort == "name":
            processes.sort(key=lambda p: p.name.lower())
        elif self._current_sort == "pid":
            processes.sort(key=lambda p: p.pid)

        # Remember scroll position and selection
        scrollbar = self.process_tree.verticalScrollBar()
        scroll_pos = scrollbar.value() if scrollbar else 0
        selected_pid = None
        current_item = self.process_tree.currentItem()
        if current_item:
            try:
                selected_pid = int(current_item.text(0))
            except (ValueError, TypeError):
                logger.debug("Failed to parse selected process PID", exc_info=True)

        # Populate tree
        self.process_tree.clear()
        new_selected_item = None

        red_brush = QBrush(QColor(self.COLOR_RED))
        yellow_brush = QBrush(QColor(self.COLOR_YELLOW))

        for proc in processes:
            memory_human = ProcessManager.bytes_to_human(proc.memory_bytes)

            item = QTreeWidgetItem([
                str(proc.pid),
                proc.name,
                proc.user,
                f"{proc.cpu_percent:.1f}",
                f"{proc.memory_percent:.1f}",
                memory_human,
                proc.state,
                str(proc.nice),
            ])

            # Right-align numeric columns
            item.setTextAlignment(
                0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            item.setTextAlignment(
                3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            item.setTextAlignment(
                4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            item.setTextAlignment(
                5, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            item.setTextAlignment(
                7, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            # Store PID in UserRole for context menu
            item.setData(0, Qt.ItemDataRole.UserRole, proc.pid)

            # Colour-code: zombie processes in red
            if proc.state == "Z":
                for col in range(self.process_tree.columnCount()):
                    item.setForeground(col, red_brush)
            # Colour-code: high CPU (>50%) in yellow
            elif proc.cpu_percent > 50.0:
                for col in range(self.process_tree.columnCount()):
                    item.setForeground(col, yellow_brush)

            self.process_tree.addTopLevelItem(item)

            if selected_pid is not None and proc.pid == selected_pid:
                new_selected_item = item

        # Restore selection and scroll position
        if new_selected_item:
            self.process_tree.setCurrentItem(new_selected_item)
        if scrollbar:
            scrollbar.setValue(scroll_pos)

    # -- Context menu ------------------------------------------------------

    def _show_context_menu(self, position):
        """Show right-click context menu for process actions."""
        item = self.process_tree.itemAt(position)
        if not item:
            return

        pid = item.data(0, Qt.ItemDataRole.UserRole)
        name = item.text(1)
        if pid is None:
            return

        menu = QMenu(self)
        menu.setObjectName("monitorContextMenu")

        # Kill (SIGTERM)
        action_term = menu.addAction(self.tr("Kill Process (SIGTERM)"))
        action_term.triggered.connect(
            lambda: self._kill_process(pid, name, 15)
        )

        # Force kill (SIGKILL)
        action_kill = menu.addAction(self.tr("Force Kill (SIGKILL)"))
        action_kill.triggered.connect(
            lambda: self._kill_process(pid, name, 9)
        )

        menu.addSeparator()

        # Renice
        action_renice = menu.addAction(self.tr("Renice..."))
        action_renice.triggered.connect(
            lambda: self._renice_process(pid, name)
        )

        menu.exec(self.process_tree.viewport().mapToGlobal(position))

    def _kill_process(self, pid: int, name: str, signal: int):
        """Kill a process after confirmation."""
        signal_name = "SIGTERM" if signal == 15 else "SIGKILL"
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Kill"),
            self.tr(
                "Send {signal} to process '{name}' (PID {pid})?"
            ).format(signal=signal_name, name=name, pid=pid),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, message = ProcessManager.kill_process(pid, signal)
            if success:
                QMessageBox.information(
                    self, self.tr("Success"), message
                )
                self.refresh_processes()
            else:
                QMessageBox.warning(self, self.tr("Error"), message)

    def _renice_process(self, pid: int, name: str):
        """Renice a process after showing an input dialog."""
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Renice"),
            self.tr(
                "Change priority of process '{name}' (PID {pid})?"
            ).format(name=name, pid=pid),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        nice_value, ok = QInputDialog.getInt(
            self,
            self.tr("Renice Process"),
            self.tr(
                "Enter new nice value (-20 to 19).\n"
                "Lower = higher priority, higher = lower priority:"
            ),
            value=0,
            min=-20,
            max=19,
        )

        if ok:
            success, message = ProcessManager.renice_process(pid, nice_value)
            if success:
                QMessageBox.information(
                    self, self.tr("Success"), message
                )
                self.refresh_processes()
            else:
                QMessageBox.warning(self, self.tr("Error"), message)


# ---------------------------------------------------------------------------
# Main consolidated tab
# ---------------------------------------------------------------------------

class MonitorTab(QWidget, PluginInterface):
    """Consolidated monitor tab merging Performance and Processes.

    Uses a QTabWidget for sub-navigation.  Does not inherit BaseTab
    because both sub-tabs rely on their own QTimer-based refresh
    cycles rather than the CommandRunner pattern.
    """

    _METADATA = PluginMetadata(
        id="monitor",
        name="System Monitor",
        description="Live CPU, memory, and process monitoring with performance graphs.",
        category="Overview",
        icon="📊",
        badge="recommended",
        order=30,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        configure_top_tabs(self.tabs)
        self.tabs.addTab(_PerformanceSubTab(), self.tr("Performance"))
        self.tabs.addTab(_ProcessesSubTab(), self.tr("Processes"))

        layout.addWidget(self.tabs)
