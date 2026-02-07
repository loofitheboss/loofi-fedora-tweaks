"""
Lazy loading widget for deferred tab initialization.
Part of v7.1 performance optimization.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from typing import Callable


class LazyWidget(QWidget):
    """
    A placeholder widget that defers loading of the actual widget
    until the tab is first shown. This reduces startup time by
    avoiding import and initialization of all tabs at once.
    """
    
    def __init__(self, loader_fn: Callable[[], QWidget], loading_text: str = "Loading..."):
        """
        Initialize the lazy widget.
        
        Args:
            loader_fn: A callable that returns the actual widget when invoked.
                       This function should handle the import and instantiation.
            loading_text: Text to show while loading (briefly visible).
        """
        super().__init__()
        self.loader_fn = loader_fn
        self.real_widget = None
        self._loaded = False
        
        # Minimal placeholder layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # Loading indicator (shown briefly)
        self._loading_label = QLabel(loading_text)
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet("color: #888; font-size: 14px;")
        self._layout.addWidget(self._loading_label)
    
    def showEvent(self, event):
        """Load the real widget when first shown."""
        if not self._loaded:
            self._loaded = True
            
            # Remove loading placeholder
            self._loading_label.hide()
            self._layout.removeWidget(self._loading_label)
            self._loading_label.deleteLater()
            
            # Load and add the real widget
            try:
                self.real_widget = self.loader_fn()
                self._layout.addWidget(self.real_widget)
            except Exception as e:
                # Show error if loading fails
                error_label = QLabel(f"Failed to load: {e}")
                error_label.setStyleSheet("color: #ff6b6b; padding: 20px;")
                error_label.setWordWrap(True)
                self._layout.addWidget(error_label)
        
        super().showEvent(event)
    
    def get_real_widget(self) -> QWidget | None:
        """Return the real widget if loaded, None otherwise."""
        return self.real_widget
