"""
Tests for utils/ports.py — PortAuditor.
Covers: scan_ports, risky port detection, firewall status,
block/allow ports, security score, and error handling.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.ports import PortAuditor, OpenPort, Result


# ---------------------------------------------------------------------------
# TestOpenPortDataclass — dataclass tests
# ---------------------------------------------------------------------------

class TestOpenPortDataclass(unittest.TestCase):
    """Tests for OpenPort dataclass."""

    def test_open_port_creation(self):
        """OpenPort stores all required fields."""
        port = OpenPort(
            protocol="TCP",
            port=22,
            address="0.0.0.0",
            process="sshd",
            pid=1234,
            is_risky=True,
            risk_reason="Remote access",
        )
        self.assertEqual(port.port, 22)
        self.assertTrue(port.is_risky)

    def test_open_port_defaults(self):
        """OpenPort has correct defaults."""
        port = OpenPort(protocol="TCP", port=8080, address="127.0.0.1",
                        process="python", pid=100)
        self.assertFalse(port.is_risky)
        self.assertEqual(port.risk_reason, "")


# ---------------------------------------------------------------------------
# TestScanPorts — port scanning
# ---------------------------------------------------------------------------

class TestScanPorts(unittest.TestCase):
    """Tests for scan_ports with mocked ss output."""

    SS_OUTPUT = (
        "Netid  State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\n"
        "tcp    LISTEN 0       128     0.0.0.0:22          0.0.0.0:*\n"
        "tcp    LISTEN 0       128     127.0.0.1:8080      0.0.0.0:*\n"
        "udp    UNCONN 0       0       0.0.0.0:5353        0.0.0.0:*\n"
    )

    @patch.object(PortAuditor, '_enhance_with_process_info')
    @patch('utils.ports.subprocess.run')
    def test_scan_ports_parses_ss_output(self, mock_run, mock_enhance):
        """scan_ports parses ss output into OpenPort list."""
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SS_OUTPUT)

        ports = PortAuditor.scan_ports()

        self.assertEqual(len(ports), 3)
        port_numbers = [p.port for p in ports]
        self.assertIn(22, port_numbers)
        self.assertIn(8080, port_numbers)

    @patch.object(PortAuditor, '_enhance_with_process_info')
    @patch('utils.ports.subprocess.run')
    def test_scan_ports_detects_risky_port(self, mock_run, mock_enhance):
        """scan_ports marks known risky ports."""
        mock_run.return_value = MagicMock(returncode=0, stdout=self.SS_OUTPUT)

        ports = PortAuditor.scan_ports()

        ssh_ports = [p for p in ports if p.port == 22]
        self.assertEqual(len(ssh_ports), 1)
        self.assertTrue(ssh_ports[0].is_risky)

    @patch('utils.ports.subprocess.run')
    def test_scan_ports_nonzero_exit(self, mock_run):
        """scan_ports returns empty list on error."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        ports = PortAuditor.scan_ports()
        self.assertEqual(ports, [])

    @patch('utils.ports.subprocess.run', side_effect=OSError("ss not found"))
    def test_scan_ports_exception(self, mock_run):
        """scan_ports returns empty list on OSError exception."""
        ports = PortAuditor.scan_ports()
        self.assertEqual(ports, [])


# ---------------------------------------------------------------------------
# TestGetRiskyPorts — risky port filtering
# ---------------------------------------------------------------------------

class TestGetRiskyPorts(unittest.TestCase):
    """Tests for get_risky_ports."""

    @patch.object(PortAuditor, 'scan_ports')
    def test_get_risky_ports_filters(self, mock_scan):
        """get_risky_ports returns only risky ports."""
        mock_scan.return_value = [
            OpenPort("TCP", 22, "0.0.0.0", "sshd", 1, True, "SSH"),
            OpenPort("TCP", 8080, "127.0.0.1", "python", 2, False, ""),
            OpenPort("TCP", 23, "0.0.0.0", "telnetd", 3, True, "Telnet"),
        ]

        risky = PortAuditor.get_risky_ports()
        self.assertEqual(len(risky), 2)
        self.assertTrue(all(p.is_risky for p in risky))


