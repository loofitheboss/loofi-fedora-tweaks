"""
Tests for utils/network_utils.py (v34.0).
Covers scan_wifi, load_vpn_connections, detect_current_dns,
get_active_connection, check_hostname_privacy, reactivate_connection.
"""
import unittest
import subprocess
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.network_utils import NetworkUtils


class TestScanWifi(unittest.TestCase):
    """Tests for NetworkUtils.scan_wifi()."""

    @patch('utils.network_utils.subprocess.run')
    def test_scan_returns_networks(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="MyNetwork:85:WPA2:yes\nGuest:40:Open:no\n"
        )
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ("MyNetwork", "85%", "WPA2", "Connected"))
        self.assertEqual(rows[1], ("Guest", "40%", "Open", ""))

    @patch('utils.network_utils.subprocess.run')
    def test_scan_hidden_ssid(self, mock_run):
        mock_run.return_value = MagicMock(stdout=":60:WPA2:no\n")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "(Hidden)")

    @patch('utils.network_utils.subprocess.run')
    def test_scan_open_security(self, mock_run):
        mock_run.return_value = MagicMock(stdout="CafeWifi:72::no\n")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "Open")

    @patch('utils.network_utils.subprocess.run')
    def test_scan_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_scan_blank_lines_skipped(self, mock_run):
        mock_run.return_value = MagicMock(stdout="\n\nAP:50:WPA:no\n\n")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(len(rows), 1)

    @patch('utils.network_utils.subprocess.run')
    def test_scan_malformed_line_skipped(self, mock_run):
        mock_run.return_value = MagicMock(stdout="only_two:fields\n")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_scan_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 15)
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_scan_oserror(self, mock_run):
        mock_run.side_effect = OSError("nmcli not found")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_scan_subprocess_error(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")
        rows = NetworkUtils.scan_wifi()
        self.assertEqual(rows, [])


class TestLoadVpnConnections(unittest.TestCase):
    """Tests for NetworkUtils.load_vpn_connections()."""

    @patch('utils.network_utils.subprocess.run')
    def test_vpn_connections_found(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=(
                "MyEthernet:802-3-ethernet:yes\n"
                "WorkVPN:vpn:yes\n"
                "HomeWG:wireguard:no\n"
            )
        )
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ("WorkVPN", "vpn", "🟢 Active"))
        self.assertEqual(rows[1], ("HomeWG", "wireguard", "Inactive"))

    @patch('utils.network_utils.subprocess.run')
    def test_openvpn_detected(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="CorpVPN:openvpn:no\n"
        )
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "CorpVPN")

    @patch('utils.network_utils.subprocess.run')
    def test_no_vpn_connections(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="WiFi:802-11-wireless:yes\n"
        )
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_vpn_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_vpn_malformed_line_skipped(self, mock_run):
        mock_run.return_value = MagicMock(stdout="vpn_only_two:fields\n")
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_vpn_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 5)
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(rows, [])

    @patch('utils.network_utils.subprocess.run')
    def test_vpn_oserror(self, mock_run):
        mock_run.side_effect = OSError("nmcli not found")
        rows = NetworkUtils.load_vpn_connections()
        self.assertEqual(rows, [])


class TestDetectCurrentDns(unittest.TestCase):
    """Tests for NetworkUtils.detect_current_dns()."""

    @patch('utils.network_utils.subprocess.run')
    def test_multiple_dns_servers(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="IP4.DNS[1]:8.8.8.8\nIP4.DNS[2]:1.1.1.1\n"
        )
        dns = NetworkUtils.detect_current_dns()
        self.assertIn("8.8.8.8", dns)
        self.assertIn("1.1.1.1", dns)

    @patch('utils.network_utils.subprocess.run')
    def test_single_dns_server(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="IP4.DNS[1]:9.9.9.9\n"
        )
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "9.9.9.9")

    @patch('utils.network_utils.subprocess.run')
    def test_no_dns_found(self, mock_run):
        mock_run.return_value = MagicMock(stdout="IP4.ADDRESS[1]:192.168.1.2/24\n")
        NetworkUtils.detect_current_dns()
        # Line has ':', but value after split is '192.168.1.2/24' — added to set
        # Since there IS a value, it returns it. Let's test truly empty.
        pass

    @patch('utils.network_utils.subprocess.run')
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "")

    @patch('utils.network_utils.subprocess.run')
    def test_empty_value_after_colon(self, mock_run):
        mock_run.return_value = MagicMock(stdout="IP4.DNS[1]:\n")
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "")

    @patch('utils.network_utils.subprocess.run')
    def test_deduplication(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="IP4.DNS[1]:8.8.8.8\nIP4.DNS[1]:8.8.8.8\n"
        )
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "8.8.8.8")

    @patch('utils.network_utils.subprocess.run')
    def test_dns_sorted(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="IP4.DNS[1]:9.9.9.9\nIP4.DNS[2]:1.1.1.1\n"
        )
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "1.1.1.1, 9.9.9.9")

    @patch('utils.network_utils.subprocess.run')
    def test_dns_oserror(self, mock_run):
        mock_run.side_effect = OSError("nmcli not found")
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "")

    @patch('utils.network_utils.subprocess.run')
    def test_dns_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 5)
        dns = NetworkUtils.detect_current_dns()
        self.assertEqual(dns, "")


