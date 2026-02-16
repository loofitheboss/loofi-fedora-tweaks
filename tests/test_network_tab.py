"""Tests for ui/network_tab.py — NetworkTab full behavioral coverage.

Exercises all sub-tabs (Connections, DNS, Privacy, Monitoring), static
helpers, and timer lifecycle.  All PyQt6 widgets run in offscreen mode
(set by conftest.py) and all system calls are mocked.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from ui.tab_utils import CONTENT_MARGINS


def _make_iface(
    name="wlp2s0",
    itype="wifi",
    is_up=True,
    ip_address="192.168.1.42",
    bytes_sent=1024,
    bytes_recv=2048,
    packets_sent=10,
    packets_recv=20,
    send_rate=100.0,
    recv_rate=200.0,
):
    """Build a mock InterfaceStats object."""
    iface = MagicMock()
    iface.name = name
    iface.type = itype
    iface.is_up = is_up
    iface.ip_address = ip_address
    iface.bytes_sent = bytes_sent
    iface.bytes_recv = bytes_recv
    iface.packets_sent = packets_sent
    iface.packets_recv = packets_recv
    iface.send_rate = send_rate
    iface.recv_rate = recv_rate
    iface.bytes_sent_human = "1.0 KB"
    iface.bytes_recv_human = "2.0 KB"
    iface.send_rate_human = "100.0 B/s"
    iface.recv_rate_human = "200.0 B/s"
    return iface


def _make_conn(
    protocol="tcp",
    local_addr="127.0.0.1",
    local_port=8080,
    remote_addr="93.184.216.34",
    remote_port=443,
    state="ESTABLISHED",
    pid=1234,
    process_name="firefox",
):
    """Build a mock ConnectionInfo object."""
    conn = MagicMock()
    conn.protocol = protocol
    conn.local_addr = local_addr
    conn.local_port = local_port
    conn.remote_addr = remote_addr
    conn.remote_port = remote_port
    conn.state = state
    conn.pid = pid
    conn.process_name = process_name
    return conn


def _create_tab():
    """Instantiate a NetworkTab with QTimer.singleShot suppressed."""
    from ui.network_tab import NetworkTab

    return NetworkTab()


# =========================================================================
# Metadata & create_widget
# =========================================================================
class TestNetworkTabMetadata(unittest.TestCase):
    """Tests for NetworkTab plugin metadata and create_widget."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_metadata_id(self, mock_ss):
        """metadata() returns PluginMetadata with id='network'."""
        tab = _create_tab()
        self.assertEqual(tab.metadata().id, "network")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_metadata_name(self, mock_ss):
        """metadata() returns name 'Network'."""
        tab = _create_tab()
        self.assertEqual(tab.metadata().name, "Network")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_metadata_category(self, mock_ss):
        """metadata() returns correct category."""
        tab = _create_tab()
        self.assertEqual(tab.metadata().category, "Network & Security")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_metadata_badge(self, mock_ss):
        """metadata() returns 'recommended' badge."""
        tab = _create_tab()
        self.assertEqual(tab.metadata().badge, "recommended")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_metadata_order(self, mock_ss):
        """metadata() returns order=10."""
        tab = _create_tab()
        self.assertEqual(tab.metadata().order, 10)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_create_widget_returns_self(self, mock_ss):
        """create_widget() returns self."""
        tab = _create_tab()
        self.assertIs(tab.create_widget(), tab)


