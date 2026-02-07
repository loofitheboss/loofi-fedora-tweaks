from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget
from ui.system_info_tab import SystemInfoTab
from ui.updates_tab import UpdatesTab
from ui.cleanup_tab import CleanupTab
from ui.tweaks_tab import TweaksTab
from ui.apps_tab import AppsTab
from ui.advanced_tab import AdvancedTab # Changed from AdvancedTweaksTab
from ui.privacy_tab import PrivacyTab
from ui.theming_tab import ThemingTab
from ui.repos_tab import ReposTab # Moved import here
from ui.gaming_tab import GamingTab # New import
from ui.network_tab import NetworkTab # New import

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loofi Fedora Tweaks v4.0.1 - HP Elitebook 840 G8")
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
        self.advanced_tab = AdvancedTab() # Changed from AdvancedTweaksTab
        self.privacy_tab = PrivacyTab()
        self.theming_tab = ThemingTab()
        self.repos_tab = ReposTab() # Moved initialization here
        self.gaming_tab = GamingTab() # New tab
        self.network_tab = NetworkTab() # New tab
        
        # Add Tabs
        self.tabs.addTab(self.system_info_tab, "System Info")
        self.tabs.addTab(self.updates_tab, "Updates")
        self.tabs.addTab(self.cleanup_tab, "Cleanup & Maintenance")
        self.tabs.addTab(self.tweaks_tab, "HP Tweaks")
        self.tabs.addTab(self.apps_tab, "Essential Apps")
        self.tabs.addTab(self.repos_tab, "Repositories") # Moved tab addition here
        self.tabs.addTab(self.gaming_tab, "Gaming") # New tab
        self.tabs.addTab(self.network_tab, "Network") # New tab
        self.tabs.addTab(self.privacy_tab, "Privacy & Security")
        self.tabs.addTab(self.theming_tab, "Theming")
        


        
        # Check dependencies
        self.check_dependencies()

    def check_dependencies(self):
        import shutil
        from PyQt6.QtWidgets import QMessageBox
        
        required = ["dnf", "pkexec"]
        missing = [tool for tool in required if not shutil.which(tool)]
        
        if missing:
            QMessageBox.critical(self, "Missing Dependencies", f"Critical tools missing: {', '.join(missing)}\nThe application may not function correctly.")
            
        optional = ["flatpak", "fwupdmgr"]
        missing_opt = [tool for tool in optional if not shutil.which(tool)]
        
        if missing_opt:
            QMessageBox.warning(self, "Missing Optional Tools", f"Optional tools missing: {', '.join(missing_opt)}\nSome features (Flatpak/Firmware updates) may not work.")
