"""
Unit tests for Agent Framework EventBus integration.
Tests event-driven agent execution, subscriptions, and rate limiting.
"""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "loofi-fedora-tweaks"))

from utils.agents import (
    AgentAction,
    AgentConfig,
    AgentRegistry,
    AgentResult,
    AgentState,
    AgentStatus,
    AgentTrigger,
    AgentType,
    ActionSeverity,
    TriggerType,
)
from utils.agent_scheduler import AgentScheduler
from utils.event_bus import Event, EventBus


class TestAgentEventIntegration(unittest.TestCase):
    """Test EventBus integration with Agent Framework."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singletons
        AgentRegistry.reset()
        EventBus._instance = None

        self.registry = AgentRegistry.instance()

        # Clear built-in agents for clean testing
        self.registry._agents.clear()
        self.registry._states.clear()

        self.event_bus = EventBus()
        self.event_bus.clear()  # Clear any existing subscriptions

        self.scheduler = AgentScheduler(registry=self.registry)

    def tearDown(self):
        """Clean up after tests."""
        AgentRegistry.reset()
        EventBus._instance = None

    def test_agent_config_includes_subscriptions(self):
        """Test that AgentConfig includes subscriptions field."""
        config = AgentConfig(
            agent_id="test-001",
            name="Test Agent",
            agent_type=AgentType.CUSTOM,
            description="Test agent with subscriptions",
            subscriptions=["system.power.battery", "agent.*.success"]
        )

        self.assertEqual(len(config.subscriptions), 2)
        self.assertIn("system.power.battery", config.subscriptions)
        self.assertIn("agent.*.success", config.subscriptions)

    def test_agent_config_to_dict_includes_subscriptions(self):
        """Test that to_dict() includes subscriptions."""
        config = AgentConfig(
            agent_id="test-002",
            name="Dict Test Agent",
            agent_type=AgentType.CUSTOM,
            description="Test serialization",
            subscriptions=["test.topic"]
        )

        data = config.to_dict()
        self.assertIn("subscriptions", data)
        self.assertEqual(data["subscriptions"], ["test.topic"])

    def test_agent_config_from_dict_includes_subscriptions(self):
        """Test that from_dict() deserializes subscriptions."""
        data = {
            "agent_id": "test-003",
            "name": "FromDict Test",
            "agent_type": "custom",
            "description": "Test deserialization",
            "subscriptions": ["topic.a", "topic.b"]
        }

        config = AgentConfig.from_dict(data)
        self.assertEqual(len(config.subscriptions), 2)
        self.assertIn("topic.a", config.subscriptions)
        self.assertIn("topic.b", config.subscriptions)

    def test_agent_subscribes_to_events_on_registration(self):
        """Test that agents subscribe to EventBus topics when registered."""
        config = AgentConfig(
            agent_id="test-004",
            name="Event Subscriber",
            agent_type=AgentType.CUSTOM,
            description="Subscribes to events",
            enabled=True,
            subscriptions=["system.test.event"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Test Action",
                    description="Test action",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        # Register agent
        self.registry.register_agent(config)

        # Create new scheduler (will auto-subscribe enabled agents)
        scheduler = AgentScheduler(registry=self.registry)

        # Verify agent is subscribed
        self.assertEqual(scheduler.get_subscribed_agent_count(), 1)

    @patch('utils.agent_scheduler.AgentScheduler._execute_action')
    def test_event_triggers_agent_execution(self, mock_execute):
        """Test that publishing an event triggers agent execution."""
        # Configure mock to return success
        mock_execute.return_value = AgentResult(
            success=True,
            message="Action executed",
            action_id="action1"
        )

        # Create agent with subscription
        config = AgentConfig(
            agent_id="test-005",
            name="Event Triggered Agent",
            agent_type=AgentType.CUSTOM,
            description="Gets triggered by event",
            enabled=True,
            subscriptions=["test.trigger.event"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Triggered Action",
                    description="Runs on event",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        self.registry.register_agent(config)
        scheduler = AgentScheduler(registry=self.registry)

        # Publish event
        self.event_bus.publish(
            topic="test.trigger.event",
            data={"test": "data"},
            source="test"
        )

        # Wait for async execution
        time.sleep(0.1)

        # Verify action was executed
        mock_execute.assert_called_once()

    def test_rate_limiting_prevents_spam(self):
        """Test that rate limiting prevents excessive agent executions."""
        # Create agent with strict rate limit
        config = AgentConfig(
            agent_id="test-006",
            name="Rate Limited Agent",
            agent_type=AgentType.CUSTOM,
            description="Has strict rate limit",
            enabled=True,
            max_actions_per_hour=2,
            subscriptions=["test.spam.event"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Limited Action",
                    description="Rate limited",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        self.registry.register_agent(config)

        # Get agent state and set it to near limit
        state = self.registry.get_state(config.agent_id)
        state.actions_this_hour = 2  # At limit
        state.hour_window_start = time.time()

        scheduler = AgentScheduler(registry=self.registry)

        # Publish event that would trigger agent
        with patch.object(scheduler, '_execute_action') as mock_execute:
            self.event_bus.publish(
                topic="test.spam.event",
                data={},
                source="test"
            )

            # Wait for async processing
            time.sleep(0.1)

            # Action should NOT be executed due to rate limit
            mock_execute.assert_not_called()

    def test_agent_success_event_published(self):
        """Test that successful agent execution publishes success event."""
        event_captured = []

        def capture_event(event: Event):
            event_captured.append(event)

        # Subscribe to agent success events
        self.event_bus.subscribe(
            topic="agent.test-007.success",
            callback=capture_event,
            subscriber_id="test_listener"
        )

        # Create agent
        config = AgentConfig(
            agent_id="test-007",
            name="Success Publisher",
            agent_type=AgentType.CUSTOM,
            description="Publishes success event",
            enabled=True,
            subscriptions=["test.trigger"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Success Action",
                    description="Always succeeds",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        self.registry.register_agent(config)
        scheduler = AgentScheduler(registry=self.registry)

        # Mock action execution to return success
        with patch.object(scheduler, '_execute_action') as mock_execute:
            mock_execute.return_value = AgentResult(
                success=True,
                message="Success",
                action_id="action1"
            )

            # Trigger agent
            self.event_bus.publish(
                topic="test.trigger",
                data={},
                source="test"
            )

            # Wait for async processing
            time.sleep(0.2)

            # Verify success event was published
            self.assertEqual(len(event_captured), 1)
            self.assertEqual(event_captured[0].topic, "agent.test-007.success")
            self.assertTrue(event_captured[0].data["success"])

    def test_agent_failure_event_published(self):
        """Test that failed agent execution publishes failure event."""
        event_captured = []

        def capture_event(event: Event):
            event_captured.append(event)

        # Subscribe to agent failure events
        self.event_bus.subscribe(
            topic="agent.test-008.failure",
            callback=capture_event,
            subscriber_id="test_listener"
        )

        # Create agent
        config = AgentConfig(
            agent_id="test-008",
            name="Failure Publisher",
            agent_type=AgentType.CUSTOM,
            description="Publishes failure event",
            enabled=True,
            subscriptions=["test.trigger.fail"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Failing Action",
                    description="Always fails",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        self.registry.register_agent(config)
        scheduler = AgentScheduler(registry=self.registry)

        # Mock action execution to return failure
        with patch.object(scheduler, '_execute_action') as mock_execute:
            mock_execute.return_value = AgentResult(
                success=False,
                message="Action failed",
                action_id="action1"
            )

            # Trigger agent
            self.event_bus.publish(
                topic="test.trigger.fail",
                data={},
                source="test"
            )

            # Wait for async processing
            time.sleep(0.2)

            # Verify failure event was published
            self.assertEqual(len(event_captured), 1)
            self.assertEqual(event_captured[0].topic, "agent.test-008.failure")
            self.assertFalse(event_captured[0].data["success"])

    def test_multiple_agents_subscribe_to_same_event(self):
        """Test that multiple agents can subscribe to the same event."""
        # Create two agents subscribing to same event
        config1 = AgentConfig(
            agent_id="test-009a",
            name="Agent A",
            agent_type=AgentType.CUSTOM,
            description="First agent",
            enabled=True,
            subscriptions=["shared.event"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Action A",
                    description="Action for agent A",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        config2 = AgentConfig(
            agent_id="test-009b",
            name="Agent B",
            agent_type=AgentType.CUSTOM,
            description="Second agent",
            enabled=True,
            subscriptions=["shared.event"],
            actions=[
                AgentAction(
                    action_id="action2",
                    name="Action B",
                    description="Action for agent B",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        self.registry.register_agent(config1)
        self.registry.register_agent(config2)

        scheduler = AgentScheduler(registry=self.registry)

        # Both agents should be subscribed
        self.assertEqual(scheduler.get_subscribed_agent_count(), 2)

        # Publish shared event
        with patch.object(scheduler, '_execute_action') as mock_execute:
            mock_execute.return_value = AgentResult(
                success=True,
                message="Executed",
                action_id="action1"
            )

            self.event_bus.publish(
                topic="shared.event",
                data={},
                source="test"
            )

            # Wait for async processing
            time.sleep(0.2)

            # Both agents should have executed (2 calls)
            self.assertEqual(mock_execute.call_count, 2)

    def test_disabled_agent_not_subscribed(self):
        """Test that disabled agents don't subscribe to events."""
        config = AgentConfig(
            agent_id="test-010",
            name="Disabled Agent",
            agent_type=AgentType.CUSTOM,
            description="Should not subscribe",
            enabled=False,  # Disabled
            subscriptions=["test.event"],
            actions=[
                AgentAction(
                    action_id="action1",
                    name="Should Not Run",
                    description="Disabled",
                    severity=ActionSeverity.INFO
                )
            ]
        )

        self.registry.register_agent(config)
        scheduler = AgentScheduler(registry=self.registry)

        # No agents should be subscribed (agent is disabled)
        self.assertEqual(scheduler.get_subscribed_agent_count(), 0)


if __name__ == "__main__":
    unittest.main()
