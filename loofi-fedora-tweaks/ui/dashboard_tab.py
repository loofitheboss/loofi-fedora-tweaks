"""
Dashboard Tab v3 — Live system overview with graphs.
Part of v16.0 "Horizon", v31.0 "Smart UX" updates.

Features:
- Welcome header with system variant badge
- v31.0: System health score gauge
- Live CPU & RAM sparkline graphs (refreshed every 2s)
- Storage breakdown per mount point
- Network speed indicator (upload/download)
- Top 5 processes by CPU
- Recent actions feed from HistoryManager
- v31.0: Configurable Quick Actions grid
"""

import getpass
from collections import deque

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGridLayout,
    QFrame,
    QProgressBar,
    QScrollArea,
)
from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata

from ui.icon_pack import get_qicon
from ui.tooltips import DASH_HEALTH_SCORE, DASH_QUICK_ACTIONS, DASH_FOCUS_MODE, DASH_SYSTEM_OVERVIEW
from services.system.processes import ProcessManager
from utils.commands import PrivilegedCommand
from services.system import SystemManager
from services.hardware.disk import DiskManager
from utils.monitor import SystemMonitor
from utils.history import HistoryManager
from utils.health_score import HealthScoreManager
from utils.quick_actions_config import QuickActionsConfig
from utils.focus_mode import FocusMode
from utils.log import get_logger

logger = get_logger(__name__)


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

        # v29.0: Use palette background instead of hardcoded dark color
        bg_color = self.palette().color(self.backgroundRole())
        painter.fillRect(0, 0, w, h, bg_color)

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
# Health Score Widget (v31.0 Smart UX)
# ---------------------------------------------------------------------------


