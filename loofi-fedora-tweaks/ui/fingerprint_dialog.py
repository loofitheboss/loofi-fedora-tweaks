from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QProgressBar
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
from utils.fingerprint import FingerprintWorker

class FingerprintDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fingerprint Enrollment")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Icon / Instructions
        self.lbl_icon = QLabel("👆") # Placeholder, could be an image
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 64px;")
        layout.addWidget(self.lbl_icon)
        
        self.lbl_status = QLabel("Ready to enroll Right Index Finger...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 5) # strict 5 steps for fprintd-enroll usually
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Buttons
        self.btn_start = QPushButton("Start Enrollment")
        self.btn_start.clicked.connect(self.start_enrollment)
        layout.addWidget(self.btn_start)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        layout.addWidget(self.btn_cancel)
        
        self.worker = None

    def start_enrollment(self):
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.lbl_status.setText("Initializing...")
        
        self.worker = FingerprintWorker() # Default: right-index-finger
        self.worker.progress_update.connect(self.update_status)
        self.worker.enroll_success.connect(self.on_success)
        self.worker.enroll_fail.connect(self.on_fail)
        self.worker.start()

    def update_status(self, text):
        self.lbl_status.setText(text)
        
        # Parse progress
        # "Enrollment scan 1 of 5"
        if "scan" in text and "of" in text:
            try:
                parts = text.split()
                # Find the number before "of"
                idx = parts.index("of")
                current = int(parts[idx-1])
                self.progress.setValue(current)
            except:
                pass

    def on_success(self):
        self.progress.setValue(5)
        self.lbl_status.setText("Enrollment Complete! 🎉")
        self.lbl_status.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
        self.btn_cancel.setText("Close")
        self.btn_start.hide()
        QMessageBox.information(self, "Success", "Fingerprint enrolled successfully.")

    def on_fail(self, error):
        self.lbl_status.setText(f"Error: {error}")
        self.lbl_status.setStyleSheet("color: red;")
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Retry")

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
        super().reject()
