"""
Containers Tab - Distrobox container management GUI.
Part of v7.1 "Developer" update.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QLineEdit, QTextEdit, QScrollArea, QFrame, QMessageBox,
    QInputDialog, QMenu, QDialog, QFormLayout, QCheckBox
)
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QAction

from utils.containers import ContainerManager, ContainerStatus
import subprocess
import shutil


class ContainersTab(QWidget):
    """Container management tab for Distrobox containers."""
    
    def __init__(self):
        super().__init__()
        self.container_list = None  # Initialize to None
        self.init_ui()
        # Only refresh if distrobox is available
        if ContainerManager.is_available() and self.container_list:
            self.refresh_containers()
    
    def init_ui(self):
        """Initialize the UI components."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Header with status
        header_layout = QHBoxLayout()
        header = QLabel(self.tr("📦 Container Management"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        header_layout.addWidget(header)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Check if distrobox is available
        if not ContainerManager.is_available():
            layout.addWidget(self._create_install_section())
        else:
            # Container list section
            layout.addWidget(self._create_container_list_section())
            
            # Create container section
            layout.addWidget(self._create_new_container_section())
        
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
    
    def _create_install_section(self) -> QGroupBox:
        """Create install distrobox section for when it's not available."""
        group = QGroupBox(self.tr("⚠️ Distrobox Not Installed"))
        layout = QVBoxLayout(group)
        
        info_label = QLabel(self.tr(
            "Distrobox is not installed on your system. It allows you to run "
            "containers based on different Linux distributions (Ubuntu, Arch, Alpine, etc.) "
            "seamlessly integrated with your desktop."
        ))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        btn_layout = QHBoxLayout()
        install_btn = QPushButton(self.tr("📥 Install Distrobox"))
        install_btn.clicked.connect(self._install_distrobox)
        btn_layout.addWidget(install_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_container_list_section(self) -> QGroupBox:
        """Create the container list section."""
        group = QGroupBox(self.tr("🐳 Your Containers"))
        layout = QVBoxLayout(group)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton(self.tr("🔄 Refresh"))
        refresh_btn.clicked.connect(self.refresh_containers)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Container list
        self.container_list = QListWidget()
        self.container_list.setMinimumHeight(200)
        self.container_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.container_list.customContextMenuRequested.connect(self._show_context_menu)
        self.container_list.itemDoubleClicked.connect(self._enter_container)
        layout.addWidget(self.container_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        enter_btn = QPushButton(self.tr("🚪 Enter Container"))
        enter_btn.clicked.connect(self._enter_container)
        btn_layout.addWidget(enter_btn)
        
        stop_btn = QPushButton(self.tr("⏹️ Stop"))
        stop_btn.clicked.connect(self._stop_container)
        btn_layout.addWidget(stop_btn)
        
        delete_btn = QPushButton(self.tr("🗑️ Delete"))
        delete_btn.clicked.connect(self._delete_container)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_new_container_section(self) -> QGroupBox:
        """Create the new container section."""
        group = QGroupBox(self.tr("➕ Create New Container"))
        layout = QVBoxLayout(group)
        
        form_layout = QHBoxLayout()
        
        # Name input
        form_layout.addWidget(QLabel(self.tr("Name:")))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("my-container")
        self.name_input.setMaximumWidth(200)
        form_layout.addWidget(self.name_input)
        
        # Image selector
        form_layout.addWidget(QLabel(self.tr("Image:")))
        self.image_combo = QComboBox()
        for name in ContainerManager.get_available_images().keys():
            self.image_combo.addItem(name.capitalize(), name)
        self.image_combo.setCurrentIndex(0)  # Default to Fedora
        form_layout.addWidget(self.image_combo)
        
        # Create button
        create_btn = QPushButton(self.tr("✅ Create"))
        create_btn.clicked.connect(self._create_container)
        form_layout.addWidget(create_btn)
        
        form_layout.addStretch()
        layout.addLayout(form_layout)
        
        # Help text
        help_label = QLabel(self.tr(
            "ℹ️ Containers share your home directory by default. "
            "Double-click a container to enter it."
        ))
        help_label.setStyleSheet("color: #888; font-size: 11px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        return group
    
    def refresh_containers(self):
        """Refresh the container list."""
        if self.container_list is None:
            return
        
        self.container_list.clear()
        
        containers = ContainerManager.list_containers()
        
        if not containers:
            item = QListWidgetItem(self.tr("No containers found. Create one below!"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.container_list.addItem(item)
            self.status_label.setText(self.tr("0 containers"))
            return
        
        for container in containers:
            # Status emoji
            if container.status == ContainerStatus.RUNNING:
                status_icon = "🟢"
            elif container.status == ContainerStatus.STOPPED:
                status_icon = "⚪"
            else:
                status_icon = "⚫"
            
            # Format: "🟢 container-name (fedora:latest)"
            text = f"{status_icon} {container.name} ({container.image.split('/')[-1]})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, container.name)
            self.container_list.addItem(item)
        
        self.status_label.setText(self.tr("{} containers").format(len(containers)))
    
    def _get_selected_container(self) -> str | None:
        """Get the currently selected container name."""
        current = self.container_list.currentItem()
        if current:
            return current.data(Qt.ItemDataRole.UserRole)
        return None
    
    def _show_context_menu(self, position):
        """Show context menu for container list."""
        container_name = self._get_selected_container()
        if not container_name:
            return
        
        menu = QMenu(self)
        
        enter_action = QAction(self.tr("🚪 Enter Container"), self)
        enter_action.triggered.connect(self._enter_container)
        menu.addAction(enter_action)
        
        terminal_action = QAction(self.tr("🖥️ Open Terminal Here"), self)
        terminal_action.triggered.connect(lambda: self._open_terminal(container_name))
        menu.addAction(terminal_action)
        
        menu.addSeparator()
        
        stop_action = QAction(self.tr("⏹️ Stop Container"), self)
        stop_action.triggered.connect(self._stop_container)
        menu.addAction(stop_action)
        
        delete_action = QAction(self.tr("🗑️ Delete Container"), self)
        delete_action.triggered.connect(self._delete_container)
        menu.addAction(delete_action)
        
        menu.exec(self.container_list.mapToGlobal(position))
    
    def _enter_container(self):
        """Enter the selected container."""
        container_name = self._get_selected_container()
        if not container_name:
            self.log(self.tr("No container selected."))
            return
        
        self._open_terminal(container_name)
    
    def _open_terminal(self, container_name: str):
        """Open a terminal inside the container."""
        cmd = ContainerManager.get_enter_command(container_name)
        
        # Try different terminal emulators
        terminals = [
            ("gnome-terminal", ["gnome-terminal", "--", "bash", "-c", f"{cmd}; exec bash"]),
            ("konsole", ["konsole", "-e", "bash", "-c", f"{cmd}; exec bash"]),
            ("xfce4-terminal", ["xfce4-terminal", "-e", f"bash -c '{cmd}; exec bash'"]),
            ("xterm", ["xterm", "-e", f"bash -c '{cmd}; exec bash'"]),
        ]
        
        for term_name, term_cmd in terminals:
            if shutil.which(term_name):
                try:
                    subprocess.Popen(term_cmd, start_new_session=True)
                    self.log(self.tr("Opened terminal in container '{}'.").format(container_name))
                    return
                except Exception as e:
                    self.log(self.tr("Failed to open {}: {}").format(term_name, e))
        
        # Fallback: show command
        self.log(self.tr("No terminal emulator found. Run manually: {}").format(cmd))
    
    def _stop_container(self):
        """Stop the selected container."""
        container_name = self._get_selected_container()
        if not container_name:
            self.log(self.tr("No container selected."))
            return
        
        result = ContainerManager.stop_container(container_name)
        self.log(result.message)
        if result.success:
            self.refresh_containers()
    
    def _delete_container(self):
        """Delete the selected container."""
        container_name = self._get_selected_container()
        if not container_name:
            self.log(self.tr("No container selected."))
            return
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Are you sure you want to delete container '{}'?").format(container_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = ContainerManager.delete_container(container_name, force=True)
            self.log(result.message)
            if result.success:
                self.refresh_containers()
    
    def _create_container(self):
        """Create a new container."""
        name = self.name_input.text().strip()
        if not name:
            self.log(self.tr("Please enter a container name."))
            return
        
        image = self.image_combo.currentData()
        
        self.log(self.tr("Creating container '{}' from {}...").format(name, image))
        
        result = ContainerManager.create_container(name, image)
        self.log(result.message)
        
        if result.success:
            self.name_input.clear()
            self.refresh_containers()
    
    def _install_distrobox(self):
        """Install distrobox via DNF."""
        from utils.command_runner import CommandRunner
        
        self.runner = CommandRunner()
        self.runner.finished.connect(self._on_install_finished)
        self.runner.output_received.connect(lambda t: self.log(t))
        self.runner.run_command("pkexec", ["dnf", "install", "distrobox", "-y"])
        self.log(self.tr("Installing Distrobox..."))
    
    def _on_install_finished(self, exit_code: int):
        """Handle distrobox installation completion."""
        if exit_code == 0:
            self.log(self.tr("Distrobox installed successfully! Please restart the tab."))
            QMessageBox.information(
                self,
                self.tr("Installation Complete"),
                self.tr("Distrobox has been installed. Please switch to another tab and back to refresh.")
            )
        else:
            self.log(self.tr("Installation failed with exit code {}.").format(exit_code))
    
    def log(self, message: str):
        """Add message to output log."""
        self.output_text.append(message)
