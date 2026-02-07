"""
Processes Tab - Process monitor and management interface.
Part of v9.2 "Pulse" update.

Provides a real-time process table with sorting, filtering,
and process control (kill, renice) via right-click context menu.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox,
    QInputDialog, QFrame, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush

from utils.processes import ProcessManager


class ProcessesTab(QWidget):
    """Process monitor tab with real-time process listing and control."""

    # Catppuccin Mocha color constants
    COLOR_BASE = "#1e1e2e"
    COLOR_SURFACE0 = "#313244"
    COLOR_SURFACE1 = "#45475a"
    COLOR_SUBTEXT0 = "#a6adc8"
    COLOR_TEXT = "#cdd6f4"
    COLOR_BLUE = "#89b4fa"
    COLOR_GREEN = "#a6e3a1"
    COLOR_RED = "#f38ba8"
    COLOR_YELLOW = "#f9e2af"
    COLOR_MAUVE = "#cba6f7"
    COLOR_PEACH = "#fab387"

    def __init__(self):
        super().__init__()
        self._show_all = True  # True = all processes, False = my processes only
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
        import os
        try:
            return os.getlogin()
        except OSError:
            import pwd
            return pwd.getpwuid(os.getuid()).pw_name

    def init_ui(self):
        """Initialize the UI components."""
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
        self.summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLOR_SURFACE0};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        summary_layout.setContentsMargins(15, 8, 15, 8)

        self.lbl_summary = QLabel(self.tr("Total: 0 | Running: 0 | Sleeping: 0 | Zombie: 0"))
        self.lbl_summary.setStyleSheet(f"""
            color: {self.COLOR_SUBTEXT0};
            font-size: 13px;
            font-weight: bold;
        """)
        summary_layout.addWidget(self.lbl_summary)
        summary_layout.addStretch()
        layout.addWidget(self.summary_frame)

        # Controls bar
        controls_layout = QHBoxLayout()

        # Sort controls
        controls_layout.addWidget(QLabel(self.tr("Sort by:")))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem(self.tr("CPU"), "cpu")
        self.sort_combo.addItem(self.tr("Memory"), "memory")
        self.sort_combo.addItem(self.tr("Name"), "name")
        self.sort_combo.addItem(self.tr("PID"), "pid")
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.COLOR_SURFACE0};
                border: 1px solid {self.COLOR_SURFACE1};
                border-radius: 6px;
                padding: 5px 10px;
                color: {self.COLOR_TEXT};
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        controls_layout.addWidget(self.sort_combo)

        controls_layout.addStretch()

        # Show All / My Processes toggle
        self.btn_toggle_filter = QPushButton(self.tr("My Processes"))
        self.btn_toggle_filter.setCheckable(True)
        self.btn_toggle_filter.setChecked(False)
        self.btn_toggle_filter.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLOR_SURFACE0};
                border: 1px solid {self.COLOR_SURFACE1};
                color: {self.COLOR_TEXT};
                padding: 6px 14px;
                border-radius: 6px;
            }}
            QPushButton:checked {{
                background-color: {self.COLOR_BLUE};
                color: {self.COLOR_BASE};
                border: 1px solid {self.COLOR_BLUE};
            }}
            QPushButton:hover {{
                background-color: {self.COLOR_SURFACE1};
            }}
            QPushButton:checked:hover {{
                background-color: {self.COLOR_BLUE};
            }}
        """)
        self.btn_toggle_filter.toggled.connect(self._on_filter_toggled)
        controls_layout.addWidget(self.btn_toggle_filter)

        # Refresh button
        btn_refresh = QPushButton(self.tr("Refresh"))
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLOR_SURFACE0};
                border: 1px solid {self.COLOR_SURFACE1};
                color: {self.COLOR_TEXT};
                padding: 6px 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.COLOR_SURFACE1};
            }}
        """)
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
        self.process_tree.setSortingEnabled(False)  # We handle sorting ourselves
        self.process_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.process_tree.customContextMenuRequested.connect(self._show_context_menu)

        # Column widths
        self.process_tree.setColumnWidth(0, 70)   # PID
        self.process_tree.setColumnWidth(1, 200)  # Name
        self.process_tree.setColumnWidth(2, 100)  # User
        self.process_tree.setColumnWidth(3, 70)   # CPU%
        self.process_tree.setColumnWidth(4, 80)   # Memory%
        self.process_tree.setColumnWidth(5, 90)   # Memory
        self.process_tree.setColumnWidth(6, 60)   # State
        self.process_tree.setColumnWidth(7, 50)   # Nice

        # Stretch the Name column to fill available space
        tree_header = self.process_tree.header()
        tree_header.setStretchLastSection(False)
        tree_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.process_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.COLOR_SURFACE0};
                border: 1px solid {self.COLOR_SURFACE1};
                border-radius: 8px;
                color: {self.COLOR_TEXT};
                font-family: monospace;
                font-size: 12px;
            }}
            QTreeWidget::item {{
                padding: 4px 2px;
            }}
            QTreeWidget::item:selected {{
                background-color: {self.COLOR_SURFACE1};
            }}
            QHeaderView::section {{
                background-color: {self.COLOR_BASE};
                color: {self.COLOR_SUBTEXT0};
                border: none;
                border-bottom: 1px solid {self.COLOR_SURFACE1};
                padding: 6px 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QTreeWidget::item:alternate {{
                background-color: {self.COLOR_BASE};
            }}
        """)

        layout.addWidget(self.process_tree)

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

    def refresh_processes(self):
        """Refresh the process list and summary bar."""
        # Update summary counts
        counts = ProcessManager.get_process_count()
        self.lbl_summary.setText(
            self.tr("Total: {total} | Running: {running} | Sleeping: {sleeping} | Zombie: {zombie}").format(
                total=counts["total"],
                running=counts["running"],
                sleeping=counts["sleeping"],
                zombie=counts["zombie"],
            )
        )

        # Get all processes
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
                pass

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
            item.setTextAlignment(0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(5, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(7, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Store PID in UserRole for context menu
            item.setData(0, Qt.ItemDataRole.UserRole, proc.pid)

            # Color-code: zombie processes in red
            if proc.state == "Z":
                for col in range(self.process_tree.columnCount()):
                    item.setForeground(col, red_brush)

            # Color-code: high CPU (>50%) in yellow
            elif proc.cpu_percent > 50.0:
                for col in range(self.process_tree.columnCount()):
                    item.setForeground(col, yellow_brush)

            self.process_tree.addTopLevelItem(item)

            # Re-select previously selected item
            if selected_pid is not None and proc.pid == selected_pid:
                new_selected_item = item

        # Restore selection and scroll position
        if new_selected_item:
            self.process_tree.setCurrentItem(new_selected_item)
        if scrollbar:
            scrollbar.setValue(scroll_pos)

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
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.COLOR_SURFACE0};
                border: 1px solid {self.COLOR_SURFACE1};
                border-radius: 6px;
                color: {self.COLOR_TEXT};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.COLOR_SURFACE1};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self.COLOR_SURFACE1};
                margin: 4px 8px;
            }}
        """)

        # Kill (SIGTERM)
        action_term = menu.addAction(self.tr("Kill Process (SIGTERM)"))
        action_term.triggered.connect(lambda: self._kill_process(pid, name, 15))

        # Force kill (SIGKILL)
        action_kill = menu.addAction(self.tr("Force Kill (SIGKILL)"))
        action_kill.triggered.connect(lambda: self._kill_process(pid, name, 9))

        menu.addSeparator()

        # Renice
        action_renice = menu.addAction(self.tr("Renice..."))
        action_renice.triggered.connect(lambda: self._renice_process(pid, name))

        menu.exec(self.process_tree.viewport().mapToGlobal(position))

    def _kill_process(self, pid: int, name: str, signal: int):
        """Kill a process after confirmation."""
        signal_name = "SIGTERM" if signal == 15 else "SIGKILL"
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Kill"),
            self.tr("Send {signal} to process '{name}' (PID {pid})?").format(
                signal=signal_name, name=name, pid=pid
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, message = ProcessManager.kill_process(pid, signal)
            if success:
                QMessageBox.information(self, self.tr("Success"), message)
                self.refresh_processes()
            else:
                QMessageBox.warning(self, self.tr("Error"), message)

    def _renice_process(self, pid: int, name: str):
        """Renice a process after showing an input dialog."""
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Renice"),
            self.tr("Change priority of process '{name}' (PID {pid})?").format(
                name=name, pid=pid
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        nice_value, ok = QInputDialog.getInt(
            self,
            self.tr("Renice Process"),
            self.tr("Enter new nice value (-20 to 19).\n"
                     "Lower = higher priority, higher = lower priority:"),
            value=0,
            min=-20,
            max=19,
        )

        if ok:
            success, message = ProcessManager.renice_process(pid, nice_value)
            if success:
                QMessageBox.information(self, self.tr("Success"), message)
                self.refresh_processes()
            else:
                QMessageBox.warning(self, self.tr("Error"), message)
