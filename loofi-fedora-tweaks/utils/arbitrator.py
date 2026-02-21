"""
Agent Arbitrator - Coordinates resource access across agents.

Provides a small policy layer to prevent background agents from
over-consuming resources when system conditions are constrained.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from services.hardware import TemperatureManager

from utils.log import get_logger
from utils.pulse import PowerState, SystemPulse

logger = get_logger(__name__)


class Priority(Enum):
    CRITICAL = 3  # Security/heat
    USER_INTERACTION = 2  # Gaming/compiling
    BACKGROUND = 1  # Updates/cleanup


@dataclass(frozen=True)
class AgentRequest:
    agent_name: str
    resource: str  # "cpu", "network", "disk", "background_process"
    priority: Priority


class Arbitrator:
    """
    Decide whether an agent request can proceed based on system state.

    Default policy:
    - Block non-critical CPU work when CPU temps exceed thermal limit.
    - Block background work while on battery.
    """

    def __init__(self, cpu_thermal_limit_c: float = 90.0):
        self._cpu_thermal_limit_c = cpu_thermal_limit_c

    def can_proceed(self, request: AgentRequest) -> bool:
        if request.resource == "cpu":
            cpu_temp = self._get_thermal_status()
            if cpu_temp > self._cpu_thermal_limit_c and request.priority != Priority.CRITICAL:
                logger.info(
                    "[Arbitrator] Deny %s CPU request: temp %.1fC > %.1fC",
                    request.agent_name,
                    cpu_temp,
                    self._cpu_thermal_limit_c,
                )
                return False

        if request.resource == "background_process":
            if self._on_battery() and request.priority == Priority.BACKGROUND:
                logger.info(
                    "[Arbitrator] Deny %s background request: on battery",
                    request.agent_name,
                )
                return False

        return True

    @staticmethod
    def _get_thermal_status() -> float:
        sensors = TemperatureManager.get_cpu_temps()
        return _max_temp(sensors)

    @staticmethod
    def _on_battery() -> bool:
        state = SystemPulse.get_power_state()
        return state == PowerState.BATTERY.value


def _max_temp(sensors: Iterable) -> float:
    max_temp = 0.0
    for sensor in sensors:
        try:
            max_temp = max(max_temp, float(sensor.current))
        except (TypeError, ValueError):
            continue
    return max_temp