# ---------------------------------------------------------------------------
# TestFirewallStatus — firewall detection
# ---------------------------------------------------------------------------

class TestFirewallStatus(unittest.TestCase):
    """Tests for firewall-related methods."""

    @patch('utils.ports.subprocess.run')
    def test_is_firewalld_running_true(self, mock_run):
        """is_firewalld_running returns True when active."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(PortAuditor.is_firewalld_running())

    @patch('utils.ports.subprocess.run')
    def test_is_firewalld_running_false(self, mock_run):
        """is_firewalld_running returns False when inactive."""
        mock_run.return_value = MagicMock(returncode=3)
        self.assertFalse(PortAuditor.is_firewalld_running())

    @patch('utils.ports.subprocess.run', side_effect=OSError("fail"))
    def test_is_firewalld_running_exception(self, mock_run):
        """is_firewalld_running returns False on OSError."""
        self.assertFalse(PortAuditor.is_firewalld_running())


# ---------------------------------------------------------------------------
# TestBlockAllowPort — firewall port management
# ---------------------------------------------------------------------------

class TestBlockAllowPort(unittest.TestCase):
    """Tests for block_port and allow_port."""

    @patch('utils.ports.subprocess.run')
    @patch.object(PortAuditor, 'is_firewalld_running', return_value=True)
    @patch('utils.ports.shutil.which', return_value='/usr/bin/firewall-cmd')
    def test_block_port_success(self, mock_which, mock_firewalld, mock_run):
        """block_port returns success when firewall-cmd succeeds."""
        mock_run.return_value = MagicMock(returncode=0)

        result = PortAuditor.block_port(8080)
        self.assertTrue(result.success)

    @patch.object(PortAuditor, 'is_firewalld_running', return_value=False)
    @patch('utils.ports.shutil.which', return_value='/usr/bin/firewall-cmd')
    def test_block_port_firewalld_not_running(self, mock_which, mock_firewalld):
        """block_port fails when firewalld is not running."""
        result = PortAuditor.block_port(8080)
        self.assertFalse(result.success)

    @patch('utils.ports.shutil.which', return_value=None)
    def test_block_port_firewall_cmd_missing(self, mock_which):
        """block_port fails when firewall-cmd not found."""
        result = PortAuditor.block_port(8080)
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch('utils.ports.subprocess.run')
    @patch.object(PortAuditor, 'is_firewalld_running', return_value=True)
    @patch('utils.ports.shutil.which', return_value='/usr/bin/firewall-cmd')
    def test_allow_port_success(self, mock_which, mock_firewalld, mock_run):
        """allow_port returns success when firewall-cmd succeeds."""
        mock_run.return_value = MagicMock(returncode=0)

        result = PortAuditor.allow_port(443)
        self.assertTrue(result.success)


# ---------------------------------------------------------------------------
# TestGetSecurityScore — security scoring
# ---------------------------------------------------------------------------

class TestGetSecurityScore(unittest.TestCase):
    """Tests for get_security_score."""

    @patch.object(PortAuditor, 'is_firewalld_running', return_value=True)
    @patch.object(PortAuditor, 'scan_ports')
    def test_security_score_no_risky_ports(self, mock_scan, mock_firewalld):
        """Perfect score when no risky ports and firewall running."""
        mock_scan.return_value = [
            OpenPort("TCP", 8080, "127.0.0.1", "dev", 1, False, ""),
        ]

        score = PortAuditor.get_security_score()
        self.assertEqual(score["score"], 100)
        self.assertEqual(score["rating"], "Excellent")

    @patch.object(PortAuditor, 'is_firewalld_running', return_value=False)
    @patch.object(PortAuditor, 'scan_ports')
    def test_security_score_no_firewall_deduction(self, mock_scan, mock_firewalld):
        """Score deducted when firewall is not running."""
        mock_scan.return_value = []

        score = PortAuditor.get_security_score()
        self.assertLess(score["score"], 100)
        self.assertIn("Firewall", score["recommendations"][0])


if __name__ == '__main__':
    unittest.main()
