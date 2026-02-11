"""
Example worker implementation using BaseWorker pattern.

This demonstrates the recommended pattern for migrating ad-hoc QThread
workers to the standardized BaseWorker base class.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from core.workers import BaseWorker


class ExampleDownloadWorker(BaseWorker):
    """
    Example worker demonstrating BaseWorker usage.

    Simulates a file download with progress reporting and cancellation support.

    Args:
        url: URL to download from
        destination: Local file path for download
        chunk_size: Download chunk size in bytes (default: 1024)

    Returns:
        dict: {
            "success": bool,
            "url": str,
            "destination": str,
            "bytes_downloaded": int,
            "duration_seconds": float
        }
    """

    def __init__(self, url: str, destination: str, chunk_size: int = 1024):
        super().__init__()
        self.url = url
        self.destination = destination
        self.chunk_size = chunk_size

    def do_work(self) -> Dict[str, Any]:
        """
        Simulate downloading a file with progress reporting.

        Checks for cancellation between chunks and reports progress.
        """
        start_time = time.time()
        total_bytes = 10 * 1024 * 1024  # Simulate 10 MB file
        downloaded_bytes = 0

        self.report_progress(f"Starting download from {self.url}", 0)

        # Simulate download in chunks
        while downloaded_bytes < total_bytes:
            # Check for cancellation
            if self.is_cancelled():
                return {
                    "success": False,
                    "url": self.url,
                    "destination": self.destination,
                    "bytes_downloaded": downloaded_bytes,
                    "duration_seconds": time.time() - start_time,
                    "cancelled": True
                }

            # Simulate downloading a chunk
            chunk = min(self.chunk_size, total_bytes - downloaded_bytes)
            time.sleep(0.01)  # Simulate network latency
            downloaded_bytes += chunk

            # Report progress
            percentage = int((downloaded_bytes / total_bytes) * 100)
            mb_downloaded = downloaded_bytes / (1024 * 1024)
            mb_total = total_bytes / (1024 * 1024)
            self.report_progress(
                f"Downloading: {mb_downloaded:.2f} MB / {mb_total:.2f} MB",
                percentage
            )

        duration = time.time() - start_time
        self.report_progress("Download complete!", 100)

        return {
            "success": True,
            "url": self.url,
            "destination": self.destination,
            "bytes_downloaded": downloaded_bytes,
            "duration_seconds": duration,
            "cancelled": False
        }


class ExampleProcessingWorker(BaseWorker):
    """
    Example worker for CPU-intensive processing.

    Demonstrates:
    - Multi-step processing with progress
    - Error handling
    - Result validation

    Args:
        data: Input data to process
        validate: Whether to validate results (default: True)

    Returns:
        dict: {
            "success": bool,
            "processed_count": int,
            "validation_passed": bool
        }
    """

    def __init__(self, data: list, validate: bool = True):
        super().__init__()
        self.data = data
        self.validate = validate

    def do_work(self) -> Dict[str, Any]:
        """
        Process data in multiple steps with validation.
        """
        total_steps = len(self.data)

        if total_steps == 0:
            raise ValueError("No data to process")

        self.report_progress("Starting data processing...", 0)

        processed_count = 0
        for i, item in enumerate(self.data):
            if self.is_cancelled():
                return {
                    "success": False,
                    "processed_count": processed_count,
                    "validation_passed": False,
                    "cancelled": True
                }

            # Simulate processing
            result = self._process_item(item)
            if result:
                processed_count += 1

            # Report progress
            percentage = int(((i + 1) / total_steps) * 100)
            self.report_progress(
                f"Processed {i + 1} of {total_steps} items",
                percentage
            )

        # Validation step
        validation_passed = True
        if self.validate:
            self.report_progress("Validating results...", 95)
            validation_passed = self._validate_results(processed_count)

        return {
            "success": True,
            "processed_count": processed_count,
            "validation_passed": validation_passed,
            "cancelled": False
        }

    def _process_item(self, item: Any) -> bool:
        """Simulate processing a single item."""
        time.sleep(0.005)  # Simulate work
        return True

    def _validate_results(self, count: int) -> bool:
        """Simulate result validation."""
        time.sleep(0.1)
        return count == len(self.data)
