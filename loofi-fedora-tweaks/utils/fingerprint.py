import subprocess
import re
from PyQt6.QtCore import QThread, pyqtSignal

class FingerprintWorker(QThread):
    progress_update = pyqtSignal(str) # "Center your finger", "Enrollment scan 1 of 5", etc.
    enroll_success = pyqtSignal()
    enroll_fail = pyqtSignal(str) # Error message
    
    def __init__(self, finger="right-index-finger"):
        super().__init__()
        self.finger = finger
        self.is_running = True

    def run(self):
        # fprintd-enroll outputs to stdout/stderr.
        # Example output:
        # Using device /net/reactivated/Fprint/Device/0
        # Enrolling right-index-finger finger.
        # Enrollment scan 1 of 5
        # Enrollment scan 2 of 5
        # Enrollment completed
        
        cmd = ["fprintd-enroll", "-f", self.finger]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1 # Line buffered
            )
            
            while self.is_running:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                    
                self.progress_update.emit(line)
                
                if "Enrollment completed" in line:
                    self.enroll_success.emit()
                    return
                elif "failed" in line.lower() or "error" in line.lower():
                    self.enroll_fail.emit(line)
                    return
            
            process.terminate()

        except Exception as e:
            self.enroll_fail.emit(str(e))

    def stop(self):
        self.is_running = False
        self.wait()
