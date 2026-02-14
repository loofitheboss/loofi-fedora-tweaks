"""
Temperature Manager - Hardware temperature monitoring via hwmon sysfs interface.
Reads CPU, GPU, disk, and other sensor temperatures from /sys/class/hwmon/.
Part of the v9.2 "Pulse Update".
"""

import glob
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


# Sensor type classification by hwmon device name
_CPU_NAMES = {"coretemp", "k10temp", "zenpower", "cpu_thermal"}
_GPU_NAMES = {"amdgpu", "nouveau", "nvidia", "radeon"}
_DISK_NAMES = {"nvme", "drivetemp"}


@dataclass
class TemperatureSensor:
    """A single temperature reading from a hardware sensor."""

    name: str  # hwmon device name, e.g. "coretemp", "amdgpu", "nvme0"
    label: str  # Human-readable label, e.g. "Core 0", "GPU Edge", "Composite"
    current: float  # Current temperature in Celsius
    high: float  # High threshold in Celsius (0 if unknown)
    critical: float  # Critical threshold in Celsius (0 if unknown)
    sensor_type: str  # One of "cpu", "gpu", "disk", "other"


def _classify_sensor(hwmon_name: str) -> str:
    """
    Classify a hwmon device name into a sensor type category.

    Args:
        hwmon_name: The name read from the hwmon device's ``name`` file.

    Returns:
        One of ``"cpu"``, ``"gpu"``, ``"disk"``, or ``"other"``.
    """
    lower = hwmon_name.lower()
    if lower in _CPU_NAMES:
        return "cpu"
    if lower in _GPU_NAMES:
        return "gpu"
    if lower in _DISK_NAMES:
        return "disk"
    return "other"


def _read_sysfs_value(path: str) -> Optional[str]:
    """
    Read a single-line value from a sysfs file.

    Args:
        path: Absolute path to the sysfs file.

    Returns:
        The stripped file contents, or ``None`` on any error.
    """
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.debug("Failed to read sysfs value from %s: %s", path, e)
        return None


def _read_millidegree(path: str) -> float:
    """
    Read a millidegree Celsius value from sysfs and convert to degrees.

    Sysfs temperature files store values in millidegrees (e.g. 45000 = 45.0 C).

    Args:
        path: Absolute path to a ``temp*_input``, ``temp*_max``, or ``temp*_crit`` file.

    Returns:
        Temperature in degrees Celsius, or ``0.0`` on any error.
    """
    raw = _read_sysfs_value(path)
    if raw is None:
        return 0.0
    try:
        return int(raw) / 1000.0
    except (ValueError, TypeError):
        return 0.0


