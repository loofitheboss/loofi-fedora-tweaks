"""
Base Tab - Common base class for all tabs with command execution.
Part of v11.0 "Aurora Update" - kills code duplication across 15+ tabs.

Provides:
- CommandRunner wiring (output_received, finished, error_occurred, progress_update)
- Shared output area (QTextEdit)
- Common run_command / append_output / command_finished pattern
- Section builder helper
- configure_table() for consistent table styling

v25.0: Implements PluginInterface as a mixin for plugin architecture support.
v31.0.2: Added configure_table() for readable data rows across all tabs.
"""

import logging

from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from utils.command_runner import CommandRunner

logger = logging.getLogger(__name__)


class _ReadableTableItemDelegate(QStyledItemDelegate):
    """Force stable table item painting across fonts, DPI, and QSS variants."""

    def __init__(self, min_row_height: int, parent=None):
        super().__init__(parent)
        self._min_row_height = min_row_height

    def initStyleOption(self, option, index):
        """Ensure text stays vertically centered in every table cell."""
        super().initStyleOption(option, index)
        option.displayAlignment = (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

    def sizeHint(self, option, index) -> QSize:
        """Guarantee a non-clipped row height for rendered item text."""
        hint = super().sizeHint(option, index)
        if hint.height() < self._min_row_height:
            hint.setHeight(self._min_row_height)
        return hint


_STUB_META = PluginMetadata(
    id="__stub__",
    name="Unnamed Tab",
    description="",
    category="General",
    icon="",
    badge="",
)


_BaseWidget = QWidget if isinstance(QWidget, type) else object


if _BaseWidget is object:
    _BaseTabBases: tuple[type, ...] = (PluginInterface,)
else:
    _BaseTabBases = (_BaseWidget, PluginInterface)


class BaseTab(*_BaseTabBases):  # type: ignore[misc]
    """Common base class for all tabs that execute system commands."""

    # Subclasses MUST override _METADATA with their own PluginMetadata
    _METADATA: PluginMetadata = _STUB_META
    _DEFAULT_TABLE_VISIBLE_ROWS = 3

    def __init__(self):
        super().__init__()
        self._commands_enabled = True

        # Output area (shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        self.output_area.setObjectName("outputArea")
        self.output_area.setAccessibleName(self.tr("Command output"))

        # Command runner
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.on_command_finished)
        self.runner.error_occurred.connect(self.on_error)
        self.runner.progress_update.connect(self.on_progress)

    def run_command(self, cmd, args, description=""):
        """Execute a command with output logging."""
        self.output_area.clear()
        if description:
            self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        """Append text to the output area and scroll to bottom."""
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def on_command_finished(self, exit_code):
        """Handle command completion."""
        self.append_output(
            self.tr("\nCommand finished with exit code: {}").format(exit_code)
        )
        if exit_code == 0:
            self.show_success(self.tr("Command completed successfully"))
        else:
            self.show_error(self.tr("Command failed (exit code {})").format(exit_code))

    def on_error(self, error_msg):
        """Handle command errors."""
        self.append_output(f"\n[ERROR] {error_msg}\n")

    def on_progress(self, percent, status):
        """Handle progress updates. Override in subclasses for custom behavior."""

    def add_section(self, title, widgets) -> QGroupBox:
        """Create a group box section with a list of widgets."""
        group = QGroupBox(self.tr(title))
        layout = QVBoxLayout(group)
        for widget in widgets:
            if isinstance(widget, QWidget):
                layout.addWidget(widget)
            else:
                layout.addLayout(widget)
        return group

    def add_output_section(self, layout):
        """Add the standard output area with Copy/Save/Cancel toolbar to a layout."""
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel(self.tr("Output Log:")))
        header_row.addStretch()

        # Copy button (v38.0)
        copy_btn = QPushButton(self.tr("📋 Copy"))
        copy_btn.setObjectName("outputCopyBtn")
        copy_btn.setToolTip(self.tr("Copy output to clipboard"))
        copy_btn.clicked.connect(self._copy_output)
        header_row.addWidget(copy_btn)

        # Save button (v38.0)
        save_btn = QPushButton(self.tr("💾 Save"))
        save_btn.setObjectName("outputSaveBtn")
        save_btn.setToolTip(self.tr("Save output to file"))
        save_btn.clicked.connect(self._save_output)
        header_row.addWidget(save_btn)

        # Cancel button (v38.0)
        cancel_btn = QPushButton(self.tr("⏹ Cancel"))
        cancel_btn.setObjectName("outputCancelBtn")
        cancel_btn.setToolTip(self.tr("Cancel running command"))
        cancel_btn.clicked.connect(self._cancel_command)
        header_row.addWidget(cancel_btn)

        layout.addLayout(header_row)
        layout.addWidget(self.output_area)

    def _copy_output(self):
        """Copy the output area text to clipboard."""
        text = self.output_area.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)

    def _save_output(self):
        """Save the output area text to a file."""
        text = self.output_area.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Output"),
            "output.txt",
            self.tr("Text Files (*.txt);;All Files (*)"),
        )
        if path:
            try:
                with open(path, "w") as f:
                    f.write(text)
            except OSError as e:
                logger.debug("Failed to save output: %s", e)

    def _cancel_command(self):
        """Cancel the currently running command."""
        if self.runner:
            self.runner.cancel()

    # ---------------------------------------------------------------- Toast feedback

    def _find_main_window(self):
        """Walk up parent chain to find MainWindow (not self)."""
        widget = self.parent() if hasattr(self, 'parent') else None
        while widget is not None:
            if hasattr(widget, 'show_toast') and widget is not self:
                return widget
            widget = widget.parent() if hasattr(widget, 'parent') else None
        return None

    def show_toast(self, title: str, message: str, category: str = "general") -> None:
        """Show a toast notification via the MainWindow.

        Args:
            title: Toast title text.
            message: Toast message body.
            category: Notification category for accent color.
        """
        mw = self._find_main_window()
        if mw:
            mw.show_toast(title, message, category)

    def show_success(self, message: str) -> None:
        """Show a success toast notification."""
        self.show_toast(self.tr("Success"), message, "general")

    def show_error(self, message: str) -> None:
        """Show an error toast notification."""
        self.show_toast(self.tr("Error"), message, "security")

    def show_info(self, message: str) -> None:
        """Show an informational toast notification."""
        self.show_toast(self.tr("Info"), message, "system")

    # ---------------------------------------------------------------- PluginInterface

    def metadata(self) -> PluginMetadata:
        """Return plugin metadata. Logs a warning if using the stub (unset) metadata."""
        if self._METADATA.id == "__stub__":
            logger.warning(
                "%s does not override _METADATA — using stub. "
                "Set _METADATA = PluginMetadata(...) on the class.",
                type(self).__name__,
            )
        return self._METADATA

    def create_widget(self) -> QWidget:
        """Default: return self. Tabs that need fresh instances must override."""
        return self

    def set_context(self, context: dict) -> None:
        """Store context for tabs that need MainWindow or executor references."""
        self._plugin_context = context

    @staticmethod
    def configure_table(table):
        """Apply consistent table styling for readable data rows.

        Call this after creating any QTableWidget to ensure:
        - Alternating row colors for scanability
        - Proper row height for readability
        - Clean appearance (no row numbers)
        - Theme-aware colors via QSS objectName

        Usage::

            self.my_table = QTableWidget(0, 4)
            BaseTab.configure_table(self.my_table)
        """
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        # Account for fallback glyphs (emoji/status symbols) that can exceed base metrics.
        metrics = table.fontMetrics()
        probe_height = metrics.boundingRect("Ag 🟢 ✅ ⚠️").height()
        row_height = max(44, metrics.height() + 20, probe_height + 20)
        table.verticalHeader().setMinimumSectionSize(row_height)
        table.verticalHeader().setDefaultSectionSize(row_height)
        table.setItemDelegate(_ReadableTableItemDelegate(row_height, table))
        table.setWordWrap(False)
        table.setTextElideMode(Qt.TextElideMode.ElideRight)
        table.setShowGrid(True)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if table.property("maxVisibleRows") is None:
            table.setProperty("maxVisibleRows", BaseTab._DEFAULT_TABLE_VISIBLE_ROWS)
        table.setObjectName("baseTable")
        BaseTab.ensure_table_row_heights(table)

    @staticmethod
    def ensure_table_row_heights(table: QTableWidget) -> None:
        """Normalize existing row heights to the configured minimum."""
        header = table.verticalHeader()
        if header is None:
            return
        min_height = header.minimumSectionSize()
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)
            if table.rowHeight(row) < min_height:
                table.setRowHeight(row, min_height)
        max_rows = BaseTab._resolve_table_row_limit(table)
        BaseTab.fit_table_height(table, max_visible_rows=max_rows)

    @staticmethod
    def _resolve_table_row_limit(table: QTableWidget) -> int:
        """Read per-table visible row cap with a safe default."""
        max_rows = table.property("maxVisibleRows")
        if not isinstance(max_rows, int) or max_rows < 1:
            return BaseTab._DEFAULT_TABLE_VISIBLE_ROWS
        return max_rows

    @staticmethod
    def fit_table_height(table: QTableWidget, max_visible_rows: int = 4) -> None:
        """Fit a table to content rows while capping visible rows."""
        if max_visible_rows < 1:
            max_visible_rows = 1

        header = table.horizontalHeader()
        vertical_header = table.verticalHeader()
        row_height = (
            vertical_header.defaultSectionSize()
            if vertical_header is not None
            else max(36, table.fontMetrics().height() + 14)
        )
        header_height = header.height() if header is not None else 0
        frame = table.frameWidth() * 2
        h_scroll = table.horizontalScrollBar()
        scroll_h = h_scroll.sizeHint().height() if h_scroll is not None else 0
        rows = max(1, table.rowCount())
        visible_rows = min(rows, max_visible_rows)
        table_height = (
            header_height + (row_height * visible_rows) + frame + scroll_h + 8
        )

        table.setFixedHeight(table_height)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    @staticmethod
    def make_table_item(text, color: str = "") -> QTableWidgetItem:
        """Create a table item. Color is applied via QSS by default."""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        if color:
            item.setForeground(QColor(color))
        return item

    @staticmethod
    def set_table_empty_state(
        table: QTableWidget, message: str, color: str = ""
    ) -> None:
        """Render a single full-width empty-state row in a table."""
        table.clearSpans()
        table.setRowCount(1)
        msg_item = BaseTab.make_table_item(message, color=color)
        msg_item.setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        table.setItem(0, 0, msg_item)
        for col in range(1, table.columnCount()):
            table.setItem(0, col, BaseTab.make_table_item("", color=color))
        BaseTab.ensure_table_row_heights(table)