class HealthScoreWidget(QWidget):
    """Circular gauge showing aggregate system health score."""

    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._score = 0
        self._grade = "—"
        self._color = QColor("#6c7086")
        self._recommendations: list = []
        self.setFixedSize(120, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_score(self, score: int, grade: str, color: str, recommendations: list):
        """Update the displayed health score."""
        self._score = score
        self._grade = grade
        self._color = QColor(color)
        self._recommendations = recommendations
        self.update()

    def mousePressEvent(self, event):
        """Emit clicked signal on left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, 60
        radius = 48

        # Background arc — use palette base color
        bg_pen = QPen(self.palette().color(self.backgroundRole()).darker(110))
        bg_pen.setWidth(8)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(
            cx - radius, cy - radius, radius * 2, radius * 2, 225 * 16, -270 * 16
        )

        # Score arc
        if self._score > 0:
            score_pen = QPen(self._color)
            score_pen.setWidth(8)
            score_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(score_pen)
            span = int(-270 * 16 * self._score / 100)
            painter.drawArc(
                cx - radius, cy - radius, radius * 2, radius * 2, 225 * 16, span
            )

        # Score text — use palette foreground
        painter.setPen(self.palette().color(self.foregroundRole()))
        from PyQt6.QtGui import QFont

        font = QFont()
        font.setPixelSize(22)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            cx - 20, cy - 8, 40, 30, Qt.AlignmentFlag.AlignCenter, str(self._score)
        )

        # Grade text
        font.setPixelSize(14)
        painter.setFont(font)
        painter.setPen(self._color)
        painter.drawText(
            cx - 20, cy + 18, 40, 20, Qt.AlignmentFlag.AlignCenter, self._grade
        )

        # Label — use palette mid color
        font.setPixelSize(11)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(0, h - 20, w, 20, Qt.AlignmentFlag.AlignCenter, "Health Score")

        painter.end()


# ---------------------------------------------------------------------------
# Dashboard Tab v3
# ---------------------------------------------------------------------------


class DashboardTab(QWidget, PluginInterface):
    """Overhauled dashboard with live graphs and richer information."""

    _METADATA = PluginMetadata(
        id="dashboard",
        name="Home",
        description="Live system overview with graphs, metrics, and quick actions.",
        category="System",
        icon="home",
        badge="recommended",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def set_context(self, context: dict) -> None:
        self.main_window = context.get("main_window")

    def __init__(self, main_window=None):
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
        self._build_health_score()
        self._build_live_metrics()
        self._build_storage_section()
        self._build_top_processes()
        self._build_recent_actions()
        self._build_undo_card()
        self._build_quick_actions()
        self._build_focus_mode_control()
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
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(4)

        try:
            username = getpass.getuser().capitalize()
        except (OSError, KeyError) as e:
            logger.debug("Failed to get username: %s", e)
            username = "User"
        header = QLabel(self.tr("Welcome back, {name}!").format(name=username))
        header.setObjectName("header")
        left_col.addWidget(header)

        variant = SystemManager.get_variant_name()
        pkg_mgr = SystemManager.get_package_manager()
        badge = QLabel(f"{variant} ({pkg_mgr})")
        badge.setObjectName("systemBadge")
        left_col.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)

        row.addLayout(left_col)
        row.addStretch()
        self._inner.addLayout(row)

        # Reboot banner (Atomic only)
        self.reboot_banner = QFrame()
        self.reboot_banner.setObjectName("rebootBanner")
        rb_layout = QHBoxLayout(self.reboot_banner)
        lbl = QLabel(self.tr("Pending changes require reboot!"))
        lbl.setObjectName("rebootLabel")
        rb_layout.addWidget(lbl)
        rb_layout.addStretch()
        reboot_btn = QPushButton(self.tr("Reboot Now"))
        reboot_btn.setObjectName("rebootButton")
        reboot_btn.setAccessibleName(self.tr("Reboot system now"))
        reboot_btn.clicked.connect(self._reboot)
        try:
            reboot_btn.setIcon(get_qicon("restart", size=17))
        except TypeError as e:
            logger.debug("Skipping reboot button icon setup: %s", e)
        rb_layout.addWidget(reboot_btn)
        self._inner.addWidget(self.reboot_banner)
        self.reboot_banner.setVisible(SystemManager.has_pending_deployment())

    # ==================================================================
    # Health Score (v31.0 Smart UX)
    # ==================================================================

    def _build_health_score(self):
        """Build the health score card."""
        card = self._card()
        card_layout = QHBoxLayout(card)

        self._health_gauge = HealthScoreWidget()
        self._health_gauge.setToolTip(
            DASH_HEALTH_SCORE + "\n" + self.tr("Click for detailed breakdown")
        )
        self._health_gauge.clicked.connect(self._show_health_detail)
        card_layout.addWidget(self._health_gauge)

        # Recommendations area
        rec_layout = QVBoxLayout()
        self._health_title = QLabel(self.tr("System Health"))
        self._health_title.setObjectName("healthTitle")
        rec_layout.addWidget(self._health_title)

        self._health_recs = QLabel(self.tr("Calculating..."))
        self._health_recs.setObjectName("healthRecs")
        self._health_recs.setWordWrap(True)
        rec_layout.addWidget(self._health_recs)
        rec_layout.addStretch()

        card_layout.addLayout(rec_layout)
        card_layout.setStretch(1, 1)
        self._inner.addWidget(card)

    # ==================================================================
    # Live Metrics Row (CPU graph + RAM graph + Network speed)
    # ==================================================================

    def _build_live_metrics(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        # CPU card
        cpu_card = self._card()
        cpu_card.setToolTip(DASH_SYSTEM_OVERVIEW)
        cpu_inner = QVBoxLayout(cpu_card)
        self.lbl_cpu = QLabel("CPU: —")
        self.lbl_cpu.setObjectName("metricLabel")
        cpu_inner.addWidget(self.lbl_cpu)
        self.spark_cpu = SparkLine("#e8556d")
        cpu_inner.addWidget(self.spark_cpu)
        row.addWidget(cpu_card)

        # RAM card
        ram_card = self._card()
        ram_card.setToolTip(DASH_SYSTEM_OVERVIEW)
        ram_inner = QVBoxLayout(ram_card)
        self.lbl_ram = QLabel("RAM: —")
        self.lbl_ram.setObjectName("metricLabel")
        ram_inner.addWidget(self.lbl_ram)
        self.spark_ram = SparkLine("#39c5cf")
        ram_inner.addWidget(self.spark_ram)
        row.addWidget(ram_card)

        # Network card
        net_card = self._card()
        net_card.setToolTip(DASH_SYSTEM_OVERVIEW)
        net_inner = QVBoxLayout(net_card)
        self.lbl_net = QLabel("Network: —")
        self.lbl_net.setObjectName("metricLabel")
        net_inner.addWidget(self.lbl_net)
        self.lbl_net_detail = QLabel("↓ 0 B/s   ↑ 0 B/s")
        self.lbl_net_detail.setObjectName("metricDetail")
        net_inner.addWidget(self.lbl_net_detail)
        net_inner.addStretch()
        row.addWidget(net_card)

        self._inner.addLayout(row)

    # ==================================================================
    # Storage Breakdown
    # ==================================================================

    def _build_storage_section(self) -> None:
        self.storage_card = self._card()
        self.storage_inner = QVBoxLayout(self.storage_card)
        title = QLabel(self.tr("Storage"))
        title.setObjectName("sectionTitle")
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
            percent = usage.percent_used if hasattr(usage, "percent_used") else 0
            free = usage.free_human if hasattr(usage, "free_human") else "?"
            total = usage.total_human if hasattr(usage, "total_human") else "?"

            lbl = QLabel(f"{mp}  —  {free} free / {total}")
            lbl.setObjectName("storageLabel")
            bar = QProgressBar()
            bar.setObjectName("storageBar")
            bar.setRange(0, 100)
            bar.setValue(int(percent))
            bar.setFixedHeight(14)
            bar.setTextVisible(False)
            if percent >= 90:
                bar.setProperty("level", "critical")
            elif percent >= 75:
                bar.setProperty("level", "warning")
            else:
                bar.setProperty("level", "ok")
            self.storage_inner.addWidget(lbl)
            self.storage_inner.addWidget(bar)
            self.storage_bars.append((lbl, bar))

    # ==================================================================
    # Top Processes
    # ==================================================================

    def _build_top_processes(self) -> None:
        card = self._card()
        inner = QVBoxLayout(card)
        title = QLabel(self.tr("Top Processes"))
        title.setObjectName("sectionTitle")
        inner.addWidget(title)
        self.process_labels: list = []
        for _ in range(5):
            lbl = QLabel("—")
            lbl.setObjectName("processLabel")
            inner.addWidget(lbl)
            self.process_labels.append(lbl)
        self._inner.addWidget(card)

    def _refresh_processes(self):
        try:
            top = ProcessManager.get_top_by_cpu(5)
            for i, lbl in enumerate(self.process_labels):
                if i < len(top):
                    p = top[i]
                    name = p.name[:30]
                    lbl.setText(
                        f"  {name:<30}  CPU {p.cpu_percent:>5.1f}%  MEM {p.memory_percent:>5.1f}%  PID {p.pid}"
                    )
                else:
                    lbl.setText("—")
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to refresh process list: %s", e)

    # ==================================================================
    # Recent Actions
    # ==================================================================

    def _build_recent_actions(self) -> None:
        card = self._card()
        inner = QVBoxLayout(card)
        title = QLabel(self.tr("Recent Actions"))
        title.setObjectName("sectionTitle")
        inner.addWidget(title)
        self.history_labels: list = []
        for _ in range(5):
            lbl = QLabel("—")
            lbl.setObjectName("historyLabel")
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
        except (RuntimeError, OSError, ValueError, KeyError) as e:
            logger.debug("Failed to refresh action history: %s", e)

    # ==================================================================
    # Undo Card (v47.0 UX)
    # ==================================================================

    def _build_undo_card(self):
        """Build the Recent Changes card with undo buttons."""
        card = self._card()
        inner = QVBoxLayout(card)
        title_row = QHBoxLayout()
        title = QLabel(self.tr("Recent Changes"))
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        inner.addLayout(title_row)

        self._undo_container = QVBoxLayout()
        inner.addLayout(self._undo_container)

        self._undo_empty_label = QLabel(self.tr("No recent changes to undo."))
        self._undo_empty_label.setObjectName("historyLabel")
        self._undo_container.addWidget(self._undo_empty_label)

        self._inner.addWidget(card)
        self._refresh_undo_card()

    def _refresh_undo_card(self):
        """Refresh the undo card with recent undoable changes."""
        try:
            hm = HistoryManager()
            recent = hm.get_recent(3)
            undoable = [e for e in recent if e.undo_command]

            # Clear existing items (except empty label)
            while self._undo_container.count() > 1:
                item = self._undo_container.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()

            if not undoable:
                self._undo_empty_label.setVisible(True)
                return

            self._undo_empty_label.setVisible(False)
            for entry in undoable:
                row = QHBoxLayout()
                desc = QLabel(f"  {entry.timestamp[:16]}  —  {entry.description}")
                desc.setObjectName("historyLabel")
                desc.setWordWrap(True)
                row.addWidget(desc, 1)

                undo_btn = QPushButton(self.tr("↩ Undo"))
                undo_btn.setObjectName("undoBtn")
                undo_btn.setFixedWidth(80)
                action_id = entry.id
                undo_btn.clicked.connect(
                    lambda checked, aid=action_id: self._do_undo(aid)
                )
                row.addWidget(undo_btn)

                container = QWidget()
                container.setLayout(row)
                self._undo_container.addWidget(container)
        except (RuntimeError, OSError, ValueError, KeyError) as e:
            logger.debug("Failed to refresh undo card: %s", e)

    def _do_undo(self, action_id: str):
        """Execute undo for a specific action."""
        try:
            hm = HistoryManager()
            success = hm.undo_action(action_id)
            if success:
                self._refresh_undo_card()
                self._refresh_history()
            else:
                logger.debug("Undo failed for action: %s", action_id)
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to undo action %s: %s", action_id, e)

    # ==================================================================
    # Quick Actions (v31.0: configurable)
    # ==================================================================

    def _build_quick_actions(self):
        section_label = QLabel(self.tr("Quick Actions"))
        section_label.setObjectName("sectionTitle")
        section_label.setToolTip(DASH_QUICK_ACTIONS)
        self._inner.addWidget(section_label)

        self._quick_actions_grid = QGridLayout()
        self._quick_actions_grid.setSpacing(12)
        self._refresh_quick_actions()

        self._inner.addLayout(self._quick_actions_grid)

    def _refresh_quick_actions(self):
        """Rebuild quick actions grid from config."""
        # Clear existing
        while self._quick_actions_grid.count():
            item = self._quick_actions_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        actions = QuickActionsConfig.get_actions()
        for i, action in enumerate(actions[:8]):  # Max 8 actions in 2x4 grid
            row, col = divmod(i, 2)
            target = action.get("target_tab", "")
            btn = self._action_btn(
                action.get("label", "Action"),
                action.get("icon", "settings"),
                action.get("color", "#39c5cf"),
                lambda checked, t=target: self._go_to_tab(t),
            )
            self._quick_actions_grid.addWidget(btn, row, col)

    # ==================================================================
    # Timer callbacks
    # ==================================================================

    def _tick_fast(self):
        """Update live graphs (every 2s)."""
        cpu = SystemMonitor.get_cpu_info()
        if cpu:
            pct = cpu.load_percent
            self.spark_cpu.add_value(pct)
            self.lbl_cpu.setText(f"CPU: {pct:.0f}%")

        mem = SystemMonitor.get_memory_info()
        if mem:
            pct = mem.percent_used
            self.spark_ram.add_value(pct)
            self.lbl_ram.setText(
                f"RAM: {mem.used_human} / {mem.total_human} ({pct:.0f}%)"
            )

        self._refresh_network()

    def _tick_slow(self):
        """Update slower sections (every 10s)."""
        self._refresh_storage()
        self._refresh_processes()
        self._refresh_history()
        self._refresh_health_score()
        self._refresh_focus_mode_status()

    # ==================================================================
    # Network
    # ==================================================================

    def _refresh_network(self):
        try:
            rx, tx = self._get_network_bytes()
            if self._prev_rx > 0:
                dl = (rx - self._prev_rx) / 2
                ul = (tx - self._prev_tx) / 2
                self.lbl_net.setText("Network")
                self.lbl_net_detail.setText(
                    f"↓ {self._human_speed(dl)}   ↑ {self._human_speed(ul)}"
                )
            self._prev_rx = rx
            self._prev_tx = tx
        except (OSError, ValueError, RuntimeError) as e:
            logger.debug("Failed to refresh network stats: %s", e)

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
            logger.debug("Failed to read network device stats", exc_info=True)
        return rx_total, tx_total

    @staticmethod
    def _human_speed(bps: float) -> str:
        if bps < 1024:
            return f"{bps:.0f} B/s"
        elif bps < 1024**2:
            return f"{bps / 1024:.1f} KB/s"
        elif bps < 1024**3:
            return f"{bps / (1024**2):.1f} MB/s"
        return f"{bps / (1024**3):.2f} GB/s"

    # ==================================================================
    # Quick Action callbacks
    # ==================================================================

    def _go_to_tab(self, tab_name: str):
        """Navigate to a named tab via MainWindow."""
        if (
            tab_name
            and self.main_window is not None
            and hasattr(self.main_window, "switch_to_tab")
        ):
            self.main_window.switch_to_tab(tab_name)
            if hasattr(self.main_window, "show_toast"):
                self.main_window.show_toast(
                    "Quick Action", f"Navigated to {tab_name}", "general"
                )

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
    # Health Score refresh (v31.0)
    # ==================================================================

    def _show_health_detail(self):
        """Open the health detail drill-down dialog (v47.0)."""
        try:
            from ui.health_detail_dialog import HealthDetailDialog
            dialog = HealthDetailDialog(self)
            dialog.navigate_to_tab.connect(self._navigate_to_tab)
            dialog.exec()
        except (ImportError, RuntimeError) as e:
            logger.debug("Failed to show health detail dialog: %s", e)

    def _navigate_to_tab(self, tab_id: str):
        """Navigate to a tab by its plugin ID."""
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'switch_to_tab'):
            tab_name_map = {
                "performance": "Performance",
                "storage": "Storage",
                "maintenance": "Maintenance",
                "security": "Security",
                "network": "Network",
            }
            tab_name = tab_name_map.get(tab_id, tab_id.title())
            self.main_window.switch_to_tab(tab_name)

    def _refresh_health_score(self):
        """Refresh the health score gauge."""
        try:
            hs = HealthScoreManager.calculate()
            self._health_gauge.set_score(
                hs.score, hs.grade, hs.color, hs.recommendations
            )
            if hs.recommendations:
                recs_text = "\n".join(f"• {r}" for r in hs.recommendations[:3])
            else:
                recs_text = "System is healthy. No issues detected."
            self._health_recs.setText(recs_text)
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to calculate health score: %s", e)
            self._health_recs.setText("Could not calculate health score")

    # ==================================================================
    # Focus Mode (v42.0 Sentinel)
    # ==================================================================

    def _build_focus_mode_control(self):
        """Build Focus Mode toggle control on dashboard."""
        section_label = QLabel(self.tr("Focus Mode"))
        section_label.setObjectName("sectionTitle")
        self._inner.addWidget(section_label)

        try:
            is_active = FocusMode.is_active()
        except (OSError, RuntimeError):
            is_active = False

        status_text = self.tr("Focus Mode: ON") if is_active else self.tr("Focus Mode: OFF")
        color = "#a6e3a1" if is_active else "#6c7086"

        self._focus_mode_btn = self._action_btn(
            status_text, "settings", color, self._toggle_focus_mode,
        )
        self._focus_mode_btn.setToolTip(DASH_FOCUS_MODE)
        self._inner.addWidget(self._focus_mode_btn)

    def _toggle_focus_mode(self, checked=False):
        """Toggle Focus Mode on/off."""
        try:
            result = FocusMode.toggle()
            if result.get("success"):
                is_active = FocusMode.is_active()
                self._update_focus_btn(is_active)
            else:
                logger.warning("Focus Mode toggle failed: %s", result.get("message"))
        except (OSError, RuntimeError) as e:
            logger.warning("Focus Mode toggle error: %s", e)

    def _refresh_focus_mode_status(self):
        """Refresh focus mode button to reflect current state."""
        try:
            is_active = FocusMode.is_active()
            self._update_focus_btn(is_active)
        except (OSError, RuntimeError):
            pass

    def _update_focus_btn(self, is_active: bool):
        """Update focus mode button text and color."""
        status_text = self.tr("Focus Mode: ON") if is_active else self.tr("Focus Mode: OFF")
        color = "#a6e3a1" if is_active else "#6c7086"
        self._focus_mode_btn.setText("%s" % status_text)
        self._focus_mode_btn.setProperty("accentColor", color)
        self._focus_mode_btn.style().unpolish(self._focus_mode_btn)
        self._focus_mode_btn.style().polish(self._focus_mode_btn)

    # ==================================================================
    # Helpers
    # ==================================================================

    def _reboot(self):
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import QProcess

        reply = QMessageBox.question(
            self,
            self.tr("Reboot Now?"),
            self.tr("Reboot now to apply pending changes?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            binary, args, _ = PrivilegedCommand.systemctl("reboot")
            QProcess.startDetached(binary, args)

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("dashboardCard")
        return card

    @staticmethod
    def _action_btn(text: str, icon: str, color: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("quickActionButton")
        btn.setAccessibleName(text)
        btn.setProperty("accentColor", color)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            btn.setIcon(get_qicon(icon, size=17))
        except TypeError as e:
            logger.debug("Skipping quick action icon setup: %s", e)
        btn.setIconSize(QSize(17, 17))
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
                    mp, fstype = parts[1], parts[2]
                    if fstype in ("ext4", "btrfs", "xfs", "f2fs", "vfat", "ntfs"):
                        if mp not in mounts and not mp.startswith("/snap"):
                            mounts.append(mp)
        except OSError:
            logger.debug("Failed to read mount points", exc_info=True)
        return mounts[:6]
