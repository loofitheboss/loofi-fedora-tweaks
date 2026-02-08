"""
Notification Panel - Slide-out notification display.
Part of v13.5 UX Polish.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
import time


class NotificationCard(QFrame):
    """Single notification card widget."""

    def __init__(self, notification, on_dismiss=None, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { border: 1px solid #45475a; border-radius: 8px; padding: 8px; margin: 2px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Header row
        header = QHBoxLayout()
        title = QLabel(f"<b>{notification.title}</b>")
        header.addWidget(title)

        dismiss_btn = QPushButton("x")
        dismiss_btn.setFixedSize(20, 20)
        dismiss_btn.setStyleSheet("QPushButton { border: none; color: #a6adc8; } QPushButton:hover { color: #f38ba8; }")
        if on_dismiss:
            dismiss_btn.clicked.connect(lambda: on_dismiss(notification.id))
        header.addWidget(dismiss_btn)
        layout.addLayout(header)

        # Message
        msg = QLabel(notification.message)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #a6adc8;")
        layout.addWidget(msg)

        # Timestamp
        elapsed = int(time.time() - notification.timestamp)
        if elapsed < 60:
            time_str = "Just now"
        elif elapsed < 3600:
            time_str = f"{elapsed // 60}m ago"
        elif elapsed < 86400:
            time_str = f"{elapsed // 3600}h ago"
        else:
            time_str = f"{elapsed // 86400}d ago"

        ts = QLabel(time_str)
        ts.setStyleSheet("color: #585b70; font-size: 11px;")
        layout.addWidget(ts)


class NotificationPanel(QWidget):
    """Slide-out notification panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        self.setStyleSheet("background-color: #1e1e2e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QHBoxLayout()
        title = QLabel(self.tr("<b>Notifications</b>"))
        title.setStyleSheet("font-size: 16px;")
        header.addWidget(title)

        self.badge = QLabel("0")
        self.badge.setStyleSheet(
            "background-color: #f38ba8; color: #1e1e2e; border-radius: 10px; "
            "padding: 2px 8px; font-size: 12px; font-weight: bold;"
        )
        header.addWidget(self.badge)
        header.addStretch()

        mark_read_btn = QPushButton(self.tr("Mark all read"))
        mark_read_btn.setStyleSheet("QPushButton { border: none; color: #89b4fa; } QPushButton:hover { color: #b4befe; }")
        mark_read_btn.clicked.connect(self._mark_all_read)
        header.addWidget(mark_read_btn)

        layout.addLayout(header)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.cards_widget)

        layout.addWidget(scroll)

        self.refresh()

    def refresh(self):
        """Refresh notification cards."""
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from utils.notification_center import NotificationCenter
        nc = NotificationCenter()

        notifications = nc.get_recent(20)
        self.badge.setText(str(nc.get_unread_count()))
        self.badge.setVisible(nc.get_unread_count() > 0)

        if not notifications:
            empty = QLabel(self.tr("No notifications"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #585b70; padding: 40px;")
            self.cards_layout.addWidget(empty)
        else:
            for notif in notifications:
                card = NotificationCard(notif, on_dismiss=self._dismiss)
                self.cards_layout.addWidget(card)

    def _dismiss(self, notification_id: str):
        from utils.notification_center import NotificationCenter
        NotificationCenter().dismiss(notification_id)
        self.refresh()

    def _mark_all_read(self):
        from utils.notification_center import NotificationCenter
        NotificationCenter().mark_all_read()
        self.refresh()
