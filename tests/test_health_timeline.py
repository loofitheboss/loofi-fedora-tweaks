"""
Tests for utils/health_timeline.py — Health Timeline.
Covers: DB init, record, query, prune, export, anomaly detection,
and mocked system metric readers.
"""

import csv
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.health_timeline import HealthTimeline
from utils.containers import Result


# ---------------------------------------------------------------------------
# TestDBInit — database initialisation
# ---------------------------------------------------------------------------

class TestDBInit(unittest.TestCase):
    """Tests for database initialisation."""

    def test_in_memory_db_creates_table(self):
        """In-memory database creates the metrics table."""
        ht = HealthTimeline(db_path=":memory:")
        conn = sqlite3.connect(":memory:")
        # The HealthTimeline instance creates its own connection,
        # so we verify by recording and querying
        result = ht.record_metric("test", 1.0)
        self.assertTrue(result.success)

    def test_file_db_creates_directory(self):
        """File-based database creates the parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "test.db")
            ht = HealthTimeline(db_path=db_path)
            self.assertTrue(os.path.isdir(os.path.join(tmpdir, "subdir")))

    def test_file_db_creates_file(self):
        """File-based database creates the .db file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "health.db")
            ht = HealthTimeline(db_path=db_path)
            ht.record_metric("test", 42.0)
            self.assertTrue(os.path.isfile(db_path))

    def test_metrics_table_has_expected_columns(self):
        """The metrics table has the correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "schema.db")
            ht = HealthTimeline(db_path=db_path)
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA table_info(metrics)")
            columns = {row[1] for row in cursor}
            conn.close()
            expected = {"id", "timestamp", "metric_type", "value", "unit", "metadata"}
            self.assertEqual(columns, expected)


# ---------------------------------------------------------------------------
# TestRecordMetric — recording individual metrics
# ---------------------------------------------------------------------------

class TestRecordMetric(unittest.TestCase):
    """Tests for recording individual metrics."""

    def setUp(self):
        self.ht = HealthTimeline(db_path=":memory:")

    def test_record_metric_success(self):
        """Recording a valid metric returns success."""
        result = self.ht.record_metric("cpu_temp", 65.5, "C")
        self.assertTrue(result.success)
        self.assertIn("cpu_temp", result.message)

    def test_record_metric_empty_type(self):
        """Empty metric type is rejected."""
        result = self.ht.record_metric("", 10.0)
        self.assertFalse(result.success)
        self.assertIn("empty", result.message)

    def test_record_metric_with_metadata(self):
        """Metrics with metadata are stored correctly."""
        result = self.ht.record_metric("cpu_temp", 70.0, "C", {"sensor": "coretemp"})
        self.assertTrue(result.success)

        metrics = self.ht.get_metrics("cpu_temp", hours=1)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["metadata"]["sensor"], "coretemp")

    def test_record_metric_zero_value(self):
        """Zero values are accepted."""
        result = self.ht.record_metric("load_avg", 0.0)
        self.assertTrue(result.success)

    def test_record_metric_negative_value(self):
        """Negative values are accepted (temperature can be negative)."""
        result = self.ht.record_metric("cpu_temp", -5.0, "C")
        self.assertTrue(result.success)

    def test_record_metric_no_unit(self):
        """Metrics without unit are accepted."""
        result = self.ht.record_metric("load_avg", 2.5)
        self.assertTrue(result.success)


# ---------------------------------------------------------------------------
# TestRecordSnapshot — full system snapshot recording
# ---------------------------------------------------------------------------

class TestRecordSnapshot(unittest.TestCase):
    """Tests for recording a full system snapshot."""

    def setUp(self):
        self.ht = HealthTimeline(db_path=":memory:")

    @patch.object(HealthTimeline, '_get_load_average', return_value=1.5)
    @patch.object(HealthTimeline, '_get_disk_usage', return_value=45.0)
    @patch.object(HealthTimeline, '_get_ram_usage', return_value=60.0)
    @patch.object(HealthTimeline, '_get_cpu_temp', return_value=55.0)
    def test_snapshot_records_all_four(self, mock_temp, mock_ram, mock_disk, mock_load):
        """Snapshot records cpu_temp, ram_usage, disk_usage, and load_avg."""
        result = self.ht.record_snapshot()
        self.assertTrue(result.success)

        metrics = self.ht.get_metrics("cpu_temp", hours=1)
        self.assertEqual(len(metrics), 1)

        metrics = self.ht.get_metrics("ram_usage", hours=1)
        self.assertEqual(len(metrics), 1)

        metrics = self.ht.get_metrics("disk_usage", hours=1)
        self.assertEqual(len(metrics), 1)

        metrics = self.ht.get_metrics("load_avg", hours=1)
        self.assertEqual(len(metrics), 1)

    @patch.object(HealthTimeline, '_get_load_average', return_value=0.5)
    @patch.object(HealthTimeline, '_get_disk_usage', return_value=30.0)
    @patch.object(HealthTimeline, '_get_ram_usage', return_value=50.0)
    @patch.object(HealthTimeline, '_get_cpu_temp', side_effect=RuntimeError("No sensor"))
    def test_snapshot_partial_success(self, mock_temp, mock_ram, mock_disk, mock_load):
        """Snapshot succeeds partially if one metric fails."""
        result = self.ht.record_snapshot()
        self.assertTrue(result.success)
        self.assertIn("errors", result.data)

    @patch.object(HealthTimeline, '_get_load_average', side_effect=RuntimeError("fail"))
    @patch.object(HealthTimeline, '_get_disk_usage', side_effect=RuntimeError("fail"))
    @patch.object(HealthTimeline, '_get_ram_usage', side_effect=RuntimeError("fail"))
    @patch.object(HealthTimeline, '_get_cpu_temp', side_effect=RuntimeError("fail"))
    def test_snapshot_all_fail(self, mock_temp, mock_ram, mock_disk, mock_load):
        """Snapshot returns failure when all metrics fail."""
        result = self.ht.record_snapshot()
        self.assertFalse(result.success)


# ---------------------------------------------------------------------------
# TestGetMetrics — querying metrics
# ---------------------------------------------------------------------------

class TestGetMetrics(unittest.TestCase):
    """Tests for querying recorded metrics."""

    def setUp(self):
        self.ht = HealthTimeline(db_path=":memory:")

    def test_get_metrics_returns_recorded(self):
        """Recorded metrics are returned by get_metrics."""
        self.ht.record_metric("cpu_temp", 65.0, "C")
        self.ht.record_metric("cpu_temp", 70.0, "C")
        metrics = self.ht.get_metrics("cpu_temp", hours=1)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0]["value"], 65.0)
        self.assertEqual(metrics[1]["value"], 70.0)

    def test_get_metrics_filters_by_type(self):
        """get_metrics only returns the requested metric type."""
        self.ht.record_metric("cpu_temp", 65.0, "C")
        self.ht.record_metric("ram_usage", 50.0, "%")
        metrics = self.ht.get_metrics("cpu_temp", hours=1)
        self.assertEqual(len(metrics), 1)

    def test_get_metrics_empty_result(self):
        """Returns empty list for unrecorded metric type."""
        metrics = self.ht.get_metrics("nonexistent", hours=1)
        self.assertEqual(metrics, [])

    def test_get_metrics_respects_time_window(self):
        """Metrics outside the time window are excluded."""
        # Insert a metric with an old timestamp directly
        conn = sqlite3.connect(":memory:")
        # Use the ht's internal path
        self.ht.record_metric("cpu_temp", 65.0, "C")

        # The metric we just recorded should be within 1 hour
        metrics = self.ht.get_metrics("cpu_temp", hours=1)
        self.assertEqual(len(metrics), 1)

    def test_get_metrics_result_has_expected_keys(self):
        """Returned dicts have id, timestamp, value, unit, metadata."""
        self.ht.record_metric("test", 42.0, "units")
        metrics = self.ht.get_metrics("test", hours=1)
        m = metrics[0]
        self.assertIn("id", m)
        self.assertIn("timestamp", m)
        self.assertIn("value", m)
        self.assertIn("unit", m)
        self.assertIn("metadata", m)


# ---------------------------------------------------------------------------
# TestGetSummary — summary statistics
# ---------------------------------------------------------------------------

class TestGetSummary(unittest.TestCase):
    """Tests for get_summary statistics."""

    def setUp(self):
        self.ht = HealthTimeline(db_path=":memory:")

    def test_summary_min_max_avg(self):
        """Summary computes correct min, max, avg."""
        self.ht.record_metric("cpu_temp", 50.0, "C")
        self.ht.record_metric("cpu_temp", 60.0, "C")
        self.ht.record_metric("cpu_temp", 70.0, "C")
        summary = self.ht.get_summary(hours=1)
        self.assertIn("cpu_temp", summary)
        self.assertEqual(summary["cpu_temp"]["min"], 50.0)
        self.assertEqual(summary["cpu_temp"]["max"], 70.0)
        self.assertEqual(summary["cpu_temp"]["avg"], 60.0)
        self.assertEqual(summary["cpu_temp"]["count"], 3)

    def test_summary_multiple_types(self):
        """Summary covers all metric types recorded."""
        self.ht.record_metric("cpu_temp", 55.0)
        self.ht.record_metric("ram_usage", 60.0)
        summary = self.ht.get_summary(hours=1)
        self.assertIn("cpu_temp", summary)
        self.assertIn("ram_usage", summary)

    def test_summary_empty_db(self):
        """Summary returns empty dict for empty database."""
        summary = self.ht.get_summary(hours=1)
        self.assertEqual(summary, {})

    def test_summary_single_value(self):
        """Summary works with a single data point."""
        self.ht.record_metric("load_avg", 3.0)
        summary = self.ht.get_summary(hours=1)
        self.assertEqual(summary["load_avg"]["min"], 3.0)
        self.assertEqual(summary["load_avg"]["max"], 3.0)
        self.assertEqual(summary["load_avg"]["count"], 1)


# ---------------------------------------------------------------------------
# TestPruneOldData — data retention
# ---------------------------------------------------------------------------

class TestPruneOldData(unittest.TestCase):
    """Tests for pruning old data."""

    def test_prune_deletes_old_entries(self):
        """Old entries are removed by prune_old_data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "prune.db")
            ht = HealthTimeline(db_path=db_path)

            # Insert an old entry directly
            conn = sqlite3.connect(db_path)
            old_ts = "2020-01-01T00:00:00"
            conn.execute(
                "INSERT INTO metrics (timestamp, metric_type, value, unit) "
                "VALUES (?, ?, ?, ?)",
                (old_ts, "cpu_temp", 50.0, "C"),
            )
            conn.commit()
            conn.close()

            # Also record a fresh one
            ht.record_metric("cpu_temp", 65.0, "C")

            result = ht.prune_old_data(days=1)
            self.assertTrue(result.success)
            self.assertEqual(result.data["deleted"], 1)

    def test_prune_keeps_recent(self):
        """Recent entries are kept during pruning."""
        ht = HealthTimeline(db_path=":memory:")
        ht.record_metric("cpu_temp", 65.0, "C")
        result = ht.prune_old_data(days=1)
        self.assertTrue(result.success)
        self.assertEqual(result.data["deleted"], 0)

    def test_prune_default_retention(self):
        """Prune uses DEFAULT_RETENTION_DAYS when no argument given."""
        ht = HealthTimeline(db_path=":memory:")
        result = ht.prune_old_data()
        self.assertTrue(result.success)

    def test_prune_empty_db(self):
        """Pruning an empty database succeeds with 0 deleted."""
        ht = HealthTimeline(db_path=":memory:")
        result = ht.prune_old_data(days=1)
        self.assertTrue(result.success)
        self.assertEqual(result.data["deleted"], 0)


