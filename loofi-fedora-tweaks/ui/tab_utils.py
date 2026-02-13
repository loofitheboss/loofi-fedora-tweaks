"""
Shared helpers for tab widgets.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget

# Standard content margins for tab root layouts
CONTENT_MARGINS = (20, 16, 20, 16)


def configure_top_tabs(tab_widget: QTabWidget) -> None:
    """Ensure top tab bars remain usable when many tabs are present."""
    tab_widget.setObjectName("contentTabs")
    tab_bar = tab_widget.tabBar()
    if tab_bar is None:
        return
    tab_bar.setUsesScrollButtons(True)
    tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
    tab_bar.setExpanding(False)
    # NOTE:
    # Document-mode tab bars can render with visual artifacts on some
    # platforms/themes when combined with custom QSS pane borders.
    # Keep document mode disabled for stable, consistent rendering.
    tab_widget.setDocumentMode(False)
    tab_bar.setDocumentMode(False)
