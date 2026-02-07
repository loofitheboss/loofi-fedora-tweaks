"""
Developer Tab - Language stacks and VS Code configuration.
Part of v7.1 "Developer" update.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QComboBox, QTextEdit, QScrollArea, QFrame,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from utils.devtools import DevToolsManager
from utils.vscode import VSCodeManager


class InstallWorker(QThread):
    """Background worker for installations."""
    finished = pyqtSignal(str, bool, str)  # tool, success, message
    
    def __init__(self, tool: str, extra_args: dict = None):
        super().__init__()
        self.tool = tool
        self.extra_args = extra_args or {}
    
    def run(self):
        try:
            if self.tool == "pyenv":
                result = DevToolsManager.install_pyenv(
                    self.extra_args.get("python_version", "3.12")
                )
            elif self.tool == "nvm":
                result = DevToolsManager.install_nvm(
                    self.extra_args.get("node_version", "lts")
                )
            elif self.tool == "rustup":
                result = DevToolsManager.install_rustup()
            elif self.tool.startswith("vscode_"):
                profile = self.tool.replace("vscode_", "")
                result = VSCodeManager.install_profile(profile)
            else:
                result = type('Result', (), {'success': False, 'message': 'Unknown tool'})()
            
            self.finished.emit(self.tool, result.success, result.message)
        except Exception as e:
            self.finished.emit(self.tool, False, str(e))


class DeveloperTab(QWidget):
    """Developer tools tab for language stacks and VS Code setup."""
    
    def __init__(self):
        super().__init__()
        self.workers = []
        self.init_ui()
        self.refresh_status()
    
    def init_ui(self):
        """Initialize the UI components."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(self.tr("🛠️ Developer Tools"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)
        
        # Language Version Managers
        layout.addWidget(self._create_language_section())
        
        # VS Code Extensions
        layout.addWidget(self._create_vscode_section())
        
        # Output Log
        log_group = QGroupBox(self.tr("Output Log:"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_language_section(self) -> QGroupBox:
        """Create language version managers section."""
        group = QGroupBox(self.tr("🐍 Language Version Managers"))
        layout = QVBoxLayout(group)
        
        info_label = QLabel(self.tr(
            "Install version managers to run multiple language versions without affecting system packages."
        ))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888;")
        layout.addWidget(info_label)
        
        # PyEnv
        pyenv_layout = QHBoxLayout()
        self.pyenv_status = QLabel()
        pyenv_layout.addWidget(self.pyenv_status)
        pyenv_layout.addStretch()
        
        self.pyenv_btn = QPushButton(self.tr("Install PyEnv + Python 3.12"))
        self.pyenv_btn.clicked.connect(lambda: self._install_tool("pyenv"))
        pyenv_layout.addWidget(self.pyenv_btn)
        layout.addLayout(pyenv_layout)
        
        # NVM
        nvm_layout = QHBoxLayout()
        self.nvm_status = QLabel()
        nvm_layout.addWidget(self.nvm_status)
        nvm_layout.addStretch()
        
        self.nvm_btn = QPushButton(self.tr("Install NVM + Node LTS"))
        self.nvm_btn.clicked.connect(lambda: self._install_tool("nvm"))
        nvm_layout.addWidget(self.nvm_btn)
        layout.addLayout(nvm_layout)
        
        # Rustup
        rust_layout = QHBoxLayout()
        self.rust_status = QLabel()
        rust_layout.addWidget(self.rust_status)
        rust_layout.addStretch()
        
        self.rust_btn = QPushButton(self.tr("Install Rustup"))
        self.rust_btn.clicked.connect(lambda: self._install_tool("rustup"))
        rust_layout.addWidget(self.rust_btn)
        layout.addLayout(rust_layout)
        
        return group
    
    def _create_vscode_section(self) -> QGroupBox:
        """Create VS Code extensions section."""
        group = QGroupBox(self.tr("📝 VS Code Extensions"))
        layout = QVBoxLayout(group)
        
        # Check availability
        if not VSCodeManager.is_available():
            not_found = QLabel(self.tr(
                "⚠️ VS Code not found. Install VS Code, VSCodium, or Code OSS to use this feature."
            ))
            not_found.setWordWrap(True)
            layout.addWidget(not_found)
            return group
        
        info_label = QLabel(self.tr(
            "Install recommended extensions for different development profiles."
        ))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888;")
        layout.addWidget(info_label)
        
        # Profile selector
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel(self.tr("Profile:")))
        
        self.profile_combo = QComboBox()
        for profile in VSCodeManager.get_available_profiles():
            self.profile_combo.addItem(
                f"{profile['name']} ({profile['extension_count']} extensions)",
                profile['key']
            )
        profile_layout.addWidget(self.profile_combo, 1)
        
        install_btn = QPushButton(self.tr("✅ Install Extensions"))
        install_btn.clicked.connect(self._install_vscode_profile)
        profile_layout.addWidget(install_btn)
        
        settings_btn = QPushButton(self.tr("⚙️ Apply Settings"))
        settings_btn.clicked.connect(self._apply_vscode_settings)
        profile_layout.addWidget(settings_btn)
        
        layout.addLayout(profile_layout)
        
        # Progress
        self.vscode_progress = QProgressBar()
        self.vscode_progress.setVisible(False)
        layout.addWidget(self.vscode_progress)
        
        return group
    
    def refresh_status(self):
        """Refresh the status of all tools."""
        tools_status = DevToolsManager.get_all_status()
        
        # PyEnv
        installed, version = tools_status.get("pyenv", (False, ""))
        if installed:
            self.pyenv_status.setText(f"✅ PyEnv: {version}")
            self.pyenv_btn.setText(self.tr("Reinstall"))
        else:
            self.pyenv_status.setText(f"⚪ PyEnv: {version}")
        
        # NVM
        installed, version = tools_status.get("nvm", (False, ""))
        if installed:
            self.nvm_status.setText(f"✅ NVM: {version}")
            self.nvm_btn.setText(self.tr("Reinstall"))
        else:
            self.nvm_status.setText(f"⚪ NVM: {version}")
        
        # Rustup
        installed, version = tools_status.get("rustup", (False, ""))
        if installed:
            self.rust_status.setText(f"✅ Rustup: {version}")
            self.rust_btn.setText(self.tr("Reinstall"))
        else:
            self.rust_status.setText(f"⚪ Rustup: {version}")
    
    def _install_tool(self, tool: str):
        """Start background installation of a tool."""
        self.log(self.tr(f"Installing {tool}... This may take a few minutes."))
        
        # Disable button during install
        if tool == "pyenv":
            self.pyenv_btn.setEnabled(False)
        elif tool == "nvm":
            self.nvm_btn.setEnabled(False)
        elif tool == "rustup":
            self.rust_btn.setEnabled(False)
        
        worker = InstallWorker(tool)
        worker.finished.connect(self._on_install_finished)
        self.workers.append(worker)
        worker.start()
    
    def _on_install_finished(self, tool: str, success: bool, message: str):
        """Handle installation completion."""
        self.log(message)
        
        # Re-enable buttons
        if tool == "pyenv":
            self.pyenv_btn.setEnabled(True)
        elif tool == "nvm":
            self.nvm_btn.setEnabled(True)
        elif tool == "rustup":
            self.rust_btn.setEnabled(True)
        elif tool.startswith("vscode_"):
            self.vscode_progress.setVisible(False)
        
        if success:
            self.refresh_status()
            if not tool.startswith("vscode_"):
                QMessageBox.information(
                    self,
                    self.tr("Installation Complete"),
                    self.tr("Please restart your terminal to use the new tools.")
                )
    
    def _install_vscode_profile(self):
        """Install VS Code extensions for selected profile."""
        profile = self.profile_combo.currentData()
        self.log(self.tr(f"Installing VS Code {profile} extensions..."))
        
        self.vscode_progress.setVisible(True)
        self.vscode_progress.setRange(0, 0)  # Indeterminate
        
        worker = InstallWorker(f"vscode_{profile}")
        worker.finished.connect(self._on_install_finished)
        self.workers.append(worker)
        worker.start()
    
    def _apply_vscode_settings(self):
        """Apply VS Code settings for selected profile."""
        profile = self.profile_combo.currentData()
        result = VSCodeManager.inject_settings(profile)
        self.log(result.message)
        
        if result.success:
            QMessageBox.information(
                self,
                self.tr("Settings Applied"),
                self.tr("VS Code settings have been updated. Restart VS Code to apply.")
            )
    
    def log(self, message: str):
        """Add message to output log."""
        self.output_text.append(message)