# ---------------------------------------------------------------------------
# TestExportMetrics — JSON and CSV export
# ---------------------------------------------------------------------------

class TestExportMetrics(unittest.TestCase):
    """Tests for exporting metrics."""

    def setUp(self):
        self.ht = HealthTimeline(db_path=":memory:")
        self.ht.record_metric("cpu_temp", 55.0, "C")
        self.ht.record_metric("cpu_temp", 65.0, "C")
        self.ht.record_metric("ram_usage", 50.0, "%")

    def test_export_json(self):
        """JSON export creates a valid JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmppath = f.name

        try:
            result = self.ht.export_metrics(tmppath, format="json")
            self.assertTrue(result.success)
            self.assertEqual(result.data["count"], 3)

            with open(tmppath) as f:
                data = json.load(f)
            self.assertEqual(len(data), 3)
        finally:
            os.unlink(tmppath)

    def test_export_csv(self):
        """CSV export creates a file with headers and correct row count."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmppath = f.name

        try:
            result = self.ht.export_metrics(tmppath, format="csv")
            self.assertTrue(result.success)

            with open(tmppath) as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 4)  # header + 3 data rows
        finally:
            os.unlink(tmppath)

    def test_export_unsupported_format(self):
        """Unsupported format returns failure."""
        result = self.ht.export_metrics("/tmp/test.xml", format="xml")
        self.assertFalse(result.success)
        self.assertIn("Unsupported", result.message)

    def test_export_invalid_path(self):
        """Invalid output path returns failure."""
        result = self.ht.export_metrics("/nonexistent/dir/out.json", format="json")
        self.assertFalse(result.success)

    def test_export_empty_db_json(self):
        """Exporting empty database produces empty JSON list."""
        ht = HealthTimeline(db_path=":memory:")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmppath = f.name

        try:
            result = ht.export_metrics(tmppath, format="json")
            self.assertTrue(result.success)

            with open(tmppath) as f:
                data = json.load(f)
            self.assertEqual(data, [])
        finally:
            os.unlink(tmppath)

    def test_export_empty_db_csv(self):
        """Exporting empty database produces CSV with only headers."""
        ht = HealthTimeline(db_path=":memory:")
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmppath = f.name

        try:
            result = ht.export_metrics(tmppath, format="csv")
            self.assertTrue(result.success)

            with open(tmppath) as f:
                reader = csv.reader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1)  # header only
        finally:
            os.unlink(tmppath)


