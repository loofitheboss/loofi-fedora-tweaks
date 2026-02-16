"""Extended tests for utils/network_monitor.py coverage."""

import os
import socket
import struct
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.network_monitor import ConnectionInfo, InterfaceStats, NetworkMonitor


class TestNetworkMonitorExtended(unittest.TestCase):
    """Branch coverage for NetworkMonitor internals and edge paths."""

    def setUp(self):
        NetworkMonitor._previous_readings = {}

    # ------------------------------------------------------------------ #
    #  InterfaceStats dataclass
    # ------------------------------------------------------------------ #

    def test_interface_stats_human_properties(self):
        """InterfaceStats helper properties format byte/rate text."""
        iface = InterfaceStats(
            name="eth0",
            type="ethernet",
            is_up=True,
            ip_address="10.0.0.2",
            bytes_sent=2048,
            bytes_recv=4096,
            packets_sent=2,
            packets_recv=4,
            send_rate=1024.0,
            recv_rate=2048.0,
        )
        self.assertIn("KB", iface.bytes_sent_human)
        self.assertIn("KB", iface.bytes_recv_human)
        self.assertTrue(iface.send_rate_human.endswith("/s"))
        self.assertTrue(iface.recv_rate_human.endswith("/s"))

    def test_interface_stats_zero_bytes(self):
        """InterfaceStats with zero bytes shows 0.0 B."""
        iface = InterfaceStats(
            name="lo",
            type="loopback",
            is_up=True,
            ip_address="127.0.0.1",
            bytes_sent=0,
            bytes_recv=0,
            packets_sent=0,
            packets_recv=0,
            send_rate=0.0,
            recv_rate=0.0,
        )
        self.assertEqual(iface.bytes_sent_human, "0.0 B")
        self.assertEqual(iface.bytes_recv_human, "0.0 B")
        self.assertEqual(iface.send_rate_human, "0.0 B/s")
        self.assertEqual(iface.recv_rate_human, "0.0 B/s")

    # ------------------------------------------------------------------ #
    #  ConnectionInfo dataclass
    # ------------------------------------------------------------------ #

    def test_connection_info_instantiation(self):
        """ConnectionInfo dataclass stores all fields correctly."""
        conn = ConnectionInfo(
            protocol="tcp",
            local_addr="192.168.1.1",
            local_port=443,
            remote_addr="10.0.0.1",
            remote_port=54321,
            state="ESTABLISHED",
            pid=1234,
            process_name="firefox",
        )
        self.assertEqual(conn.protocol, "tcp")
        self.assertEqual(conn.local_addr, "192.168.1.1")
        self.assertEqual(conn.local_port, 443)
        self.assertEqual(conn.remote_addr, "10.0.0.1")
        self.assertEqual(conn.remote_port, 54321)
        self.assertEqual(conn.state, "ESTABLISHED")
        self.assertEqual(conn.pid, 1234)
        self.assertEqual(conn.process_name, "firefox")

    # ------------------------------------------------------------------ #
    #  bytes_to_human
    # ------------------------------------------------------------------ #

    def test_bytes_to_human_zero(self):
        """Zero bytes returns '0.0 B'."""
        self.assertEqual(NetworkMonitor.bytes_to_human(0), "0.0 B")

    def test_bytes_to_human_bytes(self):
        """Small values stay in bytes."""
        self.assertEqual(NetworkMonitor.bytes_to_human(512), "512.0 B")

    def test_bytes_to_human_kilobytes(self):
        """1024 bytes converts to KB."""
        result = NetworkMonitor.bytes_to_human(1024)
        self.assertIn("KB", result)
        self.assertEqual(result, "1.0 KB")

    def test_bytes_to_human_megabytes(self):
        """1048576 bytes converts to MB."""
        result = NetworkMonitor.bytes_to_human(1024 * 1024)
        self.assertEqual(result, "1.0 MB")

    def test_bytes_to_human_gigabytes(self):
        """1 GB converts properly."""
        result = NetworkMonitor.bytes_to_human(1024**3)
        self.assertEqual(result, "1.0 GB")

    def test_bytes_to_human_terabytes(self):
        """1 TB converts properly."""
        result = NetworkMonitor.bytes_to_human(1024**4)
        self.assertEqual(result, "1.0 TB")

    def test_bytes_to_human_petabytes(self):
        """Values beyond TB fall through to PB."""
        result = NetworkMonitor.bytes_to_human(1024**5)
        self.assertEqual(result, "1.0 PB")

    def test_bytes_to_human_fractional(self):
        """Fractional byte counts are formatted with one decimal."""
        result = NetworkMonitor.bytes_to_human(1536)
        self.assertIn("KB", result)
        self.assertEqual(result, "1.5 KB")

    # ------------------------------------------------------------------ #
    #  get_all_interfaces
    # ------------------------------------------------------------------ #

    @patch("utils.network_monitor.time.monotonic")
    @patch.object(NetworkMonitor, "get_interface_ip", return_value="192.168.1.2")
    @patch.object(NetworkMonitor, "_is_interface_up", return_value=True)
    @patch.object(NetworkMonitor, "_classify_interface", return_value="ethernet")
    @patch.object(NetworkMonitor, "_read_proc_net_dev")
    def test_get_all_interfaces_rate_delta(
        self,
        mock_read,
        mock_class,
        mock_up,
        mock_ip,
        mock_mono,
    ):
        """Second call computes positive send/receive rates from previous counters."""
        mock_mono.side_effect = [100.0, 101.0]
        mock_read.side_effect = [
            {
                "eth0": {
                    "bytes_recv": 1000,
                    "packets_recv": 1,
                    "bytes_sent": 2000,
                    "packets_sent": 2,
                }
            },
            {
                "eth0": {
                    "bytes_recv": 1600,
                    "packets_recv": 2,
                    "bytes_sent": 2400,
                    "packets_sent": 3,
                }
            },
        ]

        first = NetworkMonitor.get_all_interfaces()
        second = NetworkMonitor.get_all_interfaces()

        self.assertEqual(first[0].send_rate, 0.0)
        self.assertEqual(second[0].send_rate, 400.0)
        self.assertEqual(second[0].recv_rate, 600.0)

    @patch.object(NetworkMonitor, "_read_proc_net_dev", return_value={})
    def test_get_all_interfaces_empty_proc_net_dev(self, mock_read):
        """Empty proc_net_dev returns empty interface list."""
        result = NetworkMonitor.get_all_interfaces()
        self.assertEqual(result, [])

    @patch("utils.network_monitor.time.monotonic", return_value=1000.0)
    @patch.object(NetworkMonitor, "_is_interface_up", return_value=False)
    @patch.object(NetworkMonitor, "_classify_interface", return_value="ethernet")
    @patch.object(NetworkMonitor, "_read_proc_net_dev")
    def test_get_all_interfaces_down_interface_no_ip(
        self,
        mock_read,
        mock_class,
        mock_up,
        mock_mono,
    ):
        """Interface that is down gets empty IP address without calling get_interface_ip."""
        mock_read.return_value = {
            "eth0": {
                "bytes_recv": 100,
                "packets_recv": 1,
                "bytes_sent": 200,
                "packets_sent": 2,
            },
        }

        with patch.object(NetworkMonitor, "get_interface_ip") as mock_ip:
            result = NetworkMonitor.get_all_interfaces()
            mock_ip.assert_not_called()

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].is_up)
        self.assertEqual(result[0].ip_address, "")

    # ------------------------------------------------------------------ #
    #  get_active_connections
    # ------------------------------------------------------------------ #

    @patch.object(NetworkMonitor, "_build_inode_pid_map")
    @patch.object(NetworkMonitor, "_parse_proc_net_socket")
    def test_get_active_connections_maps_processes(self, mock_parse, mock_inode):
        """Active connections map inode to process and normalize protocol states."""
        mock_inode.return_value = {"123": (42, "python")}
        mock_parse.side_effect = [
            [
                {
                    "local_addr": "127.0.0.1",
                    "local_port": 80,
                    "remote_addr": "0.0.0.0",
                    "remote_port": 0,
                    "state": "0A",
                    "inode": "123",
                }
            ],
            [],
            [
                {
                    "local_addr": "127.0.0.1",
                    "local_port": 53,
                    "remote_addr": "0.0.0.0",
                    "remote_port": 0,
                    "state": "07",
                    "inode": "999",
                }
            ],
            [],
        ]

        conns = NetworkMonitor.get_active_connections()
        self.assertEqual(len(conns), 2)
        self.assertIsInstance(conns[0], ConnectionInfo)
        self.assertEqual(conns[0].pid, 42)
        self.assertEqual(conns[0].state, "LISTEN")
        self.assertEqual(conns[1].protocol, "udp")
        self.assertEqual(conns[1].state, "CLOSE")

    @patch.object(NetworkMonitor, "_build_inode_pid_map", return_value={})
    @patch.object(NetworkMonitor, "_parse_proc_net_socket", return_value=[])
    def test_get_active_connections_no_connections(self, mock_parse, mock_inode):
        """No parsed sockets returns empty connection list."""
        conns = NetworkMonitor.get_active_connections()
        self.assertEqual(conns, [])

    @patch.object(NetworkMonitor, "_build_inode_pid_map")
    @patch.object(NetworkMonitor, "_parse_proc_net_socket")
    def test_get_active_connections_unknown_inode(self, mock_parse, mock_inode):
        """Connection with inode not in pid map gets pid=0 and empty process name."""
        mock_inode.return_value = {}
        mock_parse.side_effect = [
            [
                {
                    "local_addr": "10.0.0.1",
                    "local_port": 8080,
                    "remote_addr": "10.0.0.2",
                    "remote_port": 443,
                    "state": "01",
                    "inode": "777",
                }
            ],
            [],
            [],
            [],
        ]

        conns = NetworkMonitor.get_active_connections()
        self.assertEqual(len(conns), 1)
        self.assertEqual(conns[0].pid, 0)
        self.assertEqual(conns[0].process_name, "")
        self.assertEqual(conns[0].state, "ESTABLISHED")

    @patch.object(NetworkMonitor, "_build_inode_pid_map", return_value={})
    @patch.object(NetworkMonitor, "_parse_proc_net_socket")
    def test_get_active_connections_tcp_unknown_state(self, mock_parse, mock_inode):
        """TCP connection with unrecognized state hex passes through as-is."""
        mock_parse.side_effect = [
            [
                {
                    "local_addr": "10.0.0.1",
                    "local_port": 80,
                    "remote_addr": "10.0.0.2",
                    "remote_port": 50000,
                    "state": "FF",
                    "inode": "111",
                }
            ],
            [],
            [],
            [],
        ]

        conns = NetworkMonitor.get_active_connections()
        self.assertEqual(len(conns), 1)
        self.assertEqual(conns[0].state, "FF")

    @patch.object(NetworkMonitor, "_build_inode_pid_map", return_value={})
    @patch.object(NetworkMonitor, "_parse_proc_net_socket")
    def test_get_active_connections_udp_unknown_state(self, mock_parse, mock_inode):
        """UDP connection with unrecognized state hex maps to empty string."""
        mock_parse.side_effect = [
            [],
            [],
            [
                {
                    "local_addr": "10.0.0.1",
                    "local_port": 53,
                    "remote_addr": "0.0.0.0",
                    "remote_port": 0,
                    "state": "FF",
                    "inode": "222",
                }
            ],
            [],
        ]

        conns = NetworkMonitor.get_active_connections()
        self.assertEqual(len(conns), 1)
        self.assertEqual(conns[0].state, "")

    # ------------------------------------------------------------------ #
    #  get_bandwidth_summary
    # ------------------------------------------------------------------ #

    @patch.object(NetworkMonitor, "get_all_interfaces")
    def test_get_bandwidth_summary_excludes_loopback(self, mock_ifaces):
        """Bandwidth summary excludes loopback interfaces."""
        mock_ifaces.return_value = [
            InterfaceStats(
                name="lo",
                type="loopback",
                is_up=True,
                ip_address="127.0.0.1",
                bytes_sent=9999,
                bytes_recv=9999,
                packets_sent=99,
                packets_recv=99,
                send_rate=999.0,
                recv_rate=999.0,
            ),
            InterfaceStats(
                name="eth0",
                type="ethernet",
                is_up=True,
                ip_address="10.0.0.1",
                bytes_sent=1000,
                bytes_recv=2000,
                packets_sent=10,
                packets_recv=20,
                send_rate=100.0,
                recv_rate=200.0,
            ),
        ]

        summary = NetworkMonitor.get_bandwidth_summary()
        self.assertEqual(summary["total_sent"], 1000)
        self.assertEqual(summary["total_recv"], 2000)
        self.assertEqual(summary["total_send_rate"], 100.0)
        self.assertEqual(summary["total_recv_rate"], 200.0)

    @patch.object(NetworkMonitor, "get_all_interfaces", return_value=[])
    def test_get_bandwidth_summary_no_interfaces(self, mock_ifaces):
        """Bandwidth summary with no interfaces returns all zeros."""
        summary = NetworkMonitor.get_bandwidth_summary()
        self.assertEqual(summary["total_sent"], 0)
        self.assertEqual(summary["total_recv"], 0)
        self.assertEqual(summary["total_send_rate"], 0.0)
        self.assertEqual(summary["total_recv_rate"], 0.0)

    @patch.object(NetworkMonitor, "get_all_interfaces")
    def test_get_bandwidth_summary_multiple_non_loopback(self, mock_ifaces):
        """Bandwidth summary aggregates across multiple non-loopback interfaces."""
        mock_ifaces.return_value = [
            InterfaceStats(
                name="eth0",
                type="ethernet",
                is_up=True,
                ip_address="10.0.0.1",
                bytes_sent=1000,
                bytes_recv=2000,
                packets_sent=10,
                packets_recv=20,
                send_rate=100.0,
                recv_rate=200.0,
            ),
            InterfaceStats(
                name="wlp2s0",
                type="wifi",
                is_up=True,
                ip_address="192.168.1.5",
                bytes_sent=3000,
                bytes_recv=4000,
                packets_sent=30,
                packets_recv=40,
                send_rate=300.0,
                recv_rate=400.0,
            ),
        ]

        summary = NetworkMonitor.get_bandwidth_summary()
        self.assertEqual(summary["total_sent"], 4000)
        self.assertEqual(summary["total_recv"], 6000)
        self.assertEqual(summary["total_send_rate"], 400.0)
        self.assertEqual(summary["total_recv_rate"], 600.0)

    # ------------------------------------------------------------------ #
    #  get_interface_ip
    # ------------------------------------------------------------------ #

    @patch("utils.network_monitor.subprocess.run")
    def test_get_interface_ip_parses_inet_line(self, mock_run):
        """IPv4 parser extracts address from ip command output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="2: eth0\n    inet 10.0.0.5/24 brd 10.0.0.255 scope global\n",
        )
        self.assertEqual(NetworkMonitor.get_interface_ip("eth0"), "10.0.0.5")

    @patch("utils.network_monitor.subprocess.run")
    def test_get_interface_ip_nonzero(self, mock_run):
        """Non-zero ip command returns empty address."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(NetworkMonitor.get_interface_ip("eth0"), "")

    @patch("utils.network_monitor.subprocess.run", side_effect=OSError("timeout"))
    def test_get_interface_ip_subprocess_exception(self, mock_run):
        """Subprocess exception in get_interface_ip returns empty string."""
        self.assertEqual(NetworkMonitor.get_interface_ip("eth0"), "")

    @patch("utils.network_monitor.subprocess.run")
    def test_get_interface_ip_no_inet_line(self, mock_run):
        """Output without an inet line returns empty address."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="2: eth0: <NO-CARRIER>\n    link/ether aa:bb:cc:dd:ee:ff\n",
        )
        self.assertEqual(NetworkMonitor.get_interface_ip("eth0"), "")

    # ------------------------------------------------------------------ #
    #  _read_proc_net_dev
    # ------------------------------------------------------------------ #

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Inter-|\n face |\n eth0: 100 1 0 0 0 0 0 0 200 2 0 0 0 0 0 0\n badline\n",
    )
    def test_read_proc_net_dev_parses_valid_lines(self, mock_file):
        """Parser keeps only well-formed interface counter lines."""
        stats = NetworkMonitor._read_proc_net_dev()
        self.assertIn("eth0", stats)
        self.assertEqual(stats["eth0"]["bytes_recv"], 100)
        self.assertEqual(stats["eth0"]["bytes_sent"], 200)

    @patch("builtins.open", side_effect=FileNotFoundError("/proc/net/dev"))
    def test_read_proc_net_dev_file_not_found(self, mock_file):
        """File not found returns empty dict."""
        stats = NetworkMonitor._read_proc_net_dev()
        self.assertEqual(stats, {})

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Inter-|\n face |\n nocolon 100 1 0 0 0 0 0 0 200 2 0 0 0 0 0 0\n",
    )
    def test_read_proc_net_dev_missing_colon(self, mock_file):
        """Lines without colon are skipped."""
        stats = NetworkMonitor._read_proc_net_dev()
        self.assertEqual(stats, {})

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Inter-|\n face |\n eth0: 100 1 0\n",
    )
    def test_read_proc_net_dev_too_few_fields(self, mock_file):
        """Lines with fewer than 10 fields after colon are skipped."""
        stats = NetworkMonitor._read_proc_net_dev()
        self.assertEqual(stats, {})

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Inter-|\n face |\n eth0: 500 10 0 0 0 0 0 0 600 20 0 0 0 0 0 0\n lo: 50 5 0 0 0 0 0 0 50 5 0 0 0 0 0 0\n",
    )
    def test_read_proc_net_dev_multiple_interfaces(self, mock_file):
        """Parser handles multiple valid interfaces."""
        stats = NetworkMonitor._read_proc_net_dev()
        self.assertIn("eth0", stats)
        self.assertIn("lo", stats)
        self.assertEqual(stats["eth0"]["bytes_recv"], 500)
        self.assertEqual(stats["lo"]["bytes_sent"], 50)

    # ------------------------------------------------------------------ #
    #  _classify_interface — name patterns
    # ------------------------------------------------------------------ #

    def test_classify_interface_loopback_name(self):
        """Name 'lo' classifies as loopback."""
        self.assertEqual(NetworkMonitor._classify_interface("lo"), "loopback")

    def test_classify_interface_wifi_name(self):
        """Name starting with 'wl' classifies as wifi."""
        self.assertEqual(NetworkMonitor._classify_interface("wlp2s0"), "wifi")

    def test_classify_interface_ethernet_en_name(self):
        """Name starting with 'en' classifies as ethernet."""
        self.assertEqual(NetworkMonitor._classify_interface("enp3s0"), "ethernet")

    def test_classify_interface_ethernet_eth_name(self):
        """Name starting with 'eth' classifies as ethernet."""
        self.assertEqual(NetworkMonitor._classify_interface("eth0"), "ethernet")

    def test_classify_interface_vpn_tun_name(self):
        """Name starting with 'tun' classifies as vpn."""
        self.assertEqual(NetworkMonitor._classify_interface("tun0"), "vpn")

    def test_classify_interface_vpn_tap_name(self):
        """Name starting with 'tap' classifies as vpn."""
        self.assertEqual(NetworkMonitor._classify_interface("tap0"), "vpn")

    def test_classify_interface_vpn_wg_name(self):
        """Name starting with 'wg' classifies as vpn."""
        self.assertEqual(NetworkMonitor._classify_interface("wg0"), "vpn")

    # ------------------------------------------------------------------ #
    #  _classify_interface — sysfs fallback
    # ------------------------------------------------------------------ #

    @patch("utils.network_monitor.os.path.isdir", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="1\n")
    def test_classify_interface_sysfs_wifi(self, mock_file, mock_isdir):
        """Type=1 plus wireless path classifies as wifi."""
        self.assertEqual(NetworkMonitor._classify_interface("foo0"), "wifi")

    @patch("utils.network_monitor.os.path.isdir", return_value=False)
    @patch("builtins.open", new_callable=mock_open, read_data="65534\n")
    def test_classify_interface_sysfs_vpn(self, mock_file, mock_isdir):
        """Type 65534 fallback classifies as vpn."""
        self.assertEqual(NetworkMonitor._classify_interface("foo0"), "vpn")

    @patch("builtins.open", new_callable=mock_open, read_data="772\n")
    def test_classify_interface_sysfs_loopback(self, mock_file):
        """Type 772 in sysfs classifies as loopback."""
        self.assertEqual(NetworkMonitor._classify_interface("foo0"), "loopback")

    @patch("utils.network_monitor.os.path.isdir", return_value=False)
    @patch("builtins.open", new_callable=mock_open, read_data="1\n")
    def test_classify_interface_sysfs_ethernet(self, mock_file, mock_isdir):
        """Type=1 without wireless dir classifies as ethernet."""
        self.assertEqual(NetworkMonitor._classify_interface("foo0"), "ethernet")

    @patch("builtins.open", side_effect=OSError("no sysfs"))
    def test_classify_interface_sysfs_exception(self, mock_file):
        """Sysfs read failure falls through to 'other'."""
        self.assertEqual(NetworkMonitor._classify_interface("foo0"), "other")

    @patch("utils.network_monitor.os.path.isdir", return_value=False)
    @patch("builtins.open", new_callable=mock_open, read_data="999\n")
    def test_classify_interface_sysfs_unknown_type(self, mock_file, mock_isdir):
        """Unknown sysfs type number falls through to 'other'."""
        self.assertEqual(NetworkMonitor._classify_interface("foo0"), "other")

    # ------------------------------------------------------------------ #
    #  _is_interface_up
    # ------------------------------------------------------------------ #

    @patch("builtins.open", new_callable=mock_open, read_data="up\n")
    def test_is_interface_up_true(self, mock_file):
        """Operstate 'up' returns True."""
        self.assertTrue(NetworkMonitor._is_interface_up("eth0"))

    @patch("builtins.open", new_callable=mock_open, read_data="down\n")
    def test_is_interface_up_down(self, mock_file):
        """Operstate 'down' returns False."""
        self.assertFalse(NetworkMonitor._is_interface_up("eth0"))

    @patch("builtins.open", new_callable=mock_open, read_data="unknown\n")
    def test_is_interface_up_unknown(self, mock_file):
        """Operstate 'unknown' returns False (not 'up')."""
        self.assertFalse(NetworkMonitor._is_interface_up("eth0"))

    @patch("builtins.open", side_effect=OSError("x"))
    def test_is_interface_up_exception(self, mock_file):
        """Operstate read failure returns False."""
        self.assertFalse(NetworkMonitor._is_interface_up("eth0"))

    # ------------------------------------------------------------------ #
    #  _parse_proc_net_socket
    # ------------------------------------------------------------------ #

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="sl local rem st tx rx tr tm retrnsmt uid timeout inode\n0: 0100007F:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000 100 0 12345 1 0000000000000000 100 0 0 10 0\ninvalid\n",
    )
    def test_parse_proc_net_socket_valid_and_invalid(self, mock_file):
        """Socket parser skips malformed rows and parses valid rows."""
        rows = NetworkMonitor._parse_proc_net_socket("/proc/net/tcp", False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["local_addr"], "127.0.0.1")
        self.assertEqual(rows[0]["local_port"], 80)

    @patch("builtins.open", side_effect=OSError("no file"))
    def test_parse_proc_net_socket_file_exception(self, mock_file):
        """File open failure returns empty list."""
        rows = NetworkMonitor._parse_proc_net_socket("/proc/net/tcp", False)
        self.assertEqual(rows, [])

    @patch("builtins.open", new_callable=mock_open, read_data="header\n0: too few\n")
    def test_parse_proc_net_socket_too_few_parts(self, mock_file):
        """Rows with fewer than 10 parts are skipped."""
        rows = NetworkMonitor._parse_proc_net_socket("/proc/net/tcp", False)
        self.assertEqual(rows, [])

    @patch("builtins.open", new_callable=mock_open, read_data="header\n")
    def test_parse_proc_net_socket_header_only(self, mock_file):
        """File with only a header returns empty list."""
        rows = NetworkMonitor._parse_proc_net_socket("/proc/net/tcp", False)
        self.assertEqual(rows, [])

    # ------------------------------------------------------------------ #
    #  _decode_address
    # ------------------------------------------------------------------ #

    def test_decode_address_ipv4_and_ipv6_paths(self):
        """Address decoder covers IPv4, fallback IPv6 length, and mapped IPv4."""
        v4_addr, v4_port = NetworkMonitor._decode_address("0100007F:1F90", False)
        self.assertEqual(v4_addr, "127.0.0.1")
        self.assertEqual(v4_port, 8080)

        bad_v6_addr, bad_v6_port = NetworkMonitor._decode_address("ABCDEF:0050", True)
        self.assertEqual(bad_v6_addr, "ABCDEF")
        self.assertEqual(bad_v6_port, 80)

        mapped = "0000000000000000FFFF00000100007F:0050"
        mapped_addr, mapped_port = NetworkMonitor._decode_address(mapped, True)
        self.assertEqual(mapped_addr, "127.0.0.1")
        self.assertEqual(mapped_port, 80)

    def test_decode_address_normal_ipv6(self):
        """Normal IPv6 address (not mapped) decodes correctly."""
        # Build a valid 32-char hex IPv6 address for ::1
        # ::1 in network byte order is 15 zero bytes + 0x01
        # In /proc format, stored as four 32-bit words in host byte order (little-endian)
        # ::1 = 00000000 00000000 00000000 01000000 (little-endian words)
        addr_hex = "00000000000000000000000001000000:0050"
        addr, port = NetworkMonitor._decode_address(addr_hex, True)
        self.assertEqual(port, 80)
        # Should be ::1
        self.assertIn("1", addr)
        self.assertNotEqual(addr, "00000000000000000000000001000000")

    @patch("utils.network_monitor.socket.inet_ntoa", side_effect=OSError("bad"))
    def test_decode_address_ipv4_exception_fallback(self, mock_inet):
        """IPv4 decode exception returns raw hex as fallback."""
        addr, port = NetworkMonitor._decode_address("ZZZZZZZZ:0050", False)
        # When int() conversion fails, ValueError is caught by _parse_proc_net_socket
        # But when inet_ntoa fails with a valid hex, we get the hex fallback
        # We need a valid hex that causes inet_ntoa to fail
        addr, port = NetworkMonitor._decode_address("0100007F:0050", False)
        self.assertEqual(addr, "0100007F")
        self.assertEqual(port, 80)

    @patch("utils.network_monitor.socket.inet_ntop", side_effect=OSError("bad ipv6"))
    def test_decode_address_ipv6_inet_ntop_exception(self, mock_ntop):
        """IPv6 inet_ntop exception returns raw hex as fallback."""
        # Non-mapped IPv6 so it goes through inet_ntop path
        addr_hex = "00000001000000020000000300000004:0050"
        addr, port = NetworkMonitor._decode_address(addr_hex, True)
        self.assertEqual(addr, "00000001000000020000000300000004")
        self.assertEqual(port, 80)

    def test_decode_address_ipv4_zero(self):
        """IPv4 all-zeros decodes to 0.0.0.0."""
        addr, port = NetworkMonitor._decode_address("00000000:0000", False)
        self.assertEqual(addr, "0.0.0.0")
        self.assertEqual(port, 0)

    # ------------------------------------------------------------------ #
    #  _build_inode_pid_map
    # ------------------------------------------------------------------ #

    @patch(
        "utils.network_monitor.NetworkMonitor._get_process_name", return_value="python"
    )
    @patch("utils.network_monitor.os.readlink")
    @patch("utils.network_monitor.os.listdir")
    def test_build_inode_pid_map(self, mock_listdir, mock_readlink, mock_name):
        """Inode map resolves socket symlinks to pid and process name."""
        mock_listdir.side_effect = [
            ["1234"],
            ["4", "5"],
        ]
        mock_readlink.side_effect = ["socket:[999]", "not-a-socket"]

        mapping = NetworkMonitor._build_inode_pid_map()
        self.assertIn("999", mapping)
        self.assertEqual(mapping["999"], (1234, "python"))

    @patch("utils.network_monitor.os.listdir", side_effect=OSError("x"))
    def test_build_inode_pid_map_proc_list_error(self, mock_listdir):
        """Top-level /proc listing error returns empty mapping."""
        self.assertEqual(NetworkMonitor._build_inode_pid_map(), {})

    @patch("utils.network_monitor.os.readlink", side_effect=PermissionError("denied"))
    @patch("utils.network_monitor.os.listdir")
    def test_build_inode_pid_map_readlink_permission_error(
        self, mock_listdir, mock_readlink
    ):
        """PermissionError on readlink is silently skipped."""
        mock_listdir.side_effect = [
            ["1000"],
            ["3"],
        ]

        mapping = NetworkMonitor._build_inode_pid_map()
        self.assertEqual(mapping, {})

    @patch("utils.network_monitor.os.listdir")
    def test_build_inode_pid_map_fd_listdir_permission_error(self, mock_listdir):
        """PermissionError on fd directory listing is silently skipped."""
        mock_listdir.side_effect = [
            ["1000"],
            PermissionError("denied"),
        ]

        mapping = NetworkMonitor._build_inode_pid_map()
        self.assertEqual(mapping, {})

    @patch("utils.network_monitor.os.listdir")
    def test_build_inode_pid_map_skips_non_numeric(self, mock_listdir):
        """Non-numeric /proc entries are skipped."""
        mock_listdir.return_value = ["self", "sys", "not_a_pid"]

        mapping = NetworkMonitor._build_inode_pid_map()
        self.assertEqual(mapping, {})

    # ------------------------------------------------------------------ #
    #  _get_process_name
    # ------------------------------------------------------------------ #

    @patch("builtins.open", new_callable=mock_open, read_data="firefox\n")
    def test_get_process_name_success(self, mock_file):
        """Successful comm read returns stripped process name."""
        self.assertEqual(NetworkMonitor._get_process_name(1234), "firefox")

    @patch("builtins.open", side_effect=OSError("x"))
    def test_get_process_name_error(self, mock_file):
        """Process-name read failures return empty string."""
        self.assertEqual(NetworkMonitor._get_process_name(1), "")


if __name__ == "__main__":
    unittest.main()
