"""
Integration tests for real agent implementations.
Tests event-driven agent behavior with mocked system execution.
"""
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.action_result import ActionResult
from utils.agent_scheduler import AgentScheduler
from utils.agents import AgentRegistry, AgentStatus
from utils.event_bus import EventBus
from utils.event_simulator import EventSimulator


class TestAgentImplementations(unittest.TestCase):
    """Test practical agent implementations with event-driven execution."""

    def setUp(self):
        """Set up clean test environment."""
        # Reset singletons
        AgentRegistry.reset()
        EventBus._instance = None

        # Get fresh instances
        self.registry = AgentRegistry.instance()
        self.event_bus = EventBus()
        self.simulator = EventSimulator(self.event_bus)

        # Clear built-in agents for clean test
        self.registry._agents.clear()
        self.registry._states.clear()

        # Load test agents from JSON files
        agents_dir = Path(__file__).parent.parent / "loofi-fedora-tweaks" / "agents"
        loaded_count = self.registry.load_from_directory(str(agents_dir))
        self.assertGreater(loaded_count, 0, "Should load agent definitions from directory")

        # Create scheduler (will subscribe agents)
        self.scheduler = AgentScheduler(self.registry)

    def tearDown(self):
        """Clean up after tests."""
        self.scheduler.shutdown()
        self.event_bus.clear()

    @patch("utils.action_executor.ActionExecutor.run")
    def test_cleanup_agent_triggers_on_low_storage(self, mock_executor_run):
        """Test cleanup agent responds to system.storage.low event."""
        # Setup mock to return success for all commands
        mock_executor_run.return_value = ActionResult.ok(
            message="Command executed successfully",
            exit_code=0,
            action_id="test_action"
        )

        # Find cleanup agent
        cleanup_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-cleanup":
                cleanup_agent = agent
                break

        self.assertIsNotNone(cleanup_agent, "Cleanup agent should be loaded")
        self.assertTrue(cleanup_agent.enabled, "Cleanup agent should be enabled")
        self.assertIn("system.storage.low", cleanup_agent.subscriptions)

        # Get initial state
        state = self.registry.get_state(cleanup_agent.agent_id)
        initial_run_count = state.run_count

        # Simulate low storage event
        self.simulator.simulate_low_storage(path="/", available_mb=500)

        # Wait for async callback execution
        time.sleep(0.2)

        # Verify agent was triggered
        state = self.registry.get_state(cleanup_agent.agent_id)
        self.assertGreater(
            state.run_count,
            initial_run_count,
            "Agent should have executed"
        )
        self.assertEqual(state.status, AgentStatus.IDLE, "Agent should return to IDLE")

        # Verify ActionExecutor was called for cleanup commands
        self.assertTrue(mock_executor_run.called, "ActionExecutor should be called")

        # Verify at least one cleanup action was attempted
        call_args_list = mock_executor_run.call_args_list
        self.assertGreater(len(call_args_list), 0, "Should execute cleanup actions")

        # Check that cleanup commands were issued
        commands_executed = [call[1]["command"] for call in call_args_list if "command" in call[1]]
        self.assertTrue(
            any(cmd in ["dnf", "journalctl", "find"] for cmd in commands_executed),
            f"Should execute cleanup commands, got: {commands_executed}"
        )

    @patch("utils.action_executor.ActionExecutor.run")
    def test_security_agent_responds_to_public_wifi(self, mock_executor_run):
        """Test security agent adjusts firewall on public Wi-Fi connection."""
        # Setup mock
        mock_executor_run.return_value = ActionResult.ok(
            message="Firewall zone changed",
            exit_code=0,
            action_id="firewall_action"
        )

        # Find security agent
        security_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-security":
                security_agent = agent
                break

        self.assertIsNotNone(security_agent, "Security agent should be loaded")
        self.assertIn("network.connection.public", security_agent.subscriptions)

        # Get initial state
        state = self.registry.get_state(security_agent.agent_id)
        initial_run_count = state.run_count

        # Simulate public Wi-Fi connection
        self.simulator.simulate_public_wifi(ssid="CoffeeShop_WiFi", security="open")

        # Wait for execution
        time.sleep(0.2)

        # Verify agent executed
        state = self.registry.get_state(security_agent.agent_id)
        self.assertGreater(state.run_count, initial_run_count)

        # Verify firewall command was called
        self.assertTrue(mock_executor_run.called)
        call_args_list = mock_executor_run.call_args_list
        commands_executed = [call[1]["command"] for call in call_args_list if "command" in call[1]]

        self.assertIn(
            "firewall-cmd",
            commands_executed,
            "Should execute firewall-cmd"
        )

    @patch("utils.action_executor.ActionExecutor.run")
    def test_security_agent_restores_on_trusted_network(self, mock_executor_run):
        """Test security agent restores normal firewall on trusted network."""
        # Setup mock
        mock_executor_run.return_value = ActionResult.ok(
            message="Firewall restored",
            exit_code=0
        )

        # Find security agent
        security_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-security":
                security_agent = agent
                break

        self.assertIsNotNone(security_agent, "Security agent should be loaded")
        self.assertIn("network.connection.trusted", security_agent.subscriptions)

        # Simulate trusted network connection
        self.simulator.simulate_trusted_network(ssid="HomeNetwork", security="wpa3")

        # Wait for execution
        time.sleep(0.2)

        # Verify agent executed
        state = self.registry.get_state(security_agent.agent_id)
        self.assertGreater(state.run_count, 0)

    @patch("utils.action_executor.ActionExecutor.run")
    def test_thermal_agent_responds_to_throttling(self, mock_executor_run):
        """Test thermal agent reduces load when throttling occurs."""
        # Setup mock
        mock_executor_run.return_value = ActionResult.ok(
            message="Governor changed",
            exit_code=0
        )

        # Find thermal agent
        thermal_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-thermal":
                thermal_agent = agent
                break

        self.assertIsNotNone(thermal_agent, "Thermal agent should be loaded")
        self.assertIn("system.thermal.throttling", thermal_agent.subscriptions)

        # Get initial state
        state = self.registry.get_state(thermal_agent.agent_id)
        initial_run_count = state.run_count

        # Simulate thermal throttling
        self.simulator.simulate_thermal_throttling(temperature=95, sensor="cpu_thermal")

        # Wait for execution
        time.sleep(0.2)

        # Verify agent executed
        state = self.registry.get_state(thermal_agent.agent_id)
        self.assertGreater(state.run_count, initial_run_count)

        # Verify thermal management commands were called
        self.assertTrue(mock_executor_run.called)
        call_args_list = mock_executor_run.call_args_list
        commands_executed = [call[1]["command"] for call in call_args_list if "command" in call[1]]

        self.assertTrue(
            any(cmd in ["cpupower", "brightnessctl"] for cmd in commands_executed),
            f"Should execute thermal management commands, got: {commands_executed}"
        )

    @patch("utils.action_executor.ActionExecutor.run")
    def test_thermal_agent_restores_on_normal(self, mock_executor_run):
        """Test thermal agent restores performance when temperature normalizes."""
        # Setup mock
        mock_executor_run.return_value = ActionResult.ok(
            message="Performance restored",
            exit_code=0
        )

        # Find thermal agent
        thermal_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-thermal":
                thermal_agent = agent
                break

        self.assertIsNotNone(thermal_agent, "Thermal agent should be loaded")
        self.assertIn("system.thermal.normal", thermal_agent.subscriptions)

        # Simulate return to normal temperature
        self.simulator.simulate_thermal_normal(temperature=65, sensor="cpu_thermal")

        # Wait for execution
        time.sleep(0.2)

        # Verify agent executed
        state = self.registry.get_state(thermal_agent.agent_id)
        self.assertGreater(state.run_count, 0)

    @patch("utils.action_executor.ActionExecutor.run")
    def test_agent_rate_limiting(self, mock_executor_run):
        """Test agents respect max_actions_per_hour rate limit."""
        # Setup mock
        mock_executor_run.return_value = ActionResult.ok(
            message="OK",
            exit_code=0
        )

        # Find cleanup agent (has max_actions_per_hour: 3)
        cleanup_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-cleanup":
                cleanup_agent = agent
                break

        self.assertIsNotNone(cleanup_agent, "Cleanup agent should be loaded")
        self.assertEqual(cleanup_agent.max_actions_per_hour, 3)

        # Count how many actions per execution
        actions_per_execution = len(cleanup_agent.actions)
        self.assertEqual(actions_per_execution, 4, "Cleanup agent should have 4 actions")

        # Trigger cleanup agent 5 times rapidly
        for i in range(5):
            self.simulator.simulate_low_storage(available_mb=500 - i*10)
            time.sleep(0.1)

        # Wait for all executions
        time.sleep(0.3)

        # Verify agent was rate limited
        # With 4 actions per execution and max 3 actions/hour, it should execute once
        # (first execution records 4 actions, exceeding the limit of 3)
        state = self.registry.get_state(cleanup_agent.agent_id)
        self.assertGreaterEqual(
            state.actions_this_hour,
            actions_per_execution,
            "Agent should have executed at least once"
        )
        # After first execution (4 actions), subsequent attempts should be blocked
        # So run_count should be 4 (one execution with 4 actions)
        self.assertEqual(
            state.run_count,
            actions_per_execution,
            f"Agent should execute once (4 actions), got {state.run_count} actions recorded"
        )

    @patch("utils.action_executor.ActionExecutor.run")
    def test_agent_handles_command_failure(self, mock_executor_run):
        """Test agent handles command execution failures gracefully."""
        # Setup mock to return failure
        mock_executor_run.return_value = ActionResult.fail(
            message="Command failed",
            exit_code=1
        )

        # Find cleanup agent
        cleanup_agent = None
        for agent in self.registry.list_agents():
            if agent.agent_id == "event-cleanup":
                cleanup_agent = agent
                break

        # Trigger cleanup
        self.simulator.simulate_low_storage(available_mb=100)

        # Wait for execution
        time.sleep(0.2)

        # Verify agent recorded the failure
        state = self.registry.get_state(cleanup_agent.agent_id)
        self.assertEqual(state.status, AgentStatus.ERROR, "Agent should be in ERROR state")
        self.assertGreater(state.error_count, 0, "Error count should increase")

    @patch("utils.action_executor.ActionExecutor.run")
    def test_agent_publishes_completion_events(self, mock_executor_run):
        """Test agents publish success/failure events after execution."""
        # Setup mock
        mock_executor_run.return_value = ActionResult.ok(
            message="Success",
            exit_code=0
        )

        # Track published events
        published_events = []

        def event_tracker(event):
            published_events.append(event)

        # Subscribe to agent completion events
        self.event_bus.subscribe("agent.event-cleanup.success", event_tracker)
        self.event_bus.subscribe("agent.event-cleanup.failure", event_tracker)

        # Trigger cleanup agent
        self.simulator.simulate_low_storage(available_mb=200)

        # Wait for execution and event publishing
        time.sleep(0.3)

        # Verify at least one completion event was published
        self.assertGreater(
            len(published_events),
            0,
            "Agent should publish completion event"
        )

        # Verify event structure
        if published_events:
            event = published_events[0]
            self.assertIn("agent.event-cleanup.", event.topic)
            self.assertIn("agent_id", event.data)
            self.assertEqual(event.data["agent_id"], "event-cleanup")

    def test_agent_config_structure(self):
        """Test loaded agent configurations have correct structure."""
        agents = self.registry.list_agents()
        self.assertGreater(len(agents), 0, "Should have loaded agents")

        for agent in agents:
            # Verify required fields
            self.assertIsNotNone(agent.agent_id)
            self.assertIsNotNone(agent.name)
            self.assertIsNotNone(agent.description)
            self.assertIsInstance(agent.subscriptions, list)
            self.assertIsInstance(agent.actions, list)
            self.assertIsInstance(agent.max_actions_per_hour, int)

            # Verify subscriptions are populated
            if agent.enabled:
                self.assertGreater(
                    len(agent.subscriptions),
                    0,
                    f"Enabled agent {agent.name} should have subscriptions"
                )

            # Verify actions are valid
            for action in agent.actions:
                self.assertIsNotNone(action.action_id)
                self.assertIsNotNone(action.name)
                self.assertIsNotNone(action.severity)

    @patch("utils.action_executor.ActionExecutor.run")
    def test_event_simulator_methods(self, mock_executor_run):
        """Test EventSimulator helper methods work correctly."""
        mock_executor_run.return_value = ActionResult.ok(
            message="Simulated command",
            exit_code=0,
            action_id="simulated_action"
        )

        # Track published events
        events_received = []

        def event_tracker(event):
            events_received.append(event.topic)

        # Subscribe to all topics
        topics = [
            "system.storage.low",
            "network.connection.public",
            "network.connection.trusted",
            "system.thermal.throttling",
            "system.thermal.normal",
        ]

        for topic in topics:
            self.event_bus.subscribe(topic, event_tracker)

        # Trigger all simulator methods
        self.simulator.simulate_low_storage()
        self.simulator.simulate_public_wifi()
        self.simulator.simulate_trusted_network()
        self.simulator.simulate_thermal_throttling()
        self.simulator.simulate_thermal_normal()

        # Wait for event propagation
        time.sleep(0.1)

        # Verify all events were published
        for topic in topics:
            self.assertIn(topic, events_received, f"Should receive {topic} event")


if __name__ == "__main__":
    unittest.main()
