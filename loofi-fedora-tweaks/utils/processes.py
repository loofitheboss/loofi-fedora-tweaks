"""
Process Manager - Process monitoring and management utilities.
Part of v9.2 "Pulse" update.

Reads process information directly from /proc without psutil dependency.
Provides CPU/memory usage tracking, process listing, and signal management.
"""

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ProcessInfo:
    """Information about a single running process."""
    pid: int
    name: str
    user: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int
    state: str  # R, S, D, Z, T, etc.
    command: str  # Full command line
    nice: int


class ProcessManager:
    """
    Manages process listing, monitoring, and control.

    Reads directly from /proc to avoid psutil dependency.
    CPU percentage is calculated by comparing /proc/[pid]/stat snapshots
    between successive calls. The first call will return 0% for all processes.
    """

    # Class-level storage for CPU calculation snapshots
    _prev_snapshot: Dict[int, Tuple[float, float]] = {}  # pid -> (total_time, timestamp)
    _prev_snapshot_time: float = 0.0

    @staticmethod
    def _get_clock_ticks() -> int:
        """Get the system clock ticks per second (CLK_TCK)."""
        try:
            return os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        except (ValueError, KeyError):
            return 100  # Default on most Linux systems

    @staticmethod
    def _get_total_memory() -> int:
        """Get total system memory in bytes from /proc/meminfo."""
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        return int(parts[1]) * 1024  # kB to bytes
        except Exception:
            pass
        return 1  # Avoid division by zero

    @staticmethod
    def _get_uid_user_map() -> Dict[int, str]:
        """Build a UID-to-username mapping from /etc/passwd."""
        uid_map = {}
        try:
            with open("/etc/passwd", "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 3:
                        uid_map[int(parts[2])] = parts[0]
        except Exception:
            pass
        return uid_map

    @staticmethod
    def _read_proc_stat(pid: int) -> Optional[dict]:
        """
        Read and parse /proc/[pid]/stat.

        Returns a dict with keys: name, state, utime, stime, nice, rss, num_threads
        or None if the process cannot be read.
        """
        try:
            with open(f"/proc/{pid}/stat", "r") as f:
                content = f.read()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            return None

        # The comm field is enclosed in parentheses and may contain spaces
        # Find the last ')' to correctly split
        try:
            start = content.index("(") + 1
            end = content.rindex(")")
            name = content[start:end]
            # Fields after the closing parenthesis
            fields = content[end + 2:].split()
        except (ValueError, IndexError):
            return None

        if len(fields) < 22:
            return None

        try:
            return {
                "name": name,
                "state": fields[0],           # field 3
                "utime": int(fields[11]),      # field 14: user mode jiffies
                "stime": int(fields[12]),      # field 15: kernel mode jiffies
                "nice": int(fields[16]),       # field 19: nice value
                "num_threads": int(fields[17]),# field 20
                "rss": int(fields[21]),        # field 24: resident set size in pages
            }
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _read_proc_status_uid(pid: int) -> Optional[int]:
        """Read the real UID from /proc/[pid]/status."""
        try:
            with open(f"/proc/{pid}/status", "r") as f:
                for line in f:
                    if line.startswith("Uid:"):
                        # Format: Uid: real effective saved filesystem
                        return int(line.split()[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError, IndexError):
            pass
        return None

    @staticmethod
    def _read_proc_cmdline(pid: int) -> str:
        """Read the full command line from /proc/[pid]/cmdline."""
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                raw = f.read()
            if raw:
                # Arguments are separated by null bytes
                return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
        return ""

    @classmethod
    def get_all_processes(cls) -> List[ProcessInfo]:
        """
        Read info for all processes from /proc.

        CPU percentage is calculated by comparing total CPU time (utime + stime)
        between the current and previous snapshots. On the first call, all CPU
        percentages will be 0%.

        Returns:
            List of ProcessInfo objects for all readable processes.
        """
        clk_tck = cls._get_clock_ticks()
        total_memory = cls._get_total_memory()
        page_size = os.sysconf("SC_PAGESIZE")
        uid_map = cls._get_uid_user_map()
        num_cpus = os.cpu_count() or 1

        current_time = time.monotonic()
        elapsed = current_time - cls._prev_snapshot_time if cls._prev_snapshot_time > 0 else 0.0

        new_snapshot: Dict[int, Tuple[float, float]] = {}
        processes: List[ProcessInfo] = []

        try:
            pids = [int(entry) for entry in os.listdir("/proc") if entry.isdigit()]
        except OSError:
            return processes

        for pid in pids:
            stat = cls._read_proc_stat(pid)
            if stat is None:
                continue

            # CPU time in seconds
            total_cpu_time = (stat["utime"] + stat["stime"]) / clk_tck
            new_snapshot[pid] = (total_cpu_time, current_time)

            # Calculate CPU percentage from previous snapshot
            cpu_percent = 0.0
            if elapsed > 0 and pid in cls._prev_snapshot:
                prev_cpu_time, _ = cls._prev_snapshot[pid]
                delta_cpu = total_cpu_time - prev_cpu_time
                # Percentage relative to one CPU; cap for multi-core
                cpu_percent = (delta_cpu / elapsed) * 100.0
                # Clamp to 0..num_cpus*100
                cpu_percent = max(0.0, min(cpu_percent, num_cpus * 100.0))

            # Memory
            memory_bytes = stat["rss"] * page_size
            memory_percent = (memory_bytes / total_memory) * 100.0 if total_memory > 0 else 0.0

            # User from UID
            uid = cls._read_proc_status_uid(pid)
            user = uid_map.get(uid, str(uid)) if uid is not None else "unknown"

            # Command line (fall back to stat name)
            command = cls._read_proc_cmdline(pid)
            if not command:
                command = f"[{stat['name']}]"

            processes.append(ProcessInfo(
                pid=pid,
                name=stat["name"],
                user=user,
                cpu_percent=round(cpu_percent, 1),
                memory_percent=round(memory_percent, 1),
                memory_bytes=memory_bytes,
                state=stat["state"],
                command=command,
                nice=stat["nice"],
            ))

        # Store snapshot for next call
        cls._prev_snapshot = new_snapshot
        cls._prev_snapshot_time = current_time

        return processes

    @classmethod
    def get_top_by_cpu(cls, n: int = 10) -> List[ProcessInfo]:
        """
        Get the top N processes by CPU usage.

        Args:
            n: Number of processes to return.

        Returns:
            List of ProcessInfo sorted by CPU usage descending, limited to n.
        """
        processes = cls.get_all_processes()
        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        return processes[:n]

    @classmethod
    def get_top_by_memory(cls, n: int = 10) -> List[ProcessInfo]:
        """
        Get the top N processes by memory usage.

        Args:
            n: Number of processes to return.

        Returns:
            List of ProcessInfo sorted by memory usage descending, limited to n.
        """
        processes = cls.get_all_processes()
        processes.sort(key=lambda p: p.memory_bytes, reverse=True)
        return processes[:n]

    @staticmethod
    def kill_process(pid: int, signal: int = 15) -> Tuple[bool, str]:
        """
        Send a signal to a process.

        Tries os.kill first. If permission is denied (e.g., root process),
        falls back to pkexec kill.

        Args:
            pid: Process ID to signal.
            signal: Signal number (default 15 = SIGTERM).

        Returns:
            Tuple of (success, message).
        """
        try:
            os.kill(pid, signal)
            return True, f"Signal {signal} sent to process {pid}"
        except PermissionError:
            # Need elevated privileges
            try:
                result = subprocess.run(
                    ["pkexec", "kill", f"-{signal}", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    return True, f"Signal {signal} sent to process {pid} (elevated)"
                else:
                    error = result.stderr.strip() or "Unknown error"
                    return False, f"Failed to signal process {pid}: {error}"
            except subprocess.TimeoutExpired:
                return False, f"Timed out sending signal to process {pid}"
            except FileNotFoundError:
                return False, "pkexec not found - cannot send signal to privileged process"
            except Exception as e:
                return False, f"Failed to signal process {pid}: {e}"
        except ProcessLookupError:
            return False, f"Process {pid} not found"
        except Exception as e:
            return False, f"Error signaling process {pid}: {e}"

    @staticmethod
    def renice_process(pid: int, nice: int) -> Tuple[bool, str]:
        """
        Change the nice (priority) value of a process.

        Tries the renice command directly first. If that fails due to
        permissions, falls back to pkexec.

        Args:
            pid: Process ID to renice.
            nice: New nice value (-20 to 19).

        Returns:
            Tuple of (success, message).
        """
        nice = max(-20, min(19, nice))

        try:
            result = subprocess.run(
                ["renice", "-n", str(nice), "-p", str(pid)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, f"Process {pid} reniced to {nice}"
            else:
                # Try with elevated privileges
                result = subprocess.run(
                    ["pkexec", "renice", "-n", str(nice), "-p", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    return True, f"Process {pid} reniced to {nice} (elevated)"
                else:
                    error = result.stderr.strip() or "Unknown error"
                    return False, f"Failed to renice process {pid}: {error}"
        except subprocess.TimeoutExpired:
            return False, f"Timed out renicing process {pid}"
        except FileNotFoundError:
            return False, "renice command not found"
        except Exception as e:
            return False, f"Error renicing process {pid}: {e}"

    @classmethod
    def get_process_count(cls) -> dict:
        """
        Get a summary count of processes by state.

        Returns:
            Dict with keys: total, running, sleeping, zombie.
        """
        counts = {"total": 0, "running": 0, "sleeping": 0, "zombie": 0}

        try:
            pids = [entry for entry in os.listdir("/proc") if entry.isdigit()]
        except OSError:
            return counts

        for pid_str in pids:
            try:
                with open(f"/proc/{pid_str}/stat", "r") as f:
                    content = f.read()
                # Find state field after the comm (name) field
                end_paren = content.rindex(")")
                state = content[end_paren + 2]

                counts["total"] += 1
                if state == "R":
                    counts["running"] += 1
                elif state in ("S", "D", "I"):
                    counts["sleeping"] += 1
                elif state == "Z":
                    counts["zombie"] += 1
            except (FileNotFoundError, PermissionError, ProcessLookupError,
                    ValueError, IndexError):
                continue

        return counts

    @staticmethod
    def bytes_to_human(num_bytes: int) -> str:
        """Convert bytes to a human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(num_bytes) < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} PB"
