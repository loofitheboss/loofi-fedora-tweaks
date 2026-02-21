"""Tests for utils/agent_scheduler.py"""
import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

# Pre-mock PyQt6 for import chain through services/utils that depend on PyQt6
for _mod in ('PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'):
    sys.modules.setdefault(_mod, MagicMock())

from utils.agent_scheduler import AgentScheduler  # noqa: E402


def _make_mock_agent(
    agent_id="test-agent-1",
    name="Test Agent",
    enabled=True,
    subscriptions=None,
    actions=None,
    dry_run=False,
    max_actions_per_hour=10,
):
    """Create a mock AgentConfig for testing."""
    agent = MagicMock()
    agent.agent_id = agent_id
    agent.name = name
    agent.enabled = enabled
    agent.subscriptions = subscriptions if subscriptions is not None else ["system.boot"]
    agent.actions = actions if actions is not None else []
    agent.dry_run = dry_run
    agent.max_actions_per_hour = max_actions_per_hour
    return agent


def _make_mock_event(topic="system.boot", data=None):
    """Create a mock Event for testing."""
    event = MagicMock()
    event.topic = topic
    event.data = data or {}
    return event


def _make_mock_action(name="test-action", command="echo", args=None, operation=None, action_id="act-1"):
    """Create a mock AgentAction for testing."""
    action = MagicMock()
    action.name = name
    action.command = command
    action.args = args or ["hello"]
    action.operation = operation
    action.action_id = action_id
    action.severity = MagicMock()
    action.severity.value = "low"
    return action


class TestAgentSchedulerInit(unittest.TestCase):
    """Tests for AgentScheduler initialization."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_init_with_registry(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        self.assertEqual(scheduler._registry, mock_registry)

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_init_default_registry(self, mock_registry_cls, mock_event_bus_cls):
        mock_instance = MagicMock()
        mock_instance.get_enabled_agents.return_value = []
        mock_registry_cls.instance.return_value = mock_instance
        AgentScheduler()
        mock_registry_cls.instance.assert_called_once()

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_init_subscribes_enabled_agents(self, mock_registry_cls, mock_event_bus_cls):
        agent = _make_mock_agent(subscriptions=["system.boot", "system.shutdown"])
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = [agent]
        mock_event_bus = MagicMock()
        mock_event_bus_cls.return_value = mock_event_bus

        scheduler = AgentScheduler(registry=mock_registry)
        self.assertIn(agent.agent_id, scheduler._subscribed_agents)
        self.assertEqual(mock_event_bus.subscribe.call_count, 2)

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_init_skips_agents_without_subscriptions(self, mock_registry_cls, mock_event_bus_cls):
        agent = _make_mock_agent(subscriptions=[])
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = [agent]
        mock_event_bus = MagicMock()
        mock_event_bus_cls.return_value = mock_event_bus

        scheduler = AgentScheduler(registry=mock_registry)
        self.assertEqual(len(scheduler._subscribed_agents), 0)
        mock_event_bus.subscribe.assert_not_called()


class TestCreateAgentCallback(unittest.TestCase):
    """Tests for AgentScheduler._create_agent_callback()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_callback_calls_execute_agent(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)

        agent = _make_mock_agent()
        callback = scheduler._create_agent_callback(agent)
        event = _make_mock_event()

        with patch.object(scheduler, '_execute_agent') as mock_execute:
            callback(event)
            mock_execute.assert_called_once_with(agent, event)