class TemperatureManager:
    """
    Reads hardware temperatures from the Linux hwmon sysfs interface.

    The hwmon subsystem exposes sensor data under ``/sys/class/hwmon/hwmon*/``.
    Each device directory contains:
    - ``name`` -- the driver/device name (e.g. "coretemp", "amdgpu")
    - ``temp*_input`` -- current temperature in millidegrees Celsius
    - ``temp*_label`` -- human-readable label (optional)
    - ``temp*_max`` -- high threshold in millidegrees (optional)
    - ``temp*_crit`` -- critical threshold in millidegrees (optional)

    All methods are static and return safe defaults (empty lists, None) on error
    so callers never need to handle exceptions.
    """

    HWMON_BASE = "/sys/class/hwmon"

    @staticmethod
    def get_all_sensors() -> List[TemperatureSensor]:
        """
        Read all available temperature sensors from the hwmon sysfs interface.

        Scans every ``/sys/class/hwmon/hwmon*`` directory for ``temp*_input``
        files and builds a TemperatureSensor for each one found.

        Returns:
            A list of TemperatureSensor objects. Returns an empty list if no
            sensors are found or on any error.
        """
        sensors: List[TemperatureSensor] = []

        try:
            hwmon_dirs = glob.glob(
                os.path.join(TemperatureManager.HWMON_BASE, "hwmon*")
            )
        except Exception as e:
            logger.debug("Failed to glob hwmon directories: %s", e)
            return sensors

        for hwmon_dir in sorted(hwmon_dirs):
            # Read the device name
            hwmon_name = _read_sysfs_value(os.path.join(hwmon_dir, "name"))
            if hwmon_name is None:
                continue

            sensor_type = _classify_sensor(hwmon_name)

            # Find all temp*_input files in this hwmon device
            try:
                input_files = glob.glob(os.path.join(hwmon_dir, "temp*_input"))
            except Exception as e:
                logger.debug("Failed to glob temp input files in %s: %s", hwmon_dir, e)
                continue

            for input_path in sorted(input_files):
                # Extract the index prefix, e.g. "temp1" from "temp1_input"
                basename = os.path.basename(input_path)
                prefix = basename.replace("_input", "")  # e.g. "temp1"

                # Read the current temperature
                current = _read_millidegree(input_path)

                # Read the optional label (falls back to hwmon name + index)
                label_path = os.path.join(hwmon_dir, f"{prefix}_label")
                label = _read_sysfs_value(label_path)
                if label is None:
                    label = f"{hwmon_name} {prefix}"

                # Read optional thresholds
                high = _read_millidegree(os.path.join(hwmon_dir, f"{prefix}_max"))
                critical = _read_millidegree(os.path.join(hwmon_dir, f"{prefix}_crit"))

                sensors.append(
                    TemperatureSensor(
                        name=hwmon_name,
                        label=label,
                        current=current,
                        high=high,
                        critical=critical,
                        sensor_type=sensor_type,
                    )
                )

        return sensors

    @staticmethod
    def get_cpu_temps() -> List[TemperatureSensor]:
        """
        Get temperature readings for CPU sensors only.

        Filters sensors whose hwmon name matches known CPU drivers:
        coretemp (Intel), k10temp (AMD), zenpower, cpu_thermal (ARM/SoC).

        Returns:
            A list of CPU TemperatureSensor objects.
        """
        return [
            s for s in TemperatureManager.get_all_sensors() if s.sensor_type == "cpu"
        ]

    @staticmethod
    def get_gpu_temps() -> List[TemperatureSensor]:
        """
        Get temperature readings for GPU sensors only.

        Filters sensors whose hwmon name matches known GPU drivers:
        amdgpu, nouveau, nvidia, radeon.

        Returns:
            A list of GPU TemperatureSensor objects.
        """
        return [
            s for s in TemperatureManager.get_all_sensors() if s.sensor_type == "gpu"
        ]

    @staticmethod
    def get_disk_temps() -> List[TemperatureSensor]:
        """
        Get temperature readings for disk/NVMe sensors only.

        Filters sensors whose hwmon name matches known disk drivers:
        nvme, drivetemp.

        Returns:
            A list of disk TemperatureSensor objects.
        """
        return [
            s for s in TemperatureManager.get_all_sensors() if s.sensor_type == "disk"
        ]

    @staticmethod
    def get_hottest() -> Optional[TemperatureSensor]:
        """
        Return the sensor with the highest current temperature.

        Returns:
            The TemperatureSensor with the highest ``current`` value,
            or ``None`` if no sensors are available.
        """
        sensors = TemperatureManager.get_all_sensors()
        if not sensors:
            return None
        return max(sensors, key=lambda s: s.current)

    @staticmethod
    def get_health_status() -> Tuple[str, str]:
        """
        Evaluate overall thermal health based on all sensor readings.

        Compares each sensor's current temperature against its thresholds:
        - **critical**: any sensor at or above its critical threshold.
        - **warning**: any sensor at or above its high threshold.
        - **ok**: all sensors are below their thresholds.

        When a sensor has no defined threshold (value is 0), it is skipped
        for that threshold check.

        Returns:
            A tuple of ``(level, message)`` where *level* is one of
            ``"ok"``, ``"warning"``, or ``"critical"``, and *message*
            is a human-readable description.
        """
        sensors = TemperatureManager.get_all_sensors()

        if not sensors:
            return ("ok", "No temperature sensors detected")

        critical_sensors: List[str] = []
        warning_sensors: List[str] = []

        for sensor in sensors:
            # Check critical threshold first
            if sensor.critical > 0 and sensor.current >= sensor.critical:
                critical_sensors.append(
                    f"{sensor.label}: {sensor.current:.0f}C (critical: {sensor.critical:.0f}C)"
                )
            # Then check high threshold
            elif sensor.high > 0 and sensor.current >= sensor.high:
                warning_sensors.append(
                    f"{sensor.label}: {sensor.current:.0f}C (high: {sensor.high:.0f}C)"
                )

        if critical_sensors:
            return (
                "critical",
                f"Critical temperature on: {', '.join(critical_sensors)}",
            )

        if warning_sensors:
            return (
                "warning",
                f"High temperature on: {', '.join(warning_sensors)}",
            )

        # Find the hottest sensor for the status message
        hottest = max(sensors, key=lambda s: s.current)
        return (
            "ok",
            f"All temperatures normal (hottest: {hottest.label} at {hottest.current:.0f}C)",
        )
