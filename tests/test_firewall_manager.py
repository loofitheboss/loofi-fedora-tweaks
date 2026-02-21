"""
Tests for utils/firewall_manager.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.firewall_manager import FirewallManager, FirewallInfo, FirewallResult


class TestFirewallInfo(unittest.TestCase):
    """Tests for the FirewallInfo dataclass."""

    def test_to_dict(self):
        """Serialization to dict works."""
        info = FirewallInfo(
            running=True, default_zone="public",
            active_zones={"public": ["eth0"]},
            ports=["80/tcp", "443/tcp"],
            services=["ssh", "http"],
            rich_rules=["rule family=ipv4 accept"],
        )
        d = info.to_dict()
        self.assertTrue(d["running"])
        self.assertEqual(d["default_zone"], "public")
        self.assertEqual(len(d["ports"]), 2)
        self.assertEqual(len(d["services"]), 2)
        self.assertEqual(len(d["rich_rules"]), 1)

    def test_to_dict_all_keys(self):
        """to_dict returns all expected keys."""
        d = FirewallInfo().to_dict()
        expected = {"running", "default_zone", "active_zones",
                    "ports", "services", "rich_rules"}
        self.assertEqual(set(d.keys()), expected)

    def test_defaults(self):
        """Default values are correct."""
        info = FirewallInfo()
        self.assertFalse(info.running)
        self.assertEqual(info.default_zone, "")
        self.assertEqual(info.ports, [])
        self.assertEqual(info.services, [])
        self.assertEqual(info.rich_rules, [])


class TestFirewallResult(unittest.TestCase):
    """Tests for FirewallResult dataclass."""

    def test_success(self):
        """Success result attributes."""
        r = FirewallResult(success=True, message="OK")
        self.assertTrue(r.success)

    def test_failure(self):
        """Failure result attributes."""
        r = FirewallResult(success=False, message="Error")
        self.assertFalse(r.success)


class TestFirewallManagerAvailability(unittest.TestCase):
    """Tests for availability and running checks."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_is_available_true(self, mock_run):
        """Returns True when firewall-cmd exists."""
        mock_run.return_value = MagicMock(returncode=0)

        self.assertTrue(FirewallManager.is_available())

    @patch('utils.firewall_manager.subprocess.run')
    def test_is_available_false(self, mock_run):
        """Returns False when firewall-cmd not found."""
        mock_run.side_effect = OSError("Not found")

        self.assertFalse(FirewallManager.is_available())

    @patch('utils.firewall_manager.subprocess.run')
    def test_is_available_timeout(self, mock_run):
        """Returns False on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="firewall-cmd", timeout=5)

        self.assertFalse(FirewallManager.is_available())

    @patch('utils.firewall_manager.subprocess.run')
    def test_is_running_true(self, mock_run):
        """Returns True when firewalld is running."""
        mock_run.return_value = MagicMock(returncode=0, stdout="running\n")

        self.assertTrue(FirewallManager.is_running())

    @patch('utils.firewall_manager.subprocess.run')
    def test_is_running_false(self, mock_run):
        """Returns False when firewalld is not running."""
        mock_run.return_value = MagicMock(returncode=1, stdout="not running\n")

        self.assertFalse(FirewallManager.is_running())

    @patch('utils.firewall_manager.subprocess.run')
    def test_is_running_os_error(self, mock_run):
        """Returns False on OSError."""
        mock_run.side_effect = OSError("No such file")

        self.assertFalse(FirewallManager.is_running())


class TestFirewallManagerStatus(unittest.TestCase):
    """Tests for FirewallManager.get_status()."""

    @patch('utils.firewall_manager.FirewallManager.list_rich_rules')
    @patch('utils.firewall_manager.FirewallManager.list_services')
    @patch('utils.firewall_manager.FirewallManager.list_ports')
    @patch('utils.firewall_manager.FirewallManager.get_active_zones')
    @patch('utils.firewall_manager.FirewallManager.get_default_zone')
    @patch('utils.firewall_manager.FirewallManager.is_running')
    def test_get_status_running(self, mock_running, mock_zone, mock_active,
                                 mock_ports, mock_services, mock_rules):
        """Returns full status when running."""
        mock_running.return_value = True
        mock_zone.return_value = "public"
        mock_active.return_value = {"public": ["eth0"]}
        mock_ports.return_value = ["80/tcp"]
        mock_services.return_value = ["ssh", "http"]
        mock_rules.return_value = []

        info = FirewallManager.get_status()

        self.assertTrue(info.running)
        self.assertEqual(info.default_zone, "public")
        self.assertEqual(info.ports, ["80/tcp"])
        self.assertEqual(info.services, ["ssh", "http"])

    @patch('utils.firewall_manager.FirewallManager.is_running')
    def test_get_status_not_running(self, mock_running):
        """Returns minimal status when not running."""
        mock_running.return_value = False

        info = FirewallManager.get_status()

        self.assertFalse(info.running)
        self.assertEqual(info.default_zone, "")
        self.assertEqual(info.ports, [])


class TestFirewallManagerZones(unittest.TestCase):
    """Tests for zone operations."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_default_zone(self, mock_run):
        """Returns default zone name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="public\n")

        zone = FirewallManager.get_default_zone()

        self.assertEqual(zone, "public")

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_default_zone_failure(self, mock_run):
        """Returns empty string on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        zone = FirewallManager.get_default_zone()

        self.assertEqual(zone, "")

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_zones(self, mock_run):
        """Lists all available zones."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="block dmz drop external home internal nm-shared public trusted work\n"
        )

        zones = FirewallManager.get_zones()

        self.assertIn("public", zones)
        self.assertIn("trusted", zones)
        self.assertEqual(len(zones), 10)

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_zones_failure(self, mock_run):
        """Returns empty list on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        zones = FirewallManager.get_zones()

        self.assertEqual(zones, [])

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_active_zones(self, mock_run):
        """Parses active zones with interfaces."""
        output = "public\n  interfaces: eth0 wlan0\ntrusted\n  interfaces: virbr0\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=output)

        zones = FirewallManager.get_active_zones()

        self.assertIn("public", zones)
        self.assertIn("eth0", zones["public"])
        self.assertIn("wlan0", zones["public"])
        self.assertIn("trusted", zones)

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_active_zones_empty(self, mock_run):
        """Returns empty dict when no active zones."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        zones = FirewallManager.get_active_zones()

        self.assertEqual(zones, {})

    @patch('utils.firewall_manager.subprocess.run')
    def test_set_default_zone_success(self, mock_run):
        """Set default zone returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = FirewallManager.set_default_zone("trusted")

        self.assertTrue(result.success)
        self.assertIn("trusted", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_set_default_zone_failure(self, mock_run):
        """Set default zone returns failure on error."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Invalid zone"
        )

        result = FirewallManager.set_default_zone("bogus")

        self.assertFalse(result.success)


class TestFirewallManagerPorts(unittest.TestCase):
    """Tests for port operations."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_ports(self, mock_run):
        """Lists open ports."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="80/tcp 443/tcp 8080/tcp\n"
        )

        ports = FirewallManager.list_ports()

        self.assertEqual(len(ports), 3)
        self.assertIn("80/tcp", ports)

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_ports_empty(self, mock_run):
        """Returns empty list when no ports open."""
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")

        ports = FirewallManager.list_ports()

        self.assertEqual(ports, [])

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_ports_with_zone(self, mock_run):
        """Passes zone parameter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        FirewallManager.list_ports(zone="trusted")

        cmd = mock_run.call_args[0][0]
        self.assertIn("--zone", cmd)
        self.assertIn("trusted", cmd)

    @patch('utils.firewall_manager.FirewallManager._reload')
    @patch('utils.firewall_manager.subprocess.run')
    def test_open_port_success(self, mock_run, mock_reload):
        """Open port returns success and calls reload."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_reload.return_value = True

        result = FirewallManager.open_port("8080", "tcp")

        self.assertTrue(result.success)
        self.assertIn("8080/tcp", result.message)
        mock_reload.assert_called_once()

    @patch('utils.firewall_manager.subprocess.run')
    def test_open_port_failure(self, mock_run):
        """Open port returns failure on error."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Already open"
        )

        result = FirewallManager.open_port("8080")

        self.assertFalse(result.success)

    @patch('utils.firewall_manager.subprocess.run')
    def test_open_port_uses_pkexec(self, mock_run):
        """Open port command uses pkexec."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        FirewallManager.open_port("8080", permanent=False)

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pkexec")

    @patch('utils.firewall_manager.FirewallManager._reload')
    @patch('utils.firewall_manager.subprocess.run')
    def test_close_port_success(self, mock_run, mock_reload):
        """Close port returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_reload.return_value = True

        result = FirewallManager.close_port("8080", "tcp")

        self.assertTrue(result.success)
        self.assertIn("8080/tcp", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_open_port_timeout(self, mock_run):
        """Open port returns failure on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="firewall-cmd", timeout=15)

        result = FirewallManager.open_port("8080")

        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_open_port_non_permanent(self, mock_run):
        """Non-permanent port doesn't add --permanent flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        FirewallManager.open_port("8080", permanent=False)

        cmd = mock_run.call_args[0][0]
        self.assertNotIn("--permanent", cmd)


class TestFirewallManagerServices(unittest.TestCase):
    """Tests for service operations."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_services(self, mock_run):
        """Lists allowed services."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="dhcpv6-client http ssh\n"
        )

        services = FirewallManager.list_services()

        self.assertIn("http", services)
        self.assertIn("ssh", services)

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_services_empty(self, mock_run):
        """Returns empty list when no services."""
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")

        services = FirewallManager.list_services()

        self.assertEqual(services, [])

    @patch('utils.firewall_manager.subprocess.run')
    def test_get_available_services(self, mock_run):
        """Lists all known services."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="dhcp dns ftp http https imap imaps nfs ntp pop3 samba ssh\n"
        )

        services = FirewallManager.get_available_services()

        self.assertIn("http", services)
        self.assertIn("ssh", services)
        self.assertGreater(len(services), 5)

    @patch('utils.firewall_manager.FirewallManager._reload')
    @patch('utils.firewall_manager.subprocess.run')
    def test_add_service_success(self, mock_run, mock_reload):
        """Add service returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_reload.return_value = True

        result = FirewallManager.add_service("http")

        self.assertTrue(result.success)
        self.assertIn("http", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_add_service_failure(self, mock_run):
        """Add service returns failure on error."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Invalid service"
        )

        result = FirewallManager.add_service("bogus")

        self.assertFalse(result.success)

    @patch('utils.firewall_manager.FirewallManager._reload')
    @patch('utils.firewall_manager.subprocess.run')
    def test_remove_service_success(self, mock_run, mock_reload):
        """Remove service returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_reload.return_value = True

        result = FirewallManager.remove_service("http")

        self.assertTrue(result.success)
        self.assertIn("http", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_add_service_uses_pkexec(self, mock_run):
        """Add service uses pkexec."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        FirewallManager.add_service("http", permanent=False)

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pkexec")

    @patch('utils.firewall_manager.subprocess.run')
    def test_add_service_with_zone(self, mock_run):
        """Add service passes zone parameter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        FirewallManager.add_service("http", zone="trusted", permanent=False)

        cmd = mock_run.call_args[0][0]
        self.assertIn("--zone", cmd)
        self.assertIn("trusted", cmd)


class TestFirewallManagerRichRules(unittest.TestCase):
    """Tests for rich rule operations."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_rich_rules(self, mock_run):
        """Lists rich rules."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='rule family="ipv4" source address="192.168.1.0/24" accept\n'
        )

        rules = FirewallManager.list_rich_rules()

        self.assertEqual(len(rules), 1)
        self.assertIn("192.168.1.0/24", rules[0])

    @patch('utils.firewall_manager.subprocess.run')
    def test_list_rich_rules_empty(self, mock_run):
        """Returns empty list when no rich rules."""
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")

        rules = FirewallManager.list_rich_rules()

        self.assertEqual(rules, [])

    @patch('utils.firewall_manager.FirewallManager._reload')
    @patch('utils.firewall_manager.subprocess.run')
    def test_add_rich_rule_success(self, mock_run, mock_reload):
        """Add rich rule returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_reload.return_value = True

        result = FirewallManager.add_rich_rule('rule family="ipv4" accept')

        self.assertTrue(result.success)
        self.assertIn("rich rule", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_add_rich_rule_failure(self, mock_run):
        """Add rich rule returns failure on invalid rule."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Invalid rule"
        )

        result = FirewallManager.add_rich_rule("bad rule")

        self.assertFalse(result.success)

    @patch('utils.firewall_manager.FirewallManager._reload')
    @patch('utils.firewall_manager.subprocess.run')
    def test_remove_rich_rule_success(self, mock_run, mock_reload):
        """Remove rich rule returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_reload.return_value = True

        result = FirewallManager.remove_rich_rule('rule family="ipv4" accept')

        self.assertTrue(result.success)


class TestFirewallManagerToggle(unittest.TestCase):
    """Tests for start/stop firewall."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_start_firewall_success(self, mock_run):
        """Start firewalld returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = FirewallManager.start_firewall()

        self.assertTrue(result.success)
        self.assertIn("started", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_start_firewall_failure(self, mock_run):
        """Start firewalld returns failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Failed"
        )

        result = FirewallManager.start_firewall()

        self.assertFalse(result.success)

    @patch('utils.firewall_manager.subprocess.run')
    def test_stop_firewall_success(self, mock_run):
        """Stop firewalld returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = FirewallManager.stop_firewall()

        self.assertTrue(result.success)
        self.assertIn("stopped", result.message)

    @patch('utils.firewall_manager.subprocess.run')
    def test_stop_firewall_failure(self, mock_run):
        """Stop firewalld returns failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Failed"
        )

        result = FirewallManager.stop_firewall()

        self.assertFalse(result.success)

    @patch('utils.firewall_manager.subprocess.run')
    def test_start_firewall_uses_pkexec(self, mock_run):
        """Start firewall uses pkexec via PrivilegedCommand."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        FirewallManager.start_firewall()

        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "pkexec")

    @patch('utils.firewall_manager.subprocess.run')
    def test_start_firewall_timeout(self, mock_run):
        """Start firewall returns failure on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="systemctl", timeout=15)

        result = FirewallManager.start_firewall()

        self.assertFalse(result.success)
        self.assertIn("Error", result.message)


class TestFirewallManagerReload(unittest.TestCase):
    """Tests for internal _reload method."""

    @patch('utils.firewall_manager.subprocess.run')
    def test_reload_success(self, mock_run):
        """Reload returns True on success."""
        mock_run.return_value = MagicMock(returncode=0)

        self.assertTrue(FirewallManager._reload())

    @patch('utils.firewall_manager.subprocess.run')
    def test_reload_failure(self, mock_run):
        """Reload returns False on failure."""
        mock_run.return_value = MagicMock(returncode=1)

        self.assertFalse(FirewallManager._reload())

    @patch('utils.firewall_manager.subprocess.run')
    def test_reload_timeout(self, mock_run):
        """Reload returns False on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="firewall-cmd", timeout=15)

        self.assertFalse(FirewallManager._reload())


if __name__ == '__main__':
    unittest.main()