# =========================================================================
# Initialization & sub-tabs
# =========================================================================
class TestNetworkTabInit(unittest.TestCase):
    """Tests for NetworkTab __init__ and sub-tab structure."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_sub_tabs(self, mock_ss):
        """Tab widget contains 4 sub-tabs."""
        tab = _create_tab()
        self.assertEqual(tab.tabs.count(), 4)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_interface_table(self, mock_ss):
        """iface_table is created with 5 columns."""
        tab = _create_tab()
        self.assertEqual(tab.iface_table.columnCount(), 5)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_wifi_table(self, mock_ss):
        """wifi_table is created with 4 columns."""
        tab = _create_tab()
        self.assertEqual(tab.wifi_table.columnCount(), 4)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_vpn_table(self, mock_ss):
        """vpn_table is created with 3 columns."""
        tab = _create_tab()
        self.assertEqual(tab.vpn_table.columnCount(), 3)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_traffic_table(self, mock_ss):
        """traffic_table is created with 6 columns."""
        tab = _create_tab()
        self.assertEqual(tab.traffic_table.columnCount(), 6)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_conn_table(self, mock_ss):
        """conn_table is created with 6 columns."""
        tab = _create_tab()
        self.assertEqual(tab.conn_table.columnCount(), 6)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_dns_combo(self, mock_ss):
        """dns_combo has 6 provider entries."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.count(), 6)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_has_monitor_timer(self, mock_ss):
        """_monitor_timer is created."""
        tab = _create_tab()
        self.assertIsNotNone(tab._monitor_timer)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_layout_uses_content_margins(self, mock_ss):
        """Root layout applies standard content margins for safe scrolling."""
        tab = _create_tab()
        margins = tab.layout().contentsMargins()
        self.assertEqual(
            (
                margins.left(),
                margins.top(),
                margins.right(),
                margins.bottom(),
            ),
            CONTENT_MARGINS,
        )

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_initial_load_deferred(self, mock_ss):
        """__init__ schedules _initial_load via QTimer.singleShot."""
        _create_tab()
        mock_ss.assert_called()


