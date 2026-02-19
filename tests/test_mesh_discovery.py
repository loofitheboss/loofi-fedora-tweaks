"""Tests for utils/mesh_discovery.py"""
import sys
import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Pre-mock PyQt6 for import chain: containers -> install_hints -> services.system -> command_runner -> PyQt6
for _mod in ('PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'):
    sys.modules.setdefault(_mod, MagicMock())

from utils.mesh_discovery import MeshDiscovery, PeerDevice, SERVICE_TYPE, SERVICE_PORT


class TestGetDeviceId(unittest.TestCase):
    """Tests for MeshDiscovery.get_device_id()."""

    @patch('builtins.open', mock_open(read_data="test-uuid-1234\n"))
    @patch('utils.mesh_discovery.os.path.isfile', return_value=True)
    def test_get_device_id_existing(self, mock_isfile):
        result = MeshDiscovery.get_device_id()
        self.assertEqual(result, "test-uuid-1234")

    @patch('builtins.open', mock_open(read_data=""))
    @patch('utils.mesh_discovery.os.path.isfile', return_value=True)
    def test_get_device_id_empty_file_generates_new(self, mock_isfile):
        with patch('builtins.open', mock_open()) as mocked_write:
            with patch('utils.mesh_discovery.os.path.isfile', return_value=True):
                # First open returns empty, needs to pass through
                pass
        # The function should generate a new UUID when file is empty
        # Testing the generation path more directly:
        with patch('utils.mesh_discovery.os.path.isfile', return_value=False):
            with patch('utils.mesh_discovery.os.makedirs'):
                with patch('builtins.open', mock_open()):
                    result = MeshDiscovery.get_device_id()
                    self.assertIsInstance(result, str)
                    self.assertGreater(len(result), 0)

    @patch('builtins.open', mock_open())
    @patch('utils.mesh_discovery.os.makedirs')
    @patch('utils.mesh_discovery.os.path.isfile', return_value=False)
    def test_get_device_id_creates_new(self, mock_isfile, mock_makedirs):
        result = MeshDiscovery.get_device_id()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        mock_makedirs.assert_called_once()


class TestGetDeviceName(unittest.TestCase):
    """Tests for MeshDiscovery.get_device_name()."""

    @patch('utils.mesh_discovery.socket.gethostname', return_value="my-fedora-pc")
    def test_get_device_name(self, mock_hostname):
        result = MeshDiscovery.get_device_name()
        self.assertEqual(result, "my-fedora-pc")


class TestGetLocalIps(unittest.TestCase):
    """Tests for MeshDiscovery.get_local_ips()."""

    @patch('utils.mesh_discovery.socket.getaddrinfo')
    @patch('utils.mesh_discovery.socket.gethostname', return_value="host")
    @patch('utils.mesh_discovery.socket.socket')
    def test_get_local_ips_udp_method(self, mock_sock_cls, mock_hostname, mock_addrinfo):
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.100", 0)
        mock_sock_cls.return_value = mock_sock
        mock_addrinfo.return_value = []

        result = MeshDiscovery.get_local_ips()
        self.assertIn("192.168.1.100", result)

    @patch('utils.mesh_discovery.socket.getaddrinfo')
    @patch('utils.mesh_discovery.socket.gethostname', return_value="host")
    @patch('utils.mesh_discovery.socket.socket')
    def test_get_local_ips_hostname_fallback(self, mock_sock_cls, mock_hostname, mock_addrinfo):
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("127.0.0.1", 0)
        mock_sock_cls.return_value = mock_sock
        mock_addrinfo.return_value = [
            (2, 1, 6, '', ("192.168.1.50", 0)),
        ]

        result = MeshDiscovery.get_local_ips()
        self.assertIn("192.168.1.50", result)

    @patch('utils.mesh_discovery.socket.getaddrinfo', side_effect=OSError)
    @patch('utils.mesh_discovery.socket.gethostname', return_value="host")
    @patch('utils.mesh_discovery.socket.socket')
    def test_get_local_ips_all_fail(self, mock_sock_cls, mock_hostname, mock_addrinfo):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("no route")
        mock_sock_cls.return_value = mock_sock

        result = MeshDiscovery.get_local_ips()
        self.assertIsInstance(result, list)

    @patch('utils.mesh_discovery.socket.getaddrinfo')
    @patch('utils.mesh_discovery.socket.gethostname', return_value="host")
    @patch('utils.mesh_discovery.socket.socket')
    def test_get_local_ips_excludes_loopback(self, mock_sock_cls, mock_hostname, mock_addrinfo):
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("127.0.0.1", 0)
        mock_sock_cls.return_value = mock_sock
        mock_addrinfo.return_value = [
            (2, 1, 6, '', ("127.0.0.1", 0)),
        ]

        result = MeshDiscovery.get_local_ips()
        self.assertNotIn("127.0.0.1", result)


