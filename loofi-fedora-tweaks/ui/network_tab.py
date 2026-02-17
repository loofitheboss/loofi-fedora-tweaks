"""
Network Tab - Comprehensive network management with sub-tabs.
Part of v17.0 "Atlas" — overhauled from v4.7 thin DNS/MAC tab.

Sub-tabs:
  - Connections: Active interfaces, WiFi networks, VPN profiles
  - DNS: Provider switching (Cloudflare/Google/Quad9/AdGuard/OpenDNS)
  - Privacy: MAC randomization, hostname privacy
  - Monitoring: Real-time traffic, active connections
"""

import logging
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.base_tab import BaseTab
from ui.tab_utils import CONTENT_MARGINS, configure_top_tabs
from ui.tooltips import DIAG_NETWORK
from utils.history import HistoryManager
from utils.network_monitor import NetworkMonitor
from utils.network_utils import NetworkUtils
from core.plugins.metadata import PluginMetadata

logger = logging.getLogger(__name__)


class NetworkTab(BaseTab):
    _METADATA = PluginMetadata(
        id="network",
        name="Network",
        description="Comprehensive network management including connections, DNS, privacy, and monitoring.",
        category="Network & Security",
        icon="🌐",
        badge="recommended",
        order=10,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    """Network management with Connections, DNS, Privacy, and Monitoring sub-tabs."""

    def __init__(self):
        super().__init__()
        self.history = HistoryManager()

        layout = QVBoxLayout()
        layout.setContentsMargins(*CONTENT_MARGINS)
        self.setLayout(layout)

        header = QLabel(self.tr("Network"))
        header.setObjectName("header")
        layout.addWidget(header)

        # Sub-tab widget
        self.tabs = QTabWidget()
        configure_top_tabs(self.tabs)
        self.tabs.addTab(self._build_connections_tab(), self.tr("🔗 Connections"))
        self.tabs.addTab(self._build_dns_tab(), self.tr("🌐 DNS"))
        self.tabs.addTab(self._build_privacy_tab(), self.tr("🔒 Privacy"))
        self.tabs.addTab(self._build_monitoring_tab(), self.tr("📊 Monitoring"))
        layout.addWidget(self.tabs)

        # Output area
        self.add_output_section(layout)

        # Auto-refresh timer for monitoring
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._refresh_monitoring)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        QTimer.singleShot(200, self._initial_load)

    # ------------------------------------------------------------------ #
    #  Sub-tab builders
    # ------------------------------------------------------------------ #

    def _build_connections_tab(self):
        """Interfaces + WiFi + VPN overview."""
        container = QVBoxLayout()

        # Active Interfaces
        iface_group = QGroupBox(self.tr("Active Interfaces"))
        iface_layout = QVBoxLayout(iface_group)

        self.iface_table = QTableWidget(0, 5)
        self.iface_table.setHorizontalHeaderLabels(
            [
                self.tr("Interface"),
                self.tr("Type"),
                self.tr("Status"),
                self.tr("IP Address"),
                self.tr("MAC"),
            ]
        )
        self.iface_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.iface_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.iface_table)
        self.set_table_empty_state(self.iface_table, self.tr("Loading interfaces..."))
        iface_layout.addWidget(self.iface_table)

        btn_row = QHBoxLayout()
        btn_refresh_iface = QPushButton(self.tr("Refresh"))
        btn_refresh_iface.setAccessibleName(self.tr("Refresh interfaces"))
        btn_refresh_iface.clicked.connect(self._load_interfaces)
        btn_row.addWidget(btn_refresh_iface)
        btn_row.addStretch()
        iface_layout.addLayout(btn_row)
        container.addWidget(iface_group)

        # WiFi Networks
        wifi_group = QGroupBox(self.tr("Wi-Fi Networks"))
        wifi_layout = QVBoxLayout(wifi_group)

        self.wifi_table = QTableWidget(0, 4)
        self.wifi_table.setHorizontalHeaderLabels(
            [
                self.tr("SSID"),
                self.tr("Signal"),
                self.tr("Security"),
                self.tr("Status"),
            ]
        )
        self.wifi_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.wifi_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.wifi_table)
        self.set_table_empty_state(
            self.wifi_table, self.tr("Click 'Scan Wi-Fi' to list networks")
        )
        wifi_layout.addWidget(self.wifi_table)

        wifi_btn_row = QHBoxLayout()
        btn_scan_wifi = QPushButton(self.tr("Scan Wi-Fi"))
        btn_scan_wifi.setAccessibleName(self.tr("Scan Wi-Fi"))
        btn_scan_wifi.clicked.connect(self._scan_wifi)
        wifi_btn_row.addWidget(btn_scan_wifi)

        btn_connect_wifi = QPushButton(self.tr("Connect"))
        btn_connect_wifi.setAccessibleName(self.tr("Connect Wi-Fi"))
        btn_connect_wifi.clicked.connect(self._connect_wifi)
        wifi_btn_row.addWidget(btn_connect_wifi)

        btn_disconnect_wifi = QPushButton(self.tr("Disconnect"))
        btn_disconnect_wifi.setAccessibleName(self.tr("Disconnect Wi-Fi"))
        btn_disconnect_wifi.clicked.connect(self._disconnect_wifi)
        wifi_btn_row.addWidget(btn_disconnect_wifi)
        wifi_btn_row.addStretch()
        wifi_layout.addLayout(wifi_btn_row)
        container.addWidget(wifi_group)

        # VPN Connections
        vpn_group = QGroupBox(self.tr("VPN Connections"))
        vpn_layout = QVBoxLayout(vpn_group)

        self.vpn_table = QTableWidget(0, 3)
        self.vpn_table.setHorizontalHeaderLabels(
            [
                self.tr("Name"),
                self.tr("Type"),
                self.tr("Status"),
            ]
        )
        self.vpn_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.vpn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.vpn_table)
        self.set_table_empty_state(
            self.vpn_table, self.tr("Loading VPN connections...")
        )
        vpn_layout.addWidget(self.vpn_table)

        vpn_btn_row = QHBoxLayout()
        btn_refresh_vpn = QPushButton(self.tr("Refresh VPN"))
        btn_refresh_vpn.setAccessibleName(self.tr("Refresh VPN"))
        btn_refresh_vpn.clicked.connect(self._load_vpn)
        vpn_btn_row.addWidget(btn_refresh_vpn)
        vpn_btn_row.addStretch()
        vpn_layout.addLayout(vpn_btn_row)
        container.addWidget(vpn_group)

        container.addStretch()
        return self._make_container(container)

    def _build_dns_tab(self):
        """DNS provider switching."""
        container = QVBoxLayout()

        dns_group = QGroupBox(self.tr("DNS Switcher"))
        dns_layout = QVBoxLayout(dns_group)

        dns_desc = QLabel(
            self.tr(
                "Change DNS for the current active connection. "
                "Applies instantly via NetworkManager."
            )
        )
        dns_desc.setWordWrap(True)
        dns_layout.addWidget(dns_desc)

        # Current DNS display
        self.lbl_current_dns = QLabel(self.tr("Current DNS: detecting..."))
        self.lbl_current_dns.setObjectName("netCurrentDns")
        dns_layout.addWidget(self.lbl_current_dns)

        self.dns_combo = QComboBox()
        self.dns_combo.setAccessibleName(self.tr("DNS provider"))
        self.dns_combo.addItem(self.tr("Cloudflare (1.1.1.1)"), "1.1.1.1 1.0.0.1")
        self.dns_combo.addItem(self.tr("Google (8.8.8.8)"), "8.8.8.8 8.8.4.4")
        self.dns_combo.addItem(self.tr("Quad9 (9.9.9.9)"), "9.9.9.9 149.112.112.112")
        self.dns_combo.addItem(
            self.tr("AdGuard (94.140.14.14)"), "94.140.14.14 94.140.15.15"
        )
        self.dns_combo.addItem(
            self.tr("OpenDNS (208.67.222.222)"), "208.67.222.222 208.67.220.220"
        )
        self.dns_combo.addItem(self.tr("System Default (DHCP)"), "auto")
        dns_layout.addWidget(self.dns_combo)

        btn_apply_dns = QPushButton(self.tr("Apply DNS"))
        btn_apply_dns.setAccessibleName(self.tr("Apply DNS"))
        btn_apply_dns.clicked.connect(self.apply_dns)
        dns_layout.addWidget(btn_apply_dns)

        container.addWidget(dns_group)

        # DNS test group
        test_group = QGroupBox(self.tr("DNS Test"))
        test_layout = QVBoxLayout(test_group)
        self.lbl_dns_test = QLabel(self.tr("Test DNS resolution speed after applying."))
        test_layout.addWidget(self.lbl_dns_test)

        btn_test_dns = QPushButton(self.tr("Test DNS Resolution"))
        btn_test_dns.setAccessibleName(self.tr("Test DNS"))
        btn_test_dns.setToolTip(DIAG_NETWORK)
        btn_test_dns.clicked.connect(self._test_dns)
        test_layout.addWidget(btn_test_dns)
        container.addWidget(test_group)

        container.addStretch()
        return self._make_container(container)

    def _build_privacy_tab(self):
        """MAC randomization and hostname privacy."""
        container = QVBoxLayout()

        # MAC Randomization
        mac_group = QGroupBox(self.tr("MAC Randomization"))
        mac_layout = QVBoxLayout(mac_group)

        mac_desc = QLabel(
            self.tr(
                "Randomize your MAC address on WiFi and Ethernet connections "
                "to prevent network tracking. Requires NetworkManager restart."
            )
        )
        mac_desc.setWordWrap(True)
        mac_layout.addWidget(mac_desc)

        self.lbl_mac_status = QLabel(self.tr("MAC Randomization: detecting..."))
        self.lbl_mac_status.setObjectName("netMacStatus")
        mac_layout.addWidget(self.lbl_mac_status)

        mac_btn_row = QHBoxLayout()
        btn_enable_mac = QPushButton(self.tr("Enable"))
        btn_enable_mac.setAccessibleName(self.tr("Enable MAC randomization"))
        btn_enable_mac.clicked.connect(lambda: self.toggle_mac_randomization(True))
        mac_btn_row.addWidget(btn_enable_mac)

        btn_disable_mac = QPushButton(self.tr("Disable"))
        btn_disable_mac.setAccessibleName(self.tr("Disable MAC randomization"))
        btn_disable_mac.clicked.connect(lambda: self.toggle_mac_randomization(False))
        mac_btn_row.addWidget(btn_disable_mac)
        mac_btn_row.addStretch()
        mac_layout.addLayout(mac_btn_row)
        container.addWidget(mac_group)

        # Hostname Privacy
        hostname_group = QGroupBox(self.tr("Hostname Privacy"))
        hostname_layout = QVBoxLayout(hostname_group)

        hostname_desc = QLabel(
            self.tr(
                "Prevent your hostname from being broadcast on the network via DHCP. "
                "Sets send-hostname=false for active connections."
            )
        )
        hostname_desc.setWordWrap(True)
        hostname_layout.addWidget(hostname_desc)

        self.lbl_hostname_status = QLabel(self.tr("Hostname broadcast: detecting..."))
        self.lbl_hostname_status.setObjectName("netHostnameStatus")
        hostname_layout.addWidget(self.lbl_hostname_status)

        hostname_btn_row = QHBoxLayout()
        btn_hide_hostname = QPushButton(self.tr("Hide Hostname"))
        btn_hide_hostname.setAccessibleName(self.tr("Hide hostname"))
        btn_hide_hostname.clicked.connect(lambda: self._toggle_hostname_privacy(True))
        hostname_btn_row.addWidget(btn_hide_hostname)

        btn_show_hostname = QPushButton(self.tr("Show Hostname"))
        btn_show_hostname.setAccessibleName(self.tr("Show hostname"))
        btn_show_hostname.clicked.connect(lambda: self._toggle_hostname_privacy(False))
        hostname_btn_row.addWidget(btn_show_hostname)
        hostname_btn_row.addStretch()
        hostname_layout.addLayout(hostname_btn_row)
        container.addWidget(hostname_group)

        # Undo
        undo_group = QGroupBox(self.tr("History"))
        undo_layout = QVBoxLayout(undo_group)
        btn_undo = QPushButton(self.tr("↩ Undo Last Action"))
        btn_undo.setAccessibleName(self.tr("Undo last action"))
        btn_undo.clicked.connect(self.undo_last)
        undo_layout.addWidget(btn_undo)
        container.addWidget(undo_group)

        container.addStretch()
        return self._make_container(container)

    def _build_monitoring_tab(self):
        """Real-time traffic and active connections."""
        container = QVBoxLayout()

        # Bandwidth summary
        bw_group = QGroupBox(self.tr("Bandwidth Summary"))
        bw_layout = QVBoxLayout(bw_group)

        self.lbl_total_sent = QLabel(self.tr("Total Sent: —"))
        self.lbl_total_recv = QLabel(self.tr("Total Received: —"))
        self.lbl_send_rate = QLabel(self.tr("Upload Rate: —"))
        self.lbl_recv_rate = QLabel(self.tr("Download Rate: —"))
        for lbl in (
            self.lbl_total_sent,
            self.lbl_total_recv,
            self.lbl_send_rate,
            self.lbl_recv_rate,
        ):
            lbl.setObjectName("netBwLabel")
            bw_layout.addWidget(lbl)
        container.addWidget(bw_group)

        # Per-interface traffic
        traffic_group = QGroupBox(self.tr("Interface Traffic"))
        traffic_layout = QVBoxLayout(traffic_group)

        self.traffic_table = QTableWidget(0, 6)
        self.traffic_table.setHorizontalHeaderLabels(
            [
                self.tr("Interface"),
                self.tr("Type"),
                self.tr("Sent"),
                self.tr("Received"),
                self.tr("↑ Rate"),
                self.tr("↓ Rate"),
            ]
        )
        self.traffic_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.traffic_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.traffic_table)
        self.set_table_empty_state(
            self.traffic_table, self.tr("Switch to Monitoring to load traffic")
        )
        traffic_layout.addWidget(self.traffic_table)
        container.addWidget(traffic_group)

        # Active connections
        conn_group = QGroupBox(self.tr("Active Connections"))
        conn_layout = QVBoxLayout(conn_group)

        self.conn_table = QTableWidget(0, 6)
        self.conn_table.setHorizontalHeaderLabels(
            [
                self.tr("Protocol"),
                self.tr("Local"),
                self.tr("Remote"),
                self.tr("State"),
                self.tr("PID"),
                self.tr("Process"),
            ]
        )
        self.conn_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.conn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        BaseTab.configure_table(self.conn_table)
        self.set_table_empty_state(
            self.conn_table, self.tr("Switch to Monitoring to load connections")
        )
        conn_layout.addWidget(self.conn_table)

        conn_btn_row = QHBoxLayout()
        btn_refresh_conn = QPushButton(self.tr("Refresh"))
        btn_refresh_conn.setAccessibleName(self.tr("Refresh connections"))
        btn_refresh_conn.clicked.connect(self._refresh_monitoring)
        conn_btn_row.addWidget(btn_refresh_conn)
        conn_btn_row.addStretch()
        conn_layout.addLayout(conn_btn_row)
        container.addWidget(conn_group)

        container.addStretch()
        return self._make_container(container)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_container(layout):
        """Wrap a QVBoxLayout into a plain QWidget for use as a tab page."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import (
            QAbstractScrollArea,
            QScrollArea,
            QWidget,
        )

        layout.setContentsMargins(*CONTENT_MARGINS)
        inner = QWidget()
        inner.setLayout(layout)
        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        return scroll

    def _initial_load(self):
        """Load initial data for all sub-tabs."""
        self._load_interfaces()
        self._load_vpn()
        self._detect_current_dns()
        self.check_mac_status()
        self._check_hostname_privacy()

    @staticmethod
    def _make_table_item(text: str) -> QTableWidgetItem:
        """Create a table item with explicit readable foreground color."""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        item.setForeground(QColor("#e4e8f4"))
        return item

    def _set_empty_table_state(self, table: QTableWidget, message: str):
        """Render a visible one-row empty state message for table bodies."""
        table.clearSpans()
        table.setRowCount(1)
        table.setItem(0, 0, self._make_table_item(message))
        if table.columnCount() > 1:
            table.setSpan(0, 0, 1, table.columnCount())
        normalize = getattr(BaseTab, "ensure_table_row_heights", None)
        if callable(normalize):
            normalize(table)

    def _on_tab_changed(self, index):
        """Start/stop monitoring timer based on active sub-tab."""
        if index == 3:  # Monitoring tab
            self._refresh_monitoring()
            self._monitor_timer.start(3000)
        else:
            self._monitor_timer.stop()

    # ------------------------------------------------------------------ #
    #  Connections sub-tab
    # ------------------------------------------------------------------ #

    def _load_interfaces(self):
        """Load network interfaces from NetworkMonitor."""
        try:
            interfaces = NetworkMonitor.get_all_interfaces()
            self.iface_table.clearSpans()
            if not interfaces:
                self._set_empty_table_state(
                    self.iface_table, self.tr("No active interfaces detected")
                )
                return

            self.iface_table.setRowCount(len(interfaces))
            for i, iface in enumerate(interfaces):
                self.iface_table.setItem(i, 0, self._make_table_item(iface.name))
                self.iface_table.setItem(
                    i, 1, self._make_table_item(iface.type.capitalize())
                )
                status = "Up" if iface.is_up else "Down"
                self.iface_table.setItem(i, 2, self._make_table_item(status))
                self.iface_table.setItem(
                    i, 3, self._make_table_item(iface.ip_address or "—")
                )
                mac = self._get_mac_address(iface.name)
                self.iface_table.setItem(i, 4, self._make_table_item(mac))
            normalize = getattr(BaseTab, "ensure_table_row_heights", None)
            if callable(normalize):
                normalize(self.iface_table)
        except (RuntimeError, OSError, ValueError) as e:
            logger.error("Failed to load interfaces: %s", e)
            self._set_empty_table_state(
                self.iface_table, self.tr("Failed to load interfaces")
            )

    @staticmethod
    def _get_mac_address(iface_name):
        """Read MAC address from /sys/class/net/<iface>/address."""
        try:
            with open(f"/sys/class/net/{iface_name}/address", "r") as f:
                return f.read().strip()
        except (OSError, IOError) as e:
            logger.debug("Failed to read MAC address for %s: %s", iface_name, e)
            return "—"

    def _scan_wifi(self):
        """Scan for available WiFi networks via nmcli."""
        rows = NetworkUtils.scan_wifi()
        self.wifi_table.clearSpans()
        if not rows:
            self._set_empty_table_state(
                self.wifi_table, self.tr("No Wi-Fi networks found")
            )
        else:
            self.wifi_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.wifi_table.setItem(i, 0, self._make_table_item(row[0]))
                self.wifi_table.setItem(i, 1, self._make_table_item(row[1]))
                self.wifi_table.setItem(i, 2, self._make_table_item(row[2]))
                self.wifi_table.setItem(i, 3, self._make_table_item(row[3]))
            normalize = getattr(BaseTab, "ensure_table_row_heights", None)
            if callable(normalize):
                normalize(self.wifi_table)
        self.append_output(
            self.tr("WiFi scan complete. {} networks found.\n").format(len(rows))
        )

    def _connect_wifi(self):
        """Connect to selected WiFi network."""
        row = self.wifi_table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("Select a WiFi network first.")
            )
            return
        ssid = self.wifi_table.item(row, 0).text()
        if ssid == "(Hidden)":
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Cannot connect to a hidden network from here."),
            )
            return
        self.run_command(
            "nmcli",
            ["device", "wifi", "connect", ssid],
            self.tr("Connecting to {}...").format(ssid),
        )

    def _disconnect_wifi(self):
        """Disconnect WiFi."""
        self.run_command(
            "nmcli", ["device", "disconnect", "wlan0"], self.tr("Disconnecting WiFi...")
        )

    def _load_vpn(self):
        """Load VPN connections from NetworkManager."""
        vpn_rows = NetworkUtils.load_vpn_connections()
        self.vpn_table.clearSpans()
        self.vpn_table.setRowCount(len(vpn_rows))
        for i, (name, conn_type, status) in enumerate(vpn_rows):
            self.vpn_table.setItem(i, 0, self._make_table_item(name))
            self.vpn_table.setItem(i, 1, self._make_table_item(conn_type))
            self.vpn_table.setItem(i, 2, self._make_table_item(status))
        normalize = getattr(BaseTab, "ensure_table_row_heights", None)
        if callable(normalize):
            normalize(self.vpn_table)
        if not vpn_rows:
            self._set_empty_table_state(
                self.vpn_table, self.tr("No VPN connections configured")
            )

    # ------------------------------------------------------------------ #
    #  DNS sub-tab
    # ------------------------------------------------------------------ #

    def _detect_current_dns(self):
        """Detect and display the current DNS servers."""
        dns_str = NetworkUtils.detect_current_dns()
        if dns_str:
            self.lbl_current_dns.setText(self.tr("Current DNS: {}").format(dns_str))
        else:
            self.lbl_current_dns.setText(self.tr("Current DNS: (DHCP default)"))

    def get_active_connection(self):
        """Return the connection name of the active WiFi or Ethernet connection."""
        return NetworkUtils.get_active_connection()

    def apply_dns(self):
        """Apply selected DNS provider to active connection."""
        dns_servers = self.dns_combo.currentData()
        conn_name = self.get_active_connection()

        if not conn_name:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("No active Wi-Fi or Ethernet connection found."),
            )
            return

        if dns_servers == "auto":
            self.run_command(
                "nmcli",
                [
                    "con",
                    "mod",
                    conn_name,
                    "ipv4.ignore-auto-dns",
                    "no",
                    "ipv6.ignore-auto-dns",
                    "no",
                    "ipv4.dns",
                    "",
                ],
                self.tr("Resetting DNS to DHCP default..."),
            )
        else:
            self.run_command(
                "nmcli",
                [
                    "con",
                    "mod",
                    conn_name,
                    "ipv4.dns",
                    dns_servers,
                    "ipv4.ignore-auto-dns",
                    "yes",
                ],
                self.tr("Applying DNS: {}").format(dns_servers),
            )

        # Reapply connection in background
        NetworkUtils.reactivate_connection(conn_name)

        QTimer.singleShot(1000, self._detect_current_dns)
        QMessageBox.information(
            self,
            self.tr("Success"),
            self.tr("DNS settings applied to '{}'.").format(conn_name),
        )

    def _test_dns(self):
        """Test DNS resolution speed."""
        self.run_command(
            "bash",
            [
                "-c",
                "echo 'Testing DNS resolution...' && "
                "for domain in google.com github.com fedoraproject.org; do "
                "    start=$(date +%s%N); "
                "    nslookup $domain >/dev/null 2>&1; "
                "    end=$(date +%s%N); "
                "    ms=$(( (end - start) / 1000000 )); "
                '    echo "  $domain: ${ms}ms"; '
                "done",
            ],
            self.tr("Testing DNS resolution speed..."),
        )

    # ------------------------------------------------------------------ #
    #  Privacy sub-tab
    # ------------------------------------------------------------------ #

    def check_mac_status(self):
        """Check whether MAC randomization is enabled."""
        config_file = "/etc/NetworkManager/conf.d/00-mac-randomization.conf"
        if os.path.exists(config_file):
            self.lbl_mac_status.setText(self.tr("MAC Randomization: ✅ Enabled"))
        else:
            self.lbl_mac_status.setText(self.tr("MAC Randomization: ❌ Disabled"))

    def toggle_mac_randomization(self, enable):
        """Enable or disable MAC randomization via NetworkManager config."""
        config_file = "/etc/NetworkManager/conf.d/00-mac-randomization.conf"
        content = (
            "[device]\n"
            "wifi.scan-rand-mac-address=yes\n\n"
            "[connection]\n"
            "wifi.cloned-mac-address=random\n"
            "ethernet.cloned-mac-address=random\n"
        )

        if enable:
            tmp_file = "/tmp/00-mac-randomization.conf"
            try:
                with open(tmp_file, "w") as f:
                    f.write(content)
            except OSError as e:
                self.append_output(self.tr("Failed to write temp file: {}\n").format(e))
                return

            self.run_command(
                "pkexec",
                ["mv", tmp_file, config_file],
                self.tr("Enabling MAC randomization..."),
            )
            self.history.log_change(
                self.tr("Enabled MAC Randomization"),
                ["pkexec", "rm", "-f", config_file],
            )
            QMessageBox.information(
                self,
                self.tr("Enabled"),
                self.tr("MAC Randomization enabled. Restart NetworkManager to apply."),
            )
        else:
            self.run_command(
                "pkexec",
                ["rm", "-f", config_file],
                self.tr("Disabling MAC randomization..."),
            )
            QMessageBox.information(
                self,
                self.tr("Disabled"),
                self.tr("MAC Randomization disabled. Restart NetworkManager to apply."),
            )

        QTimer.singleShot(500, self.check_mac_status)

    def _check_hostname_privacy(self):
        """Check if hostname is hidden from DHCP broadcasts."""
        conn = self.get_active_connection()
        if not conn:
            self.lbl_hostname_status.setText(
                self.tr("Hostname broadcast: no active connection")
            )
            return
        result = NetworkUtils.check_hostname_privacy(conn)
        if result is True:
            self.lbl_hostname_status.setText(self.tr("Hostname broadcast: ✅ Hidden"))
        elif result is False:
            self.lbl_hostname_status.setText(self.tr("Hostname broadcast: ⚠️ Visible"))
        else:
            self.lbl_hostname_status.setText(self.tr("Hostname broadcast: unknown"))

    def _toggle_hostname_privacy(self, hide):
        """Hide or show hostname in DHCP requests."""
        conn = self.get_active_connection()
        if not conn:
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("No active connection found.")
            )
            return

        value = "no" if hide else "yes"
        self.run_command(
            "nmcli",
            [
                "connection",
                "modify",
                conn,
                "ipv4.dhcp-send-hostname",
                value,
            ],
            self.tr("Setting hostname visibility to {}...").format(
                "hidden" if hide else "visible"
            ),
        )

        action = (
            self.tr("Hidden hostname from DHCP")
            if hide
            else self.tr("Restored hostname to DHCP")
        )
        undo_value = "yes" if hide else "no"
        self.history.log_change(
            action,
            [
                "nmcli",
                "connection",
                "modify",
                conn,
                "ipv4.dhcp-send-hostname",
                undo_value,
            ],
        )

        QTimer.singleShot(500, self._check_hostname_privacy)
        QMessageBox.information(
            self,
            self.tr("Done"),
            self.tr("Hostname privacy updated. Reconnect to apply."),
        )

    def undo_last(self):
        """Undo the last network privacy action."""
        success, msg = self.history.undo_last_action()
        if success:
            QMessageBox.information(self, self.tr("Undo Successful"), msg)
            self.check_mac_status()
            self._check_hostname_privacy()
        else:
            QMessageBox.warning(self, self.tr("Undo Failed"), msg)

    # ------------------------------------------------------------------ #
    #  Monitoring sub-tab
    # ------------------------------------------------------------------ #

    def _refresh_monitoring(self):
        """Refresh bandwidth and connection data from NetworkMonitor."""
        try:
            # Bandwidth summary
            summary = NetworkMonitor.get_bandwidth_summary()
            self.lbl_total_sent.setText(
                self.tr("Total Sent: {}").format(
                    NetworkMonitor.bytes_to_human(summary["total_sent"])
                )
            )
            self.lbl_total_recv.setText(
                self.tr("Total Received: {}").format(
                    NetworkMonitor.bytes_to_human(summary["total_recv"])
                )
            )
            self.lbl_send_rate.setText(
                self.tr("Upload Rate: {}/s").format(
                    NetworkMonitor.bytes_to_human(summary["total_send_rate"])
                )
            )
            self.lbl_recv_rate.setText(
                self.tr("Download Rate: {}/s").format(
                    NetworkMonitor.bytes_to_human(summary["total_recv_rate"])
                )
            )

            # Per-interface traffic
            interfaces = NetworkMonitor.get_all_interfaces()
            non_lo = [i for i in interfaces if i.type != "loopback"]
            self.traffic_table.clearSpans()
            if not non_lo:
                self._set_empty_table_state(
                    self.traffic_table, self.tr("No network traffic data available")
                )
            else:
                self.traffic_table.setRowCount(len(non_lo))
                for i, iface in enumerate(non_lo):
                    self.traffic_table.setItem(i, 0, self._make_table_item(iface.name))
                    self.traffic_table.setItem(
                        i, 1, self._make_table_item(iface.type.capitalize())
                    )
                    self.traffic_table.setItem(
                        i, 2, self._make_table_item(iface.bytes_sent_human)
                    )
                    self.traffic_table.setItem(
                        i, 3, self._make_table_item(iface.bytes_recv_human)
                    )
                    self.traffic_table.setItem(
                        i, 4, self._make_table_item(iface.send_rate_human)
                    )
                    self.traffic_table.setItem(
                        i, 5, self._make_table_item(iface.recv_rate_human)
                    )
                normalize = getattr(BaseTab, "ensure_table_row_heights", None)
                if callable(normalize):
                    normalize(self.traffic_table)

            # Active connections
            connections = NetworkMonitor.get_active_connections()
            # Show only ESTABLISHED and LISTEN, limit to 100
            filtered = [c for c in connections if c.state in ("ESTABLISHED", "LISTEN")][
                :100
            ]
            self.conn_table.clearSpans()
            if not filtered:
                self._set_empty_table_state(
                    self.conn_table, self.tr("No active connections")
                )
            else:
                self.conn_table.setRowCount(len(filtered))
                for i, conn in enumerate(filtered):
                    self.conn_table.setItem(i, 0, self._make_table_item(conn.protocol))
                    self.conn_table.setItem(
                        i,
                        1,
                        self._make_table_item(f"{conn.local_addr}:{conn.local_port}"),
                    )
                    self.conn_table.setItem(
                        i,
                        2,
                        self._make_table_item(f"{conn.remote_addr}:{conn.remote_port}"),
                    )
                    self.conn_table.setItem(i, 3, self._make_table_item(conn.state))
                    self.conn_table.setItem(
                        i, 4, self._make_table_item(str(conn.pid) if conn.pid else "—")
                    )
                    self.conn_table.setItem(
                        i, 5, self._make_table_item(conn.process_name or "—")
                    )
                normalize = getattr(BaseTab, "ensure_table_row_heights", None)
                if callable(normalize):
                    normalize(self.conn_table)
        except (RuntimeError, OSError, ValueError) as e:
            logger.error("Monitoring refresh failed: %s", e)
