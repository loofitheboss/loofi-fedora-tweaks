"""
Notification Toast — v29.0 "Usability & Polish"

Slide-in toast widget that appears at the top-right of the main window
when a new notification is added to NotificationCenter.

Usage::

    from ui.notification_toast import NotificationToast

    toast = NotificationToast(parent_window)
    toast.show_toast("Update Complete", "All packages updated successfully.")
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QPainter, QColor, QPainterPath


# Category → accent color mapping (Abyss palette)
_CATEGORY_COLORS = {
    "general": "#39c5cf",       # teal accent
    "overview": "#39c5cf",      # teal
    "manage": "#b78eff",        # purple
    "hardware": "#e8b84d",      # amber
    "network & security": "#e8556d",  # coral
    "personalize": "#b78eff",   # purple
    "developer": "#3dd68c",     # green
    "automation": "#39c5cf",    # teal
    "health & logs": "#3dd68c",  # green
    "health": "#3dd68c",
    "profile": "#b78eff",
    "security": "#e8556d",
    "system": "#e8b84d",
}


class NotificationToast(QWidget):
    """Animated slide-in toast notification widget."""

    DISPLAY_MS = 4000  # Auto-hide after 4 seconds
    TOAST_WIDTH = 360
    TOAST_HEIGHT = 72

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.TOAST_WIDTH, self.TOAST_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._accent_color = QColor("#39c5cf")
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._slide_out)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 10, 10)

        # Accent bar is painted in paintEvent

        self._icon_label = QLabel("🔔")
        self._icon_label.setObjectName("toastIcon")
        self._icon_label.setFixedWidth(28)
        layout.addWidget(self._icon_label)

        # Text area
        from PyQt6.QtWidgets import QVBoxLayout
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        self._title_label = QLabel("")
        self._title_label.setObjectName("toastTitle")
        text_col.addWidget(self._title_label)

        self._message_label = QLabel("")
        self._message_label.setObjectName("toastMessage")
        self._message_label.setWordWrap(True)
        text_col.addWidget(self._message_label)

        layout.addLayout(text_col, 1)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setObjectName("toastCloseBtn")
        close_btn.clicked.connect(self._slide_out)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

    def show_toast(
        self,
        title: str,
        message: str,
        category: str = "general",
    ) -> None:
        """Display a toast notification with slide-in animation."""
        self._title_label.setText(title)
        self._message_label.setText(message[:120])  # Truncate long messages
        self._accent_color = QColor(_CATEGORY_COLORS.get(category, "#39c5cf"))

        # Position at top-right of parent
        if self.parent():
            parent = self.parent()
            x = parent.width() - self.TOAST_WIDTH - 16  # type: ignore[union-attr]
            y_start = -self.TOAST_HEIGHT
            y_end = 60  # Below breadcrumb bar

            self.move(x, y_start)
            self.show()
            self.raise_()

            # Slide-in animation
            self._anim = QPropertyAnimation(self, b"pos")
            self._anim.setDuration(300)
            self._anim.setStartValue(QPoint(x, y_start))
            self._anim.setEndValue(QPoint(x, y_end))
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.start()

            self._auto_hide_timer.start(self.DISPLAY_MS)
        else:
            self.show()
            self._auto_hide_timer.start(self.DISPLAY_MS)

    def _slide_out(self) -> None:
        """Slide out and hide."""
        self._auto_hide_timer.stop()

        if self.parent():
            current_pos = self.pos()
            end_pos = QPoint(current_pos.x(), -self.TOAST_HEIGHT)

            self._anim_out = QPropertyAnimation(self, b"pos")
            self._anim_out.setDuration(200)
            self._anim_out.setStartValue(current_pos)
            self._anim_out.setEndValue(end_pos)
            self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
            self._anim_out.finished.connect(self.hide)
            self._anim_out.start()
        else:
            self.hide()

    def paintEvent(self, event):
        """Custom paint with rounded rectangle background and accent bar."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 10.0, 10.0)
        painter.fillPath(path, QColor("#1c2030"))

        # Left accent bar
        accent_path = QPainterPath()
        accent_path.addRoundedRect(0.0, 0.0, 4.0, float(self.height()), 2.0, 2.0)
        painter.fillPath(accent_path, self._accent_color)

        # Border
        painter.setPen(QColor("#2d3348"))
        painter.drawPath(path)

        painter.end()
