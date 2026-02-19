"""Tests for utils/arbitrator.py"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Pre-mock PyQt6 for import chain: pulse -> PyQt6, services.hardware -> PyQt6
for _mod in ('PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'):
    sys.modules.setdefault(_mod, MagicMock())

from utils.arbitrator import Arbitrator, AgentRequest, Priority, _max_temp


class TestArbitratorCanProceed(unittest.TestCase):
    """Tests for Arbitrator.can_proceed()."""

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_cpu_request_allowed_normal_temp(self, mock_thermal, mock_battery):
        arb = Arbitrator(cpu_thermal_limit_c=90.0)
        request = AgentRequest(agent_name="test-agent", resource="cpu", priority=Priority.BACKGROUND)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=95.0)
    def test_cpu_request_denied_high_temp(self, mock_thermal, mock_battery):
        arb = Arbitrator(cpu_thermal_limit_c=90.0)
        request = AgentRequest(agent_name="test-agent", resource="cpu", priority=Priority.BACKGROUND)
        self.assertFalse(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=95.0)
    def test_cpu_request_allowed_critical_priority_high_temp(self, mock_thermal, mock_battery):
        arb = Arbitrator(cpu_thermal_limit_c=90.0)
        request = AgentRequest(agent_name="test-agent", resource="cpu", priority=Priority.CRITICAL)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=95.0)
    def test_cpu_request_denied_user_interaction_high_temp(self, mock_thermal, mock_battery):
        arb = Arbitrator(cpu_thermal_limit_c=90.0)
        request = AgentRequest(agent_name="test-agent", resource="cpu", priority=Priority.USER_INTERACTION)
        self.assertFalse(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=True)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_background_request_denied_on_battery(self, mock_thermal, mock_battery):
        arb = Arbitrator()
        request = AgentRequest(agent_name="test-agent", resource="background_process", priority=Priority.BACKGROUND)
        self.assertFalse(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=True)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_background_request_allowed_critical_on_battery(self, mock_thermal, mock_battery):
        arb = Arbitrator()
        request = AgentRequest(agent_name="test-agent", resource="background_process", priority=Priority.CRITICAL)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=True)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_background_request_allowed_user_interaction_on_battery(self, mock_thermal, mock_battery):
        arb = Arbitrator()
        request = AgentRequest(agent_name="test-agent", resource="background_process", priority=Priority.USER_INTERACTION)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_background_request_allowed_on_ac(self, mock_thermal, mock_battery):
        arb = Arbitrator()
        request = AgentRequest(agent_name="test-agent", resource="background_process", priority=Priority.BACKGROUND)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_network_request_always_allowed(self, mock_thermal, mock_battery):
        arb = Arbitrator()
        request = AgentRequest(agent_name="test-agent", resource="network", priority=Priority.BACKGROUND)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=50.0)
    def test_disk_request_always_allowed(self, mock_thermal, mock_battery):
        arb = Arbitrator()
        request = AgentRequest(agent_name="test-agent", resource="disk", priority=Priority.BACKGROUND)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=89.9)
    def test_cpu_request_allowed_at_limit_boundary(self, mock_thermal, mock_battery):
        arb = Arbitrator(cpu_thermal_limit_c=90.0)
        request = AgentRequest(agent_name="test-agent", resource="cpu", priority=Priority.BACKGROUND)
        self.assertTrue(arb.can_proceed(request))

    @patch('utils.arbitrator.Arbitrator._on_battery', return_value=False)
    @patch('utils.arbitrator.Arbitrator._get_thermal_status', return_value=90.0)
    def test_cpu_request_allowed_at_exact_limit(self, mock_thermal, mock_battery):
        arb = Arbitrator(cpu_thermal_limit_c=90.0)
        request = AgentRequest(agent_name="test-agent", resource="cpu", priority=Priority.BACKGROUND)
        # 90.0 is NOT > 90.0, so allowed
        self.assertTrue(arb.can_proceed(request))


class TestArbitratorThermalStatus(unittest.TestCase):
    """Tests for Arbitrator._get_thermal_status()."""

    @patch('utils.arbitrator.TemperatureManager.get_cpu_temps')
    def test_get_thermal_status(self, mock_temps):
        sensor1 = MagicMock(current=65.0)
        sensor2 = MagicMock(current=72.5)
        mock_temps.return_value = [sensor1, sensor2]
        result = Arbitrator._get_thermal_status()
        self.assertEqual(result, 72.5)

    @patch('utils.arbitrator.TemperatureManager.get_cpu_temps')
    def test_get_thermal_status_no_sensors(self, mock_temps):
        mock_temps.return_value = []
        result = Arbitrator._get_thermal_status()
        self.assertEqual(result, 0.0)


class TestArbitratorOnBattery(unittest.TestCase):
    """Tests for Arbitrator._on_battery()."""

    @patch('utils.arbitrator.SystemPulse')
    @patch('utils.arbitrator.PowerState')
    def test_on_battery_true(self, mock_power_state, mock_sys_pulse):
        mock_power_state.BATTERY.value = "battery"
        mock_sys_pulse.get_power_state.return_value = "battery"
        self.assertTrue(Arbitrator._on_battery())

    @patch('utils.arbitrator.SystemPulse')
    @patch('utils.arbitrator.PowerState')
    def test_on_battery_false(self, mock_power_state, mock_sys_pulse):
        mock_power_state.BATTERY.value = "battery"
        mock_sys_pulse.get_power_state.return_value = "ac"
        self.assertFalse(Arbitrator._on_battery())


class TestMaxTemp(unittest.TestCase):
    """Tests for _max_temp helper function."""

    def test_max_temp_normal(self):
        sensors = [MagicMock(current=50.0), MagicMock(current=70.0), MagicMock(current=60.0)]
        self.assertEqual(_max_temp(sensors), 70.0)

    def test_max_temp_empty(self):
        self.assertEqual(_max_temp([]), 0.0)

    def test_max_temp_single(self):
        sensors = [MagicMock(current=42.5)]
        self.assertEqual(_max_temp(sensors), 42.5)

    def test_max_temp_invalid_value(self):
        sensors = [MagicMock(current="not_a_number"), MagicMock(current=55.0)]
        self.assertEqual(_max_temp(sensors), 55.0)

    def test_max_temp_none_value(self):
        sensors = [MagicMock(current=None), MagicMock(current=30.0)]
        self.assertEqual(_max_temp(sensors), 30.0)


class TestAgentRequest(unittest.TestCase):
    """Tests for AgentRequest dataclass."""

    def test_create_request(self):
        req = AgentRequest(agent_name="test", resource="cpu", priority=Priority.BACKGROUND)
        self.assertEqual(req.agent_name, "test")
        self.assertEqual(req.resource, "cpu")
        self.assertEqual(req.priority, Priority.BACKGROUND)

    def test_request_is_frozen(self):
        req = AgentRequest(agent_name="test", resource="cpu", priority=Priority.CRITICAL)
        with self.assertRaises(AttributeError):
            req.agent_name = "changed"


class TestPriority(unittest.TestCase):
    """Tests for Priority enum."""

    def test_priority_values(self):
        self.assertEqual(Priority.CRITICAL.value, 3)
        self.assertEqual(Priority.USER_INTERACTION.value, 2)
        self.assertEqual(Priority.BACKGROUND.value, 1)

    def test_priority_ordering(self):
        self.assertGreater(Priority.CRITICAL.value, Priority.USER_INTERACTION.value)
        self.assertGreater(Priority.USER_INTERACTION.value, Priority.BACKGROUND.value)


class TestArbitratorInit(unittest.TestCase):
    """Tests for Arbitrator initialization."""

    def test_default_thermal_limit(self):
        arb = Arbitrator()
        self.assertEqual(arb._cpu_thermal_limit_c, 90.0)

    def test_custom_thermal_limit(self):
        arb = Arbitrator(cpu_thermal_limit_c=80.0)
        self.assertEqual(arb._cpu_thermal_limit_c, 80.0)


if __name__ == '__main__':
    unittest.main()
