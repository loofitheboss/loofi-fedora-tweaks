"""
Health Timeline - Track system health metrics over time.
Part of v13.0 "Nexus Update".

SQLite-based local storage with configurable retention.
Records CPU temp, RAM usage, disk space, battery cycles,
and load average. Supports anomaly detection via standard
deviation thresholds and export to JSON or CSV.
"""

import csv
import json
import logging
import os
import shutil
import sqlite3
import statistics
import subprocess
import time

from utils.containers import Result

logger = logging.getLogger(__name__)


class HealthTimeline:
    """
    Records and queries system health metrics over time.

    Uses a local SQLite database for persistence and supports
    configurable retention, export, and simple anomaly detection.
    """

    DB_PATH = os.path.expanduser("~/.local/share/loofi-fedora-tweaks/health_timeline.db")
    DEFAULT_RETENTION_DAYS = 30

    def __init__(self, db_path: str = None):
        """
        Initialise HealthTimeline with an optional database path override.

        Args:
            db_path: Path to the SQLite database. Defaults to DB_PATH.
                     Pass \":memory:\" for in-memory testing.
        """
        self.db_path = db_path or self.DB_PATH
        self._conn = None  # Persistent connection for :memory: databases
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection.

        For :memory: databases a persistent connection is reused so that
        data written in one call is visible to subsequent calls. For
        file-backed databases a fresh connection is opened each time.
        """
        if self.db_path == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(":memory:")
            return self._conn
        return sqlite3.connect(self.db_path)

    def _close_conn(self, conn: sqlite3.Connection) -> None:
        """Close a connection unless it is the persistent :memory: one."""
        if self.db_path != ":memory:":
            conn.close()

    def _init_db(self) -> None:
        """Create the metrics table if it does not exist."""
        if self.db_path != ":memory:":
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT DEFAULT '',
                    metadata TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type_ts
                ON metrics (metric_type, timestamp)
            """)
            conn.commit()
        finally:
            self._close_conn(conn)

    # ==================== RECORDING ====================

    def record_metric(
        self,
        metric_type: str,
        value: float,
        unit: str = "",
        metadata: dict = None,
    ) -> Result:
        """
        Record a single metric data point.

        Args:
            metric_type: Category of the metric (e.g. 'cpu_temp', 'ram_usage').
            value: Numeric value of the metric.
            unit: Unit string (e.g. 'C', '%', 'GB').
            metadata: Optional dict of extra information.

        Returns:
            Result indicating success or failure.
        """
        if not metric_type:
            return Result(False, "Metric type cannot be empty.")

        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        meta_str = json.dumps(metadata) if metadata else ""

        try:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO metrics (timestamp, metric_type, value, unit, metadata) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ts, metric_type, value, unit, meta_str),
                )
                conn.commit()
            finally:
                self._close_conn(conn)
            return Result(True, f"Recorded {metric_type}={value}{unit}")
        except sqlite3.Error as e:
            return Result(False, f"Database error: {e}")

    def record_snapshot(self) -> Result:
        """
        Record a full system snapshot: CPU temp, RAM %, disk %, load avg.

        Returns:
            Result with a summary of recorded metrics.
        """
        recorded = []
        errors = []

        # CPU temperature
        try:
            cpu_temp = self._get_cpu_temp()
            result = self.record_metric("cpu_temp", cpu_temp, "C")
            if result.success:
                recorded.append(f"cpu_temp={cpu_temp}C")
            else:
                errors.append(result.message)
        except (OSError, RuntimeError) as e:
            logger.debug("cpu_temp snapshot error: %s", e)
            errors.append(f"cpu_temp: {e}")

        # RAM usage
        try:
            ram = self._get_ram_usage()
            result = self.record_metric("ram_usage", ram, "%")
            if result.success:
                recorded.append(f"ram={ram}%")
            else:
                errors.append(result.message)
        except (OSError, RuntimeError) as e:
            logger.debug("ram_usage snapshot error: %s", e)
            errors.append(f"ram_usage: {e}")

        # Disk usage
        try:
            disk = self._get_disk_usage()
            result = self.record_metric("disk_usage", disk, "%")
            if result.success:
                recorded.append(f"disk={disk}%")
            else:
                errors.append(result.message)
        except (OSError, RuntimeError) as e:
            logger.debug("disk_usage snapshot error: %s", e)
            errors.append(f"disk_usage: {e}")

        # Load average
        try:
            load = self._get_load_average()
            result = self.record_metric("load_avg", load, "")
            if result.success:
                recorded.append(f"load_avg={load}")
            else:
                errors.append(result.message)
        except (OSError, RuntimeError) as e:
            logger.debug("load_avg snapshot error: %s", e)
            errors.append(f"load_avg: {e}")

        if errors and not recorded:
            return Result(False, f"Snapshot failed: {'; '.join(errors)}")

        msg = f"Snapshot: {', '.join(recorded)}"
        if errors:
            msg += f" (errors: {'; '.join(errors)})"
        return Result(True, msg, {"recorded": recorded, "errors": errors})

    # ==================== QUERYING ====================

    def get_metrics(self, metric_type: str, hours: int = 24) -> list[dict]:
        """
        Query recent metrics of a given type.

        Args:
            metric_type: Category to filter on.
            hours: How many hours back to look (default 24).

        Returns:
            List of dicts with keys: id, timestamp, value, unit, metadata.
        """
        cutoff = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.gmtime(time.time() - hours * 3600),
        )
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    "SELECT id, timestamp, metric_type, value, unit, metadata "
                    "FROM metrics WHERE metric_type = ? AND timestamp >= ? "
                    "ORDER BY timestamp ASC",
                    (metric_type, cutoff),
                )
                rows = []
                for row in cursor:
                    meta = row["metadata"]
                    try:
                        meta_dict = json.loads(meta) if meta else {}
                    except json.JSONDecodeError:
                        meta_dict = {}
                    rows.append({
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "value": row["value"],
                        "unit": row["unit"],
                        "metadata": meta_dict,
                    })
                return rows
            finally:
                self._close_conn(conn)
        except sqlite3.Error:
            return []

    def get_summary(self, hours: int = 24) -> dict:
        """
        Get min/max/avg statistics per metric type for the given period.

        Args:
            hours: How many hours back to analyse (default 24).

        Returns:
            Dict mapping metric_type to {min, max, avg, count}.
        """
        cutoff = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.gmtime(time.time() - hours * 3600),
        )
        summary = {}
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    "SELECT metric_type, MIN(value) as min_val, MAX(value) as max_val, "
                    "AVG(value) as avg_val, COUNT(*) as cnt "
                    "FROM metrics WHERE timestamp >= ? "
                    "GROUP BY metric_type",
                    (cutoff,),
                )
                for row in cursor:
                    summary[row["metric_type"]] = {
                        "min": row["min_val"],
                        "max": row["max_val"],
                        "avg": round(row["avg_val"], 2),
                        "count": row["cnt"],
                    }
            finally:
                self._close_conn(conn)
        except sqlite3.Error as e:
            logger.debug("get_summary query error: %s", e)
        return summary

    # ==================== MAINTENANCE ====================

    def prune_old_data(self, days: int = None) -> Result:
        """
        Delete metrics older than the specified number of days.

        Args:
            days: Retention period in days. Defaults to DEFAULT_RETENTION_DAYS.

        Returns:
            Result with count of deleted rows.
        """
        if days is None:
            days = self.DEFAULT_RETENTION_DAYS

        cutoff = time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.gmtime(time.time() - days * 86400),
        )
        try:
            conn = self._get_conn()
            try:
                cursor = conn.execute(
                    "DELETE FROM metrics WHERE timestamp < ?", (cutoff,)
                )
                deleted = cursor.rowcount
                conn.commit()
            finally:
                self._close_conn(conn)
            return Result(True, f"Pruned {deleted} old metric(s).", {"deleted": deleted})
        except sqlite3.Error as e:
            return Result(False, f"Prune failed: {e}")

    # ==================== EXPORT ====================

    def export_metrics(self, output_path: str, format: str = "json") -> Result:
        """
        Export all metrics to a file in JSON or CSV format.

        Args:
            output_path: Destination file path.
            format: 'json' or 'csv'.

        Returns:
            Result with success status.
        """
        if format not in ("json", "csv"):
            return Result(False, f"Unsupported format: '{format}'. Use 'json' or 'csv'.")

        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    "SELECT id, timestamp, metric_type, value, unit, metadata "
                    "FROM metrics ORDER BY timestamp ASC"
                )
                rows = [dict(row) for row in cursor]
            finally:
                self._close_conn(conn)
        except sqlite3.Error as e:
            return Result(False, f"Database error during export: {e}")

        try:
            if format == "json":
                with open(output_path, "w") as f:
                    json.dump(rows, f, indent=2)
            elif format == "csv":
                with open(output_path, "w", newline="") as f:
                    if rows:
                        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                    else:
                        writer = csv.writer(f)
                        writer.writerow(["id", "timestamp", "metric_type", "value", "unit", "metadata"])

            return Result(
                True,
                f"Exported {len(rows)} metric(s) to {output_path}.",
                {"count": len(rows), "path": output_path},
            )
        except OSError as e:
            return Result(False, f"Failed to write export file: {e}")

    # ==================== ANOMALY DETECTION ====================

    def detect_anomalies(self, metric_type: str, hours: int = 24) -> list[dict]:
        """
        Flag metric values more than 2 standard deviations from the mean.

        Args:
            metric_type: Metric category to analyse.
            hours: How many hours back to consider.

        Returns:
            List of anomaly dicts with keys: id, timestamp, value, deviation.
        """
        metrics = self.get_metrics(metric_type, hours)
        if len(metrics) < 3:
            return []

        values = [m["value"] for m in metrics]
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
        except statistics.StatisticsError:
            return []

        if stdev == 0:
            return []

        anomalies = []
        threshold = 2 * stdev
        for m in metrics:
            deviation = abs(m["value"] - mean)
            if deviation > threshold:
                anomalies.append({
                    "id": m["id"],
                    "timestamp": m["timestamp"],
                    "value": m["value"],
                    "deviation": round(deviation / stdev, 2),
                    "mean": round(mean, 2),
                    "stdev": round(stdev, 2),
                })

        return anomalies

    # ==================== SYSTEM METRIC READERS ====================

    @staticmethod
    def _get_cpu_temp() -> float:
        """
        Read CPU temperature from thermal zones or the sensors command.

        Returns:
            Temperature in degrees Celsius.

        Raises:
            RuntimeError: If no temperature source is available.
        """
        # Try /sys/class/thermal first
        thermal_base = "/sys/class/thermal"
        try:
            if os.path.isdir(thermal_base):
                for entry in sorted(os.listdir(thermal_base)):
                    if not entry.startswith("thermal_zone"):
                        continue
                    temp_file = os.path.join(thermal_base, entry, "temp")
                    type_file = os.path.join(thermal_base, entry, "type")
                    if os.path.isfile(temp_file):
                        with open(temp_file, "r") as f:
                            raw = f.read().strip()
                        temp = int(raw) / 1000.0
                        if temp > 0:
                            return round(temp, 1)
        except (OSError, ValueError) as e:
            logger.debug("Failed to read thermal zone: %s", e)

        # Fallback: sensors command
        if shutil.which("sensors"):
            try:
                result = subprocess.run(
                    ["sensors"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "Core 0" in line or "Tctl" in line:
                            parts = line.split("+")
                            if len(parts) > 1:
                                temp_str = parts[1].split("\u00b0")[0].split("C")[0].strip()
                                return round(float(temp_str), 1)
            except (subprocess.TimeoutExpired, OSError, ValueError) as e:
                logger.debug("sensors command failed: %s", e)

        raise RuntimeError("No CPU temperature source available.")

    @staticmethod
    def _get_ram_usage() -> float:
        """
        Read RAM usage percentage from /proc/meminfo.

        Returns:
            RAM usage as a percentage (0-100).

        Raises:
            RuntimeError: If /proc/meminfo cannot be read.
        """
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
        except OSError:
            raise RuntimeError("Cannot read /proc/meminfo.")

        info = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                val_parts = parts[1].strip().split()
                if val_parts:
                    try:
                        info[key] = int(val_parts[0])
                    except ValueError:
                        pass

        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)

        if total <= 0:
            raise RuntimeError("Invalid MemTotal in /proc/meminfo.")

        used_pct = ((total - available) / total) * 100
        return round(used_pct, 1)

    @staticmethod
    def _get_disk_usage() -> float:
        """
        Read root filesystem disk usage percentage.

        Returns:
            Disk usage as a percentage (0-100).
        """
        try:
            st = os.statvfs("/")
            total = st.f_blocks * st.f_frsize
            free = st.f_bfree * st.f_frsize
            if total <= 0:
                return 0.0
            used_pct = ((total - free) / total) * 100
            return round(used_pct, 1)
        except OSError as e:
            logger.debug("Failed to read disk usage: %s", e)
            return 0.0

    @staticmethod
    def _get_load_average() -> float:
        """
        Read 1-minute load average.

        Returns:
            1-minute load average as a float.
        """
        try:
            load1, _, _ = os.getloadavg()
            return round(load1, 2)
        except OSError as e:
            logger.debug("Failed to read load average: %s", e)
            return 0.0
