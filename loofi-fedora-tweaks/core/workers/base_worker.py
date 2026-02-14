"""
Base worker classes for background tasks in v23.0 Architecture Hardening.

Provides standardized QThread worker pattern with:
- Consistent signal protocol
- Progress reporting
- Error handling
- Cancellation support
- Thread-safe result passing

Usage Example:
    ```python
    from core.workers import BaseWorker
    from PyQt6.QtCore import pyqtSignal

    class DataFetchWorker(BaseWorker):
        '''Worker for fetching data from remote API.'''

        def do_work(self) -> Any:
            '''Implement the actual work logic here.'''
            # Check cancellation periodically
            if self.is_cancelled():
                return None

            # Report progress
            self.report_progress("Fetching data...", 25)

            # Do actual work
            data = fetch_from_api()

            self.report_progress("Processing data...", 75)
            result = process(data)

            return result

    # In your UI code:
    worker = DataFetchWorker()
    worker.progress.connect(lambda msg, pct: print(f"{msg} - {pct}%"))
    worker.finished.connect(lambda result: handle_result(result))
    worker.error.connect(lambda msg: show_error(msg))
    worker.start()

    # To cancel:
    worker.cancel()
    ```
"""

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.sip import wrappertype

logger = logging.getLogger(__name__)


# Resolve metaclass conflict between QThread and ABC
class _BaseWorkerMeta(wrappertype, ABCMeta):
    """Metaclass combining QThread's metaclass and ABC's metaclass."""

    pass


class BaseWorker(QThread, metaclass=_BaseWorkerMeta):
    """
    Abstract base class for background worker threads.

    Provides standardized signal protocol and lifecycle management.
    Subclasses must implement `do_work()` method.

    Signals:
        started: Emitted when work begins (no parameters)
        progress(str, int): Emitted during work (message, percentage 0-100)
        finished(Any): Emitted on successful completion (result data)
        error(str): Emitted on error (error message)

    Attributes:
        _should_stop: Internal cancellation flag
        _result: Internal storage for work result
    """

    # Standard signal protocol
    started = pyqtSignal()
    progress = pyqtSignal(str, int)  # message, percentage (0-100)
    finished = pyqtSignal(object)  # result data (Any type)
    error = pyqtSignal(str)  # error message

    def __init__(self, parent: Optional[Any] = None):
        """
        Initialize the worker.

        Args:
            parent: Optional parent QObject for Qt object hierarchy
        """
        super().__init__(parent)
        self._should_stop = False
        self._result: Optional[Any] = None

    def run(self) -> None:
        """
        QThread entry point. Do not override this method.

        Template method that handles signal emission and error handling.
        Calls `do_work()` abstract method for actual work.
        """
        self._result = None

        try:
            logger.debug("%s started", self.__class__.__name__)
            self.started.emit()

            # Call subclass implementation
            self._result = self.do_work()

            if not self._should_stop:
                logger.debug("%s completed successfully", self.__class__.__name__)
                self.finished.emit(self._result)
            else:
                logger.debug("%s cancelled", self.__class__.__name__)
                self.error.emit("Operation cancelled by user")

        except Exception as e:
            logger.error("%s error: %s", self.__class__.__name__, e, exc_info=True)
            self.error.emit(f"{type(e).__name__}: {e}")

    @abstractmethod
    def do_work(self) -> Any:
        """
        Implement the actual background work here.

        This method is called by `run()` in a background thread.
        Check `is_cancelled()` periodically for long-running operations.
        Use `report_progress()` to update progress.

        Returns:
            Any: The result of the work, passed to `finished` signal

        Raises:
            Exception: Any exception will be caught and emitted via `error` signal
        """
        pass

    def cancel(self) -> None:
        """
        Request cancellation of the worker.

        Sets the internal cancellation flag. Subclasses should check
        `is_cancelled()` periodically and return early if True.
        """
        logger.debug("Cancellation requested for %s", self.__class__.__name__)
        self._should_stop = True

    def is_cancelled(self) -> bool:
        """
        Check if cancellation has been requested.

        Returns:
            bool: True if cancellation requested, False otherwise
        """
        return self._should_stop

    def report_progress(self, message: str, percentage: int = 0) -> None:
        """
        Report progress to UI.

        Args:
            message: Progress message (e.g., "Downloading file...")
            percentage: Progress percentage 0-100 (default: 0)
        """
        if not self._should_stop:
            self.progress.emit(message, percentage)

    def get_result(self) -> Optional[Any]:
        """
        Get the result after worker has finished.

        Returns:
            Optional[Any]: The result from `do_work()`, or None if not finished
        """
        return self._result
