"""
Teleport Tab - State Teleport UI for capturing and restoring workspace state.
Part of v12.0 "Sovereign Update".

Provides:
- Workspace state capture with git repo auto-detection
- Saved teleport package management (list, export, import)
- Teleport restore with preview and confirmation
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QScrollArea, QFrame, QMessageBox, QFileDialog,
    QLineEdit,
)

from ui.base_tab import BaseTab
from ui.tab_utils import CONTENT_MARGINS
from utils.state_teleport import StateTeleportManager
from utils.file_drop import FileDropManager
from utils.mesh_discovery import MeshDiscovery
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata

import os
import time


class TeleportTab(QWidget, PluginInterface):
    """State Teleport tab for capturing and restoring workspace state."""

    _METADATA = PluginMetadata(
        id="teleport",
        name="State Teleport",
        description="Capture and restore workspace state including git repos and environment snapshots.",
        category="Automation",
        icon="📡",
        badge="advanced",
        order=30,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._current_package = None  # Holds the last captured/imported package
        self.init_ui()

    def init_ui(self):
        """Initialize the UI layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("State Teleport"))
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #a277ff;"
        )
        layout.addWidget(header)

        description = QLabel(self.tr(
            "Capture your development workspace state and restore it "
            "on another device. Includes git branch, VS Code workspace, "
            "terminal state, and environment."
        ))
        description.setWordWrap(True)
        description.setStyleSheet("color: #9da7bf; font-size: 12px;")
        layout.addWidget(description)

        # Capture section
        layout.addWidget(self._create_capture_section())

        # Saved States section
        layout.addWidget(self._create_saved_section())

        # Restore section
        layout.addWidget(self._create_restore_section())

        # Output log
        log_group = QGroupBox(self.tr("Output Log"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        layout.addWidget(log_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*CONTENT_MARGINS)
        main_layout.addWidget(scroll)

    # ==================== CAPTURE SECTION ====================

    def _create_capture_section(self) -> QGroupBox:
        """Create the workspace capture section."""
        group = QGroupBox(self.tr("Capture Workspace"))
        layout = QVBoxLayout(group)

        # Workspace path selector
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel(self.tr("Workspace Path:")))

        self.workspace_path_edit = QLineEdit()
        self.workspace_path_edit.setPlaceholderText(
            self.tr("Auto-detect from current directory")
        )
        # Try to auto-detect a git repo in CWD
        cwd = os.getcwd()
        if os.path.isdir(os.path.join(cwd, ".git")):
            self.workspace_path_edit.setText(cwd)
        path_layout.addWidget(self.workspace_path_edit)

        browse_btn = QPushButton(self.tr("Browse..."))
        browse_btn.clicked.connect(self._browse_workspace)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Capture button
        btn_layout = QHBoxLayout()
        capture_btn = QPushButton(self.tr("Capture State"))
        capture_btn.setStyleSheet(
            "font-weight: bold; padding: 8px 16px;"
        )
        capture_btn.clicked.connect(self._capture_state)
        btn_layout.addWidget(capture_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Capture summary label
        self.capture_summary = QLabel(self.tr("No state captured yet."))
        self.capture_summary.setWordWrap(True)
        self.capture_summary.setStyleSheet("color: #9da7bf;")
        layout.addWidget(self.capture_summary)

        return group

    # ==================== SAVED STATES SECTION ====================

    def _create_saved_section(self) -> QGroupBox:
        """Create the saved teleport packages section."""
        group = QGroupBox(self.tr("Saved States"))
        layout = QVBoxLayout(group)

        # Table of saved packages
        self.packages_table = QTableWidget(0, 4)
        self.packages_table.setHorizontalHeaderLabels([
            self.tr("Package ID"),
            self.tr("Source Device"),
            self.tr("Date"),
            self.tr("Size"),
        ])
        header = self.packages_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.packages_table.setMaximumHeight(180)
        self.packages_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        BaseTab.configure_table(self.packages_table)
        layout.addWidget(self.packages_table)

        # Action buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton(self.tr("Refresh List"))
        refresh_btn.clicked.connect(self._refresh_packages)
        btn_layout.addWidget(refresh_btn)

        export_btn = QPushButton(self.tr("Export to File"))
        export_btn.clicked.connect(self._export_package)
        btn_layout.addWidget(export_btn)

        send_btn = QPushButton(self.tr("Send to Device"))
        send_btn.clicked.connect(self._send_to_device)
        btn_layout.addWidget(send_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    # ==================== RESTORE SECTION ====================

    def _create_restore_section(self) -> QGroupBox:
        """Create the restore section."""
        group = QGroupBox(self.tr("Restore"))
        layout = QVBoxLayout(group)

        # Import button
        import_layout = QHBoxLayout()
        import_btn = QPushButton(self.tr("Import from File"))
        import_btn.clicked.connect(self._import_package)
        import_layout.addWidget(import_btn)
        import_layout.addStretch()
        layout.addLayout(import_layout)

        # Incoming teleport preview
        self.restore_preview = QLabel(
            self.tr("No incoming teleport. Import a package file to begin.")
        )
        self.restore_preview.setWordWrap(True)
        self.restore_preview.setStyleSheet("color: #9da7bf;")
        layout.addWidget(self.restore_preview)

        # Apply button
        apply_layout = QHBoxLayout()
        self.apply_btn = QPushButton(self.tr("Apply Teleport"))
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet(
            "font-weight: bold; padding: 8px 16px;"
        )
        self.apply_btn.clicked.connect(self._apply_teleport)
        apply_layout.addWidget(self.apply_btn)
        apply_layout.addStretch()
        layout.addLayout(apply_layout)

        return group

    # ==================== SLOTS ====================

    def _browse_workspace(self):
        """Open a directory picker for the workspace path."""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Workspace Directory"),
            self.workspace_path_edit.text() or os.path.expanduser("~"),
        )
        if directory:
            self.workspace_path_edit.setText(directory)

    def _capture_state(self):
        """Capture the current workspace state."""
        ws_path = self.workspace_path_edit.text().strip() or None
        self.log(self.tr("Capturing workspace state..."))

        try:
            state = StateTeleportManager.capture_full_state(ws_path)
            package = StateTeleportManager.create_teleport_package(
                state, target_device="pending"
            )
            self._current_package = package

            # Save to package directory
            pkg_dir = StateTeleportManager.get_package_dir()
            filename = f"teleport_{package.package_id[:8]}.json"
            filepath = os.path.join(pkg_dir, filename)
            StateTeleportManager.save_package_to_file(package, filepath)

            # Update summary
            git_branch = state.git_state.get("branch", "N/A")
            git_status = state.git_state.get("status", "N/A")
            summary = self.tr(
                "Captured: host={host}, branch={branch} ({status}), "
                "files={files}, size={size} bytes"
            ).format(
                host=state.hostname,
                branch=git_branch,
                status=git_status,
                files=len(state.open_files),
                size=package.size_bytes,
            )
            self.capture_summary.setText(summary)
            self.log(self.tr("State captured successfully."))
            self._refresh_packages()

        except Exception as exc:
            self.log(self.tr("Failed to capture state: {}").format(str(exc)))

    def _refresh_packages(self):
        """Refresh the saved packages table."""
        try:
            packages = StateTeleportManager.list_saved_packages()
        except Exception:
            packages = []

        self.packages_table.setRowCount(len(packages))

        for row, pkg in enumerate(packages):
            self.packages_table.setItem(
                row, 0,
                QTableWidgetItem(pkg.get("package_id", "")[:12]),
            )
            self.packages_table.setItem(
                row, 1,
                QTableWidgetItem(pkg.get("source_device", "")),
            )
            created = pkg.get("created_at", 0)
            date_str = (
                time.strftime("%Y-%m-%d %H:%M", time.localtime(created))
                if created
                else "Unknown"
            )
            self.packages_table.setItem(row, 2, QTableWidgetItem(date_str))
            size = pkg.get("size_bytes", 0)
            self.packages_table.setItem(
                row, 3, QTableWidgetItem(f"{size} B")
            )

    def _export_package(self):
        """Export the last captured package to a file."""
        if not self._current_package:
            self.log(self.tr("No captured state to export. Capture first."))
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Teleport Package"),
            os.path.expanduser("~/teleport_package.json"),
            self.tr("JSON files (*.json)"),
        )
        if path:
            result = StateTeleportManager.save_package_to_file(
                self._current_package, path
            )
            self.log(result.message)

    def _send_to_device(self):
        """Send a package to a discovered device on the mesh network."""
        # Check if we have a current package
        if not self._current_package:
            self.log(self.tr("No package to send. Capture or import a package first."))
            return

        # Discover mesh devices
        self.log(self.tr("Discovering mesh devices..."))
        peers = MeshDiscovery.discover_peers(timeout=3)

        if not peers:
            self.log(self.tr(
                "No mesh devices found. "
                "Use 'Export to File' for manual transfer."
            ))
            return

        # For now, use the first peer found (could add a device selector dialog)
        peer = peers[0]

        try:
            # Get the package file path
            pkg_dir = StateTeleportManager.get_package_dir()
            filename = f"teleport_{self._current_package.package_id[:8]}.json"
            package_path = os.path.join(pkg_dir, filename)

            # If the package file doesn't exist, save it first
            if not os.path.isfile(package_path):
                StateTeleportManager.save_package_to_file(self._current_package, package_path)

            # Send the file to the peer
            self.log(self.tr("Sending package to {}...").format(peer.name))
            result = FileDropManager.send_file(
                peer.address,
                peer.port,
                package_path
            )

            if result.success:
                self.log(self.tr("Package sent to {} successfully.").format(peer.name))
            else:
                self.log(self.tr("Failed to send package: {}").format(result.message))

        except Exception as e:
            self.log(self.tr("Error sending package: {}").format(str(e)))

    def _import_package(self):
        """Import a teleport package from a file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Teleport Package"),
            os.path.expanduser("~"),
            self.tr("JSON files (*.json)"),
        )
        if not path:
            return

        try:
            package = StateTeleportManager.load_package_from_file(path)
            self._current_package = package
            self.apply_btn.setEnabled(True)

            ws = package.workspace
            branch = ws.git_state.get("branch", "N/A")
            ws_path = ws.vscode_workspace.get("workspace_path", "N/A")
            files_count = len(ws.open_files)

            preview = self.tr(
                "Incoming teleport from {source}:\n"
                "  Branch: {branch}\n"
                "  Workspace: {workspace}\n"
                "  Open files: {files}\n"
                "  Captured: {time}"
            ).format(
                source=package.source_device,
                branch=branch,
                workspace=ws_path,
                files=files_count,
                time=time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(ws.timestamp)
                ),
            )
            self.restore_preview.setText(preview)
            self.log(self.tr("Package imported successfully."))

        except (ValueError, FileNotFoundError, Exception) as exc:
            self.log(self.tr("Failed to import package: {}").format(str(exc)))

    def _apply_teleport(self):
        """Apply an imported teleport package with confirmation."""
        if not self._current_package:
            return

        ws = self._current_package.workspace
        branch = ws.git_state.get("branch", "N/A")

        reply = QMessageBox.question(
            self,
            self.tr("Confirm Teleport"),
            self.tr(
                "This will:\n"
                "- Checkout branch '{branch}'\n"
                "- Open VS Code at the workspace\n\n"
                "Continue?"
            ).format(branch=branch),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log(self.tr("Applying teleport..."))
        result = StateTeleportManager.apply_teleport(self._current_package)
        self.log(result.message)

        if result.success:
            self.log(self.tr("Teleport applied successfully."))
        else:
            self.log(self.tr("Teleport completed with warnings."))

    def log(self, message: str):
        """Add a message to the output log."""
        self.output_text.append(message)
