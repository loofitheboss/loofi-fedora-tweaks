"""
Event Simulator — Testing utility for event-driven agent behavior.
Part of v20.0 "Agent Hive Mind" integration testing.

Provides helper methods to manually trigger system events for testing
agent reactions without requiring actual system state changes.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from utils.event_bus import EventBus

logger = logging.getLogger(__name__)


class EventSimulator:
    """
    Utility class for simulating system events in testing environments.

    Publishes standardized events to the EventBus to trigger agent reactions
    without requiring actual system changes (battery discharge, network changes, etc.).
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize EventSimulator.

        Args:
            event_bus: EventBus instance to publish to. If None, uses singleton.
        """
        self._event_bus = event_bus or EventBus()

    def simulate_low_storage(
        self,
        path: str = "/",
        available_mb: int = 500,
        threshold_mb: int = 1000
    ) -> None:
        """
        Simulate low storage space event.

        Args:
            path: Filesystem path with low space
            available_mb: Available space in MB
            threshold_mb: Threshold that triggered the alert
        """
        data = {
            "path": path,
            "available_mb": available_mb,
            "threshold_mb": threshold_mb,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="system.storage.low",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated low storage event: %s (%dMB available)",
            path,
            available_mb
        )

    def simulate_public_wifi(
        self,
        ssid: str = "PublicWiFi",
        security: str = "open",
        interface: str = "wlan0"
    ) -> None:
        """
        Simulate connection to public Wi-Fi network.

        Args:
            ssid: Network SSID
            security: Security type (open, wpa2, wpa3, etc.)
            interface: Network interface name
        """
        data = {
            "ssid": ssid,
            "security": security,
            "interface": interface,
            "is_public": True,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="network.connection.public",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated public Wi-Fi connection: %s (%s)",
            ssid,
            security
        )

    def simulate_trusted_network(
        self,
        ssid: str = "HomeNetwork",
        security: str = "wpa3",
        interface: str = "wlan0"
    ) -> None:
        """
        Simulate connection to trusted network.

        Args:
            ssid: Network SSID
            security: Security type
            interface: Network interface name
        """
        data = {
            "ssid": ssid,
            "security": security,
            "interface": interface,
            "is_public": False,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="network.connection.trusted",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated trusted network connection: %s",
            ssid
        )

    def simulate_thermal_throttling(
        self,
        temperature: int = 95,
        sensor: str = "cpu_thermal",
        threshold: int = 90
    ) -> None:
        """
        Simulate CPU thermal throttling event.

        Args:
            temperature: Current temperature in Celsius
            sensor: Thermal sensor name
            threshold: Temperature threshold for throttling
        """
        data = {
            "temperature": temperature,
            "sensor": sensor,
            "threshold": threshold,
            "throttling": True,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="system.thermal.throttling",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated thermal throttling: %d°C on %s",
            temperature,
            sensor
        )

    def simulate_thermal_normal(
        self,
        temperature: int = 65,
        sensor: str = "cpu_thermal",
        threshold: int = 90
    ) -> None:
        """
        Simulate return to normal thermal state.

        Args:
            temperature: Current temperature in Celsius
            sensor: Thermal sensor name
            threshold: Temperature threshold for throttling
        """
        data = {
            "temperature": temperature,
            "sensor": sensor,
            "threshold": threshold,
            "throttling": False,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="system.thermal.normal",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated thermal normal: %d°C on %s",
            temperature,
            sensor
        )

    def simulate_battery_low(
        self,
        level: int = 15,
        status: str = "discharging",
        threshold: int = 20
    ) -> None:
        """
        Simulate low battery event.

        Args:
            level: Battery level percentage
            status: Battery status (charging, discharging, full)
            threshold: Low battery threshold
        """
        data = {
            "level": level,
            "status": status,
            "threshold": threshold,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="system.power.battery",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated low battery event: %d%% (%s)",
            level,
            status
        )

    def simulate_firewall_panic(
        self,
        source: str = "192.168.1.100",
        reason: str = "port_scan_detected"
    ) -> None:
        """
        Simulate firewall panic mode trigger.

        Args:
            source: Source IP or identifier
            reason: Reason for panic mode
        """
        data = {
            "source": source,
            "reason": reason,
            "timestamp": time.time(),
        }

        self._event_bus.publish(
            topic="security.firewall.panic",
            data=data,
            source="EventSimulator"
        )

        logger.info(
            "Simulated firewall panic: %s from %s",
            reason,
            source
        )

    def simulate_custom_event(
        self,
        topic: str,
        data: Dict[str, Any],
        source: str = "EventSimulator"
    ) -> None:
        """
        Simulate a custom event with arbitrary topic and data.

        Args:
            topic: Event topic string
            data: Event data dictionary
            source: Source identifier for the event
        """
        self._event_bus.publish(
            topic=topic,
            data=data,
            source=source
        )

        logger.info("Simulated custom event: %s", topic)
