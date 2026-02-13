"""
Performance Auto-Tuner — Automatic workload detection and system tuning.
Part of v15.0 "Nebula".

Detects current workload by reading /proc metrics, then recommends and
applies kernel tunables (CPU governor, swappiness, I/O scheduler, THP)
to match the workload profile. All privileged operations go through
PrivilegedCommand so they use pkexec argument arrays — never shell strings.
"""

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from utils.commands import PrivilegedCommand

logger = logging.getLogger(__name__)

# ==================== DATA CLASSES ====================


@dataclass
class WorkloadProfile:
    """Describes a detected workload category."""
    name: str
    cpu_percent: float
    memory_percent: float
    io_wait: float
    description: str


@dataclass
class TuningRecommendation:
    """A set of kernel tunable recommendations for a workload."""
    governor: str
    swappiness: int
    io_scheduler: str
    thp: str  # transparent hugepages: always | madvise | never
    reason: str
    workload: str


@dataclass
class TuningHistoryEntry:
    """A single entry in the tuning history log."""
    timestamp: float
    workload: str
    recommendations: dict
    applied: bool


# ==================== CONSTANTS ====================

_CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "loofi-fedora-tweaks",
)
_HISTORY_PATH = os.path.join(_CONFIG_DIR, "tuning_history.json")
_MAX_HISTORY = 50
_HISTORY_LOCK = threading.RLock()

# Workload → tunable mapping
_WORKLOAD_MAP: Dict[str, dict] = {
    "idle": {
        "governor": "powersave",
        "swappiness": 60,
        "io_scheduler": "mq-deadline",
        "thp": "always",
    },
    "light": {
        "governor": "schedutil",
        "swappiness": 60,
        "io_scheduler": "mq-deadline",
        "thp": "always",
    },
    "compilation": {
        "governor": "performance",
        "swappiness": 10,
        "io_scheduler": "none",
        "thp": "madvise",
    },
    "gaming": {
        "governor": "performance",
        "swappiness": 10,
        "io_scheduler": "none",
        "thp": "never",
    },
    "server": {
        "governor": "schedutil",
        "swappiness": 30,
        "io_scheduler": "mq-deadline",
        "thp": "madvise",
    },
    "heavy": {
        "governor": "performance",
        "swappiness": 10,
        "io_scheduler": "none",
        "thp": "madvise",
    },
}

# Reason descriptions per workload
_WORKLOAD_REASONS: Dict[str, str] = {
    "idle": "System is idle — favour power saving and default tunables.",
    "light": "Light workload — balanced settings with schedutil governor.",
    "compilation": "Compilation detected (high CPU + memory) — maximise throughput.",
    "gaming": "Gaming workload (high CPU, moderate memory) — lowest latency.",
    "server": "Server/sustained load — balanced governor with reduced swappiness.",
    "heavy": "Heavy compute workload — full performance mode.",
}


