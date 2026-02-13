"""
Hardware Tab - Consolidated hardware control interface.
CPU Governor, GPU Mode, Fan Control, Battery Limits
Expanded in v10.0 "Zenith" to absorb Tweaks tab features:
- Audio services restart (Pipewire)
- Battery charge limit control
- Fingerprint enrollment
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QSlider, QMessageBox, QGridLayout, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from utils.hardware import HardwareManager
from utils.command_runner import CommandRunner
from utils.bluetooth import BluetoothManager
from core.plugins.interface import PluginInterface
from core.plugins.metadata import PluginMetadata


class HardwareTab(QWidget, PluginInterface):
    """Consolidated hardware control tab."""

    _METADATA = PluginMetadata(
        id="hardware",
        name="Hardware",
        description="Hardware info and settings including CPU governor, GPU mode, fan control, and battery.",
        category="Hardware",
        icon="⚡",
        badge="recommended",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self._setup_command_runner()
        self.init_ui()

        # Auto-refresh timer for dynamic values
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def _setup_command_runner(self):
        """Setup CommandRunner for hardware commands (from Tweaks tab)."""
        self.hw_runner = CommandRunner()
        self.hw_runner.output_received.connect(self._on_hw_output)
        self.hw_runner.finished.connect(self._on_hw_command_finished)

    def _on_hw_output(self, text):
        """Handle output from hardware commands."""
        if hasattr(self, 'hw_output_area'):
            self.hw_output_area.moveCursor(
                self.hw_output_area.textCursor().MoveOperation.End
            )
            self.hw_output_area.insertPlainText(text)
            self.hw_output_area.moveCursor(
                self.hw_output_area.textCursor().MoveOperation.End
            )

    def _on_hw_command_finished(self, exit_code):
        """Handle hardware command completion."""
        if hasattr(self, 'hw_output_area'):
            self.hw_output_area.moveCursor(
                self.hw_output_area.textCursor().MoveOperation.End
            )
            self.hw_output_area.insertPlainText(
                self.tr("\nCommand finished with exit code: {}\n").format(exit_code)
            )

    def _run_hw_command(self, cmd, args, description=""):
        """Execute a hardware command with output logging."""
        if hasattr(self, 'hw_output_area'):
            self.hw_output_area.clear()
            if description:
                self.hw_output_area.setPlainText(description + "\n")
        self.hw_runner.run_command(cmd, args)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("⚡ Hardware Control"))
        header.setObjectName("header")
        layout.addWidget(header)

        # Grid for cards
        grid = QGridLayout()
        grid.setSpacing(20)

        # CPU Card
        cpu_card = self.create_cpu_card()
        grid.addWidget(cpu_card, 0, 0)

        # Power Profile Card
        power_card = self.create_power_profile_card()
        grid.addWidget(power_card, 0, 1)

        # GPU Card (if hybrid)
        gpu_card = self.create_gpu_card()
        grid.addWidget(gpu_card, 1, 0)

        # Fan Control Card
        fan_card = self.create_fan_card()
        grid.addWidget(fan_card, 1, 1)

        # Audio Card (from Tweaks tab, row 2, col 0)
        audio_card = self.create_audio_card()
        grid.addWidget(audio_card, 2, 0)

        # Battery Limit Card (from Tweaks tab, row 2, col 1)
        battery_card = self.create_battery_limit_card()
        grid.addWidget(battery_card, 2, 1)

        # Fingerprint Card (from Tweaks tab, row 3, col 0)
        fingerprint_card = self.create_fingerprint_card()
        grid.addWidget(fingerprint_card, 3, 0)

        # Bluetooth Card (v17.0 Atlas)
        bluetooth_card = self.create_bluetooth_card()
        grid.addWidget(bluetooth_card, 3, 1)

        layout.addLayout(grid)

        # Output area for hardware commands (from Tweaks tab)
        layout.addWidget(QLabel(self.tr("Output Log:")))
        self.hw_output_area = QTextEdit()
        self.hw_output_area.setReadOnly(True)
        self.hw_output_area.setMaximumHeight(150)
        layout.addWidget(self.hw_output_area)

        layout.addStretch()

    def create_card(self, title: str, icon: str) -> QGroupBox:
        """Create a styled card group box."""
        card = QGroupBox(f"{icon} {title}")
        card.setStyleSheet("""
            QGroupBox {
                background-color: #313244;
                border-radius: 12px;
                padding: 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                padding: 10px;
            }
        """)
        return card

    # ==================== CPU GOVERNOR ====================

    def create_cpu_card(self) -> QGroupBox:
        card = self.create_card(self.tr("CPU Governor"), "🔧")
        layout = QVBoxLayout(card)

        # Current frequency display
        freq = HardwareManager.get_cpu_frequency()
        self.lbl_cpu_freq = QLabel(self.tr("Current: {} MHz / {} MHz").format(freq['current'], freq['max']))
        self.lbl_cpu_freq.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.lbl_cpu_freq)

        # Governor dropdown
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(self.tr("Governor:")))

        self.combo_governor = QComboBox()
        governors = HardwareManager.get_available_governors()
        self.combo_governor.addItems(governors)

        # Set current governor
        current = HardwareManager.get_current_governor()
        if current in governors:
            self.combo_governor.setCurrentText(current)

        self.combo_governor.currentTextChanged.connect(self.on_governor_changed)
        h_layout.addWidget(self.combo_governor)
        layout.addLayout(h_layout)

        # Description
        desc = QLabel(self.tr("Controls CPU frequency scaling policy"))
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(desc)

        return card

    def on_governor_changed(self, governor: str):
        """Handle governor change."""
        success = HardwareManager.set_governor(governor)
        if success:
            self.show_toast(self.tr("CPU Governor set to '{}'").format(governor))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to set governor to '{}'").format(governor))
            # Revert combo box
            current = HardwareManager.get_current_governor()
            self.combo_governor.blockSignals(True)
            self.combo_governor.setCurrentText(current)
            self.combo_governor.blockSignals(False)

    # ==================== POWER PROFILE ====================

    def create_power_profile_card(self) -> QGroupBox:
        card = self.create_card(self.tr("Power Profile"), "🔋")
        layout = QVBoxLayout(card)

        if not HardwareManager.is_power_profiles_available():
            layout.addWidget(QLabel(self.tr("❌ power-profiles-daemon not installed")))
            return card

        # Current profile
        current = HardwareManager.get_power_profile()
        self.lbl_power_profile = QLabel(self.tr("Current: {}").format(current.title()))
        self.lbl_power_profile.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.lbl_power_profile)

        # Profile buttons
        btn_layout = QHBoxLayout()

        profiles = [
            ("🔋 Saver", "power-saver", "#a6e3a1"),
            ("⚖️ Balanced", "balanced", "#89b4fa"),
            ("⚡ Performance", "performance", "#f38ba8")
        ]

        for label, profile, color in profiles:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}20;
                    border: 1px solid {color};
                    color: {color};
                    padding: 8px 12px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    color: #1e1e2e;
                }}
            """)
            btn.clicked.connect(lambda checked, p=profile: self.set_power_profile(p))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        return card

    def set_power_profile(self, profile: str):
        success = HardwareManager.set_power_profile(profile)
        if success:
            self.lbl_power_profile.setText(self.tr("Current: {}").format(profile.title()))
            self.show_toast(self.tr("Power profile set to '{}'").format(profile))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to set power profile to '{}'").format(profile))

    # ==================== GPU MODE ====================

    def create_gpu_card(self) -> QGroupBox:
        card = self.create_card(self.tr("GPU Mode"), "🎮")
        layout = QVBoxLayout(card)

        if not HardwareManager.is_hybrid_gpu():
            layout.addWidget(QLabel(self.tr("ℹ️ No hybrid GPU detected")))
            return card

        tools = HardwareManager.get_available_gpu_tools()
        if not tools:
            layout.addWidget(QLabel(self.tr("❌ No GPU switching tool found")))
            install_btn = QPushButton(self.tr("📦 Install envycontrol"))
            install_btn.clicked.connect(self.install_envycontrol)
            layout.addWidget(install_btn)
            return card

        # Current mode
        current = HardwareManager.get_gpu_mode()
        self.lbl_gpu_mode = QLabel(self.tr("Current: {}").format(current.title()))
        self.lbl_gpu_mode.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.lbl_gpu_mode)

        # Mode buttons
        btn_layout = QHBoxLayout()

        modes = [
            ("☀️ Integrated", "integrated", "#a6e3a1"),
            ("🔀 Hybrid", "hybrid", "#89b4fa"),
            ("🚀 NVIDIA", "nvidia", "#f38ba8")
        ]

        for label, mode, color in modes:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color}20;
                    border: 1px solid {color};
                    color: {color};
                    padding: 8px 12px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    color: #1e1e2e;
                }}
            """)
            btn.clicked.connect(lambda checked, m=mode: self.set_gpu_mode(m))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # Warning
        warn = QLabel(self.tr("⚠️ Requires logout/reboot"))
        warn.setStyleSheet("color: #f9e2af; font-size: 11px;")
        layout.addWidget(warn)

        return card

    def set_gpu_mode(self, mode: str):
        reply = QMessageBox.question(
            self, self.tr("Confirm GPU Mode Change"),
            self.tr("Switch GPU to '{}' mode?\n\nThis requires a logout or reboot.").format(mode.title()),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, message = HardwareManager.set_gpu_mode(mode)
            if success:
                self.lbl_gpu_mode.setText(self.tr("Current: {} (pending)").format(mode.title()))
                QMessageBox.information(self, self.tr("Success"), message)
            else:
                QMessageBox.warning(self, self.tr("Error"), message)

    def install_envycontrol(self):
        """Guide user to install envycontrol."""
        QMessageBox.information(
            self, self.tr("Install envycontrol"),
            self.tr("To control GPU modes, install envycontrol:\n\n"
                    "pip install --user envycontrol\n\n"
                    "Or visit: https://github.com/bayasdev/envycontrol")
        )

    # ==================== FAN CONTROL ====================

    def create_fan_card(self) -> QGroupBox:
        card = self.create_card(self.tr("Fan Control"), "🌀")
        layout = QVBoxLayout(card)

        if not HardwareManager.is_nbfc_available():
            layout.addWidget(QLabel(self.tr("❌ nbfc-linux not installed")))
            install_btn = QPushButton(self.tr("📦 Learn how to install"))
            install_btn.clicked.connect(self.show_nbfc_help)
            layout.addWidget(install_btn)
            return card

        # Current status
        status = HardwareManager.get_fan_status()
        self.lbl_fan_status = QLabel(self.tr("Speed: {}% | Temp: {}°C").format(int(status['speed']), int(status['temperature'])))
        self.lbl_fan_status.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.lbl_fan_status)

        # Fan speed slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel(self.tr("Manual:")))

        self.slider_fan = QSlider(Qt.Orientation.Horizontal)
        self.slider_fan.setRange(0, 100)
        self.slider_fan.setValue(50)
        self.slider_fan.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_fan.setTickInterval(25)
        slider_layout.addWidget(self.slider_fan)

        self.lbl_fan_percent = QLabel("50%")
        slider_layout.addWidget(self.lbl_fan_percent)

        self.slider_fan.valueChanged.connect(lambda v: self.lbl_fan_percent.setText(f"{v}%"))
        layout.addLayout(slider_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_apply = QPushButton(self.tr("✅ Apply"))
        btn_apply.clicked.connect(lambda: self.set_fan_speed(self.slider_fan.value()))
        btn_layout.addWidget(btn_apply)

        btn_auto = QPushButton(self.tr("🔄 Auto"))
        btn_auto.clicked.connect(lambda: self.set_fan_speed(-1))
        btn_layout.addWidget(btn_auto)

        layout.addLayout(btn_layout)
        return card

    def set_fan_speed(self, speed: int):
        success = HardwareManager.set_fan_speed(speed)
        if success:
            mode = self.tr("Auto") if speed < 0 else f"{speed}%"
            self.show_toast(self.tr("Fan speed set to {}").format(mode))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to set fan speed"))

    def show_nbfc_help(self):
        QMessageBox.information(
            self, self.tr("Install nbfc-linux"),
            self.tr("NBFC (NoteBook FanControl) for Linux:\n\n"
                    "1. Visit: https://github.com/nbfc-linux/nbfc-linux\n"
                    "2. Follow installation instructions for your distro\n"
                    "3. Find a config for your laptop model\n"
                    "4. Restart this app")
        )

    # ==================== AUDIO (from Tweaks tab) ====================

    def create_audio_card(self) -> QGroupBox:
        """Create audio services restart card (from TweaksTab)."""
        card = self.create_card(self.tr("Audio Services"), "🔊")
        layout = QVBoxLayout(card)

        desc = QLabel(self.tr("Restart Pipewire audio services if sound is not working"))
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_restart_audio = QPushButton(self.tr("Restart Audio Services (Pipewire)"))
        btn_restart_audio.clicked.connect(
            lambda: self._run_hw_command(
                "systemctl",
                ["--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"],
                self.tr("Restarting Audio Services...")
            )
        )
        layout.addWidget(btn_restart_audio)

        return card

    # ==================== BATTERY LIMIT (from Tweaks tab) ====================

    def create_battery_limit_card(self) -> QGroupBox:
        """Create battery charge limit card (from TweaksTab)."""
        card = self.create_card(self.tr("Battery Charge Limit"), "🔋")
        layout = QVBoxLayout(card)

        desc = QLabel(self.tr("Limit battery charge to extend battery lifespan"))
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()

        btn_limit_80 = QPushButton(self.tr("Limit to 80%"))
        btn_limit_80.clicked.connect(lambda: self._set_battery_limit(80))
        btn_layout.addWidget(btn_limit_80)

        btn_limit_100 = QPushButton(self.tr("Limit to 100% (Full)"))
        btn_limit_100.clicked.connect(lambda: self._set_battery_limit(100))
        btn_layout.addWidget(btn_limit_100)

        layout.addLayout(btn_layout)

        return card

    def _set_battery_limit(self, limit):
        """Set battery charge limit using BatteryManager."""
        from utils.battery import BatteryManager
        manager = BatteryManager()
        cmd, args = manager.set_limit(limit)

        if cmd:
            self._run_hw_command(
                cmd, args,
                self.tr("Setting Battery Limit to {}% (Persistent)...").format(limit)
            )
        else:
            if hasattr(self, 'hw_output_area'):
                self.hw_output_area.setPlainText(
                    self.tr("Failed to prepare battery script.\n")
                )

    # ==================== FINGERPRINT (from Tweaks tab) ====================

    def create_fingerprint_card(self) -> QGroupBox:
        """Create fingerprint enrollment card (from TweaksTab)."""
        card = self.create_card(self.tr("Fingerprint Reader"), "👆")
        layout = QVBoxLayout(card)

        desc = QLabel(self.tr("Enroll your fingerprint for authentication"))
        desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_enroll_finger = QPushButton(self.tr("Enroll Fingerprint (GUI)"))
        btn_enroll_finger.clicked.connect(self._enroll_fingerprint)
        layout.addWidget(btn_enroll_finger)

        return card

    def _enroll_fingerprint(self):
        """Open the fingerprint enrollment dialog."""
        from ui.fingerprint_dialog import FingerprintDialog
        dialog = FingerprintDialog(self)
        dialog.exec()

    # ==================== BLUETOOTH (v17.0 Atlas) ====================

    def create_bluetooth_card(self) -> QGroupBox:
        """Create Bluetooth management card."""
        card = self.create_card(self.tr("Bluetooth"), "📶")
        layout = QVBoxLayout(card)

        # Adapter status
        self.lbl_bt_status = QLabel(self.tr("Bluetooth: detecting..."))
        self.lbl_bt_status.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.lbl_bt_status)

        # Device list (compact)
        self.lbl_bt_devices = QLabel(self.tr("Paired devices: —"))
        self.lbl_bt_devices.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.lbl_bt_devices.setWordWrap(True)
        layout.addWidget(self.lbl_bt_devices)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_power_on = QPushButton(self.tr("Power On"))
        btn_power_on.clicked.connect(self._bt_power_on)
        btn_layout.addWidget(btn_power_on)

        btn_power_off = QPushButton(self.tr("Power Off"))
        btn_power_off.clicked.connect(self._bt_power_off)
        btn_layout.addWidget(btn_power_off)

        btn_scan = QPushButton(self.tr("Scan"))
        btn_scan.clicked.connect(self._bt_scan)
        btn_layout.addWidget(btn_scan)

        layout.addLayout(btn_layout)

        # Initial status check
        QTimer.singleShot(500, self._bt_refresh_status)

        return card

    def _bt_refresh_status(self):
        """Refresh Bluetooth adapter and device status."""
        try:
            status = BluetoothManager.get_adapter_status()
            if status.adapter_name:
                power = "🟢 On" if status.powered else "🔴 Off"
                self.lbl_bt_status.setText(
                    self.tr("Bluetooth: {} | Adapter: {}").format(power, status.adapter_name)
                )
            else:
                self.lbl_bt_status.setText(self.tr("Bluetooth: ❌ No adapter found"))
                return

            devices = BluetoothManager.list_devices(paired_only=True)
            if devices:
                names = [f"{d.name} ({'connected' if d.connected else 'paired'})"
                         for d in devices[:5]]
                self.lbl_bt_devices.setText(
                    self.tr("Paired devices: {}").format(", ".join(names))
                )
            else:
                self.lbl_bt_devices.setText(self.tr("Paired devices: none"))
        except Exception:
            self.lbl_bt_status.setText(self.tr("Bluetooth: ❌ bluetoothctl not available"))

    def _bt_power_on(self):
        """Turn Bluetooth adapter on."""
        result = BluetoothManager.power_on()
        if result.success:
            self.show_toast(self.tr("Bluetooth powered on"))
        else:
            QMessageBox.warning(self, self.tr("Error"), result.message)
        QTimer.singleShot(500, self._bt_refresh_status)

    def _bt_power_off(self):
        """Turn Bluetooth adapter off."""
        result = BluetoothManager.power_off()
        if result.success:
            self.show_toast(self.tr("Bluetooth powered off"))
        else:
            QMessageBox.warning(self, self.tr("Error"), result.message)
        QTimer.singleShot(500, self._bt_refresh_status)

    def _bt_scan(self):
        """Scan for nearby Bluetooth devices."""
        self._run_hw_command("bluetoothctl", ["--timeout", "10", "scan", "on"],
                             self.tr("Scanning for Bluetooth devices..."))
        QTimer.singleShot(12000, self._bt_refresh_status)

    # ==================== UTILITIES ====================

    def refresh_status(self):
        """Refresh dynamic values."""
        try:
            # CPU frequency
            freq = HardwareManager.get_cpu_frequency()
            self.lbl_cpu_freq.setText(self.tr("Current: {} MHz / {} MHz").format(freq['current'], freq['max']))

            # Fan status
            if HardwareManager.is_nbfc_available():
                status = HardwareManager.get_fan_status()
                self.lbl_fan_status.setText(self.tr("Speed: {}% | Temp: {}°C").format(int(status['speed']), int(status['temperature'])))
        except Exception:
            pass

    def show_toast(self, message: str):
        """Show a quick toast notification (status bar style)."""
        # For now, just update window title briefly
        parent = self.window()
        if parent:
            original = parent.windowTitle()
            parent.setWindowTitle(f"✓ {message}")
            QTimer.singleShot(2000, lambda: parent.setWindowTitle(original))
