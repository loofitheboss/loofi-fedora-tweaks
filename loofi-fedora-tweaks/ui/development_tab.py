"""
Development Tab - Consolidated Containers + Developer Tools interface.
Part of v11.0 "Aurora Update" - merges Containers and Developer tabs.

Sub-tabs:
- Containers: Distrobox container management
- Developer Tools: Language version managers, VS Code extensions
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QLineEdit, QTextEdit, QScrollArea, QFrame, QMessageBox,
    QInputDialog, QMenu, QDialog, QFormLayout, QCheckBox,
    QTabWidget, QProgressBar
)
from PyQt6.QtCore import Qt, QProcess, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs
from utils.containers import ContainerManager, ContainerStatus
from utils.devtools import DevToolsManager
from utils.vscode import VSCodeManager
from utils.command_runner import CommandRunner
import subprocess
import shutil


class InstallWorker(QThread):
    """Background worker for developer tool installations."""
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


class DevelopmentTab(BaseTab):
    """Consolidated Development tab: Containers + Developer Tools."""

    def __init__(self):
        super().__init__()
        self.container_list = None
        self.workers = []
        self.init_ui()

        # Only refresh containers if distrobox is available
        if ContainerManager.is_available() and self.container_list:
            self.refresh_containers()

        # Refresh developer tool statuses
        self.refresh_dev_status()

    def init_ui(self):
        """Initialize the UI with sub-tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sub-tab widget
        self.sub_tabs = QTabWidget()
        configure_top_tabs(self.sub_tabs)
        layout.addWidget(self.sub_tabs)

        # Sub-tab 1: Containers (from ContainersTab)
        self.sub_tabs.addTab(
            self._create_containers_tab(), self.tr("Containers")
        )

        # Sub-tab 2: Developer Tools (from DeveloperTab)
        self.sub_tabs.addTab(
            self._create_developer_tab(), self.tr("Developer Tools")
        )

        # Shared output area at bottom
        self.add_output_section(layout)

    # ================================================================
    # CONTAINERS SUB-TAB (from ContainersTab)
    # ================================================================

    def _create_containers_tab(self) -> QWidget:
        """Create the Containers sub-tab content."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        ct_layout = QVBoxLayout(container)
        ct_layout.setSpacing(15)

        # Header with status
        header_layout = QHBoxLayout()
        header = QLabel(self.tr("Container Management"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        header_layout.addWidget(header)

        self.container_status_label = QLabel()
        self.container_status_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self.container_status_label)
        header_layout.addStretch()
        ct_layout.addLayout(header_layout)

        # Check if distrobox is available
        if not ContainerManager.is_available():
            ct_layout.addWidget(self._create_install_section())
        else:
            # Container list section
            ct_layout.addWidget(self._create_container_list_section())

            # Create container section
            ct_layout.addWidget(self._create_new_container_section())

        ct_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_install_section(self) -> QGroupBox:
        """Create install distrobox section for when it's not available."""
        group = QGroupBox(self.tr("Distrobox Not Installed"))
        layout = QVBoxLayout(group)

        info_label = QLabel(self.tr(
            "Distrobox is not installed on your system. It allows you to run "
            "containers based on different Linux distributions (Ubuntu, Arch, Alpine, etc.) "
            "seamlessly integrated with your desktop."
        ))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        btn_layout = QHBoxLayout()
        install_btn = QPushButton(self.tr("Install Distrobox"))
        install_btn.clicked.connect(self._install_distrobox)
        btn_layout.addWidget(install_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_container_list_section(self) -> QGroupBox:
        """Create the container list section."""
        group = QGroupBox(self.tr("Your Containers"))
        layout = QVBoxLayout(group)

        # Toolbar
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton(self.tr("Refresh"))
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

        enter_btn = QPushButton(self.tr("Enter Container"))
        enter_btn.clicked.connect(self._enter_container)
        btn_layout.addWidget(enter_btn)

        stop_btn = QPushButton(self.tr("Stop"))
        stop_btn.clicked.connect(self._stop_container)
        btn_layout.addWidget(stop_btn)

        delete_btn = QPushButton(self.tr("Delete"))
        delete_btn.clicked.connect(self._delete_container)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_new_container_section(self) -> QGroupBox:
        """Create the new container section."""
        group = QGroupBox(self.tr("Create New Container"))
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
        self.image_combo.setCurrentIndex(0)
        form_layout.addWidget(self.image_combo)

        # Create button
        create_btn = QPushButton(self.tr("Create"))
        create_btn.clicked.connect(self._create_container)
        form_layout.addWidget(create_btn)

        form_layout.addStretch()
        layout.addLayout(form_layout)

        # Help text
        help_label = QLabel(self.tr(
            "Containers share your home directory by default. "
            "Double-click a container to enter it."
        ))
        help_label.setStyleSheet("color: #888; font-size: 11px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        return group

    # -- Container actions --

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
            self.container_status_label.setText(self.tr("0 containers"))
            return

        for ct in containers:
            # Status emoji
            if ct.status == ContainerStatus.RUNNING:
                status_icon = "Running"
            elif ct.status == ContainerStatus.STOPPED:
                status_icon = "Stopped"
            else:
                status_icon = "Unknown"

            text = f"[{status_icon}] {ct.name} ({ct.image.split('/')[-1]})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ct.name)
            self.container_list.addItem(item)

        self.container_status_label.setText(
            self.tr("{} containers").format(len(containers))
        )

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

        enter_action = QAction(self.tr("Enter Container"), self)
        enter_action.triggered.connect(self._enter_container)
        menu.addAction(enter_action)

        terminal_action = QAction(self.tr("Open Terminal Here"), self)
        terminal_action.triggered.connect(lambda: self._open_terminal(container_name))
        menu.addAction(terminal_action)

        menu.addSeparator()

        stop_action = QAction(self.tr("Stop Container"), self)
        stop_action.triggered.connect(self._stop_container)
        menu.addAction(stop_action)

        delete_action = QAction(self.tr("Delete Container"), self)
        delete_action.triggered.connect(self._delete_container)
        menu.addAction(delete_action)

        menu.exec(self.container_list.mapToGlobal(position))

    def _enter_container(self):
        """Enter the selected container."""
        container_name = self._get_selected_container()
        if not container_name:
            self.append_output(self.tr("No container selected.\n"))
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
                    self.append_output(
                        self.tr("Opened terminal in container '{}'.\n").format(container_name)
                    )
                    return
                except Exception as e:
                    self.append_output(
                        self.tr("Failed to open {}: {}\n").format(term_name, e)
                    )

        # Fallback: show command
        self.append_output(
            self.tr("No terminal emulator found. Run manually: {}\n").format(cmd)
        )

    def _stop_container(self):
        """Stop the selected container."""
        container_name = self._get_selected_container()
        if not container_name:
            self.append_output(self.tr("No container selected.\n"))
            return

        result = ContainerManager.stop_container(container_name)
        self.append_output(result.message + "\n")
        if result.success:
            self.refresh_containers()

    def _delete_container(self):
        """Delete the selected container."""
        container_name = self._get_selected_container()
        if not container_name:
            self.append_output(self.tr("No container selected.\n"))
            return

        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Are you sure you want to delete container '{}'?").format(container_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = ContainerManager.delete_container(container_name, force=True)
            self.append_output(result.message + "\n")
            if result.success:
                self.refresh_containers()

    def _create_container(self):
        """Create a new container."""
        name = self.name_input.text().strip()
        if not name:
            self.append_output(self.tr("Please enter a container name.\n"))
            return

        image = self.image_combo.currentData()

        self.append_output(
            self.tr("Creating container '{}' from {}...\n").format(name, image)
        )

        result = ContainerManager.create_container(name, image)
        self.append_output(result.message + "\n")

        if result.success:
            self.name_input.clear()
            self.refresh_containers()

    def _install_distrobox(self):
        """Install distrobox via DNF."""
        self._distrobox_runner = CommandRunner()
        self._distrobox_runner.finished.connect(self._on_distrobox_install_finished)
        self._distrobox_runner.output_received.connect(lambda t: self.append_output(t))
        self._distrobox_runner.run_command("pkexec", ["dnf", "install", "distrobox", "-y"])
        self.append_output(self.tr("Installing Distrobox...\n"))

    def _on_distrobox_install_finished(self, exit_code: int):
        """Handle distrobox installation completion."""
        if exit_code == 0:
            self.append_output(self.tr("Distrobox installed successfully! Please restart the tab.\n"))
            QMessageBox.information(
                self,
                self.tr("Installation Complete"),
                self.tr("Distrobox has been installed. Please switch to another tab and back to refresh.")
            )
        else:
            self.append_output(
                self.tr("Installation failed with exit code {}.\n").format(exit_code)
            )

    # ================================================================
    # DEVELOPER TOOLS SUB-TAB (from DeveloperTab)
    # ================================================================

    def _create_developer_tab(self) -> QWidget:
        """Create the Developer Tools sub-tab content."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        dev_layout = QVBoxLayout(container)
        dev_layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("Developer Tools"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        dev_layout.addWidget(header)

        # Language Version Managers
        dev_layout.addWidget(self._create_language_section())

        # VS Code Extensions
        dev_layout.addWidget(self._create_vscode_section())

        dev_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_language_section(self) -> QGroupBox:
        """Create language version managers section."""
        group = QGroupBox(self.tr("Language Version Managers"))
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
        group = QGroupBox(self.tr("VS Code Extensions"))
        layout = QVBoxLayout(group)

        # Check availability
        if not VSCodeManager.is_available():
            not_found = QLabel(self.tr(
                "VS Code not found. Install VS Code, VSCodium, or Code OSS to use this feature."
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

        install_btn = QPushButton(self.tr("Install Extensions"))
        install_btn.clicked.connect(self._install_vscode_profile)
        profile_layout.addWidget(install_btn)

        settings_btn = QPushButton(self.tr("Apply Settings"))
        settings_btn.clicked.connect(self._apply_vscode_settings)
        profile_layout.addWidget(settings_btn)

        layout.addLayout(profile_layout)

        # Progress
        self.vscode_progress = QProgressBar()
        self.vscode_progress.setVisible(False)
        layout.addWidget(self.vscode_progress)

        return group

    # -- Developer Tool actions --

    def refresh_dev_status(self):
        """Refresh the status of all developer tools."""
        tools_status = DevToolsManager.get_all_status()

        # PyEnv
        installed, version = tools_status.get("pyenv", (False, ""))
        if installed:
            self.pyenv_status.setText(self.tr("PyEnv: {}").format(version))
            self.pyenv_btn.setText(self.tr("Reinstall"))
        else:
            self.pyenv_status.setText(self.tr("PyEnv: {}").format(version))

        # NVM
        installed, version = tools_status.get("nvm", (False, ""))
        if installed:
            self.nvm_status.setText(self.tr("NVM: {}").format(version))
            self.nvm_btn.setText(self.tr("Reinstall"))
        else:
            self.nvm_status.setText(self.tr("NVM: {}").format(version))

        # Rustup
        installed, version = tools_status.get("rustup", (False, ""))
        if installed:
            self.rust_status.setText(self.tr("Rustup: {}").format(version))
            self.rust_btn.setText(self.tr("Reinstall"))
        else:
            self.rust_status.setText(self.tr("Rustup: {}").format(version))

    def _install_tool(self, tool: str):
        """Start background installation of a tool."""
        self.append_output(self.tr("Installing {}... This may take a few minutes.\n").format(tool))

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
        self.append_output(message + "\n")

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
            self.refresh_dev_status()
            if not tool.startswith("vscode_"):
                QMessageBox.information(
                    self,
                    self.tr("Installation Complete"),
                    self.tr("Please restart your terminal to use the new tools.")
                )

    def _install_vscode_profile(self):
        """Install VS Code extensions for selected profile."""
        profile = self.profile_combo.currentData()
        self.append_output(
            self.tr("Installing VS Code {} extensions...\n").format(profile)
        )

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
        self.append_output(result.message + "\n")

        if result.success:
            QMessageBox.information(
                self,
                self.tr("Settings Applied"),
                self.tr("VS Code settings have been updated. Restart VS Code to apply.")
            )
