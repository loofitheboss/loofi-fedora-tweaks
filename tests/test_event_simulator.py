"""Tests for utils/event_simulator.py — EventSimulator event publishing."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.event_simulator import EventSimulator


class TestEventSimulatorInit(unittest.TestCase):
    """Tests for EventSimulator initialization."""

    @patch('utils.event_simulator.EventBus')
    def test_creates_default_event_bus(self, mock_bus_class):
        sim = EventSimulator()
        mock_bus_class.assert_called_once()
        self.assertIsNotNone(sim._event_bus)

    def test_accepts_custom_event_bus(self):
        bus = MagicMock()
        sim = EventSimulator(event_bus=bus)
        self.assertIs(sim._event_bus, bus)


class TestSimulateLowStorage(unittest.TestCase):
    """Tests for simulate_low_storage."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_storage_event(self):
        self.sim.simulate_low_storage()
        self.bus.publish.assert_called_once()
        call_kwargs = self.bus.publish.call_args
        self.assertEqual(call_kwargs.kwargs["topic"], "system.storage.low")
        self.assertEqual(call_kwargs.kwargs["source"], "EventSimulator")

    def test_default_values_in_data(self):
        self.sim.simulate_low_storage()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["path"], "/")
        self.assertEqual(data["available_mb"], 500)
        self.assertEqual(data["threshold_mb"], 1000)
        self.assertIn("timestamp", data)

    def test_custom_values(self):
        self.sim.simulate_low_storage(path="/home", available_mb=100, threshold_mb=2000)
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["path"], "/home")
        self.assertEqual(data["available_mb"], 100)
        self.assertEqual(data["threshold_mb"], 2000)


class TestSimulatePublicWifi(unittest.TestCase):
    """Tests for simulate_public_wifi."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_network_event(self):
        self.sim.simulate_public_wifi()
        self.bus.publish.assert_called_once()
        call_kwargs = self.bus.publish.call_args
        self.assertEqual(call_kwargs.kwargs["topic"], "network.connection.public")

    def test_default_data(self):
        self.sim.simulate_public_wifi()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["ssid"], "PublicWiFi")
        self.assertEqual(data["security"], "open")
        self.assertTrue(data["is_public"])

    def test_custom_ssid(self):
        self.sim.simulate_public_wifi(ssid="CoffeeShop", security="wpa2")
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["ssid"], "CoffeeShop")
        self.assertEqual(data["security"], "wpa2")


class TestSimulateTrustedNetwork(unittest.TestCase):
    """Tests for simulate_trusted_network."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_trusted_event(self):
        self.sim.simulate_trusted_network()
        self.bus.publish.assert_called_once()
        self.assertEqual(self.bus.publish.call_args.kwargs["topic"], "network.connection.trusted")

    def test_is_not_public(self):
        self.sim.simulate_trusted_network()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertFalse(data["is_public"])


class TestSimulateThermalThrottling(unittest.TestCase):
    """Tests for simulate_thermal_throttling."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_throttling_event(self):
        self.sim.simulate_thermal_throttling()
        self.assertEqual(self.bus.publish.call_args.kwargs["topic"], "system.thermal.throttling")

    def test_default_values(self):
        self.sim.simulate_thermal_throttling()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["temperature"], 95)
        self.assertTrue(data["throttling"])

    def test_custom_temperature(self):
        self.sim.simulate_thermal_throttling(temperature=105, sensor="gpu_thermal")
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["temperature"], 105)
        self.assertEqual(data["sensor"], "gpu_thermal")


class TestSimulateThermalNormal(unittest.TestCase):
    """Tests for simulate_thermal_normal."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_normal_event(self):
        self.sim.simulate_thermal_normal()
        self.assertEqual(self.bus.publish.call_args.kwargs["topic"], "system.thermal.normal")

    def test_not_throttling(self):
        self.sim.simulate_thermal_normal()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertFalse(data["throttling"])


class TestSimulateBatteryLow(unittest.TestCase):
    """Tests for simulate_battery_low."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_battery_event(self):
        self.sim.simulate_battery_low()
        self.assertEqual(self.bus.publish.call_args.kwargs["topic"], "system.power.battery")

    def test_default_values(self):
        self.sim.simulate_battery_low()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["level"], 15)
        self.assertEqual(data["status"], "discharging")

    def test_custom_level(self):
        self.sim.simulate_battery_low(level=5, status="charging")
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["level"], 5)
        self.assertEqual(data["status"], "charging")


class TestSimulateFirewallPanic(unittest.TestCase):
    """Tests for simulate_firewall_panic."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_panic_event(self):
        self.sim.simulate_firewall_panic()
        self.assertEqual(self.bus.publish.call_args.kwargs["topic"], "security.firewall.panic")

    def test_default_values(self):
        self.sim.simulate_firewall_panic()
        data = self.bus.publish.call_args.kwargs["data"]
        self.assertEqual(data["source"], "192.168.1.100")
        self.assertEqual(data["reason"], "port_scan_detected")


class TestSimulateCustomEvent(unittest.TestCase):
    """Tests for simulate_custom_event."""

    def setUp(self):
        self.bus = MagicMock()
        self.sim = EventSimulator(event_bus=self.bus)

    def test_publishes_custom_topic(self):
        self.sim.simulate_custom_event(topic="test.custom", data={"foo": "bar"})
        call_kwargs = self.bus.publish.call_args.kwargs
        self.assertEqual(call_kwargs["topic"], "test.custom")
        self.assertEqual(call_kwargs["data"], {"foo": "bar"})
        self.assertEqual(call_kwargs["source"], "EventSimulator")

    def test_custom_source(self):
        self.sim.simulate_custom_event(topic="x", data={}, source="MySource")
        self.assertEqual(self.bus.publish.call_args.kwargs["source"], "MySource")


if __name__ == "__main__":
    unittest.main()
