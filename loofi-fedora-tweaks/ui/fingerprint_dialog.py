from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
from PyQt6.QtCore import QProcess, Qt
from utils.log import get_logger

logger = get_logger(__name__)

class FingerprintDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fingerprint Enrollment")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Instructions
        self.lbl_status = QLabel("Ready to enroll.\nClick 'Start Enrollment' to begin.")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 14px; margin: 10px;")
        layout.addWidget(self.lbl_status)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100) # fprintd doesn't give exact % but usually 5-7 touches?
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        
        # Step Counter
        self.lbl_steps = QLabel("Waiting...")
        self.lbl_steps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_steps)
        
        # Buttons
        self.btn_start = QPushButton("Start Enrollment")
        self.btn_start.clicked.connect(self.start_enrollment)
        layout.addWidget(self.btn_start)
        
        self.btn_cancel = QPushButton("Close")
        self.btn_cancel.clicked.connect(self.accept)
        layout.addWidget(self.btn_cancel)
        
        # Process
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.on_output)
        self.process.readyReadStandardError.connect(self.on_error)
        self.process.finished.connect(self.on_finished)
        
        self.enroll_step = 0

    def start_enrollment(self):
        self.btn_start.setEnabled(False)
        self.lbl_status.setText("Enrolling right index finger...\nPlease swipe/touch the sensor.")
        self.progress.setValue(0)
        self.enroll_step = 0
        
        # We enroll the right index finger by default for simplicity
        # Command: fprintd-enroll <user> (defaults to current user) -f right-index-finger
        self.process.start("fprintd-enroll", ["-f", "right-index-finger"])

    def on_output(self):
        data = self.process.readAllStandardOutput().data().decode().strip()
        # Parse output
        # Typical output: "Enroll result: enroll-stage-passed"
        lines = data.split('\n')
        for line in lines:
            if "enroll-stage-passed" in line:
                self.enroll_step += 1
                # Heuristic: usually requires ~5 successful touches
                new_val = min(self.enroll_step * 20, 95)
                self.progress.setValue(new_val)
                self.lbl_steps.setText(f"Successful scans: {self.enroll_step}")
                self.lbl_status.setText("Scan accepted! Lift and touch again.")
            elif "enroll-retry-scan" in line:
                 self.lbl_status.setText("Scan failed - too short or dirty. Try again.")
            elif "enroll-completed" in line:
                self.progress.setValue(100)
                self.lbl_status.setText("Enrollment Completed Successfully! 🎉")
                self.lbl_steps.setText("Done.")
                self.btn_start.setText("Enroll Again")
                self.btn_start.setEnabled(True)

    def on_error(self):
        data = self.process.readAllStandardError().data().decode().strip()
        if data:
            logger.error("Enroll error: %s", data)
            # Some prompts appear in stderr sometimes?
            if "Permission denied" in data:
                 self.lbl_status.setText("Error: Permission Denied.")

    def on_finished(self, exit_code, exit_status):
        self.btn_start.setEnabled(True)
        if exit_code != 0 and self.progress.value() < 100:
            self.lbl_status.setText(f"Enrollment failed or cancelled.")
