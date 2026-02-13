"""Extended tests for utils/network_monitor.py coverage."""

import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.network_monitor import ConnectionInfo, InterfaceStats, NetworkMonitor


class TestNetworkMonitorExtended(unittest.TestCase):
    """Branch coverage for NetworkMonitor internals and edge paths."""

    def setUp(self):
        NetworkMonitor._previous_readings = {}

    def test_interface_stats_human_properties(self):
        """InterfaceStats helper properties format byte/rate text."""
        iface = InterfaceStats(
            name='eth0',
            type='ethernet',
            is_up=True,
            ip_address='10.0.0.2',
            bytes_sent=2048,
            bytes_recv=4096,
            packets_sent=2,
            packets_recv=4,
            send_rate=1024.0,
            recv_rate=2048.0,
        )
        self.assertIn('KB', iface.bytes_sent_human)
        self.assertIn('KB', iface.bytes_recv_human)
        self.assertTrue(iface.send_rate_human.endswith('/s'))
        self.assertTrue(iface.recv_rate_human.endswith('/s'))

    @patch('utils.network_monitor.time.monotonic')
    @patch.object(NetworkMonitor, 'get_interface_ip', return_value='192.168.1.2')
    @patch.object(NetworkMonitor, '_is_interface_up', return_value=True)
    @patch.object(NetworkMonitor, '_classify_interface', return_value='ethernet')
    @patch.object(NetworkMonitor, '_read_proc_net_dev')
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
            {'eth0': {'bytes_recv': 1000, 'packets_recv': 1, 'bytes_sent': 2000, 'packets_sent': 2}},
            {'eth0': {'bytes_recv': 1600, 'packets_recv': 2, 'bytes_sent': 2400, 'packets_sent': 3}},
        ]

        first = NetworkMonitor.get_all_interfaces()
        second = NetworkMonitor.get_all_interfaces()

        self.assertEqual(first[0].send_rate, 0.0)
        self.assertEqual(second[0].send_rate, 400.0)
        self.assertEqual(second[0].recv_rate, 600.0)

    @patch.object(NetworkMonitor, '_build_inode_pid_map')
    @patch.object(NetworkMonitor, '_parse_proc_net_socket')
    def test_get_active_connections_maps_processes(self, mock_parse, mock_inode):
        """Active connections map inode to process and normalize protocol states."""
        mock_inode.return_value = {'123': (42, 'python')}
        mock_parse.side_effect = [
            [{'local_addr': '127.0.0.1', 'local_port': 80, 'remote_addr': '0.0.0.0', 'remote_port': 0, 'state': '0A', 'inode': '123'}],
            [],
            [{'local_addr': '127.0.0.1', 'local_port': 53, 'remote_addr': '0.0.0.0', 'remote_port': 0, 'state': '07', 'inode': '999'}],
            [],
        ]

        conns = NetworkMonitor.get_active_connections()
        self.assertEqual(len(conns), 2)
        self.assertIsInstance(conns[0], ConnectionInfo)
        self.assertEqual(conns[0].pid, 42)
        self.assertEqual(conns[0].state, 'LISTEN')
        self.assertEqual(conns[1].protocol, 'udp')
        self.assertEqual(conns[1].state, 'CLOSE')

    @patch('utils.network_monitor.subprocess.run')
    def test_get_interface_ip_parses_inet_line(self, mock_run):
        """IPv4 parser extracts address from ip command output."""
        mock_run.return_value = MagicMock(returncode=0, stdout='2: eth0\n    inet 10.0.0.5/24 brd 10.0.0.255 scope global\n')
        self.assertEqual(NetworkMonitor.get_interface_ip('eth0'), '10.0.0.5')

    @patch('utils.network_monitor.subprocess.run')
    def test_get_interface_ip_nonzero(self, mock_run):
        """Non-zero ip command returns empty address."""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        self.assertEqual(NetworkMonitor.get_interface_ip('eth0'), '')

    @patch('builtins.open', new_callable=mock_open, read_data='Inter-|\n face |\n eth0: 100 1 0 0 0 0 0 0 200 2 0 0 0 0 0 0\n badline\n')
    def test_read_proc_net_dev_parses_valid_lines(self, mock_file):
        """Parser keeps only well-formed interface counter lines."""
        stats = NetworkMonitor._read_proc_net_dev()
        self.assertIn('eth0', stats)
        self.assertEqual(stats['eth0']['bytes_recv'], 100)
        self.assertEqual(stats['eth0']['bytes_sent'], 200)

    @patch('utils.network_monitor.os.path.isdir', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='1\n')
    def test_classify_interface_sysfs_wifi(self, mock_file, mock_isdir):
        """Type=1 plus wireless path classifies as wifi."""
        self.assertEqual(NetworkMonitor._classify_interface('foo0'), 'wifi')

    @patch('utils.network_monitor.os.path.isdir', return_value=False)
    @patch('builtins.open', new_callable=mock_open, read_data='65534\n')
    def test_classify_interface_sysfs_vpn(self, mock_file, mock_isdir):
        """Type 65534 fallback classifies as vpn."""
        self.assertEqual(NetworkMonitor._classify_interface('foo0'), 'vpn')

    @patch('builtins.open', side_effect=OSError('x'))
    def test_is_interface_up_exception(self, mock_file):
        """Operstate read failure returns False."""
        self.assertFalse(NetworkMonitor._is_interface_up('eth0'))

    @patch('builtins.open', new_callable=mock_open, read_data='sl local rem st tx rx tr tm retrnsmt uid timeout inode\n0: 0100007F:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000 100 0 12345 1 0000000000000000 100 0 0 10 0\ninvalid\n')
    def test_parse_proc_net_socket_valid_and_invalid(self, mock_file):
        """Socket parser skips malformed rows and parses valid rows."""
        rows = NetworkMonitor._parse_proc_net_socket('/proc/net/tcp', False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['local_addr'], '127.0.0.1')
        self.assertEqual(rows[0]['local_port'], 80)

    def test_decode_address_ipv4_and_ipv6_paths(self):
        """Address decoder covers IPv4, fallback IPv6 length, and mapped IPv4."""
        v4_addr, v4_port = NetworkMonitor._decode_address('0100007F:1F90', False)
        self.assertEqual(v4_addr, '127.0.0.1')
        self.assertEqual(v4_port, 8080)

        bad_v6_addr, bad_v6_port = NetworkMonitor._decode_address('ABCDEF:0050', True)
        self.assertEqual(bad_v6_addr, 'ABCDEF')
        self.assertEqual(bad_v6_port, 80)

        mapped = '0000000000000000FFFF00000100007F:0050'
        mapped_addr, mapped_port = NetworkMonitor._decode_address(mapped, True)
        self.assertEqual(mapped_addr, '127.0.0.1')
        self.assertEqual(mapped_port, 80)

    @patch('utils.network_monitor.NetworkMonitor._get_process_name', return_value='python')
    @patch('utils.network_monitor.os.readlink')
    @patch('utils.network_monitor.os.listdir')
    def test_build_inode_pid_map(self, mock_listdir, mock_readlink, mock_name):
        """Inode map resolves socket symlinks to pid and process name."""
        mock_listdir.side_effect = [
            ['1234'],
            ['4', '5'],
        ]
        mock_readlink.side_effect = ['socket:[999]', 'not-a-socket']

        mapping = NetworkMonitor._build_inode_pid_map()
        self.assertIn('999', mapping)
        self.assertEqual(mapping['999'], (1234, 'python'))

    @patch('utils.network_monitor.os.listdir', side_effect=OSError('x'))
    def test_build_inode_pid_map_proc_list_error(self, mock_listdir):
        """Top-level /proc listing error returns empty mapping."""
        self.assertEqual(NetworkMonitor._build_inode_pid_map(), {})

    @patch('builtins.open', side_effect=OSError('x'))
    def test_get_process_name_error(self, mock_file):
        """Process-name read failures return empty string."""
        self.assertEqual(NetworkMonitor._get_process_name(1), '')


if __name__ == '__main__':
    unittest.main()