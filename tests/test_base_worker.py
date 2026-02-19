"""
Tests for BaseWorker standardized pattern (v23.0 Architecture Hardening).

Tests cover:
- Signal protocol compliance
- Cancellation support
- Error handling
- Progress reporting
- Result passing
"""

import time
import unittest
from typing import Any
from unittest.mock import MagicMock

import os
import pytest

_SKIP_QT = os.environ.get("DISPLAY") is None and os.environ.get("WAYLAND_DISPLAY") is None

try:
    from PyQt6.QtCore import QCoreApplication
    from core.workers import BaseWorker
except ImportError:
    _SKIP_QT = True
    # Provide a dummy so class definitions don't crash at collection time
    class BaseWorker:  # type: ignore[no-redef]
        """Dummy BaseWorker for environments without PyQt6."""
        def __init__(self, *a, **kw): pass
        def report_progress(self, *a, **kw): pass
        def is_cancelled(self): return False

pytestmark = pytest.mark.skipif(_SKIP_QT, reason="Qt/PyQt6 not available in headless environment")


class SimpleWorker(BaseWorker):
    """Test worker that completes successfully."""

    def do_work(self) -> Any:
        self.report_progress("Working...", 50)
        time.sleep(0.05)
        return {"result": "success"}


class ErrorWorker(BaseWorker):
    """Test worker that raises an error."""

    def do_work(self) -> Any:
        self.report_progress("About to fail...", 30)
        raise ValueError("Intentional test error")


class CancellableWorker(BaseWorker):
    """Test worker with cancellation checking."""

    def do_work(self) -> Any:
        for i in range(10):
            if self.is_cancelled():
                return None
            self.report_progress(f"Step {i+1}/10", (i+1) * 10)
            time.sleep(0.02)
        return {"completed": True}


