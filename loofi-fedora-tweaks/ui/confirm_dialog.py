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
    """Rich confirmation dialog with action details, risk level, and snapshot option."""

    # Risk level constants
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"

    def __init__(
        self,
        parent=None,
        action: str = "",
        description: str = "",
        undo_hint: str = "",
        offer_snapshot: bool = False,
        command_preview: str = "",
        risk_level: str = "",
        action_key: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Confirm Action"))
        self.setMinimumWidth(440)
        self.setMaximumWidth(600)
        self._snapshot_requested = False
        self._command_preview = command_preview
        self._action_key = action_key  # For per-action "don't ask again"

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Warning icon + action header + risk badge
        header_row = QHBoxLayout()
        icon_label = QLabel("⚠️")
        icon_label.setObjectName("confirmIcon")
        header_row.addWidget(icon_label)

        action_label = QLabel(action or self.tr("Are you sure?"))
        action_label.setObjectName("confirmAction")
        action_label.setWordWrap(True)
        header_row.addWidget(action_label, 1)

        # Risk level badge (v38.0)
        if risk_level:
            badge_text = {
                self.RISK_LOW: self.tr("LOW"),
                self.RISK_MEDIUM: self.tr("MEDIUM"),
                self.RISK_HIGH: self.tr("HIGH"),
            }.get(risk_level, risk_level.upper())
            risk_badge = QLabel(badge_text)
            risk_badge.setObjectName("riskBadge")
            risk_badge.setProperty("level", risk_level)
            header_row.addWidget(risk_badge)

        layout.addLayout(header_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("confirmSeparator")
        layout.addWidget(sep)

        # Description
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setObjectName("confirmDescription")
            layout.addWidget(desc_label)

        # Undo hint
        if undo_hint:
            undo_frame = QFrame()
            undo_frame.setObjectName("confirmUndoFrame")
            undo_layout = QHBoxLayout(undo_frame)
            undo_layout.setContentsMargins(10, 8, 10, 8)
            undo_icon = QLabel("💡")
            undo_icon.setObjectName("confirmIcon")
            undo_layout.addWidget(undo_icon)
            undo_text = QLabel(undo_hint)
            undo_text.setWordWrap(True)
            undo_text.setObjectName("confirmUndoText")
            undo_layout.addWidget(undo_text, 1)
            layout.addWidget(undo_frame)

        # Snapshot checkbox
        self.snapshot_cb = None
        if offer_snapshot:
            self.snapshot_cb = QCheckBox(
                self.tr("Create system snapshot before proceeding")
            )
            self.snapshot_cb.setChecked(True)
            self.snapshot_cb.setObjectName("confirmSnapshot")
            layout.addWidget(self.snapshot_cb)

        # Don't ask again checkbox
        self.dont_ask_cb = QCheckBox(
            self.tr("Don't ask for confirmation again"))
        self.dont_ask_cb.setObjectName("confirmDontAsk")
        layout.addWidget(self.dont_ask_cb)

        # Command preview area (hidden by default, v35.0)
        self._preview_area = None
        if command_preview:
            self._preview_area = QTextEdit()
            self._preview_area.setReadOnly(True)
            self._preview_area.setPlainText(command_preview)
            self._preview_area.setObjectName("confirmPreview")
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
        # Save "don't ask" preference (per-action if action_key provided, global otherwise)
        if self.dont_ask_cb.isChecked():
            try:
                mgr = SettingsManager.instance()
                if self._action_key:
                    # Per-action suppression (v38.0)
                    suppressed = mgr.get("suppressed_confirmations") or []
                    if self._action_key not in suppressed:
                        suppressed.append(self._action_key)
                    mgr.set("suppressed_confirmations", suppressed)
                else:
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
        risk_level: str = "",
        action_key: str = "",
    ) -> bool:
        """
        Convenience method to show a confirmation dialog.

        Returns True if the user confirmed, False if cancelled.
        If ``confirm_dangerous_actions`` is disabled in settings and
        ``force`` is False, returns True immediately (user opted out).
        ``command_preview`` (v35.0): optional command string to show via Preview button.
        ``risk_level`` (v38.0): "low", "medium", or "high" to show risk badge.
        ``action_key`` (v38.0): unique key for per-action "don't ask again".
        """
        if not force:
            try:
                mgr = SettingsManager.instance()
                # Check per-action suppression first (v38.0)
                if action_key:
                    suppressed = mgr.get("suppressed_confirmations") or []
                    if action_key in suppressed:
                        return True
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
            risk_level=risk_level,
            action_key=action_key,
        )
        return dialog.exec() == QDialog.DialogCode.Accepted
