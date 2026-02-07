import sys
import os
import argparse

# Ensure we can import from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        prog="loofi-fedora-tweaks",
        description="System tweaks and maintenance for Fedora"
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as background daemon for scheduled tasks"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 6.1.0"
    )
    
    args = parser.parse_args()
    
    if args.daemon:
        # Run in daemon mode
        from utils.daemon import Daemon
        Daemon.run()
    else:
        # Run GUI
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTranslator, QLocale
        from ui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        
        # Load translations based on system locale
        locale = QLocale.system().name()  # Returns 'sv_SE', 'en_US', etc.
        translator = QTranslator()
        translations_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "translations")
        
        # Try to load locale-specific translation, fallback to language only
        if translator.load(f"loofi_{locale}", translations_path):
            app.installTranslator(translator)
        elif translator.load(f"loofi_{locale.split('_')[0]}", translations_path):
            app.installTranslator(translator)
        
        # Load QSS Stylesheet
        style_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "style.qss")
        if os.path.exists(style_file):
            with open(style_file, "r") as f:
                app.setStyleSheet(f.read())
                
        window = MainWindow()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
