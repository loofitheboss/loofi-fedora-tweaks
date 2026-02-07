"""
Base Tab - Common base class for all tabs with command execution.
Part of v10.0 "Zenith Update" - kills code duplication across 15+ tabs.

Provides:
- CommandRunner wiring (output_received, finished, error_occurred, progress_update)
- Shared output area (QTextEdit)
- Common run_command / append_output / command_finished pattern
- Section builder helper
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QTextEdit, QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt
from utils.command_runner import CommandRunner


class BaseTab(QWidget):
    """Common base class for all tabs that execute system commands."""

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
        pass

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
