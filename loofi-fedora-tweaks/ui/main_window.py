from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget
from ui.updates_tab import UpdatesTab
from ui.cleanup_tab import CleanupTab
from ui.tweaks_tab import TweaksTab
from ui.apps_tab import AppsTab
from ui.advanced_tab import AdvancedTweaksTab
from ui.system_info_tab import SystemInfoTab
from ui.privacy_tab import PrivacyTab
from ui.theming_tab import ThemingTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loofi Fedora Tweaks v2.0 - HP Elitebook 840 G8")
        self.setGeometry(100, 100, 950, 800)
        
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
        self.system_info_tab = SystemInfoTab()
        self.updates_tab = UpdatesTab()
        self.cleanup_tab = CleanupTab()
        self.tweaks_tab = TweaksTab()
        self.apps_tab = AppsTab()
        self.advanced_tab = AdvancedTweaksTab()
        self.privacy_tab = PrivacyTab()
        self.theming_tab = ThemingTab()
        
        # Add Tabs
        self.tabs.addTab(self.system_info_tab, "System Info")
        self.tabs.addTab(self.updates_tab, "Updates")
        self.tabs.addTab(self.cleanup_tab, "Cleanup & Maintenance")
        self.tabs.addTab(self.tweaks_tab, "HP Tweaks")
        self.tabs.addTab(self.apps_tab, "Essential Apps")
        self.tabs.addTab(self.advanced_tab, "Advanced Tweaks")
        self.tabs.addTab(self.privacy_tab, "Privacy & Security")
        self.tabs.addTab(self.theming_tab, "Theming")