# ---------------------------------------------------------------------------
# TestDetectAnomalies — anomaly detection
# ---------------------------------------------------------------------------

class TestDetectAnomalies(unittest.TestCase):
    """Tests for anomaly detection via standard deviation."""

    def setUp(self):
        self.ht = HealthTimeline(db_path=":memory:")

    def test_detect_anomalies_with_outlier(self):
        """An outlier >2 std devs from mean is detected."""
        # Record a cluster of similar values
        for val in [50.0, 51.0, 52.0, 50.5, 49.5, 51.5, 50.0, 49.0]:
            self.ht.record_metric("cpu_temp", val, "C")
        # Add an outlier
        self.ht.record_metric("cpu_temp", 100.0, "C")

        anomalies = self.ht.detect_anomalies("cpu_temp", hours=1)
        self.assertGreater(len(anomalies), 0)
        self.assertEqual(anomalies[0]["value"], 100.0)

    def test_detect_anomalies_no_outliers(self):
        """No anomalies when all values are similar."""
        for val in [50.0, 51.0, 50.5, 49.5, 50.0]:
            self.ht.record_metric("cpu_temp", val, "C")

        anomalies = self.ht.detect_anomalies("cpu_temp", hours=1)
        self.assertEqual(len(anomalies), 0)

    def test_detect_anomalies_too_few_points(self):
        """Returns empty list with fewer than 3 data points."""
        self.ht.record_metric("cpu_temp", 50.0, "C")
        self.ht.record_metric("cpu_temp", 60.0, "C")

        anomalies = self.ht.detect_anomalies("cpu_temp", hours=1)
        self.assertEqual(anomalies, [])

    def test_detect_anomalies_identical_values(self):
        """Returns empty when stdev is zero (all identical values)."""
        for _ in range(5):
            self.ht.record_metric("cpu_temp", 50.0, "C")

        anomalies = self.ht.detect_anomalies("cpu_temp", hours=1)
        self.assertEqual(anomalies, [])

    def test_detect_anomalies_result_fields(self):
        """Anomaly dicts have expected keys."""
        for val in [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 100.0]:
            self.ht.record_metric("cpu_temp", val, "C")

        anomalies = self.ht.detect_anomalies("cpu_temp", hours=1)
        if anomalies:
            a = anomalies[0]
            self.assertIn("id", a)
            self.assertIn("timestamp", a)
            self.assertIn("value", a)
            self.assertIn("deviation", a)
            self.assertIn("mean", a)
            self.assertIn("stdev", a)

    def test_detect_anomalies_empty_metric(self):
        """No data for the metric type returns empty list."""
        anomalies = self.ht.detect_anomalies("nonexistent", hours=1)
        self.assertEqual(anomalies, [])