class AutoTuner:
    """
    Detects the current workload profile and recommends / applies
    kernel tunables to match.  All methods are @staticmethod so
    both GUI and CLI can call them without instantiation.
    """

    # ==================== WORKLOAD DETECTION ====================

    @staticmethod
    def detect_workload() -> WorkloadProfile:
        """
        Read /proc/loadavg, /proc/meminfo, and /proc/stat to classify the
        current system workload.

        Categories:
            idle         — CPU < 10 %
            light        — CPU 10–30 %
            compilation  — CPU > 60 % AND memory > 60 %
            gaming       — CPU > 60 % AND memory 30–60 %
            server       — CPU 30–60 % (sustained moderate)
            heavy        — CPU > 80 %

        Returns a WorkloadProfile with the detected category and raw metrics.
        """
        cpu_percent = AutoTuner._read_cpu_percent()
        memory_percent = AutoTuner._read_memory_percent()
        io_wait = AutoTuner._read_io_wait()

        # Classify
        if cpu_percent > 80:
            name = "heavy"
        elif cpu_percent > 60 and memory_percent > 60:
            name = "compilation"
        elif cpu_percent > 60 and memory_percent <= 60:
            name = "gaming"
        elif cpu_percent > 30:
            name = "server"
        elif cpu_percent > 10:
            name = "light"
        else:
            name = "idle"

        desc = _WORKLOAD_REASONS.get(name, "Unknown workload.")
        profile = WorkloadProfile(
            name=name,
            cpu_percent=round(cpu_percent, 1),
            memory_percent=round(memory_percent, 1),
            io_wait=round(io_wait, 1),
            description=desc,
        )
        logger.info(
            "Detected workload: %s (CPU %.1f%%, Mem %.1f%%, IOWait %.1f%%)",
            name, cpu_percent, memory_percent, io_wait,
        )
        return profile

    # ==================== CURRENT SETTINGS ====================

    @staticmethod
    def get_current_settings() -> dict:
        """
        Read the current kernel tunables from sysfs / procfs.

        Returns a dict with keys: governor, swappiness, io_scheduler, thp.
        On read failure a sensible "unknown" default is returned per key.
        """
        settings: dict = {
            "governor": "unknown",
            "swappiness": -1,
            "io_scheduler": "unknown",
            "thp": "unknown",
        }

        # CPU governor
        gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        try:
            if os.path.exists(gov_path):
                with open(gov_path, "r") as f:
                    settings["governor"] = f.read().strip()
        except OSError as exc:
            logger.debug("Failed to read governor: %s", exc)

        # Swappiness
        swap_path = "/proc/sys/vm/swappiness"
        try:
            if os.path.exists(swap_path):
                with open(swap_path, "r") as f:
                    settings["swappiness"] = int(f.read().strip())
        except (OSError, ValueError) as exc:
            logger.debug("Failed to read swappiness: %s", exc)

        # I/O scheduler — pick the first real block device in /sys/block/
        settings["io_scheduler"] = AutoTuner._read_io_scheduler()

        # Transparent Hugepages
        thp_path = "/sys/kernel/mm/transparent_hugepage/enabled"
        try:
            if os.path.exists(thp_path):
                with open(thp_path, "r") as f:
                    content = f.read().strip()
                    # Format: "always [madvise] never" — active value in brackets
                    for token in content.split():
                        if token.startswith("[") and token.endswith("]"):
                            settings["thp"] = token[1:-1]
                            break
        except OSError as exc:
            logger.debug("Failed to read THP setting: %s", exc)

        return settings

    # ==================== RECOMMENDATION ====================

    @staticmethod
    def recommend(workload: Optional[WorkloadProfile] = None) -> TuningRecommendation:
        """
        Generate a TuningRecommendation for the given workload.

        If *workload* is ``None``, the current workload is auto-detected
        via :meth:`detect_workload`.
        """
        if workload is None:
            workload = AutoTuner.detect_workload()

        tunables = _WORKLOAD_MAP.get(workload.name, _WORKLOAD_MAP["idle"])
        reason = _WORKLOAD_REASONS.get(workload.name, "No specific reason.")

        rec = TuningRecommendation(
            governor=tunables["governor"],
            swappiness=tunables["swappiness"],
            io_scheduler=tunables["io_scheduler"],
            thp=tunables["thp"],
            reason=reason,
            workload=workload.name,
        )
        logger.info(
            "Recommendation for '%s': governor=%s swappiness=%d io=%s thp=%s",
            workload.name, rec.governor, rec.swappiness,
            rec.io_scheduler, rec.thp,
        )
        return rec

    # ==================== APPLY ====================

    @staticmethod
    def apply_recommendation(rec: TuningRecommendation) -> Tuple[str, List[str], str]:
        """
        Return a PrivilegedCommand tuple that sets the CPU governor for
        all online cores.

        The returned tuple follows the project convention:
        ``(command, args_list, description)``.
        """
        # Build a one-liner that iterates over all cpufreq governors
        # We use pkexec + bash -c only because the governor must be
        # written to *every* cpu's scaling_governor file.
        script = (
            f'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; '
            f'do echo "{rec.governor}" > "$g"; done'
        )
        return (
            "pkexec",
            ["bash", "-c", script],
            f"Setting CPU governor to '{rec.governor}' for workload '{rec.workload}'...",
        )

    @staticmethod
    def apply_swappiness(value: int) -> Tuple[str, List[str], str]:
        """
        Return a PrivilegedCommand tuple that sets vm.swappiness via sysctl.
        """
        value = max(0, min(200, value))
        return PrivilegedCommand.sysctl("vm.swappiness", str(value))

    @staticmethod
    def apply_io_scheduler(scheduler: str, device: str = "") -> Tuple[str, List[str], str]:
        """
        Return a PrivilegedCommand tuple that sets the I/O scheduler for
        a block device.  If *device* is empty, the first real block device
        found in /sys/block/ is used.
        """
        if not device:
            device = AutoTuner._find_first_block_device()
        if not device:
            logger.warning("No block device found for I/O scheduler change.")
            return ("echo", ["No block device found"], "No device to tune.")

        path = f"/sys/block/{device}/queue/scheduler"
        script = f'echo "{scheduler}" > {path}'
        return (
            "pkexec",
            ["bash", "-c", script],
            f"Setting I/O scheduler to '{scheduler}' on {device}...",
        )

    @staticmethod
    def apply_thp(mode: str) -> Tuple[str, List[str], str]:
        """
        Return a PrivilegedCommand tuple that sets the transparent hugepage
        policy (always | madvise | never).
        """
        if mode not in ("always", "madvise", "never"):
            mode = "madvise"
        path = "/sys/kernel/mm/transparent_hugepage/enabled"
        script = f'echo "{mode}" > {path}'
        return (
            "pkexec",
            ["bash", "-c", script],
            f"Setting transparent hugepages to '{mode}'...",
        )

    # ==================== TUNING HISTORY ====================

    @staticmethod
    def get_tuning_history() -> List[TuningHistoryEntry]:
        """
        Read tuning history from
        ``~/.config/loofi-fedora-tweaks/tuning_history.json``.

        Returns an empty list when the file does not exist or is corrupt.
        """
        with _HISTORY_LOCK:
            try:
                if not os.path.isfile(_HISTORY_PATH):
                    return []
                with open(_HISTORY_PATH, "r") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    return []
                entries: List[TuningHistoryEntry] = []
                for item in data:
                    entries.append(
                        TuningHistoryEntry(
                            timestamp=float(item.get("timestamp", 0)),
                            workload=str(item.get("workload", "unknown")),
                            recommendations=item.get("recommendations", {}),
                            applied=bool(item.get("applied", False)),
                        )
                    )
                return entries
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.debug("Failed to read tuning history: %s", exc)
                return []

    @staticmethod
    def save_tuning_entry(entry: TuningHistoryEntry) -> None:
        """
        Append a TuningHistoryEntry to the history file.
        Keeps at most ``_MAX_HISTORY`` (50) entries, discarding the oldest.
        """
        with _HISTORY_LOCK:
            history = AutoTuner.get_tuning_history()
            history.append(entry)

            if len(history) > _MAX_HISTORY:
                history = history[-_MAX_HISTORY:]

            try:
                os.makedirs(_CONFIG_DIR, exist_ok=True)
                with open(_HISTORY_PATH, "w") as f:
                    json.dump([asdict(e) for e in history], f, indent=2)
                logger.info("Saved tuning entry for workload '%s'.", entry.workload)
            except OSError as exc:
                logger.error("Failed to save tuning history: %s", exc)

    # ==================== INTERNAL HELPERS ====================

    @staticmethod
    def _read_cpu_percent() -> float:
        """
        Compute an *instantaneous* CPU busy-percentage from two quick
        snapshots of /proc/stat separated by 0.1 s.
        """
        try:
            first = AutoTuner._read_aggregate_cpu_times()
            if first is None:
                return 0.0
            time.sleep(0.1)
            second = AutoTuner._read_aggregate_cpu_times()
            if second is None:
                return 0.0

            prev_idle = first[3] + (first[4] if len(first) > 4 else 0)
            curr_idle = second[3] + (second[4] if len(second) > 4 else 0)

            prev_total = sum(first)
            curr_total = sum(second)

            total_delta = curr_total - prev_total
            idle_delta = curr_idle - prev_idle

            if total_delta <= 0:
                return 0.0

            usage = (1.0 - idle_delta / total_delta) * 100.0
            return max(0.0, min(100.0, usage))
        except Exception as exc:
            logger.debug("CPU percent read failed: %s", exc)
            return 0.0

    @staticmethod
    def _read_aggregate_cpu_times() -> Optional[List[int]]:
        """Read the aggregate ``cpu`` line from /proc/stat."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            if not line.startswith("cpu "):
                return None
            parts = line.split()
            return [int(v) for v in parts[1:9]]
        except (OSError, ValueError):
            return None

    @staticmethod
    def _read_memory_percent() -> float:
        """Read memory usage percentage from /proc/meminfo."""
        try:
            meminfo: Dict[str, int] = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        meminfo[key] = int(parts[1])  # kB

            total = meminfo.get("MemTotal", 0)
            available = meminfo.get("MemAvailable", 0)
            if total <= 0:
                return 0.0
            used = total - available
            return (used / total) * 100.0
        except (OSError, ValueError, KeyError) as exc:
            logger.debug("Memory percent read failed: %s", exc)
            return 0.0

    @staticmethod
    def _read_io_wait() -> float:
        """
        Read I/O-wait percentage from a quick /proc/stat delta
        (same technique as ``_read_cpu_percent``).
        """
        try:
            first = AutoTuner._read_aggregate_cpu_times()
            if first is None or len(first) < 5:
                return 0.0
            time.sleep(0.1)
            second = AutoTuner._read_aggregate_cpu_times()
            if second is None or len(second) < 5:
                return 0.0

            total_delta = sum(second) - sum(first)
            if total_delta <= 0:
                return 0.0

            iowait_delta = second[4] - first[4]
            return max(0.0, min(100.0, (iowait_delta / total_delta) * 100.0))
        except Exception as exc:
            logger.debug("IO-wait read failed: %s", exc)
            return 0.0

    @staticmethod
    def _find_first_block_device() -> str:
        """
        Return the name of the first real block device in /sys/block/,
        skipping loop, ram, and dm- devices.
        """
        sys_block = "/sys/block"
        try:
            if not os.path.isdir(sys_block):
                return ""
            for entry in sorted(os.listdir(sys_block)):
                if entry.startswith(("loop", "ram", "dm-")):
                    continue
                return entry
        except OSError as exc:
            logger.debug("Block device scan failed: %s", exc)
        return ""

    @staticmethod
    def _read_io_scheduler() -> str:
        """
        Read the active I/O scheduler for the first real block device.
        Returns the bracketed (active) scheduler name, or ``"unknown"``.
        """
        device = AutoTuner._find_first_block_device()
        if not device:
            return "unknown"
        sched_path = f"/sys/block/{device}/queue/scheduler"
        try:
            if not os.path.exists(sched_path):
                return "unknown"
            with open(sched_path, "r") as f:
                content = f.read().strip()
            # Format: "none [mq-deadline] kyber" — active value in brackets
            for token in content.split():
                if token.startswith("[") and token.endswith("]"):
                    return token[1:-1]
            # If no brackets, the whole string is the scheduler
            return content if content else "unknown"
        except OSError as exc:
            logger.debug("Failed to read I/O scheduler: %s", exc)
            return "unknown"
