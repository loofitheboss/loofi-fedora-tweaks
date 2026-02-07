from PyQt6.QtCore import QProcess, pyqtSignal, QObject
import re

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
        # DNF Progress: [===                 ] ---  B/s |   0  B     --:-- ETA
        # Flatpak Progress: 45%
        
        # Simple DNF Regex (detecting the bar roughly)
        if "[" in text and "]" in text and ("ETA" in text or "B/s" in text):
            try:
                # Count '=' to guess percentage (max 20 chars usually)
                bar_content = text.split("[")[1].split("]")[0]
                equals = bar_content.count("=")
                spaces = bar_content.count(" ")
                total = equals + spaces
                if total > 0:
                    percent = int((equals / total) * 100)
                    self.progress_update.emit(percent, "Downloading/Installing...")
            except:
                pass
                
        # Flatpak Percentage Rule
        # looking for number% pattern at start or end of line
        match = re.search(r'(\d+)%', text)
        if match:
            try:
                percent = int(match.group(1))
                self.progress_update.emit(percent, "Processing...")
            except:
                pass

    def handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code)

    def handle_error(self, error):
        self.error_occurred.emit(str(error))

    def stop(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
