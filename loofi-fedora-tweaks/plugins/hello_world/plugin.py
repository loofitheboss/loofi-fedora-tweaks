"""
Hello World Plugin - Example plugin demonstrating the Loofi Plugin SDK.
Shows how to create a simple plugin with a widget and CLI commands.
"""

import logging

from utils.plugin_base import LoofiPlugin, PluginInfo

logger = logging.getLogger("loofi.plugins.hello_world")


class HelloWorldPlugin(LoofiPlugin):
    """A minimal example plugin demonstrating the Loofi Plugin SDK."""

    @property
    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="Hello World",
            version="1.0.0",
            author="Loofi Team",
            description="Example plugin demonstrating the Loofi Plugin SDK",
            icon="\U0001f44b",
        )

    def create_widget(self):
        """Create and return a simple greeting widget."""
        from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel("Hello from the Loofi Plugin SDK!")
        layout.addWidget(label)

        button = QPushButton("Say Hello")
        button.clicked.connect(lambda: label.setText("Hello World!"))
        layout.addWidget(button)

        layout.addStretch()
        return widget

    def get_cli_commands(self) -> dict:
        """Return CLI commands provided by this plugin."""
        return {
            "hello": lambda: "Hello from the Loofi Plugin SDK!",
        }

    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        logger.info("Hello World plugin loaded")

    def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        logger.info("Hello World plugin unloaded")
