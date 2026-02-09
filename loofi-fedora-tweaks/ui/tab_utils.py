"""
Shared helpers for tab widgets.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget


def configure_top_tabs(tab_widget: QTabWidget) -> None:
    """Ensure top tab bars remain usable when many tabs are present."""
    tab_bar = tab_widget.tabBar()
    tab_bar.setUsesScrollButtons(True)
    tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
    tab_bar.setExpanding(False)
    tab_bar.setDocumentMode(True)
