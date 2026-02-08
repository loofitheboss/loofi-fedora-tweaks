from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget
from ui.updates_tab import UpdatesTab
from ui.cleanup_tab import CleanupTab
from ui.tweaks_tab import TweaksTab
from ui.apps_tab import AppsTab
from ui.advanced_tab import AdvancedTweaksTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loofi Fedora Tweaks - HP Elitebook 840 G8")
        self.setGeometry(100, 100, 900, 700)
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Initialize Tabs
        self.updates_tab = UpdatesTab()
        self.cleanup_tab = CleanupTab()
        self.tweaks_tab = TweaksTab()
        self.apps_tab = AppsTab()
        self.advanced_tab = AdvancedTweaksTab()
        
        # Add Tabs
        self.tabs.addTab(self.updates_tab, "Updates")
        self.tabs.addTab(self.cleanup_tab, "Cleanup & Maintenance")
        self.tabs.addTab(self.tweaks_tab, "HP Tweaks")
        self.tabs.addTab(self.apps_tab, "Essential Apps")
        self.tabs.addTab(self.advanced_tab, "Advanced Tweaks")
