"""
Tour Overlay — v47.0 UX Improvement.

Semi-transparent overlay widget that highlights UI elements during
the guided tour. Shows a spotlight cutout on the target widget with
a tooltip-style card containing step title, description, and
Next/Skip buttons.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QRegion

from utils.guided_tour import GuidedTourManager, TourStep


class TourOverlay(QWidget):
    """Full-window overlay that highlights widgets during the guided tour."""

    tour_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tourOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._steps = GuidedTourManager.get_tour_steps()
        self._current_step = 0
        self._target_rect = QRect()

        # Card widget
        self._card = QWidget(self)
        self._card.setObjectName("tourCard")
        self._card.setFixedWidth(320)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 16, 16, 12)
        card_layout.setSpacing(8)

        self._step_counter = QLabel()
        self._step_counter.setObjectName("tourStepCounter")
        card_layout.addWidget(self._step_counter)

        self._title_label = QLabel()
        self._title_label.setObjectName("tourTitle")
        self._title_label.setWordWrap(True)
        card_layout.addWidget(self._title_label)

        self._desc_label = QLabel()
        self._desc_label.setObjectName("tourDesc")
        self._desc_label.setWordWrap(True)
        card_layout.addWidget(self._desc_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._skip_btn = QPushButton(self.tr("Skip Tour"))
        self._skip_btn.setObjectName("tourSkipBtn")
        self._skip_btn.clicked.connect(self._skip)
        btn_row.addWidget(self._skip_btn)

        btn_row.addStretch()

        self._next_btn = QPushButton(self.tr("Next →"))
        self._next_btn.setObjectName("tourNextBtn")
        self._next_btn.clicked.connect(self._next_step)
        btn_row.addWidget(self._next_btn)

        card_layout.addLayout(btn_row)

        self._update_step()

    def start(self):
        """Start the tour by showing the overlay."""
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()

    def _update_step(self):
        """Update the card with the current step's content."""
        if self._current_step >= len(self._steps):
            self._finish()
            return

        step = self._steps[self._current_step]
        total = len(self._steps)
        self._step_counter.setText(
            self.tr("Step {} of {}").format(self._current_step + 1, total)
        )
        self._title_label.setText(step.title)
        self._desc_label.setText(step.description)

        if self._current_step == total - 1:
            self._next_btn.setText(self.tr("Finish"))
        else:
            self._next_btn.setText(self.tr("Next →"))

        # Try to find target widget
        self._target_rect = QRect()
        if self.parent():
            target = self.parent().findChild(QWidget, step.widget_name)
            if target and target.isVisible():
                pos = target.mapTo(self.parent(), QPoint(0, 0))
                self._target_rect = QRect(pos, target.size())

        self._position_card(step)
        self.update()

    def _position_card(self, step: TourStep):
        """Position the card relative to the target widget."""
        parent = self.parentWidget()
        if parent is None:
            return

        parent_rect = parent.rect()
        card_w = self._card.width()
        card_h = self._card.sizeHint().height()

        if self._target_rect.isValid():
            if step.position == "right":
                x = self._target_rect.right() + 16
                y = self._target_rect.top()
            elif step.position == "left":
                x = self._target_rect.left() - card_w - 16
                y = self._target_rect.top()
            elif step.position == "above":
                x = self._target_rect.left()
                y = self._target_rect.top() - card_h - 16
            else:  # below
                x = self._target_rect.left()
                y = self._target_rect.bottom() + 16
        else:
            x = (parent_rect.width() - card_w) // 2
            y = (parent_rect.height() - card_h) // 2

        # Clamp to parent bounds
        x = max(8, min(x, parent_rect.width() - card_w - 8))
        y = max(8, min(y, parent_rect.height() - card_h - 8))

        self._card.move(x, y)

    def _next_step(self):
        """Advance to the next tour step."""
        self._current_step += 1
        self._update_step()

    def _skip(self):
        """Skip the tour entirely."""
        self._finish()

    def _finish(self):
        """Complete the tour."""
        GuidedTourManager.mark_tour_complete()
        self.hide()
        self.tour_completed.emit()

    def paintEvent(self, event):
        """Draw semi-transparent overlay with spotlight cutout."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent background
        overlay_color = QColor(0, 0, 0, 160)

        if self._target_rect.isValid():
            # Create region with cutout
            full = QRegion(self.rect())
            cutout = QRegion(self._target_rect.adjusted(-4, -4, 4, 4))
            painter.setClipRegion(full.subtracted(cutout))

        painter.fillRect(self.rect(), overlay_color)

        if self._target_rect.isValid():
            painter.setClipping(False)
            # Draw highlight border around target
            painter.setPen(QColor("#39c5cf"))
            painter.drawRoundedRect(
                self._target_rect.adjusted(-4, -4, 4, 4), 4, 4
            )

        painter.end()

    def resizeEvent(self, event):
        """Handle parent resize."""
        super().resizeEvent(event)
        if self._current_step < len(self._steps):
            self._update_step()
