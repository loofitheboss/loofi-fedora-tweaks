"""
Health Detail Dialog — v47.0 UX Improvement.

Modal dialog showing per-component health score breakdown with
actionable fix suggestions and navigation links to relevant tabs.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from utils.health_detail import HealthDetailManager
from utils.health_score import HealthScoreManager


class HealthDetailDialog(QDialog):
    """Modal dialog showing detailed health score breakdown."""

    navigate_to_tab = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("System Health Details"))
        self.setMinimumSize(500, 400)
        self.setObjectName("healthDetailDialog")
        self._init_ui()

    def _init_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Overall score header
        health = HealthScoreManager.calculate()
        header = QHBoxLayout()

        grade_label = QLabel(health.grade)
        grade_label.setObjectName("healthGradeLabel")
        grade_label.setStyleSheet(
            f"font-size: 48px; font-weight: bold; color: {health.color};"
        )
        header.addWidget(grade_label)

        score_info = QVBoxLayout()
        score_label = QLabel(self.tr("Overall Health Score: {}/100").format(health.score))
        score_label.setObjectName("healthScoreLabel")
        score_info.addWidget(score_label)

        status_text = self.tr("Your system is in good shape.") if health.score >= 75 else self.tr("Some areas need attention.")
        status_label = QLabel(status_text)
        status_label.setObjectName("healthStatusLabel")
        score_info.addWidget(status_label)
        header.addLayout(score_info)
        header.addStretch()

        layout.addLayout(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Component scores
        components_label = QLabel(self.tr("Component Breakdown"))
        components_label.setObjectName("healthSectionLabel")
        layout.addWidget(components_label)

        components = HealthDetailManager.get_component_scores()
        grid = QGridLayout()
        grid.setSpacing(8)
        row = 0

        for key in ["cpu", "ram", "disk", "uptime", "updates"]:
            if key not in components:
                continue
            comp = components[key]

            name_label = QLabel(comp.name)
            name_label.setMinimumWidth(120)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(comp.score)
            bar.setTextVisible(True)
            bar.setFormat(f"{comp.score}/100")
            if comp.status == "critical":
                bar.setObjectName("healthBarCritical")
            elif comp.status == "warning":
                bar.setObjectName("healthBarWarning")
            else:
                bar.setObjectName("healthBarHealthy")

            weight_label = QLabel(f"{comp.weight * 100:.0f}%")
            weight_label.setToolTip(self.tr("Weight in overall score"))

            grid.addWidget(name_label, row, 0)
            grid.addWidget(bar, row, 1)
            grid.addWidget(weight_label, row, 2)

            if comp.recommendation:
                rec_label = QLabel(f"  ℹ {comp.recommendation}")
                rec_label.setObjectName("healthRecLabel")
                rec_label.setWordWrap(True)
                row += 1
                grid.addWidget(rec_label, row, 0, 1, 3)

            row += 1

        layout.addLayout(grid)

        # Actionable fixes
        fixes = HealthDetailManager.get_actionable_fixes()
        if fixes:
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.Shape.HLine)
            layout.addWidget(sep2)

            fixes_label = QLabel(self.tr("Suggested Actions"))
            fixes_label.setObjectName("healthSectionLabel")
            layout.addWidget(fixes_label)

            for fix in fixes:
                fix_row = QHBoxLayout()
                severity_icon = "🔴" if fix.severity == "high" else "🟡"
                fix_text = QLabel(f"{severity_icon} {fix.description}")
                fix_text.setWordWrap(True)
                fix_row.addWidget(fix_text, 1)

                fix_btn = QPushButton(self.tr("Fix it →"))
                fix_btn.setObjectName("healthFixBtn")
                tab_id = fix.tab_id
                fix_btn.clicked.connect(lambda checked, t=tab_id: self._navigate(t))
                fix_row.addWidget(fix_btn)

                layout.addLayout(fix_row)

        # Close button
        layout.addStretch()
        close_btn = QPushButton(self.tr("Close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _navigate(self, tab_id: str):
        """Emit navigation signal and close dialog."""
        self.navigate_to_tab.emit(tab_id)
        self.accept()