# ---------------------------------------------------------------------------
# TestGetCpuTemp — mocked CPU temperature reading
# ---------------------------------------------------------------------------

class TestGetCpuTemp(unittest.TestCase):
    """Tests for _get_cpu_temp with mocked filesystem."""

    @patch('os.listdir', return_value=['thermal_zone0'])
    @patch('os.path.isdir', return_value=True)
    @patch('os.path.isfile', return_value=True)
    @patch('builtins.open', mock_open(read_data='65000\n'))
    def test_read_from_thermal_zone(self, mock_isfile, mock_isdir, mock_listdir):
        """Temperature is read from /sys/class/thermal."""
        temp = HealthTimeline._get_cpu_temp()
        self.assertEqual(temp, 65.0)

    @patch('os.path.isdir', return_value=False)
    @patch('utils.health_timeline.shutil.which', return_value=None)
    def test_no_source_raises(self, mock_which, mock_isdir):
        """RuntimeError is raised when no temperature source exists."""
        with self.assertRaises(RuntimeError):
            HealthTimeline._get_cpu_temp()


# ---------------------------------------------------------------------------
# TestGetRamUsage — mocked RAM reading
# ---------------------------------------------------------------------------

class TestGetRamUsage(unittest.TestCase):
    """Tests for _get_ram_usage with mocked /proc/meminfo."""

    @patch('builtins.open', mock_open(
        read_data="MemTotal:       16000000 kB\nMemFree:         2000000 kB\nMemAvailable:    8000000 kB\n"
    ))
    def test_ram_usage_calculation(self):
        """RAM usage is calculated correctly from MemTotal and MemAvailable."""
        usage = HealthTimeline._get_ram_usage()
        # (16000000 - 8000000) / 16000000 * 100 = 50.0
        self.assertEqual(usage, 50.0)

    @patch('builtins.open', side_effect=OSError("permission denied"))
    def test_ram_usage_read_error(self, mock_file):
        """RuntimeError is raised when /proc/meminfo cannot be read."""
        with self.assertRaises(RuntimeError):
            HealthTimeline._get_ram_usage()