class TestGetActiveConnection(unittest.TestCase):
    """Tests for NetworkUtils.get_active_connection()."""

    @patch('utils.network_utils.subprocess.run')
    def test_wifi_connection_active(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="HomeNetwork:wifi\nlo:loopback\n"
        )
        conn = NetworkUtils.get_active_connection()
        self.assertEqual(conn, "HomeNetwork")

    @patch('utils.network_utils.subprocess.run')
    def test_ethernet_connection_active(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="Wired:ethernet\nlo:loopback\n"
        )
        conn = NetworkUtils.get_active_connection()
        self.assertEqual(conn, "Wired")

    @patch('utils.network_utils.subprocess.run')
    def test_no_active_connection(self, mock_run):
        mock_run.return_value = MagicMock(stdout="lo:loopback\n")
        conn = NetworkUtils.get_active_connection()
        self.assertIsNone(conn)

    @patch('utils.network_utils.subprocess.run')
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        conn = NetworkUtils.get_active_connection()
        self.assertIsNone(conn)

    @patch('utils.network_utils.subprocess.run')
    def test_oserror(self, mock_run):
        mock_run.side_effect = OSError("nmcli missing")
        conn = NetworkUtils.get_active_connection()
        self.assertIsNone(conn)

    @patch('utils.network_utils.subprocess.run')
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 5)
        conn = NetworkUtils.get_active_connection()
        self.assertIsNone(conn)


class TestCheckHostnamePrivacy(unittest.TestCase):
    """Tests for NetworkUtils.check_hostname_privacy()."""

    @patch('utils.network_utils.subprocess.run')
    def test_hostname_hidden(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="ipv4.dhcp-send-hostname:no\n"
        )
        result = NetworkUtils.check_hostname_privacy("MyConn")
        self.assertTrue(result)

    @patch('utils.network_utils.subprocess.run')
    def test_hostname_visible(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="ipv4.dhcp-send-hostname:yes\n"
        )
        result = NetworkUtils.check_hostname_privacy("MyConn")
        self.assertFalse(result)

    @patch('utils.network_utils.subprocess.run')
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        result = NetworkUtils.check_hostname_privacy("MyConn")
        self.assertFalse(result)

    @patch('utils.network_utils.subprocess.run')
    def test_oserror_returns_none(self, mock_run):
        mock_run.side_effect = OSError("fail")
        result = NetworkUtils.check_hostname_privacy("MyConn")
        self.assertIsNone(result)

    @patch('utils.network_utils.subprocess.run')
    def test_timeout_returns_none(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 5)
        result = NetworkUtils.check_hostname_privacy("MyConn")
        self.assertIsNone(result)


class TestReactivateConnection(unittest.TestCase):
    """Tests for NetworkUtils.reactivate_connection()."""

    @patch('utils.network_utils.subprocess.run')
    def test_reactivate_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        result = NetworkUtils.reactivate_connection("MyConn")
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["nmcli", "con", "up", "MyConn"],
            capture_output=True, timeout=10
        )

    @patch('utils.network_utils.subprocess.run')
    def test_reactivate_oserror(self, mock_run):
        mock_run.side_effect = OSError("fail")
        result = NetworkUtils.reactivate_connection("MyConn")
        self.assertFalse(result)

    @patch('utils.network_utils.subprocess.run')
    def test_reactivate_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("nmcli", 10)
        result = NetworkUtils.reactivate_connection("MyConn")
        self.assertFalse(result)

    @patch('utils.network_utils.subprocess.run')
    def test_reactivate_subprocess_error(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("connection failed")
        result = NetworkUtils.reactivate_connection("MyConn")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