class LongRunningWorker(BaseWorker):
    """Test worker that runs for extended period."""

    def __init__(self, iterations: int = 5):
        super().__init__()
        self.iterations = iterations

    def do_work(self) -> Any:
        results = []
        for i in range(self.iterations):
            if self.is_cancelled():
                return {"cancelled": True, "partial_results": results}
            self.report_progress(f"Iteration {i+1}/{self.iterations}", (i+1) * 100 // self.iterations)
            results.append(i * 2)
            time.sleep(0.02)
        return {"completed": True, "results": results}


class TestBaseWorker(unittest.TestCase):
    """Test suite for BaseWorker base class."""

    @classmethod
    def setUpClass(cls):
        """Create QCoreApplication if not already running."""
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        """Reset state before each test."""
        self.signals_received = {
            "started": 0,
            "progress": [],
            "finished": [],
            "error": []
        }

    def _inc_started(self):
        """Increment started signal count."""
        self.signals_received["started"] += 1

    def _flush_events(self):
        """Process queued Qt signals."""
        self.app.processEvents()
        self.app.processEvents()

    def test_simple_success(self):
        """Test basic successful worker execution."""
        worker = SimpleWorker()

        # Connect signals
        worker.started.connect(self._inc_started)
        worker.progress.connect(lambda msg, pct: self.signals_received["progress"].append((msg, pct)))
        worker.finished.connect(lambda result: self.signals_received["finished"].append(result))
        worker.error.connect(lambda msg: self.signals_received["error"].append(msg))

        # Run worker
        worker.start()
        worker.wait(1000)
        self._flush_events()

        # Verify signals
        self.assertEqual(self.signals_received["started"], 1)
        self.assertGreater(len(self.signals_received["progress"]), 0)
        self.assertEqual(len(self.signals_received["finished"]), 1)
        self.assertEqual(len(self.signals_received["error"]), 0)

        # Verify result
        result = self.signals_received["finished"][0]
        self.assertEqual(result, {"result": "success"})

    def test_error_handling(self):
        """Test that errors are caught and emitted via error signal."""
        worker = ErrorWorker()

        worker.started.connect(self._inc_started)
        worker.progress.connect(lambda msg, pct: self.signals_received["progress"].append((msg, pct)))
        worker.finished.connect(lambda result: self.signals_received["finished"].append(result))
        worker.error.connect(lambda msg: self.signals_received["error"].append(msg))

        worker.start()
        worker.wait(1000)
        self._flush_events()

        # Verify error signal
        self.assertEqual(self.signals_received["started"], 1)
        self.assertEqual(len(self.signals_received["finished"]), 0)
        self.assertEqual(len(self.signals_received["error"]), 1)
        self.assertIn("Intentional test error", self.signals_received["error"][0])

    def test_cancellation(self):
        """Test worker cancellation support."""
        worker = CancellableWorker()

        worker.started.connect(self._inc_started)
        worker.progress.connect(lambda msg, pct: self.signals_received["progress"].append((msg, pct)))
        worker.finished.connect(lambda result: self.signals_received["finished"].append(result))
        worker.error.connect(lambda msg: self.signals_received["error"].append(msg))

        worker.start()
        time.sleep(0.05)  # Let it run briefly
        worker.cancel()
        worker.wait(1000)
        self._flush_events()

        # Verify cancellation
        self.assertEqual(self.signals_received["started"], 1)
        self.assertTrue(worker.is_cancelled())

        # Should receive error signal for cancellation
        self.assertEqual(len(self.signals_received["error"]), 1)
        self.assertIn("cancelled", self.signals_received["error"][0].lower())

    def test_progress_reporting(self):
        """Test progress signal emission."""
        worker = LongRunningWorker(iterations=5)

        worker.progress.connect(lambda msg, pct: self.signals_received["progress"].append((msg, pct)))

        worker.start()
        worker.wait(1000)
        self._flush_events()

        # Verify progress signals
        self.assertGreaterEqual(len(self.signals_received["progress"]), 5)

        # Verify progress percentages are in valid range
        for msg, pct in self.signals_received["progress"]:
            self.assertGreaterEqual(pct, 0)
            self.assertLessEqual(pct, 100)

    def test_result_retrieval(self):
        """Test get_result() method."""
        worker = SimpleWorker()
        worker.finished.connect(lambda result: self.signals_received["finished"].append(result))

        self.assertIsNone(worker.get_result())  # Before execution

        worker.start()
        worker.wait(1000)
        self._flush_events()

        result = worker.get_result()
        self.assertEqual(result, {"result": "success"})

    def test_multiple_workers_isolation(self):
        """Test that multiple workers don't interfere with each other."""
        worker1 = SimpleWorker()
        worker2 = LongRunningWorker(iterations=3)

        results = {"worker1": None, "worker2": None}

        worker1.finished.connect(lambda result: results.update({"worker1": result}))
        worker2.finished.connect(lambda result: results.update({"worker2": result}))

        worker1.start()
        worker2.start()

        worker1.wait(1000)
        worker2.wait(1000)
        self._flush_events()

        # Both should complete independently
        self.assertIsNotNone(results["worker1"])
        self.assertIsNotNone(results["worker2"])
        self.assertEqual(results["worker1"], {"result": "success"})
        self.assertTrue(results["worker2"]["completed"])

    def test_signal_protocol_compliance(self):
        """Test that all required signals are present."""
        worker = SimpleWorker()

        # Verify signal presence
        self.assertTrue(hasattr(worker, "started"))
        self.assertTrue(hasattr(worker, "progress"))
        self.assertTrue(hasattr(worker, "finished"))
        self.assertTrue(hasattr(worker, "error"))

    def test_cancellation_before_start(self):
        """Test cancelling a worker before it starts."""
        worker = CancellableWorker()
        worker.cancel()

        worker.started.connect(self._inc_started)
        worker.error.connect(lambda msg: self.signals_received["error"].append(msg))

        # Should still run but immediately detect cancellation
        worker.start()
        worker.wait(1000)
        self._flush_events()

        self.assertEqual(self.signals_received["started"], 1)
        self.assertEqual(len(self.signals_received["error"]), 1)

    def test_exception_in_do_work(self):
        """Test that exceptions in do_work are properly caught."""
        worker = ErrorWorker()
        error_messages = []

        worker.error.connect(lambda msg: error_messages.append(msg))

        worker.start()
        worker.wait(1000)
        self._flush_events()

        self.assertEqual(len(error_messages), 1)
        self.assertIn("ValueError", error_messages[0])


class TestExampleWorkers(unittest.TestCase):
    """Test suite for example worker implementations."""

    @classmethod
    def setUpClass(cls):
        """Create QCoreApplication if not already running."""
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def _flush_events(self):
        """Process queued Qt signals."""
        self.app.processEvents()
        self.app.processEvents()

    def test_example_download_worker(self):
        """Test ExampleDownloadWorker from example_worker.py."""
        from core.workers.example_worker import ExampleDownloadWorker

        worker = ExampleDownloadWorker(
            url="https://example.com/file.bin",
            destination="/tmp/file.bin",
            chunk_size=1024 * 1024  # 1 MB chunks
        )

        results = []
        errors = []
        worker.finished.connect(lambda result: results.append(result))
        worker.error.connect(lambda msg: errors.append(msg))

        worker.start()
        worker.wait(5000)
        self._flush_events()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://example.com/file.bin")
        self.assertGreater(result["bytes_downloaded"], 0)

    def test_example_download_worker_cancellation(self):
        """Test cancelling ExampleDownloadWorker."""
        from core.workers.example_worker import ExampleDownloadWorker

        worker = ExampleDownloadWorker(
            url="https://example.com/largefile.bin",
            destination="/tmp/largefile.bin",
            chunk_size=1024  # Small chunks to allow cancellation
        )

        results = []
        errors = []
        worker.finished.connect(lambda result: results.append(result))
        worker.error.connect(lambda msg: errors.append(msg))

        worker.start()
        time.sleep(0.1)  # Let it start
        worker.cancel()
        worker.wait(5000)
        self._flush_events()

        # BaseWorker cancellation emits error instead of finished result.
        self.assertEqual(len(results), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("cancelled", errors[0].lower())

    def test_example_processing_worker(self):
        """Test ExampleProcessingWorker."""
        from core.workers.example_worker import ExampleProcessingWorker

        test_data = list(range(10))
        worker = ExampleProcessingWorker(data=test_data, validate=True)

        results = []
        worker.finished.connect(lambda result: results.append(result))

        worker.start()
        worker.wait(5000)
        self._flush_events()

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result["success"])
        self.assertEqual(result["processed_count"], 10)
        self.assertTrue(result["validation_passed"])

    def test_example_processing_worker_empty_data_error(self):
        """Test ExampleProcessingWorker with empty data raises error."""
        from core.workers.example_worker import ExampleProcessingWorker

        worker = ExampleProcessingWorker(data=[], validate=False)

        errors = []
        worker.error.connect(lambda msg: errors.append(msg))

        worker.start()
        worker.wait(5000)
        self._flush_events()

        self.assertEqual(len(errors), 1)
        self.assertIn("No data to process", errors[0])


if __name__ == "__main__":
    unittest.main()