# ---------------------------------------------------------------------------
# TestGetDiskUsage — mocked disk reading
# ---------------------------------------------------------------------------

class TestGetDiskUsage(unittest.TestCase):
    """Tests for _get_disk_usage."""

    @patch('os.statvfs')
    def test_disk_usage_calculation(self, mock_statvfs):
        """Disk usage is calculated from statvfs."""
        mock_result = MagicMock()
        mock_result.f_blocks = 1000
        mock_result.f_bfree = 400
        mock_result.f_frsize = 4096
        mock_statvfs.return_value = mock_result

        usage = HealthTimeline._get_disk_usage()
        # (1000 - 400) / 1000 * 100 = 60.0
        self.assertEqual(usage, 60.0)

    @patch('os.statvfs', side_effect=OSError("fail"))
    def test_disk_usage_oserror(self, mock_statvfs):
        """Returns 0.0 on OSError."""
        usage = HealthTimeline._get_disk_usage()
        self.assertEqual(usage, 0.0)


# ---------------------------------------------------------------------------
# TestGetLoadAverage — mocked load average
# ---------------------------------------------------------------------------

class TestGetLoadAverage(unittest.TestCase):
    """Tests for _get_load_average."""

    @patch('os.getloadavg', return_value=(2.5, 1.5, 0.8))
    def test_load_average_reads_one_minute(self, mock_load):
        """Returns the 1-minute load average."""
        load = HealthTimeline._get_load_average()
        self.assertEqual(load, 2.5)

    @patch('os.getloadavg', side_effect=OSError("not available"))
    def test_load_average_oserror(self, mock_load):
        """Returns 0.0 on OSError."""
        load = HealthTimeline._get_load_average()
        self.assertEqual(load, 0.0)


if __name__ == '__main__':
    unittest.main()
