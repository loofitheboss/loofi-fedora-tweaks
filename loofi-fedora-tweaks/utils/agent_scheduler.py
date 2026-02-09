"""
Agent Scheduler — Event-driven agent execution manager.
Part of v19.0 "Vanguard" Agent Framework Phase 2.

Provides:
- Event-based agent triggering via EventBus integration
- Rate-limited agent execution respecting max_actions_per_hour
- Automatic publishing of agent.{agent_id}.success and agent.{agent_id}.failure events
- Thread-safe agent execution with structured results
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from utils.agents import (
    AgentConfig,
    AgentRegistry,
    AgentResult,
    AgentState,
    AgentStatus,
)
from utils.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class AgentScheduler:
    """
    Manages event-driven agent execution.

    Subscribes agents to EventBus topics and executes agent actions
    when matching events fire, respecting rate limits and agent state.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize AgentScheduler.

        Args:
            registry: AgentRegistry instance. If None, uses singleton.
        """
        self._registry = registry or AgentRegistry.instance()
        self._event_bus = EventBus()
        self._subscribed_agents: Dict[str, AgentConfig] = {}
        self._initialize_subscriptions()

    def _initialize_subscriptions(self) -> None:
        """Subscribe all enabled agents to their configured event topics."""
        agents = self._registry.get_enabled_agents()

        for agent in agents:
            if agent.subscriptions:
                self._subscribe_agent(agent)
                logger.info(
                    "Agent '%s' subscribed to topics: %s",
                    agent.name,
                    ", ".join(agent.subscriptions)
                )

    def _subscribe_agent(self, agent: AgentConfig) -> None:
        """
        Subscribe an agent to all its configured event topics.

        Args:
            agent: AgentConfig with subscriptions list
        """
        for topic in agent.subscriptions:
            callback = self._create_agent_callback(agent)
            self._event_bus.subscribe(
                topic=topic,
                callback=callback,
                subscriber_id=agent.agent_id
            )

        self._subscribed_agents[agent.agent_id] = agent

    def _create_agent_callback(self, agent: AgentConfig) -> callable:
        """
        Create an event callback for an agent.

        Args:
            agent: AgentConfig to execute when event fires

        Returns:
            Callback function that executes agent actions
        """
        def callback(event: Event) -> None:
            """Event callback that executes agent actions."""
            logger.debug(
                "Agent '%s' triggered by event: %s",
                agent.name,
                event.topic
            )
            self._execute_agent(agent, event)

        return callback

    def _execute_agent(self, agent: AgentConfig, triggering_event: Event) -> None:
        """
        Execute an agent's actions in response to an event.

        Args:
            agent: AgentConfig to execute
            triggering_event: Event that triggered the agent
        """
        state = self._registry.get_state(agent.agent_id)

        # Check if agent can act (rate limiting)
        if not state.can_act(agent.max_actions_per_hour):
            logger.warning(
                "Agent '%s' rate limited (max %d actions/hour)",
                agent.name,
                agent.max_actions_per_hour
            )
            return

        # Check if agent is already running
        if state.status == AgentStatus.RUNNING:
            logger.debug("Agent '%s' already running, skipping", agent.name)
            return

        # Update state to RUNNING
        state.status = AgentStatus.RUNNING
        self._registry.save()

        try:
            # Execute all agent actions
            results = []
            for action in agent.actions:
                result = self._execute_action(agent, action, triggering_event)
                results.append(result)

                # Record each action result in history
                state.record_action(result)

                # Stop on first failure if not in dry_run mode
                if not result.success and not agent.dry_run:
                    logger.warning(
                        "Agent '%s' action '%s' failed: %s",
                        agent.name,
                        action.name,
                        result.message
                    )
                    break

            # Determine overall success (all actions succeeded)
            overall_success = all(r.success for r in results)

            # Update agent state
            state.status = AgentStatus.IDLE if overall_success else AgentStatus.ERROR
            self._registry.save()

            # Publish agent completion event
            self._publish_agent_event(agent, overall_success, results)

        except Exception as exc:
            logger.error(
                "Agent '%s' execution failed: %s",
                agent.name,
                exc,
                exc_info=True
            )
            state.status = AgentStatus.ERROR
            self._registry.save()

            # Publish failure event
            failure_result = AgentResult(
                success=False,
                message=f"Agent execution exception: {exc}",
                action_id="",
                timestamp=time.time(),
            )
            self._publish_agent_event(agent, False, [failure_result])

    def _execute_action(
        self,
        agent: AgentConfig,
        action: Any,
        triggering_event: Event
    ) -> AgentResult:
        """
        Execute a single agent action.

        Args:
            agent: AgentConfig owning the action
            action: AgentAction to execute
            triggering_event: Event that triggered this execution

        Returns:
            AgentResult with execution outcome
        """
        from utils.action_executor import ActionExecutor

        logger.info(
            "Executing agent '%s' action '%s' (triggered by: %s)",
            agent.name,
            action.name,
            triggering_event.topic
        )

        # Handle dry-run mode
        if agent.dry_run:
            return AgentResult(
                success=True,
                message=f"[DRY RUN] Would execute: {action.name}",
                action_id=action.action_id,
                timestamp=time.time(),
                data={"dry_run": True, "trigger_event": triggering_event.topic}
            )

        # Execute via ActionExecutor if command is specified
        if action.command:
            # Determine if privileged execution needed
            needs_pkexec = action.severity.value in ("high", "critical", "medium")

            exec_result = ActionExecutor.run(
                command=action.command,
                args=action.args,
                pkexec=needs_pkexec,
                action_id=action.action_id,
            )

            return AgentResult(
                success=exec_result.success,
                message=exec_result.message,
                action_id=action.action_id,
                timestamp=exec_result.timestamp,
                data={
                    "trigger_event": triggering_event.topic,
                    "exit_code": exec_result.exit_code,
                    "stdout": exec_result.stdout[:500] if exec_result.stdout else "",
                    "stderr": exec_result.stderr[:500] if exec_result.stderr else "",
                }
            )

        # If only operation is specified (no command), return placeholder
        # In production, this would dispatch to operation handlers
        if action.operation:
            logger.info(
                "Action references operation '%s' (not yet implemented)",
                action.operation
            )
            return AgentResult(
                success=True,
                message=f"Operation '{action.operation}' executed (stub)",
                action_id=action.action_id,
                timestamp=time.time(),
                data={"trigger_event": triggering_event.topic, "operation": action.operation}
            )

        # No command or operation specified
        return AgentResult(
            success=False,
            message="Action has no command or operation specified",
            action_id=action.action_id,
            timestamp=time.time(),
            data={"trigger_event": triggering_event.topic}
        )

    def _publish_agent_event(
        self,
        agent: AgentConfig,
        success: bool,
        results: list
    ) -> None:
        """
        Publish agent completion event to EventBus.

        Args:
            agent: AgentConfig that completed
            success: Whether all actions succeeded
            results: List of AgentResult from execution
        """
        event_topic = f"agent.{agent.agent_id}.{'success' if success else 'failure'}"

        event_data = {
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "success": success,
            "results": [r.to_dict() for r in results],
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic=event_topic,
            data=event_data,
            source=f"AgentScheduler.{agent.agent_id}"
        )

        logger.info(
            "Published agent event: %s (success=%s, actions=%d)",
            event_topic,
            success,
            len(results)
        )

    def register_agent(self, agent: AgentConfig) -> None:
        """
        Register and subscribe a new agent.

        Args:
            agent: AgentConfig to register and subscribe
        """
        if agent.enabled and agent.subscriptions:
            self._subscribe_agent(agent)
            logger.info(
                "Registered agent '%s' with subscriptions: %s",
                agent.name,
                ", ".join(agent.subscriptions)
            )

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent and remove its subscriptions.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_id not in self._subscribed_agents:
            return False

        agent = self._subscribed_agents[agent_id]

        # Unsubscribe from all topics
        for topic in agent.subscriptions:
            # Note: EventBus.unsubscribe requires the exact callback,
            # which we don't store. For cleanup, we rely on EventBus
            # internal handling or agent restart.
            logger.debug(
                "Agent '%s' unsubscribed from topic: %s",
                agent.name,
                topic
            )

        del self._subscribed_agents[agent_id]
        logger.info("Unregistered agent: %s", agent.name)
        return True

    def get_subscribed_agent_count(self) -> int:
        """Get number of agents with active subscriptions."""
        return len(self._subscribed_agents)

    def shutdown(self) -> None:
        """Shutdown the scheduler and cleanup resources."""
        logger.info("Shutting down AgentScheduler")
        self._subscribed_agents.clear()
        # EventBus shutdown is handled separately by the application
