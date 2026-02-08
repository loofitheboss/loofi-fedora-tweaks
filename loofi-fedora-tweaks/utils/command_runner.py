from PyQt6.QtCore import QProcess, pyqtSignal, QObject
import re

from utils.log import get_logger

logger = get_logger(__name__)

class CommandRunner(QObject):
    output_received = pyqtSignal(str)
    finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(int, str) # New signal: percentage, status_text

    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_finished)
        self.process.errorOccurred.connect(self.handle_error)

    def run_command(self, command, args):
        import os
        if os.path.exists('/.flatpak-info') and command != "flatpak-spawn":
            # We are running inside Flatpak, use flatpak-spawn --host
            new_args = ["--host", command] + args
            command = "flatpak-spawn"
            args = new_args
            
        self.process.start(command, args)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        output = bytes(data).decode('utf-8')
        self.parse_progress(output)
        self.output_received.emit(output)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        output = bytes(data).decode('utf-8')
        # DNF often sends progress to stderr
        self.parse_progress(output)
        self.output_received.emit(output) # Treat stderr as output for now

    def parse_progress(self, text):
        # DNF regex for progress bar: [===       ]
        dnf_bar_match = re.search(r'\[(=+)( *)\]', text)
        if dnf_bar_match:
            equals = len(dnf_bar_match.group(1))
            spaces = len(dnf_bar_match.group(2))
            total = equals + spaces
            if total > 0:
                percent = int((equals / total) * 100)
                self.progress_update.emit(percent, "Processing...")
                return

        # DNF regex for text state (Downloading/Installing)
        if "Downloading" in text:
            self.progress_update.emit(-1, "Downloading Packages...") # -1 can mean indeterminate or just status update
            return
        if "Installing" in text:
             self.progress_update.emit(-1, "Installing...")
             return
        if "Verifying" in text:
             self.progress_update.emit(-1, "Verifying...")
             return
             
        # DNF/General Percentage: ( 45%)
        paren_percent = re.search(r'\(\s*(\d+)%\)', text)
        if paren_percent:
            try:
                percent = int(paren_percent.group(1))
                self.progress_update.emit(percent, "Processing...")
                return
            except:
                pass

        # Flatpak Percentage: 45% (often at start of line or standalone)
        flatpak_match = re.search(r'^\s*(\d+)%', text)
        if flatpak_match:
            try:
                percent = int(flatpak_match.group(1))
                self.progress_update.emit(percent, "Processing...")
                return
            except:
                pass

    def handle_finished(self, exit_code, exit_status):
        if exit_code != 0:
            logger.debug("Command finished with non-zero exit: %s", exit_code)
        self.finished.emit(exit_code)

    def handle_error(self, error):
        logger.warning("Command runner error: %s", error)
        self.error_occurred.emit(str(error))

    def stop(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