class TestExecuteAgent(unittest.TestCase):
    """Tests for AgentScheduler._execute_agent()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def _create_scheduler(self, mock_registry_cls, mock_event_bus_cls, agents=None):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = agents or []
        scheduler = AgentScheduler(registry=mock_registry)
        return scheduler, mock_registry

    def test_execute_agent_rate_limited(self):
        scheduler, mock_registry = self._create_scheduler()
        agent = _make_mock_agent(max_actions_per_hour=5)
        event = _make_mock_event()

        mock_state = MagicMock()
        mock_state.can_act.return_value = False
        mock_registry.get_state.return_value = mock_state

        scheduler._execute_agent(agent, event)
        # Should return early without executing actions
        mock_state.record_action.assert_not_called()

    def test_execute_agent_already_running(self):
        scheduler, mock_registry = self._create_scheduler()
        agent = _make_mock_agent()
        event = _make_mock_event()

        from utils.agents import AgentStatus
        mock_state = MagicMock()
        mock_state.can_act.return_value = True
        mock_state.status = AgentStatus.RUNNING
        mock_registry.get_state.return_value = mock_state

        scheduler._execute_agent(agent, event)
        mock_state.record_action.assert_not_called()

    def test_execute_agent_success(self):
        scheduler, mock_registry = self._create_scheduler()
        action = _make_mock_action()
        agent = _make_mock_agent(actions=[action])
        event = _make_mock_event()

        from utils.agents import AgentStatus
        mock_state = MagicMock()
        mock_state.can_act.return_value = True
        mock_state.status = AgentStatus.IDLE
        mock_registry.get_state.return_value = mock_state

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.to_dict.return_value = {"success": True}

        with patch.object(scheduler, '_execute_action', return_value=mock_result):
            with patch.object(scheduler, '_publish_agent_event'):
                scheduler._execute_agent(agent, event)
                mock_state.record_action.assert_called_once()
                mock_registry.save.assert_called()

    def test_execute_agent_action_failure_stops(self):
        scheduler, mock_registry = self._create_scheduler()
        action1 = _make_mock_action(name="action1", action_id="a1")
        action2 = _make_mock_action(name="action2", action_id="a2")
        agent = _make_mock_agent(actions=[action1, action2], dry_run=False)
        event = _make_mock_event()

        from utils.agents import AgentStatus
        mock_state = MagicMock()
        mock_state.can_act.return_value = True
        mock_state.status = AgentStatus.IDLE
        mock_registry.get_state.return_value = mock_state

        fail_result = MagicMock()
        fail_result.success = False
        fail_result.message = "fail"
        fail_result.to_dict.return_value = {"success": False}

        with patch.object(scheduler, '_execute_action', return_value=fail_result):
            with patch.object(scheduler, '_publish_agent_event'):
                scheduler._execute_agent(agent, event)
                # Should only execute one action then stop
                self.assertEqual(mock_state.record_action.call_count, 1)

    def test_execute_agent_exception(self):
        scheduler, mock_registry = self._create_scheduler()
        action = _make_mock_action()
        agent = _make_mock_agent(actions=[action])
        event = _make_mock_event()

        from utils.agents import AgentStatus
        mock_state = MagicMock()
        mock_state.can_act.return_value = True
        mock_state.status = AgentStatus.IDLE
        mock_registry.get_state.return_value = mock_state

        with patch.object(scheduler, '_execute_action', side_effect=RuntimeError("boom")):
            with patch.object(scheduler, '_publish_agent_event'):
                scheduler._execute_agent(agent, event)
                self.assertEqual(mock_state.status, AgentStatus.ERROR)


class TestExecuteAction(unittest.TestCase):
    """Tests for AgentScheduler._execute_action()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def _create_scheduler(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        return scheduler

    def test_execute_action_dry_run(self):
        scheduler = self._create_scheduler()
        agent = _make_mock_agent(dry_run=True)
        action = _make_mock_action(name="test-action")
        event = _make_mock_event()

        result = scheduler._execute_action(agent, action, event)
        self.assertTrue(result.success)
        self.assertIn("DRY RUN", result.message)

    @patch('utils.action_executor.ActionExecutor')
    def test_execute_action_with_command(self, mock_executor_cls):
        scheduler = self._create_scheduler()
        agent = _make_mock_agent(dry_run=False)
        action = _make_mock_action(command="echo", args=["hello"])
        action.severity.value = "low"
        event = _make_mock_event()

        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_exec_result.message = "OK"
        mock_exec_result.timestamp = time.time()
        mock_exec_result.exit_code = 0
        mock_exec_result.stdout = "hello"
        mock_exec_result.stderr = ""
        mock_executor_cls.run.return_value = mock_exec_result

        result = scheduler._execute_action(agent, action, event)
        self.assertTrue(result.success)
        mock_executor_cls.run.assert_called_once()

    @patch('utils.action_executor.ActionExecutor')
    def test_execute_action_privileged(self, mock_executor_cls):
        scheduler = self._create_scheduler()
        agent = _make_mock_agent(dry_run=False)
        action = _make_mock_action(command="systemctl", args=["restart", "service"])
        action.severity.value = "high"
        event = _make_mock_event()

        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_exec_result.message = "OK"
        mock_exec_result.timestamp = time.time()
        mock_exec_result.exit_code = 0
        mock_exec_result.stdout = ""
        mock_exec_result.stderr = ""
        mock_executor_cls.run.return_value = mock_exec_result

        result = scheduler._execute_action(agent, action, event)
        self.assertTrue(result.success)
        # Should have pkexec=True for high severity
        call_kwargs = mock_executor_cls.run.call_args
        self.assertTrue(call_kwargs.kwargs.get("pkexec", False) or call_kwargs[1].get("pkexec", False))

    def test_execute_action_with_operation_only(self):
        scheduler = self._create_scheduler()
        agent = _make_mock_agent(dry_run=False)
        action = _make_mock_action(command=None, operation="cleanup")
        event = _make_mock_event()

        result = scheduler._execute_action(agent, action, event)
        self.assertTrue(result.success)
        self.assertIn("cleanup", result.message)

    def test_execute_action_no_command_no_operation(self):
        scheduler = self._create_scheduler()
        agent = _make_mock_agent(dry_run=False)
        action = _make_mock_action(command=None, operation=None)
        event = _make_mock_event()

        result = scheduler._execute_action(agent, action, event)
        self.assertFalse(result.success)
        self.assertIn("no command", result.message.lower())


class TestPublishAgentEvent(unittest.TestCase):
    """Tests for AgentScheduler._publish_agent_event()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_publish_success_event(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        mock_event_bus = MagicMock()
        mock_event_bus_cls.return_value = mock_event_bus

        scheduler = AgentScheduler(registry=mock_registry)
        agent = _make_mock_agent(agent_id="my-agent")

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"success": True}

        scheduler._publish_agent_event(agent, True, [mock_result])
        mock_event_bus.publish.assert_called_once()
        call_kwargs = mock_event_bus.publish.call_args
        self.assertIn("success", call_kwargs.kwargs.get("topic", call_kwargs[1].get("topic", "")))

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_publish_failure_event(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        mock_event_bus = MagicMock()
        mock_event_bus_cls.return_value = mock_event_bus

        scheduler = AgentScheduler(registry=mock_registry)
        agent = _make_mock_agent(agent_id="my-agent")

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"success": False}

        scheduler._publish_agent_event(agent, False, [mock_result])
        mock_event_bus.publish.assert_called_once()
        call_kwargs = mock_event_bus.publish.call_args
        self.assertIn("failure", call_kwargs.kwargs.get("topic", call_kwargs[1].get("topic", "")))


class TestRegisterAgent(unittest.TestCase):
    """Tests for AgentScheduler.register_agent()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_register_enabled_agent(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        mock_event_bus = MagicMock()
        mock_event_bus_cls.return_value = mock_event_bus

        scheduler = AgentScheduler(registry=mock_registry)
        agent = _make_mock_agent(enabled=True, subscriptions=["system.boot"])

        scheduler.register_agent(agent)
        self.assertIn(agent.agent_id, scheduler._subscribed_agents)

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_register_disabled_agent_ignored(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        agent = _make_mock_agent(enabled=False, subscriptions=["system.boot"])

        scheduler.register_agent(agent)
        self.assertNotIn(agent.agent_id, scheduler._subscribed_agents)

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_register_agent_no_subscriptions_ignored(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        agent = _make_mock_agent(enabled=True, subscriptions=[])

        scheduler.register_agent(agent)
        self.assertNotIn(agent.agent_id, scheduler._subscribed_agents)


class TestUnregisterAgent(unittest.TestCase):
    """Tests for AgentScheduler.unregister_agent()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_unregister_existing_agent(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        agent = _make_mock_agent(agent_id="agent-to-remove")
        scheduler._subscribed_agents["agent-to-remove"] = agent

        result = scheduler.unregister_agent("agent-to-remove")
        self.assertTrue(result)
        self.assertNotIn("agent-to-remove", scheduler._subscribed_agents)

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_unregister_nonexistent_agent(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)

        result = scheduler.unregister_agent("nonexistent")
        self.assertFalse(result)


class TestGetSubscribedAgentCount(unittest.TestCase):
    """Tests for AgentScheduler.get_subscribed_agent_count()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_count_zero(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        self.assertEqual(scheduler.get_subscribed_agent_count(), 0)

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_count_with_agents(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        scheduler._subscribed_agents["a"] = MagicMock()
        scheduler._subscribed_agents["b"] = MagicMock()
        self.assertEqual(scheduler.get_subscribed_agent_count(), 2)


class TestShutdown(unittest.TestCase):
    """Tests for AgentScheduler.shutdown()."""

    @patch('utils.agent_scheduler.EventBus')
    @patch('utils.agent_scheduler.AgentRegistry')
    def test_shutdown_clears_subscriptions(self, mock_registry_cls, mock_event_bus_cls):
        mock_registry = MagicMock()
        mock_registry.get_enabled_agents.return_value = []
        scheduler = AgentScheduler(registry=mock_registry)
        scheduler._subscribed_agents["a"] = MagicMock()
        scheduler._subscribed_agents["b"] = MagicMock()

        scheduler.shutdown()
        self.assertEqual(len(scheduler._subscribed_agents), 0)


if __name__ == '__main__':
    unittest.main()
