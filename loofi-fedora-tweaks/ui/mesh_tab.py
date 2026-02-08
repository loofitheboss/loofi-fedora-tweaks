"""
Loofi Link tab — mesh device discovery, clipboard sync, and File Drop.
Part of v12.0 "Sovereign Update".

Provides a three-sub-tab interface:
  Devices    — discovered peers, scan/refresh, online status
  Clipboard  — clipboard preview, sync-to-device, pairing code
  File Drop  — drag-and-drop file sending, transfer progress, incoming acceptance
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QTextEdit, QScrollArea, QFrame, QTabWidget, QFileDialog,
    QProgressBar, QLineEdit, QMessageBox,
)
from PyQt6.QtCore import Qt

from utils.mesh_discovery import MeshDiscovery, PeerDevice
from utils.clipboard_sync import ClipboardSync
from utils.file_drop import FileDropManager


class MeshTab(QWidget):
    """Loofi Link tab with Devices, Clipboard, and File Drop sub-tabs."""

    def __init__(self):
        super().__init__()
        self._peers: list = []
        self.init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def init_ui(self):
        """Build the complete tab layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # ---- Top banner: device name + local IPs ----
        banner = QGroupBox(self.tr("Loofi Link — This Device"))
        banner_layout = QVBoxLayout(banner)

        device_name = MeshDiscovery.get_device_name()
        local_ips = MeshDiscovery.get_local_ips()
        ip_text = ", ".join(local_ips) if local_ips else self.tr("No network interfaces detected")

        self.lbl_device_name = QLabel(self.tr("Device Name: {}").format(device_name))
        self.lbl_device_name.setStyleSheet("font-weight: bold;")
        banner_layout.addWidget(self.lbl_device_name)

        self.lbl_local_ips = QLabel(self.tr("Local IPs: {}").format(ip_text))
        banner_layout.addWidget(self.lbl_local_ips)

        main_layout.addWidget(banner)

        # ---- Sub-tabs ----
        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self._build_devices_tab(), self.tr("Devices"))
        self.sub_tabs.addTab(self._build_clipboard_tab(), self.tr("Clipboard"))
        self.sub_tabs.addTab(self._build_filedrop_tab(), self.tr("File Drop"))
        main_layout.addWidget(self.sub_tabs)

        # ---- Output log ----
        log_group = QGroupBox(self.tr("Output Log"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        main_layout.addWidget(log_group)

    # ------------------------------------------------------------------
    # Sub-tab: Devices
    # ------------------------------------------------------------------

    def _build_devices_tab(self) -> QWidget:
        """Construct the Devices sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Peer list
        peer_group = QGroupBox(self.tr("Discovered Peers"))
        peer_layout = QVBoxLayout(peer_group)

        self.peer_list = QListWidget()
        self.peer_list.setMinimumHeight(180)
        peer_layout.addWidget(self.peer_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_scan = QPushButton(self.tr("Scan Network"))
        self.btn_scan.clicked.connect(self.on_scan_peers)
        btn_layout.addWidget(self.btn_scan)

        self.btn_register = QPushButton(self.tr("Announce This Device"))
        self.btn_register.clicked.connect(self.on_register_service)
        btn_layout.addWidget(self.btn_register)

        self.btn_unregister = QPushButton(self.tr("Stop Announcing"))
        self.btn_unregister.clicked.connect(self.on_unregister_service)
        btn_layout.addWidget(self.btn_unregister)

        btn_layout.addStretch()
        peer_layout.addLayout(btn_layout)

        layout.addWidget(peer_group)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Sub-tab: Clipboard
    # ------------------------------------------------------------------

    def _build_clipboard_tab(self) -> QWidget:
        """Construct the Clipboard sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Clipboard preview
        clip_group = QGroupBox(self.tr("Clipboard Preview"))
        clip_layout = QVBoxLayout(clip_group)

        self.clipboard_preview = QTextEdit()
        self.clipboard_preview.setReadOnly(True)
        self.clipboard_preview.setMaximumHeight(100)
        clip_layout.addWidget(self.clipboard_preview)

        btn_refresh_clip = QPushButton(self.tr("Refresh Clipboard"))
        btn_refresh_clip.clicked.connect(self.on_refresh_clipboard)
        clip_layout.addWidget(btn_refresh_clip)

        layout.addWidget(clip_group)

        # Sync controls
        sync_group = QGroupBox(self.tr("Sync to Device"))
        sync_layout = QVBoxLayout(sync_group)

        row = QHBoxLayout()
        self.device_combo = QComboBox()
        row.addWidget(self.device_combo)

        btn_sync = QPushButton(self.tr("Send Clipboard"))
        btn_sync.clicked.connect(self.on_send_clipboard)
        row.addWidget(btn_sync)
        row.addStretch()
        sync_layout.addLayout(row)

        layout.addWidget(sync_group)

        # Pairing section
        pair_group = QGroupBox(self.tr("Device Pairing"))
        pair_layout = QVBoxLayout(pair_group)

        pair_row = QHBoxLayout()
        self.lbl_pairing_code = QLabel(self.tr("Pairing Code: ------"))
        self.lbl_pairing_code.setStyleSheet("font-family: monospace; font-size: 16px;")
        pair_row.addWidget(self.lbl_pairing_code)

        btn_generate = QPushButton(self.tr("Generate Code"))
        btn_generate.clicked.connect(self.on_generate_pairing_code)
        pair_row.addWidget(btn_generate)
        pair_row.addStretch()
        pair_layout.addLayout(pair_row)

        layout.addWidget(pair_group)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Sub-tab: File Drop
    # ------------------------------------------------------------------

    def _build_filedrop_tab(self) -> QWidget:
        """Construct the File Drop sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Drop zone
        drop_group = QGroupBox(self.tr("Send File"))
        drop_layout = QVBoxLayout(drop_group)

        self.lbl_drop = QLabel(
            self.tr(
                "Drag and drop a file here, or click 'Choose File' to select one.\n"
                "Files are transferred over your local network only."
            )
        )
        self.lbl_drop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop.setMinimumHeight(80)
        self.lbl_drop.setStyleSheet(
            "border: 2px dashed #666; border-radius: 8px; padding: 20px; color: #aaa;"
        )
        drop_layout.addWidget(self.lbl_drop)

        file_btn_row = QHBoxLayout()
        self.btn_choose_file = QPushButton(self.tr("Choose File"))
        self.btn_choose_file.clicked.connect(self.on_choose_file)
        file_btn_row.addWidget(self.btn_choose_file)

        self.lbl_selected_file = QLabel(self.tr("No file selected"))
        file_btn_row.addWidget(self.lbl_selected_file)
        file_btn_row.addStretch()
        drop_layout.addLayout(file_btn_row)

        layout.addWidget(drop_group)

        # Transfer progress
        progress_group = QGroupBox(self.tr("Transfer Progress"))
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.lbl_transfer_status = QLabel(self.tr("No active transfer"))
        progress_layout.addWidget(self.lbl_transfer_status)

        layout.addWidget(progress_group)

        # Incoming transfers
        incoming_group = QGroupBox(self.tr("Incoming Transfers"))
        incoming_layout = QVBoxLayout(incoming_group)

        self.incoming_list = QListWidget()
        self.incoming_list.setMaximumHeight(120)
        incoming_layout.addWidget(self.incoming_list)

        inc_btn_row = QHBoxLayout()
        btn_accept = QPushButton(self.tr("Accept"))
        btn_accept.clicked.connect(self.on_accept_transfer)
        inc_btn_row.addWidget(btn_accept)

        btn_reject = QPushButton(self.tr("Reject"))
        btn_reject.clicked.connect(self.on_reject_transfer)
        inc_btn_row.addWidget(btn_reject)

        inc_btn_row.addStretch()
        incoming_layout.addLayout(inc_btn_row)

        layout.addWidget(incoming_group)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Slots / actions
    # ------------------------------------------------------------------

    def on_scan_peers(self):
        """Scan the LAN for Loofi peers."""
        self.log(self.tr("Scanning for peers..."))
        self._peers = MeshDiscovery.discover_peers(timeout=5)
        self.peer_list.clear()

        if not self._peers:
            self.peer_list.addItem(QListWidgetItem(self.tr("No peers found.")))
            self.log(self.tr("Scan complete. No peers found."))
            return

        for peer in self._peers:
            caps = ", ".join(peer.capabilities) if peer.capabilities else self.tr("none")
            text = self.tr("{name} ({addr}) - {caps}").format(
                name=peer.name, addr=peer.address, caps=caps,
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, peer.device_id)
            self.peer_list.addItem(item)

        self.log(self.tr("Found {} peer(s).").format(len(self._peers)))
        self._update_device_combo()

    def on_register_service(self):
        """Announce this device on the network."""
        result = MeshDiscovery.register_service()
        self.log(result.message)

    def on_unregister_service(self):
        """Stop announcing this device."""
        result = MeshDiscovery.unregister_service()
        self.log(result.message)

    def on_refresh_clipboard(self):
        """Read the system clipboard and display it."""
        content = ClipboardSync.get_clipboard_content()
        self.clipboard_preview.setPlainText(content or self.tr("(empty clipboard)"))

    def on_send_clipboard(self):
        """Send clipboard content to the selected peer (stub)."""
        idx = self.device_combo.currentIndex()
        if idx < 0 or not self._peers:
            self.log(self.tr("No peer selected for clipboard sync."))
            return
        peer = self._peers[idx]
        self.log(self.tr("Clipboard sync to {} requested (not yet implemented).").format(peer.name))

    def on_generate_pairing_code(self):
        """Generate and display a new 6-digit pairing code."""
        code = ClipboardSync.generate_pairing_key()
        self.lbl_pairing_code.setText(self.tr("Pairing Code: {}").format(code))
        self.log(self.tr("New pairing code generated."))

    def on_choose_file(self):
        """Open a file dialog to select a file for transfer."""
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Select File"))
        if path:
            metadata = FileDropManager.prepare_file_metadata(path)
            size_str = FileDropManager.format_file_size(metadata["size"])
            self.lbl_selected_file.setText(
                self.tr("{} ({})").format(metadata["name"], size_str)
            )
            self.log(self.tr("Selected file: {}").format(path))

    def on_accept_transfer(self):
        """Accept the selected incoming transfer."""
        current = self.incoming_list.currentItem()
        if not current:
            self.log(self.tr("No transfer selected."))
            return
        transfer_id = current.data(Qt.ItemDataRole.UserRole)
        if transfer_id:
            result = FileDropManager.accept_transfer(transfer_id)
            self.log(result.message)

    def on_reject_transfer(self):
        """Reject the selected incoming transfer."""
        current = self.incoming_list.currentItem()
        if not current:
            self.log(self.tr("No transfer selected."))
            return
        transfer_id = current.data(Qt.ItemDataRole.UserRole)
        if transfer_id:
            result = FileDropManager.reject_transfer(transfer_id)
            self.log(result.message)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_device_combo(self):
        """Repopulate the clipboard device selector from discovered peers."""
        self.device_combo.clear()
        for peer in self._peers:
            self.device_combo.addItem(
                f"{peer.name} ({peer.address})", peer.device_id
            )

    def log(self, message: str):
        """Append a message to the output log."""
        self.output_text.append(message)
