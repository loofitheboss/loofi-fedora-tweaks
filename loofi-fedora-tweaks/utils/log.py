"""
Centralized logging configuration for Loofi Fedora Tweaks.
Provides a consistent logger across all modules.

Usage:
    from utils.log import get_logger
    logger = get_logger(__name__)
    logger.info("Operation completed")
    logger.error("Something failed")
"""

import logging
import os
import sys
from pathlib import Path


_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_initialized = False


def _get_log_dir() -> Path:
    """Get the XDG-compliant log directory."""
    xdg_state = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    log_dir = Path(xdg_state) / "loofi-fedora-tweaks"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _setup_root_logger():
    """Configure the root logger once."""
    global _initialized
    if _initialized:
        return

    root = logging.getLogger("loofi")
    root.setLevel(logging.DEBUG)

    # Console handler (INFO and above)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    root.addHandler(console)

    # File handler (DEBUG and above)
    try:
        log_file = _get_log_dir() / "app.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
        root.addHandler(file_handler)
    except (OSError, PermissionError):
        # If we can't write logs to file, continue with console only
        root.warning("Could not create log file, using console logging only")

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given module name.

    Args:
        name: Module name, typically __name__

    Returns:
        Configured logger instance
    """
    _setup_root_logger()
    # Prefix all loggers under 'loofi' namespace
    if not name.startswith("loofi"):
        name = f"loofi.{name}"
    return logging.getLogger(name)