# =========================================================================
# Static helpers
# =========================================================================
class TestNetworkTabStaticHelpers(unittest.TestCase):
    """Tests for _get_mac_address and _make_table_item."""

    @patch("builtins.open", mock_open(read_data="aa:bb:cc:dd:ee:ff\n"))
    def test_get_mac_address_success(self):
        """_get_mac_address reads MAC from /sys/class/net/."""
        from ui.network_tab import NetworkTab

        result = NetworkTab._get_mac_address("eth0")
        self.assertEqual(result, "aa:bb:cc:dd:ee:ff")

    @patch("builtins.open", side_effect=OSError("No such file"))
    def test_get_mac_address_failure(self, mock_f):
        """_get_mac_address returns dash on read failure."""
        from ui.network_tab import NetworkTab

        result = NetworkTab._get_mac_address("nonexistent0")
        self.assertEqual(result, "—")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_make_table_item_text(self, mock_ss):
        """_make_table_item creates item with correct text."""
        tab = _create_tab()
        item = tab._make_table_item("hello")
        self.assertEqual(item.text(), "hello")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_make_table_item_numeric(self, mock_ss):
        """_make_table_item converts non-string to string."""
        tab = _create_tab()
        item = tab._make_table_item(42)
        self.assertEqual(item.text(), "42")

    def test_make_container_sets_scroll_and_margins(self):
        """_make_container wraps layout with scroll area and standard margins."""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QAbstractScrollArea, QScrollArea, QVBoxLayout

        from ui.network_tab import NetworkTab

        layout = QVBoxLayout()
        scroll = NetworkTab._make_container(layout)
        margins = layout.contentsMargins()
        self.assertEqual(
            (
                margins.left(),
                margins.top(),
                margins.right(),
                margins.bottom(),
            ),
            CONTENT_MARGINS,
        )
        self.assertIsInstance(scroll, QScrollArea)
        self.assertEqual(
            scroll.sizeAdjustPolicy(),
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents,
        )
        self.assertEqual(
            scroll.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertEqual(
            scroll.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )


# =========================================================================
# _initial_load
# =========================================================================
class TestNetworkTabInitialLoad(unittest.TestCase):
    """Tests for _initial_load orchestration."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    @patch("ui.network_tab.NetworkMonitor")
    @patch("ui.network_tab.os.path.exists", return_value=False)
    def test_initial_load_calls_all(self, mock_exists, mock_nm, mock_nu, mock_ss):
        """_initial_load invokes all sub-loaders."""
        tab = _create_tab()
        mock_nu.scan_wifi.return_value = []
        mock_nu.load_vpn_connections.return_value = []
        mock_nu.detect_current_dns.return_value = None
        mock_nu.get_active_connection.return_value = None
        mock_nu.check_hostname_privacy.return_value = None
        mock_nm.get_all_interfaces.return_value = []

        tab._initial_load()

        mock_nm.get_all_interfaces.assert_called_once()
        mock_nu.load_vpn_connections.assert_called_once()
        mock_nu.detect_current_dns.assert_called_once()


# =========================================================================
# Connections sub-tab
# =========================================================================
class TestNetworkTabConnections(unittest.TestCase):
    """Tests for _load_interfaces, _scan_wifi, _connect_wifi, _disconnect_wifi, _load_vpn."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    @patch("builtins.open", mock_open(read_data="aa:bb:cc:dd:ee:ff\n"))
    def test_load_interfaces_success(self, mock_nm, mock_ss):
        """_load_interfaces populates table with interface data."""
        iface = _make_iface()
        mock_nm.get_all_interfaces.return_value = [iface]
        tab = _create_tab()

        tab._load_interfaces()

        self.assertEqual(tab.iface_table.rowCount(), 1)
        self.assertEqual(tab.iface_table.item(0, 0).text(), "wlp2s0")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_load_interfaces_empty(self, mock_nm, mock_ss):
        """_load_interfaces shows empty message when no interfaces."""
        mock_nm.get_all_interfaces.return_value = []
        tab = _create_tab()

        tab._load_interfaces()

        self.assertEqual(tab.iface_table.rowCount(), 1)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_load_interfaces_exception(self, mock_nm, mock_ss):
        """_load_interfaces handles exception gracefully."""
        mock_nm.get_all_interfaces.side_effect = RuntimeError("fail")
        tab = _create_tab()

        tab._load_interfaces()

        # Should set empty state instead of crashing
        self.assertEqual(tab.iface_table.rowCount(), 1)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    @patch("builtins.open", mock_open(read_data="11:22:33:44:55:66\n"))
    def test_load_interfaces_down(self, mock_nm, mock_ss):
        """_load_interfaces shows down status correctly."""
        iface = _make_iface(is_up=False, ip_address=None)
        mock_nm.get_all_interfaces.return_value = [iface]
        tab = _create_tab()

        tab._load_interfaces()

        self.assertEqual(tab.iface_table.rowCount(), 1)
        status_text = tab.iface_table.item(0, 2).text()
        self.assertIn("Down", status_text)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_scan_wifi_with_results(self, mock_nu, mock_ss):
        """_scan_wifi populates wifi_table with results."""
        mock_nu.scan_wifi.return_value = [
            ("MyWiFi", "80%", "WPA2", "Connected"),
            ("OtherNet", "50%", "Open", ""),
        ]
        tab = _create_tab()

        tab._scan_wifi()

        self.assertEqual(tab.wifi_table.rowCount(), 2)
        self.assertEqual(tab.wifi_table.item(0, 0).text(), "MyWiFi")
        self.assertEqual(tab.wifi_table.item(1, 0).text(), "OtherNet")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_scan_wifi_no_results(self, mock_nu, mock_ss):
        """_scan_wifi shows empty state when no networks found."""
        mock_nu.scan_wifi.return_value = []
        tab = _create_tab()

        tab._scan_wifi()

        self.assertEqual(tab.wifi_table.rowCount(), 1)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    def test_connect_wifi_no_selection(self, mock_msgbox, mock_ss):
        """_connect_wifi shows warning when no network selected."""
        tab = _create_tab()
        tab.wifi_table.setCurrentCell(-1, -1)

        tab._connect_wifi()

        mock_msgbox.warning.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    @patch("ui.network_tab.QMessageBox")
    def test_connect_wifi_hidden_network(self, mock_msgbox, mock_nu, mock_ss):
        """_connect_wifi shows warning for hidden network."""
        mock_nu.scan_wifi.return_value = [("(Hidden)", "70%", "WPA2", "")]
        tab = _create_tab()

        tab._scan_wifi()
        tab.wifi_table.setCurrentCell(0, 0)

        tab._connect_wifi()

        mock_msgbox.warning.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_connect_wifi_success(self, mock_nu, mock_ss):
        """_connect_wifi calls run_command with ssid."""
        mock_nu.scan_wifi.return_value = [("TestNet", "90%", "WPA2", "")]
        tab = _create_tab()

        tab._scan_wifi()
        tab.wifi_table.setCurrentCell(0, 0)

        with patch.object(tab, "run_command") as mock_run:
            tab._connect_wifi()
            mock_run.assert_called_once()
            args = mock_run.call_args
            self.assertEqual(args[0][0], "nmcli")
            self.assertIn("TestNet", args[0][1])

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_disconnect_wifi(self, mock_ss):
        """_disconnect_wifi calls run_command to disconnect wlan0."""
        tab = _create_tab()

        with patch.object(tab, "run_command") as mock_run:
            tab._disconnect_wifi()
            mock_run.assert_called_once()
            args = mock_run.call_args
            self.assertEqual(args[0][0], "nmcli")
            self.assertIn("disconnect", args[0][1])

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_load_vpn_with_connections(self, mock_nu, mock_ss):
        """_load_vpn populates vpn_table with VPN data."""
        mock_nu.load_vpn_connections.return_value = [
            ("Work VPN", "vpn", "Active"),
            ("Personal VPN", "wireguard", "Inactive"),
        ]
        tab = _create_tab()

        tab._load_vpn()

        self.assertEqual(tab.vpn_table.rowCount(), 2)
        self.assertEqual(tab.vpn_table.item(0, 0).text(), "Work VPN")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_load_vpn_empty(self, mock_nu, mock_ss):
        """_load_vpn shows empty state when no VPNs configured."""
        mock_nu.load_vpn_connections.return_value = []
        tab = _create_tab()

        tab._load_vpn()

        self.assertEqual(tab.vpn_table.rowCount(), 1)


# =========================================================================
# DNS sub-tab
# =========================================================================
class TestNetworkTabDNS(unittest.TestCase):
    """Tests for _detect_current_dns, get_active_connection, apply_dns, _test_dns."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_detect_current_dns_found(self, mock_nu, mock_ss):
        """_detect_current_dns sets label with detected DNS."""
        mock_nu.detect_current_dns.return_value = "1.1.1.1"
        tab = _create_tab()

        tab._detect_current_dns()

        self.assertIn("1.1.1.1", tab.lbl_current_dns.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_detect_current_dns_not_found(self, mock_nu, mock_ss):
        """_detect_current_dns shows DHCP default when no DNS detected."""
        mock_nu.detect_current_dns.return_value = None
        tab = _create_tab()

        tab._detect_current_dns()

        self.assertIn("DHCP", tab.lbl_current_dns.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_get_active_connection(self, mock_nu, mock_ss):
        """get_active_connection delegates to NetworkUtils."""
        mock_nu.get_active_connection.return_value = "Wired connection 1"
        tab = _create_tab()

        result = tab.get_active_connection()

        self.assertEqual(result, "Wired connection 1")
        mock_nu.get_active_connection.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.NetworkUtils")
    def test_apply_dns_no_connection(self, mock_nu, mock_msgbox, mock_ss):
        """apply_dns shows warning when no active connection."""
        mock_nu.get_active_connection.return_value = None
        tab = _create_tab()

        tab.apply_dns()

        mock_msgbox.warning.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.NetworkUtils")
    def test_apply_dns_auto_dhcp(self, mock_nu, mock_msgbox, mock_ss):
        """apply_dns resets DNS to DHCP when 'auto' is selected."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        tab = _create_tab()
        # Select "System Default (DHCP)" which has data "auto"
        tab.dns_combo.setCurrentIndex(5)

        with patch.object(tab, "run_command") as mock_run:
            tab.apply_dns()
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertEqual(args[0], "nmcli")
            self.assertIn("ipv4.ignore-auto-dns", args[1])
            self.assertIn("no", args[1])

        mock_nu.reactivate_connection.assert_called_once_with("WiFi Home")
        mock_msgbox.information.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.NetworkUtils")
    def test_apply_dns_custom_provider(self, mock_nu, mock_msgbox, mock_ss):
        """apply_dns applies custom DNS servers for non-auto selection."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        tab = _create_tab()
        # Select Cloudflare (index 0)
        tab.dns_combo.setCurrentIndex(0)

        with patch.object(tab, "run_command") as mock_run:
            tab.apply_dns()
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertEqual(args[0], "nmcli")
            self.assertIn("ipv4.dns", args[1])
            self.assertIn("1.1.1.1 1.0.0.1", args[1])

        mock_nu.reactivate_connection.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_test_dns(self, mock_ss):
        """_test_dns calls run_command with bash and nslookup."""
        tab = _create_tab()

        with patch.object(tab, "run_command") as mock_run:
            tab._test_dns()
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertEqual(args[0], "bash")
            self.assertIn("nslookup", args[1][1])


# =========================================================================
# Privacy sub-tab
# =========================================================================
class TestNetworkTabPrivacy(unittest.TestCase):
    """Tests for MAC randomization and hostname privacy."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.os.path.exists", return_value=True)
    def test_check_mac_status_enabled(self, mock_exists, mock_ss):
        """check_mac_status sets enabled label when config file exists."""
        tab = _create_tab()

        tab.check_mac_status()

        self.assertIn("Enabled", tab.lbl_mac_status.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.os.path.exists", return_value=False)
    def test_check_mac_status_disabled(self, mock_exists, mock_ss):
        """check_mac_status sets disabled label when config file missing."""
        tab = _create_tab()

        tab.check_mac_status()

        self.assertIn("Disabled", tab.lbl_mac_status.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("builtins.open", mock_open())
    def test_toggle_mac_enable_success(self, mock_msgbox, mock_ss):
        """toggle_mac_randomization(True) writes config and runs pkexec mv."""
        tab = _create_tab()
        tab.history = MagicMock()

        with patch.object(tab, "run_command") as mock_run:
            tab.toggle_mac_randomization(True)
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertEqual(args[0], "pkexec")
            self.assertIn("mv", args[1])

        tab.history.log_change.assert_called_once()
        mock_msgbox.information.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_toggle_mac_enable_write_error(self, mock_open_f, mock_ss):
        """toggle_mac_randomization(True) handles temp file write failure."""
        tab = _create_tab()

        with patch.object(tab, "append_output") as mock_output:
            tab.toggle_mac_randomization(True)
            mock_output.assert_called()
            output_text = mock_output.call_args[0][0]
            self.assertIn("Failed", output_text)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    def test_toggle_mac_disable(self, mock_msgbox, mock_ss):
        """toggle_mac_randomization(False) runs pkexec rm."""
        tab = _create_tab()

        with patch.object(tab, "run_command") as mock_run:
            tab.toggle_mac_randomization(False)
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertEqual(args[0], "pkexec")
            self.assertIn("rm", args[1])

        mock_msgbox.information.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_check_hostname_privacy_no_connection(self, mock_nu, mock_ss):
        """_check_hostname_privacy handles no active connection."""
        mock_nu.get_active_connection.return_value = None
        tab = _create_tab()

        tab._check_hostname_privacy()

        self.assertIn("no active connection", tab.lbl_hostname_status.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_check_hostname_privacy_hidden(self, mock_nu, mock_ss):
        """_check_hostname_privacy shows hidden when result is True."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        mock_nu.check_hostname_privacy.return_value = True
        tab = _create_tab()

        tab._check_hostname_privacy()

        self.assertIn("Hidden", tab.lbl_hostname_status.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_check_hostname_privacy_visible(self, mock_nu, mock_ss):
        """_check_hostname_privacy shows visible when result is False."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        mock_nu.check_hostname_privacy.return_value = False
        tab = _create_tab()

        tab._check_hostname_privacy()

        self.assertIn("Visible", tab.lbl_hostname_status.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkUtils")
    def test_check_hostname_privacy_unknown(self, mock_nu, mock_ss):
        """_check_hostname_privacy shows unknown for None result."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        mock_nu.check_hostname_privacy.return_value = None
        tab = _create_tab()

        tab._check_hostname_privacy()

        self.assertIn("unknown", tab.lbl_hostname_status.text())

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.NetworkUtils")
    def test_toggle_hostname_privacy_no_connection(self, mock_nu, mock_msgbox, mock_ss):
        """_toggle_hostname_privacy warns when no active connection."""
        mock_nu.get_active_connection.return_value = None
        tab = _create_tab()

        tab._toggle_hostname_privacy(True)

        mock_msgbox.warning.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.NetworkUtils")
    def test_toggle_hostname_hide(self, mock_nu, mock_msgbox, mock_ss):
        """_toggle_hostname_privacy(True) sets send-hostname to 'no'."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        tab = _create_tab()
        tab.history = MagicMock()

        with patch.object(tab, "run_command") as mock_run:
            tab._toggle_hostname_privacy(True)
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertEqual(args[0], "nmcli")
            self.assertIn("no", args[1])

        tab.history.log_change.assert_called_once()
        mock_msgbox.information.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.NetworkUtils")
    def test_toggle_hostname_show(self, mock_nu, mock_msgbox, mock_ss):
        """_toggle_hostname_privacy(False) sets send-hostname to 'yes'."""
        mock_nu.get_active_connection.return_value = "WiFi Home"
        tab = _create_tab()
        tab.history = MagicMock()

        with patch.object(tab, "run_command") as mock_run:
            tab._toggle_hostname_privacy(False)
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            self.assertIn("yes", args[1])

        tab.history.log_change.assert_called_once()


# =========================================================================
# Undo
# =========================================================================
class TestNetworkTabUndo(unittest.TestCase):
    """Tests for undo_last action."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    @patch("ui.network_tab.os.path.exists", return_value=False)
    @patch("ui.network_tab.NetworkUtils")
    def test_undo_last_success(self, mock_nu, mock_exists, mock_msgbox, mock_ss):
        """undo_last shows success message and refreshes status."""
        mock_nu.get_active_connection.return_value = None
        tab = _create_tab()
        tab.history = MagicMock()
        tab.history.undo_last_action.return_value = (
            True,
            "Undid: Enabled MAC Randomization",
        )

        tab.undo_last()

        mock_msgbox.information.assert_called_once()
        tab.history.undo_last_action.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.QMessageBox")
    def test_undo_last_failure(self, mock_msgbox, mock_ss):
        """undo_last shows warning on failure."""
        tab = _create_tab()
        tab.history = MagicMock()
        tab.history.undo_last_action.return_value = (False, "No actions to undo.")

        tab.undo_last()

        mock_msgbox.warning.assert_called_once()


# =========================================================================
# Monitoring sub-tab
# =========================================================================
class TestNetworkTabMonitoring(unittest.TestCase):
    """Tests for _refresh_monitoring and _on_tab_changed."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_refresh_monitoring_success(self, mock_nm, mock_ss):
        """_refresh_monitoring populates bandwidth labels and tables."""
        mock_nm.get_bandwidth_summary.return_value = {
            "total_sent": 1048576,
            "total_recv": 2097152,
            "total_send_rate": 1024.0,
            "total_recv_rate": 2048.0,
        }
        mock_nm.bytes_to_human.side_effect = lambda b: f"{b} B"

        wifi_iface = _make_iface(name="wlp2s0", itype="wifi")
        eth_iface = _make_iface(name="enp3s0", itype="ethernet")
        mock_nm.get_all_interfaces.return_value = [wifi_iface, eth_iface]

        conn = _make_conn()
        mock_nm.get_active_connections.return_value = [conn]

        tab = _create_tab()

        tab._refresh_monitoring()

        self.assertIn("1048576 B", tab.lbl_total_sent.text())
        self.assertIn("2097152 B", tab.lbl_total_recv.text())
        self.assertEqual(tab.traffic_table.rowCount(), 2)
        self.assertEqual(tab.conn_table.rowCount(), 1)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_refresh_monitoring_no_interfaces(self, mock_nm, mock_ss):
        """_refresh_monitoring handles empty interfaces list."""
        mock_nm.get_bandwidth_summary.return_value = {
            "total_sent": 0,
            "total_recv": 0,
            "total_send_rate": 0.0,
            "total_recv_rate": 0.0,
        }
        mock_nm.bytes_to_human.side_effect = lambda b: "0.0 B"
        mock_nm.get_all_interfaces.return_value = []
        mock_nm.get_active_connections.return_value = []

        tab = _create_tab()

        tab._refresh_monitoring()

        # traffic_table should show empty state
        self.assertEqual(tab.traffic_table.rowCount(), 1)
        # conn_table should show empty state
        self.assertEqual(tab.conn_table.rowCount(), 1)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_refresh_monitoring_filters_loopback(self, mock_nm, mock_ss):
        """_refresh_monitoring excludes loopback interfaces from traffic table."""
        mock_nm.get_bandwidth_summary.return_value = {
            "total_sent": 0,
            "total_recv": 0,
            "total_send_rate": 0.0,
            "total_recv_rate": 0.0,
        }
        mock_nm.bytes_to_human.side_effect = lambda b: "0.0 B"

        lo = _make_iface(name="lo", itype="loopback")
        eth = _make_iface(name="enp3s0", itype="ethernet")
        mock_nm.get_all_interfaces.return_value = [lo, eth]
        mock_nm.get_active_connections.return_value = []

        tab = _create_tab()

        tab._refresh_monitoring()

        self.assertEqual(tab.traffic_table.rowCount(), 1)
        self.assertEqual(tab.traffic_table.item(0, 0).text(), "enp3s0")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_refresh_monitoring_filters_connection_states(self, mock_nm, mock_ss):
        """_refresh_monitoring only shows ESTABLISHED and LISTEN connections."""
        mock_nm.get_bandwidth_summary.return_value = {
            "total_sent": 0,
            "total_recv": 0,
            "total_send_rate": 0.0,
            "total_recv_rate": 0.0,
        }
        mock_nm.bytes_to_human.side_effect = lambda b: "0.0 B"
        mock_nm.get_all_interfaces.return_value = []

        conn_est = _make_conn(state="ESTABLISHED")
        conn_listen = _make_conn(state="LISTEN", remote_addr="0.0.0.0", remote_port=0)
        conn_wait = _make_conn(state="TIME_WAIT")
        mock_nm.get_active_connections.return_value = [conn_est, conn_listen, conn_wait]

        tab = _create_tab()

        tab._refresh_monitoring()

        self.assertEqual(tab.conn_table.rowCount(), 2)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_refresh_monitoring_exception(self, mock_nm, mock_ss):
        """_refresh_monitoring handles exceptions without crashing."""
        mock_nm.get_bandwidth_summary.side_effect = RuntimeError("network error")
        tab = _create_tab()

        # Should not raise
        tab._refresh_monitoring()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    @patch("ui.network_tab.NetworkMonitor")
    def test_refresh_monitoring_conn_no_pid(self, mock_nm, mock_ss):
        """_refresh_monitoring handles connections with no PID."""
        mock_nm.get_bandwidth_summary.return_value = {
            "total_sent": 0,
            "total_recv": 0,
            "total_send_rate": 0.0,
            "total_recv_rate": 0.0,
        }
        mock_nm.bytes_to_human.side_effect = lambda b: "0.0 B"
        mock_nm.get_all_interfaces.return_value = []

        conn = _make_conn(pid=0, process_name="")
        mock_nm.get_active_connections.return_value = [conn]

        tab = _create_tab()

        tab._refresh_monitoring()

        self.assertEqual(tab.conn_table.rowCount(), 1)
        # PID=0 is falsy, should show "—"
        self.assertEqual(tab.conn_table.item(0, 4).text(), "—")
        self.assertEqual(tab.conn_table.item(0, 5).text(), "—")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_on_tab_changed_monitoring(self, mock_ss):
        """_on_tab_changed starts timer when switching to monitoring tab (index 3)."""
        tab = _create_tab()

        with patch.object(tab, "_refresh_monitoring") as mock_refresh:
            with patch.object(tab._monitor_timer, "start") as mock_start:
                tab._on_tab_changed(3)
                mock_refresh.assert_called_once()
                mock_start.assert_called_once_with(3000)

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_on_tab_changed_other(self, mock_ss):
        """_on_tab_changed stops timer when switching away from monitoring."""
        tab = _create_tab()

        with patch.object(tab._monitor_timer, "stop") as mock_stop:
            tab._on_tab_changed(0)
            mock_stop.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_on_tab_changed_dns(self, mock_ss):
        """_on_tab_changed stops timer when switching to DNS tab (index 1)."""
        tab = _create_tab()

        with patch.object(tab._monitor_timer, "stop") as mock_stop:
            tab._on_tab_changed(1)
            mock_stop.assert_called_once()

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_on_tab_changed_privacy(self, mock_ss):
        """_on_tab_changed stops timer when switching to Privacy tab (index 2)."""
        tab = _create_tab()

        with patch.object(tab._monitor_timer, "stop") as mock_stop:
            tab._on_tab_changed(2)
            mock_stop.assert_called_once()


# =========================================================================
# Empty table state helper
# =========================================================================
class TestNetworkTabEmptyState(unittest.TestCase):
    """Tests for _set_empty_table_state helper."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_set_empty_table_state(self, mock_ss):
        """_set_empty_table_state sets single-row message with span."""
        tab = _create_tab()

        tab._set_empty_table_state(tab.iface_table, "No data")

        self.assertEqual(tab.iface_table.rowCount(), 1)
        self.assertEqual(tab.iface_table.item(0, 0).text(), "No data")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_set_empty_table_state_single_column(self, mock_ss):
        """_set_empty_table_state works with single-column table."""
        from PyQt6.QtWidgets import QTableWidget

        tab = _create_tab()
        single_col = QTableWidget(0, 1)

        tab._set_empty_table_state(single_col, "Empty")

        self.assertEqual(single_col.rowCount(), 1)
        self.assertEqual(single_col.item(0, 0).text(), "Empty")


# =========================================================================
# DNS combo data values
# =========================================================================
class TestNetworkTabDNSComboData(unittest.TestCase):
    """Tests for DNS combo box data values."""

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_cloudflare_dns_data(self, mock_ss):
        """Cloudflare entry has correct DNS servers."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.itemData(0), "1.1.1.1 1.0.0.1")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_google_dns_data(self, mock_ss):
        """Google entry has correct DNS servers."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.itemData(1), "8.8.8.8 8.8.4.4")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_quad9_dns_data(self, mock_ss):
        """Quad9 entry has correct DNS servers."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.itemData(2), "9.9.9.9 149.112.112.112")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_adguard_dns_data(self, mock_ss):
        """AdGuard entry has correct DNS servers."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.itemData(3), "94.140.14.14 94.140.15.15")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_opendns_dns_data(self, mock_ss):
        """OpenDNS entry has correct DNS servers."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.itemData(4), "208.67.222.222 208.67.220.220")

    @patch("PyQt6.QtCore.QTimer.singleShot")
    def test_dhcp_dns_data(self, mock_ss):
        """System Default (DHCP) entry has 'auto' data value."""
        tab = _create_tab()
        self.assertEqual(tab.dns_combo.itemData(5), "auto")


if __name__ == "__main__":
    unittest.main()
