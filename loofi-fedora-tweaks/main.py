import sys
import os
import argparse
import logging

# Ensure we can import from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from version import __version__

# Set up file logging so crashes are visible even when launched from desktop
LOG_DIR = os.path.expanduser("~/.local/share/loofi-fedora-tweaks")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "startup.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("loofi.main")


def _notify_error(title: str, message: str):
    """Send a desktop notification when the GUI can't start."""
    import subprocess as _sp

    try:
        _sp.Popen(
            [
                "notify-send",
                "--app-name=Loofi Fedora Tweaks",
                "--icon=dialog-error",
                title,
                message,
            ],
            stdout=_sp.DEVNULL,
            stderr=_sp.DEVNULL,
        )
    except FileNotFoundError:
        pass  # notify-send not installed, nothing we can do


def _check_pyqt6():
    """Pre-flight check for PyQt6 availability with a helpful message."""
    try:
        from PyQt6.QtWidgets import QApplication  # noqa: F401

        return True
    except ImportError as exc:
        msg = str(exc)
        if "libGL" in msg:
            from utils.install_hints import build_install_hint
            hint = (
                "PyQt6 cannot load because libGL is missing.\n"
                f"Fix:  {build_install_hint('mesa-libGL mesa-libEGL')}"
            )
        elif "No module named" in msg:
            from utils.install_hints import build_install_hint
            hint = f"PyQt6 is not installed.\nFix:  {build_install_hint('python3-pyqt6')}"
        else:
            hint = f"PyQt6 import failed: {msg}"

        _log.critical("PyQt6 check failed: %s", hint)
        print(f"ERROR: {hint}", file=sys.stderr)
        _notify_error("Loofi Fedora Tweaks — Cannot Start", hint)
        return False


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        prog="loofi-fedora-tweaks",
        description="System tweaks and maintenance for Fedora",
    )
    parser.add_argument(
        "--daemon",
        "-d",
        action="store_true",
        help="Run as background daemon for scheduled tasks",
    )
    parser.add_argument(
        "--cli",
        "-c",
        action="store_true",
        help="Run in command-line mode (pass remaining args to CLI)",
    )
    parser.add_argument(
        "--web", action="store_true", help="Run headless Loofi Web API server"
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__version__}"
    )

    args, remaining = parser.parse_known_args()

    if args.daemon:
        # Run in daemon mode
        from utils.daemon import Daemon

        Daemon.run()
    elif args.web:
        from utils.api_server import APIServer

        server = APIServer()
        server.start()
        _log.info("Loofi Web API started on %s:%s", server.host, server.port)
        try:
            while True:
                __import__("time").sleep(1)
        except KeyboardInterrupt:
            _log.info("Loofi Web API shutting down")
    elif args.cli:
        # Run CLI mode
        from cli.main import main as cli_main

        sys.exit(cli_main(remaining))
    else:
        # Run GUI
        _log.info("Starting Loofi Fedora Tweaks v%s (GUI)", __version__)

        if not _check_pyqt6():
            sys.exit(1)

        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            from PyQt6.QtCore import QTranslator, QLocale
            from ui.main_window import MainWindow
        except ImportError as exc:
            _log.critical("Failed to import GUI modules: %s", exc, exc_info=True)
            _notify_error("Loofi — Import Error", str(exc))
            sys.exit(1)

        try:
            app = QApplication(sys.argv)

            # Install centralized error handler (v29.0)
            from utils.error_handler import install_error_handler

            install_error_handler()

            # Load translations based on system locale
            locale = QLocale.system().name()
            translator = QTranslator()
            translations_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "resources",
                "translations",
            )

            if translator.load(f"loofi_{locale}", translations_path):
                app.installTranslator(translator)
            elif translator.load(f"loofi_{locale.split('_')[0]}", translations_path):
                app.installTranslator(translator)

            # Load QSS Stylesheet
            style_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "assets",
                "modern.qss",
            )
            if os.path.exists(style_file):
                with open(style_file, "r") as f:
                    app.setStyleSheet(f.read())

            window = MainWindow()
            window.show()
            _log.info("MainWindow shown successfully")
            sys.exit(app.exec())

        except (OSError, RuntimeError, ValueError, ImportError) as exc:
            _log.critical("GUI startup crashed: %s", exc, exc_info=True)
            # Try to show a Qt error dialog if QApplication exists
            try:
                if QApplication.instance():
                    QMessageBox.critical(
                        None,
                        "Loofi Fedora Tweaks — Startup Error",
                        f"The application failed to start:\n\n{exc}\n\n"
                        f"Check the log at:\n{LOG_FILE}",
                    )
            except (RuntimeError, OSError, ValueError) as e:
                _log.debug("Failed to show Qt error dialog: %s", e)
            _notify_error("Loofi — Startup Crash", str(exc))
            print(f"FATAL: {exc}", file=sys.stderr)
            print(f"Log file: {LOG_FILE}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