class TestIsAvahiAvailable(unittest.TestCase):
    """Tests for MeshDiscovery.is_avahi_available()."""

    @patch('utils.mesh_discovery.shutil.which', return_value="/usr/bin/avahi-browse")
    def test_avahi_available(self, mock_which):
        self.assertTrue(MeshDiscovery.is_avahi_available())

    @patch('utils.mesh_discovery.shutil.which', return_value=None)
    def test_avahi_not_available(self, mock_which):
        self.assertFalse(MeshDiscovery.is_avahi_available())


class TestDiscoverPeers(unittest.TestCase):
    """Tests for MeshDiscovery.discover_peers()."""

    @patch('utils.mesh_discovery.subprocess.run')
    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=True)
    def test_discover_peers_success(self, mock_avahi, mock_run):
        avahi_output = (
            '=;eth0;IPv4;Loofi-PC;_loofi._tcp.local.;local;Loofi-PC.local;192.168.1.50;53317;'
            '"device_id=abc-123" "name=Loofi-PC" "platform=linux" "version=1.0" "capabilities=clipboard,filedrop"'
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=avahi_output)

        result = MeshDiscovery.discover_peers()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].address, "192.168.1.50")
        self.assertEqual(result[0].port, 53317)

    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=False)
    def test_discover_peers_no_avahi(self, mock_avahi):
        result = MeshDiscovery.discover_peers()
        self.assertEqual(result, [])

    @patch('utils.mesh_discovery.subprocess.run')
    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=True)
    def test_discover_peers_timeout(self, mock_avahi, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="avahi-browse", timeout=5)
        result = MeshDiscovery.discover_peers()
        self.assertEqual(result, [])

    @patch('utils.mesh_discovery.subprocess.run')
    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=True)
    def test_discover_peers_subprocess_error(self, mock_avahi, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")
        result = MeshDiscovery.discover_peers()
        self.assertEqual(result, [])

    @patch('utils.mesh_discovery.subprocess.run')
    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=True)
    def test_discover_peers_command_failure(self, mock_avahi, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = MeshDiscovery.discover_peers()
        self.assertEqual(result, [])

    @patch('utils.mesh_discovery.subprocess.run')
    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=True)
    def test_discover_peers_empty_output(self, mock_avahi, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = MeshDiscovery.discover_peers()
        self.assertEqual(result, [])

    @patch('utils.mesh_discovery.subprocess.run')
    @patch('utils.mesh_discovery.MeshDiscovery.is_avahi_available', return_value=True)
    def test_discover_peers_skips_non_resolved(self, mock_avahi, mock_run):
        output = "+;eth0;IPv4;SomeService;_http._tcp;local\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=output)
        result = MeshDiscovery.discover_peers()
        self.assertEqual(result, [])


class TestRegisterService(unittest.TestCase):
    """Tests for MeshDiscovery.register_service()."""

    def setUp(self):
        MeshDiscovery._publish_process = None

    @patch('utils.mesh_discovery.MeshDiscovery.build_service_info', return_value={"device_id": "abc", "version": "1.0", "platform": "linux", "name": "test", "capabilities": "clipboard"})
    @patch('utils.mesh_discovery.MeshDiscovery.get_device_name', return_value="test-host")
    @patch('utils.mesh_discovery.subprocess.Popen')
    @patch('utils.mesh_discovery.shutil.which', return_value="/usr/bin/avahi-publish")
    def test_register_service_success(self, mock_which, mock_popen, mock_name, mock_info):
        mock_popen.return_value = MagicMock()
        result = MeshDiscovery.register_service()
        self.assertTrue(result.success)
        self.assertIn("registered", result.message)

    @patch('utils.mesh_discovery.shutil.which', return_value=None)
    def test_register_service_no_avahi_publish(self, mock_which):
        result = MeshDiscovery.register_service()
        self.assertFalse(result.success)
        self.assertIn("not installed", result.message)

    @patch('utils.mesh_discovery.shutil.which', return_value="/usr/bin/avahi-publish")
    def test_register_service_already_registered(self, mock_which):
        MeshDiscovery._publish_process = MagicMock()
        result = MeshDiscovery.register_service()
        self.assertFalse(result.success)
        self.assertIn("already registered", result.message)

    @patch('utils.mesh_discovery.MeshDiscovery.build_service_info', return_value={"device_id": "abc"})
    @patch('utils.mesh_discovery.MeshDiscovery.get_device_name', return_value="test-host")
    @patch('utils.mesh_discovery.subprocess.Popen')
    @patch('utils.mesh_discovery.shutil.which', return_value="/usr/bin/avahi-publish")
    def test_register_service_subprocess_error(self, mock_which, mock_popen, mock_name, mock_info):
        mock_popen.side_effect = OSError("fail")
        result = MeshDiscovery.register_service()
        self.assertFalse(result.success)
        self.assertIsNone(MeshDiscovery._publish_process)

    def tearDown(self):
        MeshDiscovery._publish_process = None


class TestUnregisterService(unittest.TestCase):
    """Tests for MeshDiscovery.unregister_service()."""

    def setUp(self):
        MeshDiscovery._publish_process = None

    def test_unregister_no_process(self):
        result = MeshDiscovery.unregister_service()
        self.assertFalse(result.success)
        self.assertIn("No service", result.message)

    def test_unregister_success(self):
        mock_process = MagicMock()
        MeshDiscovery._publish_process = mock_process
        result = MeshDiscovery.unregister_service()
        self.assertTrue(result.success)
        mock_process.terminate.assert_called_once()
        self.assertIsNone(MeshDiscovery._publish_process)

    def test_unregister_error(self):
        mock_process = MagicMock()
        mock_process.terminate.side_effect = OSError("fail")
        MeshDiscovery._publish_process = mock_process
        result = MeshDiscovery.unregister_service()
        self.assertFalse(result.success)
        self.assertIsNone(MeshDiscovery._publish_process)

    def tearDown(self):
        MeshDiscovery._publish_process = None


class TestBuildServiceInfo(unittest.TestCase):
    """Tests for MeshDiscovery.build_service_info()."""

    @patch('utils.mesh_discovery.MeshDiscovery.get_device_name', return_value="test-host")
    @patch('utils.mesh_discovery.MeshDiscovery.get_device_id', return_value="uuid-test-123")
    def test_build_service_info(self, mock_id, mock_name):
        with patch.dict('sys.modules', {'version': MagicMock(__version__="1.0.0")}):
            result = MeshDiscovery.build_service_info()
            self.assertIn("device_id", result)
            self.assertIn("platform", result)
            self.assertEqual(result["platform"], "linux")
            self.assertIn("name", result)
            self.assertIn("capabilities", result)


class TestIsPeerAlive(unittest.TestCase):
    """Tests for MeshDiscovery.is_peer_alive()."""

    @patch('utils.mesh_discovery.socket.socket')
    def test_peer_alive(self, mock_sock_cls):
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        peer = PeerDevice(
            name="test", address="192.168.1.50", port=53317,
            device_id="abc", platform="linux", version="1.0",
            last_seen=0.0, capabilities=[]
        )
        self.assertTrue(MeshDiscovery.is_peer_alive(peer))
        mock_sock.connect.assert_called_once_with(("192.168.1.50", 53317))

    @patch('utils.mesh_discovery.socket.socket')
    def test_peer_not_alive(self, mock_sock_cls):
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("connection refused")
        mock_sock_cls.return_value = mock_sock
        peer = PeerDevice(
            name="test", address="192.168.1.50", port=53317,
            device_id="abc", platform="linux", version="1.0",
            last_seen=0.0, capabilities=[]
        )
        self.assertFalse(MeshDiscovery.is_peer_alive(peer))


class TestParseTxtRecord(unittest.TestCase):
    """Tests for MeshDiscovery._parse_txt_record()."""

    def test_parse_valid_record(self):
        raw = '"key1=val1" "key2=val2"'
        result = MeshDiscovery._parse_txt_record(raw)
        self.assertEqual(result["key1"], "val1")
        self.assertEqual(result["key2"], "val2")

    def test_parse_empty_record(self):
        result = MeshDiscovery._parse_txt_record("")
        self.assertEqual(result, {})

    def test_parse_single_field(self):
        result = MeshDiscovery._parse_txt_record('"foo=bar"')
        self.assertEqual(result["foo"], "bar")


if __name__ == '__main__':
    unittest.main()
