"""
Simplified tests for BaseWorker (v23.0 Architecture Hardening).

Tests basic functionality without Qt event loop complexities.
"""

import time
import unittest
from typing import Any

import os
import pytest

_SKIP_QT = os.environ.get("DISPLAY") is None and os.environ.get("WAYLAND_DISPLAY") is None

try:
    from core.workers import BaseWorker
except ImportError:
    _SKIP_QT = True

pytestmark = pytest.mark.skipif(_SKIP_QT, reason="Qt/PyQt6 not available in headless environment")


class SimpleWorker(BaseWorker):
    """Test worker that completes successfully."""

    def do_work(self) -> Any:
        time.sleep(0.05)
        return {"result": "success"}


class ErrorWorker(BaseWorker):
    """Test worker that raises an error."""

    def do_work(self) -> Any:
        raise ValueError("Intentional test error")


class CancellableWorker(BaseWorker):
    """Test worker with cancellation checking."""

    def do_work(self) -> Any:
        for i in range(10):
            if self.is_cancelled():
                return None
            time.sleep(0.02)
        return {"completed": True}


class TestBaseWorkerCore(unittest.TestCase):
    """Test core BaseWorker functionality."""

    def test_worker_completes(self):
        """Test that worker executes and completes."""
        worker = SimpleWorker()
        worker.start()
        completed = worker.wait(1000)
        self.assertTrue(completed)

    def test_get_result(self):
        """Test getting result after completion."""
        worker = SimpleWorker()
        worker.start()
        worker.wait(1000)
        result = worker.get_result()
        self.assertIsNotNone(result)
        self.assertEqual(result, {"result": "success"})

    def test_cancellation_flag(self):
        """Test cancellation flag setting."""
        worker = CancellableWorker()
        self.assertFalse(worker.is_cancelled())
        worker.cancel()
        self.assertTrue(worker.is_cancelled())

    def test_cancellation_stops_work(self):
        """Test that cancellation stops long-running work."""
        worker = CancellableWorker()
        worker.start()
        time.sleep(0.05)  # Let it start
        worker.cancel()
        worker.wait(500)
        # Worker should complete quickly after cancellation
        result = worker.get_result()
        self.assertIsNone(result)

    def test_error_handling_doesnt_crash(self):
        """Test that errors don't crash the worker."""
        worker = ErrorWorker()
        worker.start()
        completed = worker.wait(1000)
        self.assertTrue(completed)  # Should complete even with error

    def test_signal_protocol_exists(self):
        """Test that all required signals are present."""
        worker = SimpleWorker()
        self.assertTrue(hasattr(worker, "started"))
        self.assertTrue(hasattr(worker, "progress"))
        self.assertTrue(hasattr(worker, "finished"))
        self.assertTrue(hasattr(worker, "error"))

    def test_report_progress_doesnt_crash(self):
        """Test that report_progress can be called."""
        worker = SimpleWorker()
        worker.report_progress("Test message", 50)
        # If we get here, it didn't crash

    def test_multiple_workers(self):
        """Test that multiple workers can run independently."""
        worker1 = SimpleWorker()
        worker2 = SimpleWorker()

        worker1.start()
        worker2.start()

        completed1 = worker1.wait(1000)
        completed2 = worker2.wait(1000)

        self.assertTrue(completed1)
        self.assertTrue(completed2)

        self.assertEqual(worker1.get_result(), {"result": "success"})
        self.assertEqual(worker2.get_result(), {"result": "success"})

    def test_result_none_before_completion(self):
        """Test that result is None before worker completes."""
        worker = SimpleWorker()
        self.assertIsNone(worker.get_result())

    def test_cancellation_before_start(self):
        """Test cancelling before start is reset by run()."""
        worker = CancellableWorker()
        worker.cancel()
        self.assertTrue(worker.is_cancelled())
        worker.start()
        completed = worker.wait(500)
        self.assertTrue(completed)
        # Flag is reset at start of run(), so will be False after
        # (unless do_work() detects early cancellation)


if __name__ == "__main__":
    unittest.main()
