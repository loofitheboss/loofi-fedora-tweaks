#!/usr/bin/env python3
"""
Agent Hive Mind Demo — v20.0 EventBus Integration
Demonstrates practical agent implementations responding to system events.

This script shows how agents automatically react to events without UI interaction.
"""
import logging
import time
from pathlib import Path

from utils.agent_scheduler import AgentScheduler
from utils.agents import AgentRegistry
from utils.event_bus import EventBus
from utils.event_simulator import EventSimulator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def main():
    """Run agent demonstration."""
    logger.info("=== Agent Hive Mind Demo - v20.0 ===")

    # Initialize system
    logger.info("Initializing agent framework...")
    registry = AgentRegistry.instance()
    event_bus = EventBus()
    simulator = EventSimulator(event_bus)

    # Load practical agents from JSON definitions
    agents_dir = Path(__file__).parent.parent / "loofi-fedora-tweaks" / "agents"
    loaded_count = registry.load_from_directory(str(agents_dir))
    logger.info(f"Loaded {loaded_count} agent definitions")

    # List loaded agents
    agents = registry.list_agents()
    for agent in agents:
        if agent.enabled:
            logger.info(
                f"  - {agent.name} ({agent.agent_id}): "
                f"subscribes to {', '.join(agent.subscriptions)}"
            )

    # Create scheduler (subscribes agents to events)
    scheduler = AgentScheduler(registry)
    logger.info(f"Scheduler initialized with {scheduler.get_subscribed_agent_count()} subscribed agents")

    # Subscribe to agent completion events
    def log_agent_event(event):
        agent_name = event.data.get('agent_name', 'Unknown')
        success = event.data.get('success', False)
        logger.info(f"[EVENT] Agent '{agent_name}' completed: {'SUCCESS' if success else 'FAILURE'}")

    event_bus.subscribe("agent.event-cleanup.success", log_agent_event)
    event_bus.subscribe("agent.event-security.success", log_agent_event)
    event_bus.subscribe("agent.event-thermal.success", log_agent_event)

    # Demo 1: Low Storage Event
    logger.info("\n--- Demo 1: Low Storage Event ---")
    logger.info("Simulating low storage on / filesystem...")
    simulator.simulate_low_storage(path="/", available_mb=450)
    time.sleep(1.0)  # Wait for agent execution

    state = registry.get_state("event-cleanup")
    logger.info(f"Cleanup agent executed {state.run_count} actions")
    if state.last_result:
        logger.info(f"Last action: {state.last_result.message}")

    # Demo 2: Public Wi-Fi Connection
    logger.info("\n--- Demo 2: Public Wi-Fi Connection ---")
    logger.info("Simulating connection to public Wi-Fi...")
    simulator.simulate_public_wifi(ssid="CoffeeShop_WiFi", security="open")
    time.sleep(1.0)

    state = registry.get_state("event-security")
    logger.info(f"Security agent executed {state.run_count} actions")
    if state.last_result:
        logger.info(f"Last action: {state.last_result.message}")

    # Demo 3: Thermal Throttling
    logger.info("\n--- Demo 3: Thermal Throttling ---")
    logger.info("Simulating CPU thermal throttling at 95°C...")
    simulator.simulate_thermal_throttling(temperature=95, sensor="cpu_thermal")
    time.sleep(1.0)

    state = registry.get_state("event-thermal")
    logger.info(f"Thermal agent executed {state.run_count} actions")
    if state.last_result:
        logger.info(f"Last action: {state.last_result.message}")

    # Demo 4: Return to Normal Temperature
    logger.info("\n--- Demo 4: Temperature Normalized ---")
    logger.info("Simulating return to normal temperature...")
    simulator.simulate_thermal_normal(temperature=65, sensor="cpu_thermal")
    time.sleep(1.0)

    state = registry.get_state("event-thermal")
    logger.info(f"Thermal agent total actions: {state.run_count}")

    # Summary
    logger.info("\n=== Demo Complete ===")
    summary = registry.get_agent_summary()
    logger.info(f"Total agents: {summary['total_agents']}")
    logger.info(f"Enabled: {summary['enabled']}")
    logger.info(f"Total runs: {summary['total_runs']}")

    # Show recent activity
    logger.info("\nRecent Activity:")
    activity = registry.get_recent_activity(limit=5)
    for act in activity:
        logger.info(
            f"  [{act['timestamp']:.0f}] {act['agent_name']}: "
            f"{act['action_id']} - {act['message'][:60]}"
        )

    # Cleanup
    scheduler.shutdown()
    logger.info("\nDemo finished successfully!")


if __name__ == "__main__":
    main()
