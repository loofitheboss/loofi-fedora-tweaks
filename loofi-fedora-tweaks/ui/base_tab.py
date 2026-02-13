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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QTextEdit, QTableWidget, QTableWidgetItem
)
from PyQt6.QtGui import QColor, QPalette
from utils.command_runner import CommandRunner
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata

logger = logging.getLogger(__name__)

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
    _BaseTabBases = (PluginInterface,)
else:
    _BaseTabBases = (_BaseWidget, PluginInterface)


class BaseTab(*_BaseTabBases):
    """Common base class for all tabs that execute system commands."""

    # Subclasses MUST override _METADATA with their own PluginMetadata
    _METADATA: PluginMetadata = _STUB_META

    def __init__(self):
        super().__init__()
        self._commands_enabled = True

        # Output area (shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        self.output_area.setObjectName("outputArea")

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
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )

    def on_command_finished(self, exit_code):
        """Handle command completion."""
        self.append_output(
            self.tr("\nCommand finished with exit code: {}").format(exit_code)
        )

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
        """Add the standard output area to a layout."""
        layout.addWidget(QLabel(self.tr("Output Log:")))
        layout.addWidget(self.output_area)

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
        - Explicit text color via palette for data rows

        Usage::

            self.my_table = QTableWidget(0, 4)
            BaseTab.configure_table(self.my_table)
        """
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(36)
        table.setShowGrid(True)

        # Force text color via palette — QSS alone doesn't always apply to items
        pal = table.palette()
        pal.setColor(QPalette.ColorRole.Text, QColor("#e4e8f4"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#e4e8f4"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#1e1e2e"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#252540"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#585b70"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        table.setPalette(pal)

    @staticmethod
    def make_table_item(text, color: str = "#e4e8f4") -> QTableWidgetItem:
        """Create a table item with explicit foreground color for readability."""
        item = QTableWidgetItem(str(text))
        item.setForeground(QColor(color))
        return item

    @staticmethod
    def set_table_empty_state(table: QTableWidget, message: str, color: str = "#a6adc8") -> None:
        """Render a single full-width empty-state row in a table."""
        table.clearSpans()
        table.setRowCount(1)
        table.setItem(0, 0, BaseTab.make_table_item(message, color=color))
        if table.columnCount() > 1:
            table.setSpan(0, 0, 1, table.columnCount())
