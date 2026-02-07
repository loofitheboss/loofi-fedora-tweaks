"""
Pulse Tab - Automation and event-driven triggers UI.
Manages Focus Mode, automation profiles, and event triggers.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QDialog, QFormLayout, QComboBox, QLineEdit,
    QCheckBox, QTextEdit, QTabWidget, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from utils.focus_mode import FocusMode
from utils.automation_profiles import AutomationProfiles, TriggerType, ActionType
from utils.pulse import SystemPulse
import uuid


class AddRuleDialog(QDialog):
    """Dialog for adding a new automation rule."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Add Automation Rule"))
        self.setMinimumWidth(450)
        
        layout = QFormLayout()
        self.setLayout(layout)
        
        # Rule name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Battery Power Saver")
        layout.addRow(self.tr("Name:"), self.name_input)
        
        # Trigger selection
        self.trigger_combo = QComboBox()
        trigger_options = [
            ("On Battery", TriggerType.ON_BATTERY.value),
            ("On AC Power", TriggerType.ON_AC.value),
            ("On Public Wi-Fi", TriggerType.ON_PUBLIC_WIFI.value),
            ("On Home Wi-Fi", TriggerType.ON_HOME_WIFI.value),
            ("On Ultrawide Monitor", TriggerType.ON_ULTRAWIDE.value),
            ("On Laptop Only", TriggerType.ON_LAPTOP_ONLY.value),
            ("On Startup", TriggerType.ON_STARTUP.value),
        ]
        for label, value in trigger_options:
            self.trigger_combo.addItem(label, value)
        layout.addRow(self.tr("When:"), self.trigger_combo)
        
        # Action selection
        self.action_combo = QComboBox()
        action_options = [
            ("Set Power Profile", ActionType.SET_POWER_PROFILE.value),
            ("Set CPU Governor", ActionType.SET_CPU_GOVERNOR.value),
            ("Enable VPN", ActionType.ENABLE_VPN.value),
            ("Disable VPN", ActionType.DISABLE_VPN.value),
            ("Enable Tiling", ActionType.ENABLE_TILING.value),
            ("Disable Tiling", ActionType.DISABLE_TILING.value),
            ("Set Theme", ActionType.SET_THEME.value),
            ("Enable Focus Mode", ActionType.ENABLE_FOCUS_MODE.value),
            ("Disable Focus Mode", ActionType.DISABLE_FOCUS_MODE.value),
            ("Run Command", ActionType.RUN_COMMAND.value),
        ]
        for label, value in action_options:
            self.action_combo.addItem(label, value)
        self.action_combo.currentIndexChanged.connect(self._on_action_changed)
        layout.addRow(self.tr("Then:"), self.action_combo)
        
        # Action parameter (dynamic based on action)
        self.param_label = QLabel(self.tr("Profile:"))
        self.param_combo = QComboBox()
        self.param_input = QLineEdit()
        self.param_input.hide()
        
        self._update_param_options()
        layout.addRow(self.param_label, self.param_combo)
        layout.addRow("", self.param_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton(self.tr("Add Rule"))
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton(self.tr("Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addRow(btn_layout)
    
    def _on_action_changed(self, index):
        """Update parameter options based on selected action."""
        self._update_param_options()
    
    def _update_param_options(self):
        """Update the parameter combo/input based on action type."""
        action = self.action_combo.currentData()
        self.param_combo.clear()
        self.param_combo.show()
        self.param_input.hide()
        
        if action == ActionType.SET_POWER_PROFILE.value:
            self.param_label.setText(self.tr("Profile:"))
            self.param_combo.addItem("Power Saver", "power-saver")
            self.param_combo.addItem("Balanced", "balanced")
            self.param_combo.addItem("Performance", "performance")
        elif action == ActionType.SET_CPU_GOVERNOR.value:
            self.param_label.setText(self.tr("Governor:"))
            self.param_combo.addItem("Power Save", "powersave")
            self.param_combo.addItem("Schedutil", "schedutil")
            self.param_combo.addItem("Performance", "performance")
            self.param_combo.addItem("Ondemand", "ondemand")
        elif action == ActionType.SET_THEME.value:
            self.param_label.setText(self.tr("Theme:"))
            self.param_combo.addItem("Dark", "dark")
            self.param_combo.addItem("Light", "light")
        elif action in (ActionType.ENABLE_TILING.value, ActionType.DISABLE_TILING.value):
            self.param_label.setText(self.tr("Script:"))
            self.param_combo.addItem("Polonium", "polonium")
            self.param_combo.addItem("Bismuth", "bismuth")
            self.param_combo.addItem("Krohnkite", "krohnkite")
        elif action == ActionType.RUN_COMMAND.value:
            self.param_label.setText(self.tr("Command:"))
            self.param_combo.hide()
            self.param_input.show()
            self.param_input.setPlaceholderText("e.g., notify-send 'Hello'")
        elif action in (ActionType.ENABLE_FOCUS_MODE.value,):
            self.param_label.setText(self.tr("Profile:"))
            for profile in FocusMode.list_profiles():
                self.param_combo.addItem(profile.title(), profile)
        else:
            self.param_label.setText("")
            self.param_combo.hide()
    
    def get_rule(self) -> dict:
        """Get the configured rule."""
        action = self.action_combo.currentData()
        
        # Build action params based on action type
        action_params = {}
        if action == ActionType.SET_POWER_PROFILE.value:
            action_params["profile"] = self.param_combo.currentData()
        elif action == ActionType.SET_CPU_GOVERNOR.value:
            action_params["governor"] = self.param_combo.currentData()
        elif action == ActionType.SET_THEME.value:
            action_params["theme"] = self.param_combo.currentData()
        elif action in (ActionType.ENABLE_TILING.value, ActionType.DISABLE_TILING.value):
            action_params["script"] = self.param_combo.currentData()
        elif action == ActionType.RUN_COMMAND.value:
            action_params["command"] = self.param_input.text()
        elif action == ActionType.ENABLE_FOCUS_MODE.value:
            action_params["profile"] = self.param_combo.currentData() or "default"
        
        return {
            "id": str(uuid.uuid4())[:8],
            "name": self.name_input.text() or "Unnamed Rule",
            "trigger": self.trigger_combo.currentData(),
            "action": action,
            "action_params": action_params,
            "enabled": True
        }


class FocusModeSection(QGroupBox):
    """Focus Mode control section."""
    
    focus_toggled = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.setTitle(self.tr("🎯 Focus Mode"))
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Status and toggle
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel()
        self.status_label.setFont(QFont("", 10))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.toggle_btn = QPushButton()
        self.toggle_btn.setMinimumWidth(120)
        self.toggle_btn.clicked.connect(self._toggle_focus)
        status_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(status_layout)
        
        # Profile selector
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel(self.tr("Profile:")))
        
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch()
        
        layout.addLayout(profile_layout)
        
        # Info about what focus mode does
        info_label = QLabel(self.tr(
            "Focus Mode blocks distracting websites, enables Do Not Disturb, "
            "and closes distracting apps."
        ))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(info_label)
        
        self.refresh()
    
    def refresh(self):
        """Refresh focus mode status."""
        is_active = FocusMode.is_active()
        active_profile = FocusMode.get_active_profile()
        
        # Update profile combo
        self.profile_combo.clear()
        for profile in FocusMode.list_profiles():
            self.profile_combo.addItem(profile.replace("_", " ").title(), profile)
        
        if is_active:
            self.status_label.setText(f"✅ Active ({active_profile})")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.toggle_btn.setText(self.tr("Disable"))
            self.toggle_btn.setStyleSheet("background-color: #f44336;")
            self.profile_combo.setEnabled(False)
        else:
            self.status_label.setText("⭕ Inactive")
            self.status_label.setStyleSheet("color: #888;")
            self.toggle_btn.setText(self.tr("Enable"))
            self.toggle_btn.setStyleSheet("background-color: #4CAF50;")
            self.profile_combo.setEnabled(True)
    
    def _toggle_focus(self):
        """Toggle focus mode."""
        if FocusMode.is_active():
            result = FocusMode.disable()
        else:
            profile = self.profile_combo.currentData() or "default"
            result = FocusMode.enable(profile)
        
        if not result.get("success"):
            QMessageBox.warning(
                self, self.tr("Focus Mode"),
                result.get("message", "Unknown error")
            )
        
        self.refresh()
        self.focus_toggled.emit(FocusMode.is_active())


class AutomationRulesSection(QGroupBox):
    """Automation rules management section."""
    
    def __init__(self):
        super().__init__()
        self.setTitle(self.tr("⚡ Automation Rules"))
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Enable toggle
        enable_layout = QHBoxLayout()
        self.enable_check = QCheckBox(self.tr("Enable Automation"))
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        enable_layout.addWidget(self.enable_check)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)
        
        # Rules list
        self.rules_list = QListWidget()
        self.rules_list.setMinimumHeight(150)
        self.rules_list.itemDoubleClicked.connect(self._toggle_rule)
        layout.addWidget(self.rules_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton(self.tr("➕ Add Rule"))
        self.add_btn.clicked.connect(self._add_rule)
        btn_layout.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton(self.tr("🗑️ Delete"))
        self.delete_btn.clicked.connect(self._delete_rule)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        self.preset_btn = QPushButton(self.tr("📦 Add Presets"))
        self.preset_btn.clicked.connect(self._add_presets)
        btn_layout.addWidget(self.preset_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh()
    
    def refresh(self):
        """Refresh automation rules display."""
        self.enable_check.setChecked(AutomationProfiles.is_enabled())
        
        self.rules_list.clear()
        for rule in AutomationProfiles.list_rules():
            enabled = "✓" if rule.get("enabled") else "✗"
            trigger = rule.get("trigger", "").replace("_", " ").title()
            action = rule.get("action", "").replace("_", " ").title()
            
            item = QListWidgetItem(f"[{enabled}] {rule.get('name')} — {trigger} → {action}")
            item.setData(Qt.ItemDataRole.UserRole, rule.get("id"))
            
            if not rule.get("enabled"):
                item.setForeground(Qt.GlobalColor.gray)
            
            self.rules_list.addItem(item)
    
    def _on_enable_changed(self, state):
        """Handle enable checkbox change."""
        AutomationProfiles.set_enabled(state == Qt.CheckState.Checked.value)
    
    def _add_rule(self):
        """Open dialog to add a new rule."""
        dialog = AddRuleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rule = dialog.get_rule()
            result = AutomationProfiles.add_rule(rule)
            if result.get("success"):
                self.refresh()
            else:
                QMessageBox.warning(self, self.tr("Error"), result.get("message"))
    
    def _toggle_rule(self, item):
        """Toggle a rule enabled/disabled."""
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        rule = AutomationProfiles.get_rule(rule_id)
        if rule:
            AutomationProfiles.enable_rule(rule_id, not rule.get("enabled", True))
            self.refresh()
    
    def _delete_rule(self):
        """Delete selected rule."""
        item = self.rules_list.currentItem()
        if not item:
            return
        
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, self.tr("Confirm Delete"),
            self.tr("Delete this automation rule?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            AutomationProfiles.delete_rule(rule_id)
            self.refresh()
    
    def _add_presets(self):
        """Add common preset rules."""
        reply = QMessageBox.question(
            self, self.tr("Add Presets"),
            self.tr("Add common automation presets (battery saver, auto-tiling)?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            AutomationProfiles.create_battery_saver_preset()
            AutomationProfiles.create_tiling_preset()
            self.refresh()
            QMessageBox.information(
                self, self.tr("Presets Added"),
                self.tr("Added battery saver and auto-tiling presets.")
            )


class SystemStatusSection(QGroupBox):
    """System status display section."""
    
    def __init__(self):
        super().__init__()
        self.setTitle(self.tr("📊 System Status"))
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Power status
        power_layout = QHBoxLayout()
        power_layout.addWidget(QLabel(self.tr("Power:")))
        self.power_label = QLabel()
        self.power_label.setFont(QFont("", 10, QFont.Weight.Bold))
        power_layout.addWidget(self.power_label)
        power_layout.addStretch()
        layout.addLayout(power_layout)
        
        # Network status
        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel(self.tr("Network:")))
        self.network_label = QLabel()
        self.network_label.setFont(QFont("", 10, QFont.Weight.Bold))
        network_layout.addWidget(self.network_label)
        network_layout.addStretch()
        layout.addLayout(network_layout)
        
        # Monitor status
        monitor_layout = QHBoxLayout()
        monitor_layout.addWidget(QLabel(self.tr("Displays:")))
        self.monitor_label = QLabel()
        self.monitor_label.setFont(QFont("", 10, QFont.Weight.Bold))
        monitor_layout.addWidget(self.monitor_label)
        monitor_layout.addStretch()
        layout.addLayout(monitor_layout)
        
        # Refresh button
        self.refresh_btn = QPushButton(self.tr("🔄 Refresh"))
        self.refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_btn)
        
        self.refresh()
    
    def refresh(self):
        """Refresh system status."""
        # Power
        power = SystemPulse.get_power_state()
        battery = SystemPulse.get_battery_level()
        if power == "ac":
            self.power_label.setText(f"🔌 AC Power")
            self.power_label.setStyleSheet("color: #4CAF50;")
        elif power == "battery":
            self.power_label.setText(f"🔋 Battery ({battery}%)")
            self.power_label.setStyleSheet("color: #FF9800;" if battery > 20 else "color: #f44336;")
        else:
            self.power_label.setText("❓ Unknown")
            self.power_label.setStyleSheet("")
        
        # Network
        network = SystemPulse.get_network_state()
        ssid = SystemPulse.get_wifi_ssid()
        if network == "connected":
            if ssid:
                self.network_label.setText(f"📶 {ssid}")
            else:
                self.network_label.setText("🔗 Connected")
            self.network_label.setStyleSheet("color: #4CAF50;")
        else:
            self.network_label.setText("❌ Disconnected")
            self.network_label.setStyleSheet("color: #f44336;")
        
        # Monitors
        monitors = SystemPulse.get_connected_monitors()
        if monitors:
            names = [m.get("name", "Unknown") for m in monitors]
            ultrawide = any(m.get("is_ultrawide") for m in monitors)
            text = f"🖥️ {len(monitors)} display(s)"
            if ultrawide:
                text += " (Ultrawide)"
            self.monitor_label.setText(text)
            self.monitor_label.setStyleSheet("color: #2196F3;")
        else:
            self.monitor_label.setText("🖥️ Unknown")
            self.monitor_label.setStyleSheet("")
    
    def update_power(self, state: str):
        """Update power status from signal."""
        if state == "ac":
            self.power_label.setText("🔌 AC Power")
            self.power_label.setStyleSheet("color: #4CAF50;")
        else:
            self.power_label.setText("🔋 Battery")
            self.power_label.setStyleSheet("color: #FF9800;")
    
    def update_network(self, state: str):
        """Update network status from signal."""
        if state == "connected":
            self.network_label.setText("🔗 Connected")
            self.network_label.setStyleSheet("color: #4CAF50;")
        else:
            self.network_label.setText("❌ Disconnected")
            self.network_label.setStyleSheet("color: #f44336;")


class PulseTab(QWidget):
    """Main Pulse/Automation tab."""
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # Header
        header = QLabel(self.tr("⚡ Automation & Focus"))
        header.setFont(QFont("", 18, QFont.Weight.Bold))
        layout.addWidget(header)
        
        subtitle = QLabel(self.tr(
            "Configure event-driven automation and focus mode for productivity."
        ))
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)
        content.setLayout(content_layout)
        
        # System status section
        self.status_section = SystemStatusSection()
        content_layout.addWidget(self.status_section)
        
        # Focus mode section
        self.focus_section = FocusModeSection()
        content_layout.addWidget(self.focus_section)
        
        # Automation rules section
        self.rules_section = AutomationRulesSection()
        content_layout.addWidget(self.rules_section)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def connect_pulse(self, pulse: SystemPulse):
        """Connect to SystemPulse signals for real-time updates."""
        pulse.power_state_changed.connect(self.status_section.update_power)
        pulse.network_state_changed.connect(self.status_section.update_network)
        pulse.monitor_count_changed.connect(lambda _: self.status_section.refresh())
        
        # Trigger automation rules on events
        pulse.power_state_changed.connect(self._on_power_changed)
        pulse.network_state_changed.connect(self._on_network_changed)
        pulse.event_triggered.connect(self._on_event_triggered)
    
    def _on_power_changed(self, state: str):
        """Handle power state change."""
        trigger = TriggerType.ON_BATTERY.value if state == "battery" else TriggerType.ON_AC.value
        AutomationProfiles.execute_rules_for_trigger(trigger)
    
    def _on_network_changed(self, state: str):
        """Handle network state change."""
        if state == "connected":
            if SystemPulse.is_public_wifi():
                AutomationProfiles.execute_rules_for_trigger(TriggerType.ON_PUBLIC_WIFI.value)
            else:
                AutomationProfiles.execute_rules_for_trigger(TriggerType.ON_HOME_WIFI.value)
    
    def _on_event_triggered(self, event_name: str, event_data: dict):
        """Handle generic events."""
        trigger_map = {
            "ultrawide_connected": TriggerType.ON_ULTRAWIDE.value,
            "laptop_only": TriggerType.ON_LAPTOP_ONLY.value,
        }
        if event_name in trigger_map:
            AutomationProfiles.execute_rules_for_trigger(trigger_map[event_name])
    
    def refresh(self):
        """Refresh all sections."""
        self.status_section.refresh()
        self.focus_section.refresh()
        self.rules_section.refresh()
