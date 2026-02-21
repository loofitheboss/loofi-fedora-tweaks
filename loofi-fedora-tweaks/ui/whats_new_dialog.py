"""
What's New dialog - shows release highlights after version upgrade.
Part of v14.0 "Horizon Update".
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from utils.log import get_logger
from version import __version__, __version_codename__

logger = get_logger(__name__)


# Release notes for each version
RELEASE_NOTES = {
    "14.0.0": [
        "Update Checker - automatic update notifications from GitHub",
        "What's New dialog - see highlights after each upgrade",
        "Activity Feed - global history of configuration changes with undo",
        "Factory Reset - backup and restore configuration to defaults",
        "System tray: profile switching and power mode submenus",
        "10 new CLI commands: update-check, activity, backup, reset, and more",
        "Plugin lifecycle events: on_app_start, on_app_quit, on_tab_switch",
    ],
    "13.5.0": [
        "Settings tab with dark/light theme switching",
        "Catppuccin Latte light theme",
        "Keyboard shortcuts (Ctrl+1-9, Ctrl+Tab, F1)",
        "Sidebar search/filter",
        "Notification center with slide-out panel",
        "Tooltip constants module",
    ],
    "13.1.0": [
        "Exception cleanup across 20 files",
        "Security hardening: removed shell=True, localhost binding",
        "Rate limiter for network services",
        "188 new tests",
    ],
    "13.0.0": [
        "System profiles (Gaming, Development, Battery Saver, etc.)",
        "Health timeline with SQLite metrics tracking",
        "Plugin SDK v2 with permissions model",
        "Shell completions for bash, zsh, fish",
    ],
}


class WhatsNewDialog(QDialog):
    """Dialog showing what's new in the current version."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("What's New in Loofi Fedora Tweaks"))
        self.setMinimumSize(500, 400)
        self._dont_show = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            self.tr('What\'s New in v{version} "{codename}"').format(
                version=__version__, codename=__version_codename__
            )
        )
        header.setObjectName("whatsNewHeader")
        layout.addWidget(header)

        # Release notes
        notes_text = QTextEdit()
        notes_text.setReadOnly(True)

        content = ""
        notes = RELEASE_NOTES.get(__version__, [])
        if notes:
            for item in notes:
                content += f"  - {item}\n"
        else:
            content = self.tr("No release notes available for this version.")

        # Also show previous version notes
        versions = sorted(
            RELEASE_NOTES.keys(),
            key=lambda v: tuple(int(p) for p in v.split(".")),
            reverse=True,
        )
        for ver in versions:
            if ver == __version__:
                continue
            content += f"\n--- v{ver} ---\n"
            for item in RELEASE_NOTES[ver]:
                content += f"  - {item}\n"

        notes_text.setPlainText(content)
        layout.addWidget(notes_text)

        # Don't show again checkbox
        self.dont_show_cb = QCheckBox(self.tr("Don't show this again"))
        layout.addWidget(self.dont_show_cb)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton(self.tr("Got it!"))
        close_btn.setObjectName("whatsNewCloseBtn")
        close_btn.clicked.connect(self._on_close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _on_close(self):
        self._dont_show = self.dont_show_cb.isChecked()
        self.accept()

    @property
    def dont_show_again(self) -> bool:
        return bool(self._dont_show)

    @staticmethod
    def should_show() -> bool:
        """Check if the dialog should be shown based on last seen version."""
        try:
            from utils.settings import SettingsManager

            mgr = SettingsManager.instance()
            last_seen = mgr.get("last_seen_version", "0.0.0")
            return bool(last_seen != __version__)
        except (ImportError, RuntimeError, OSError, ValueError, TypeError) as e:
            logger.debug("Failed to check last seen version: %s", e)
            return True

    @staticmethod
    def mark_seen():
        """Mark the current version as seen."""
        try:
            from utils.settings import SettingsManager

            mgr = SettingsManager.instance()
            mgr.set("last_seen_version", __version__)
            mgr.save()
        except (ImportError, RuntimeError, OSError, ValueError, TypeError, AttributeError) as e:
            logger.debug("Failed to save last seen version: %s", e)
