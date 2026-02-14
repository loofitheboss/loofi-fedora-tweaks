"""
Confirm Action Dialog — v29.0 "Usability & Polish"

A rich confirmation dialog for dangerous/destructive operations.
Displays action description, undo info, and optional snapshot checkbox.
Integrates with SafetyManager and SettingsManager.

Usage::

    from ui.confirm_dialog import ConfirmActionDialog

    if ConfirmActionDialog.confirm(
        parent=self,
        action="Remove 12 packages",
        description="This will uninstall the selected packages and their unused dependencies.",
        undo_hint="You can reinstall them later from the Software tab.",
        offer_snapshot=True,
    ):
        # User confirmed — proceed
        ...
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from utils.log import get_logger
from utils.settings import SettingsManager

logger = get_logger(__name__)


class ConfirmActionDialog(QDialog):
    """Rich confirmation dialog with action details and snapshot option."""

    def __init__(
        self,
        parent=None,
        action: str = "",
        description: str = "",
        undo_hint: str = "",
        offer_snapshot: bool = False,
        command_preview: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Confirm Action"))
        self.setMinimumWidth(440)
        self.setMaximumWidth(600)
        self._snapshot_requested = False
        self._command_preview = command_preview

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Warning icon + action header
        header_row = QHBoxLayout()
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 28px;")
        header_row.addWidget(icon_label)

        action_label = QLabel(action or self.tr("Are you sure?"))
        action_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        action_label.setWordWrap(True)
        header_row.addWidget(action_label, 1)
        layout.addLayout(header_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2d3348;")
        layout.addWidget(sep)

        # Description
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #9da7bf; font-size: 13px;")
            layout.addWidget(desc_label)

        # Undo hint
        if undo_hint:
            undo_frame = QFrame()
            undo_frame.setStyleSheet(
                "QFrame { background-color: #0b0e14; border: 1px solid #2d3348; "
                "border-radius: 8px; padding: 10px; }"
            )
            undo_layout = QHBoxLayout(undo_frame)
            undo_layout.setContentsMargins(10, 8, 10, 8)
            undo_icon = QLabel("💡")
            undo_icon.setStyleSheet("font-size: 16px;")
            undo_layout.addWidget(undo_icon)
            undo_text = QLabel(undo_hint)
            undo_text.setWordWrap(True)
            undo_text.setStyleSheet("color: #39c5cf; font-size: 12px;")
            undo_layout.addWidget(undo_text, 1)
            layout.addWidget(undo_frame)

        # Snapshot checkbox
        self.snapshot_cb = None
        if offer_snapshot:
            self.snapshot_cb = QCheckBox(
                self.tr("Create system snapshot before proceeding")
            )
            self.snapshot_cb.setChecked(True)
            self.snapshot_cb.setStyleSheet("font-size: 12px; padding: 4px 0;")
            layout.addWidget(self.snapshot_cb)

        # Don't ask again checkbox
        self.dont_ask_cb = QCheckBox(
            self.tr("Don't ask for confirmation again"))
        self.dont_ask_cb.setStyleSheet("font-size: 11px; color: #5c6578;")
        layout.addWidget(self.dont_ask_cb)

        # Command preview area (hidden by default, v35.0)
        self._preview_area = None
        if command_preview:
            self._preview_area = QTextEdit()
            self._preview_area.setReadOnly(True)
            self._preview_area.setPlainText(command_preview)
            self._preview_area.setStyleSheet(
                "QTextEdit { background-color: #0b0e14; color: #c8d0e0; "
                "border: 1px solid #2d3348; border-radius: 6px; "
                "font-family: monospace; font-size: 12px; padding: 8px; }"
            )
            self._preview_area.setMaximumHeight(100)
            self._preview_area.setVisible(False)
            layout.addWidget(self._preview_area)

        # Buttons
        btn_row = QHBoxLayout()

        # Preview button (v35.0 Fortress)
        if command_preview:
            preview_btn = QPushButton(self.tr("🔍 Preview"))
            preview_btn.setMinimumWidth(90)
            preview_btn.setToolTip(
                self.tr("Show the exact command that will run"))
            preview_btn.clicked.connect(self._toggle_preview)
            btn_row.addWidget(preview_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton(self.tr("Confirm"))
        confirm_btn.setObjectName("dangerAction")
        confirm_btn.setMinimumWidth(100)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

    def _on_confirm(self):
        """Handle confirm button click."""
        # Save "don't ask" preference
        if self.dont_ask_cb.isChecked():
            try:
                mgr = SettingsManager.instance()
                mgr.set("confirm_dangerous_actions", False)
                mgr.save()
            except Exception:
                logger.debug(
                    "Failed to save confirmation preference", exc_info=True)

        # Record snapshot request
        if self.snapshot_cb and self.snapshot_cb.isChecked():
            self._snapshot_requested = True

        self.accept()

    def _toggle_preview(self):
        """Toggle the command preview area visibility."""
        if self._preview_area:
            visible = self._preview_area.isVisible()
            self._preview_area.setVisible(not visible)
            self.adjustSize()

    @property
    def snapshot_requested(self) -> bool:
        """Whether the user opted to create a snapshot."""
        return self._snapshot_requested

    @staticmethod
    def confirm(
        parent=None,
        action: str = "",
        description: str = "",
        undo_hint: str = "",
        offer_snapshot: bool = False,
        force: bool = False,
        command_preview: str = "",
    ) -> bool:
        """
        Convenience method to show a confirmation dialog.

        Returns True if the user confirmed, False if cancelled.
        If ``confirm_dangerous_actions`` is disabled in settings and
        ``force`` is False, returns True immediately (user opted out).
        ``command_preview`` (v35.0): optional command string to show via Preview button.
        """
        if not force:
            try:
                mgr = SettingsManager.instance()
                if not mgr.get("confirm_dangerous_actions"):
                    return True
            except Exception:
                logger.debug(
                    "Failed to read confirmation preference", exc_info=True)

        dialog = ConfirmActionDialog(
            parent=parent,
            action=action,
            description=description,
            undo_hint=undo_hint,
            offer_snapshot=offer_snapshot,
            command_preview=command_preview,
        )
        return dialog.exec() == QDialog.DialogCode.Accepted
