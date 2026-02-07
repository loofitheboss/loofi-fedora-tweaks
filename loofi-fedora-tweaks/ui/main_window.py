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
        self.setWindowTitle("Loofi Fedora Tweaks v4.2.0 - HP Elitebook 840 G8")
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
        


        
        
        # System Tray
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QIcon, QAction
        import os
        
        self.tray_icon = QSystemTrayIcon(self)
        # Use a standard icon or app icon
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "loofi-fedora-tweaks.png")
        if os.path.exists(icon_path):
             self.tray_icon.setIcon(QIcon(icon_path))
        else:
             # Fallback to a system icon or just standard window icon
             self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
             
        # Tray Menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        
        doctor_action = QAction("System Doctor", self)
        doctor_action.triggered.connect(self.show_doctor)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(doctor_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Check dependencies
        self.check_dependencies()

    def closeEvent(self, event):
        # Minimize to tray instead of closing
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "Loofi Fedora Tweaks",
                "Application minimized to tray. Running in background.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()
            
    def quit_app(self):
        self.tray_icon.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def check_dependencies(self):
        from ui.doctor import DependencyDoctor
        
        # We only check for critical missing tools to decide whether to show the doctor automatically
        # The doctor itself will check everything
        import shutil
        critical = ["dnf", "pkexec"]
        missing = [tool for tool in critical if not shutil.which(tool)]
        
        # Also show if optional tools like flatpak/timeshift are missing?
        # Let's just run the doctor check and see if ANY are missing, IF so, show it.
        # But we need to be careful not to annoy user every time if they intentionally don't want something.
        # For now, let's show it if CRITICAL are missing, or if it's the first run (maybe too complex for now).
        
        # Simple logic: Check for critical tools. If missing, show doctor.
        # For optional tools, we won't force show it on startup to avoid annoyance, 
        # but we should add a menu option to open "System Doctor".
        
        if missing:
             self.show_doctor()

    def show_doctor(self):
        from ui.doctor import DependencyDoctor
        doctor = DependencyDoctor(self)
        doctor.exec()
