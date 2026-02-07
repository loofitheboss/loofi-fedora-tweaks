from PyQt6.QtCore import QProcess, pyqtSignal, QObject

class CommandRunner(QObject):
    output_received = pyqtSignal(str)
    finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_finished)
        self.process.errorOccurred.connect(self.handle_error)

    def run_command(self, command, args):
        import os
        if os.path.exists('/.flatpak-info'):
            # We are running inside Flatpak, use flatpak-spawn --host
            # Prepend flatpak-spawn --host to the command
            new_args = ["--host", command] + args
            command = "flatpak-spawn"
            args = new_args
            
        self.process.start(command, args)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        output = bytes(data).decode('utf-8')
        self.output_received.emit(output)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        output = bytes(data).decode('utf-8')
        self.output_received.emit(output) # Treat stderr as output for now

    def handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code)

    def handle_error(self, error):
        self.error_occurred.emit(str(error))

    def stop(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
