"""
Centralized Error Handler — v29.0 "Usability & Polish"

Provides a global sys.excepthook override that catches unhandled
LoofiError subtypes, shows user-friendly dialogs with recovery hints,
and logs to the smart log system.

Usage::

    from utils.error_handler import install_error_handler
    install_error_handler()  # Call once at startup after QApplication init
"""

import logging
import sys
import traceback
from typing import Type

logger = logging.getLogger(__name__)

# Original excepthook for fallback
_original_excepthook = sys.excepthook


def _format_user_message(exc: Exception) -> str:
    """Format a user-friendly error message from a LoofiError."""
    from utils.errors import LoofiError

    if isinstance(exc, LoofiError):
        parts = [str(exc)]
        if exc.hint:
            parts.append(f"\n\n💡 Hint: {exc.hint}")
        if exc.code:
            parts.append(f"\n\nError code: {exc.code}")
        if exc.recoverable:
            parts.append(
                "\n\nThis error is recoverable — you can continue using the app."
            )
        return "".join(parts)
    return str(exc)


def _show_error_dialog(exc: Exception) -> None:
    """Show a Qt error dialog for the exception, if QApplication exists."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance()
        if not app:
            return

        from utils.errors import LoofiError

        if isinstance(exc, LoofiError):
            title = f"Loofi — {exc.code}"
            icon = (
                QMessageBox.Icon.Warning
                if exc.recoverable
                else QMessageBox.Icon.Critical
            )
        else:
            title = "Loofi — Unexpected Error"
            icon = QMessageBox.Icon.Critical

        msg = QMessageBox()
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(_format_user_message(exc))
        msg.setDetailedText(traceback.format_exc())
        msg.exec()
    except (ImportError, RuntimeError, OSError, ValueError, TypeError) as e:
        # If we can't show a dialog, just log it
        logger.debug("Failed to show error dialog: %s", e)


def _log_error(exc_type: Type[BaseException], exc_value: BaseException, exc_tb) -> None:
    """Log the exception to the logging system."""
    from utils.errors import LoofiError

    if isinstance(exc_value, LoofiError):
        logger.error(
            "LoofiError [%s]: %s (recoverable=%s)",
            exc_value.code,
            exc_value,
            exc_value.recoverable,
            exc_info=(exc_type, exc_value, exc_tb),
        )
    else:
        logger.critical(
            "Unhandled exception: %s",
            exc_value,
            exc_info=(exc_type, exc_value, exc_tb),
        )

    # Also log to NotificationCenter for in-app visibility
    try:
        from utils.notification_center import NotificationCenter

        nc = NotificationCenter()
        if isinstance(exc_value, LoofiError):
            nc.add(
                title=f"Error: {exc_value.code}",
                message=str(exc_value),
                category="system",
            )
        else:
            nc.add(
                title="Unexpected Error",
                message=str(exc_value)[:200],
                category="system",
            )
    except Exception as e:
        logger.debug("Failed to send notification for error: %s", e)


def _loofi_excepthook(
    exc_type: Type[BaseException], exc_value: BaseException, exc_tb
) -> None:
    """
    Global exception handler for unhandled exceptions.

    - LoofiError subtypes: show user-friendly dialog with hint
    - KeyboardInterrupt: pass through to original handler
    - Other exceptions: log and show generic dialog
    """
    # Don't intercept keyboard interrupts
    if issubclass(exc_type, KeyboardInterrupt):
        _original_excepthook(exc_type, exc_value, exc_tb)
        return

    # Log the error
    _log_error(exc_type, exc_value, exc_tb)

    # Show dialog (only for Exception subclasses, not SystemExit etc.)
    if issubclass(exc_type, Exception):
        assert isinstance(exc_value, Exception)
        _show_error_dialog(exc_value)


def install_error_handler() -> None:
    """
    Install the centralized error handler as sys.excepthook.

    Call this once at startup, after QApplication is created.
    Safe to call multiple times — only installs once.
    """
    if sys.excepthook is not _loofi_excepthook:
        sys.excepthook = _loofi_excepthook
        logger.debug("Centralized error handler installed")


def uninstall_error_handler() -> None:
    """Restore the original sys.excepthook. Mainly for testing."""
    sys.excepthook = _original_excepthook
