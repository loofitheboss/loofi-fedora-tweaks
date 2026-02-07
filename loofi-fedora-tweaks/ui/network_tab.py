from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QGroupBox, QComboBox, QMessageBox
from utils.process import CommandRunner
import subprocess

class NetworkTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        header = QLabel("Network & Privacy")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)
        
        # DNS Switcher Group
        dns_group = QGroupBox("DNS Switcher")
        dns_layout = QVBoxLayout()
        dns_group.setLayout(dns_layout)
        
        dns_desc = QLabel("Change DNS for the current active connection.")
        dns_layout.addWidget(dns_desc)
        
        self.dns_combo = QComboBox()
        self.dns_combo.addItem("Cloudflare (1.1.1.1)", "1.1.1.1 1.0.0.1")
        self.dns_combo.addItem("Google (8.8.8.8)", "8.8.8.8 8.8.4.4")
        self.dns_combo.addItem("Quad9 (9.9.9.9)", "9.9.9.9 149.112.112.112")
        self.dns_combo.addItem("AdGuard (94.140.14.14)", "94.140.14.14 94.140.15.15")
        self.dns_combo.addItem("System Default (DHCP)", "auto")
        dns_layout.addWidget(self.dns_combo)
        
        btn_apply_dns = QPushButton("Apply DNS")
        btn_apply_dns.clicked.connect(self.apply_dns)
        dns_layout.addWidget(btn_apply_dns)
        
        layout.addWidget(dns_group)
        
        # MAC Randomization Group
        mac_group = QGroupBox("Wi-Fi Privacy")
        mac_layout = QVBoxLayout()
        mac_group.setLayout(mac_layout)
        
        self.lbl_mac_status = QLabel("MAC Randomization: Unknown")
        mac_layout.addWidget(self.lbl_mac_status)
        
        btn_enable_mac = QPushButton("Enable MAC Randomization")
        btn_enable_mac.clicked.connect(lambda: self.toggle_mac_randomization(True))
        mac_layout.addWidget(btn_enable_mac)
        
        btn_disable_mac = QPushButton("Disable MAC Randomization")
        btn_disable_mac.clicked.connect(lambda: self.toggle_mac_randomization(False))
        mac_layout.addWidget(btn_disable_mac)
        
        layout.addWidget(mac_group)
        layout.addStretch()
        
        self.runner = CommandRunner()
        self.check_mac_status()

    def get_active_connection(self):
        # returns the connection name of the active connection
        try:
            # nmcli -t -f NAME,DEVICE,TYPE connection show --active
            # We want likely the wifi or ethernet one
            res = subprocess.run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "wifi" in line or "ethernet" in line:
                    return line.split(":")[0]
        except:
            pass
        return None

    def apply_dns(self):
        dns_servers = self.dns_combo.currentData()
        conn_name = self.get_active_connection()
        
        if not conn_name:
            QMessageBox.warning(self, "Error", "No active Wi-Fi or Ethernet connection found.")
            return

        if dns_servers == "auto":
            # ignore ipv4.dns
             self.runner.run_command("nmcli", ["con", "mod", conn_name, "ipv4.ignore-auto-dns", "no", "ipv6.ignore-auto-dns", "no"])
             # Clear dns
             subprocess.run(["nmcli", "con", "mod", conn_name, "ipv4.dns", ""])
        else:
            # set ipv4.dns
            # We assume ipv4 for now
            # nmcli con mod <conn> ipv4.dns "1.1.1.1 1.0.0.1" ipv4.ignore-auto-dns yes
            self.runner.run_command("nmcli", ["con", "mod", conn_name, "ipv4.dns", dns_servers, "ipv4.ignore-auto-dns", "yes"])
            
        # Reapply
        subprocess.run(["nmcli", "con", "up", conn_name])
        QMessageBox.information(self, "Success", f"DNS settings applied to '{conn_name}'.")

    def toggle_mac_randomization(self, enable):
        config_file = "/etc/NetworkManager/conf.d/00-mac-randomization.conf"
        content = """[device]
wifi.scan-rand-mac-address=yes

[connection]
wifi.cloned-mac-address=random
ethernet.cloned-mac-address=random
"""
        import os
        if enable:
            # We need root to write this file.
            # echo content | sudo tee file
            # command runner might be tricky with multiline echo.
            # simpler: write to tmp then move
            tmp_file = "/tmp/00-mac-randomization.conf"
            with open(tmp_file, "w") as f:
                f.write(content)
            
            self.runner.run_command("pkexec", ["mv", tmp_file, config_file])
            QMessageBox.information(self, "Enabled", "MAC Randomization enabled. Restart NetworkManager/Reboot to apply.")
        else:
            self.runner.run_command("pkexec", ["rm", "-f", config_file])
            QMessageBox.information(self, "Disabled", "MAC Randomization disabled. Restart NetworkManager/Reboot to apply.")
            
        # Verify status after short delay?
        # For now just update label based on intent or file existence check later
        self.lbl_mac_status.setText(f"MAC Randomization: {'Enabled' if enable else 'Disabled'}")

    def check_mac_status(self):
        import os
        if os.path.exists("/etc/NetworkManager/conf.d/00-mac-randomization.conf"):
            self.lbl_mac_status.setText("MAC Randomization: ✅ Enabled")
        else:
             self.lbl_mac_status.setText("MAC Randomization: ❌ Disabled")
