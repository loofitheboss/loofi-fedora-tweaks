from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit, QScrollArea, QFrame
from utils.process import CommandRunner
import json
import subprocess
import os

class AppsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header with Refresh Button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Essential Applications"))
        header_layout.addStretch()
        btn_refresh = QPushButton("Refresh Status")
        btn_refresh.clicked.connect(self.refresh_list)
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)
        
        # Scroll Area for apps list if it gets long
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        scroll.setWidget(self.scroll_content)
        
        layout.addWidget(scroll)
        
        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # Load Apps
        self.apps = self.load_apps()
        self.refresh_list()

        layout.addWidget(QLabel("Output Log:"))
        layout.addWidget(self.output_area)

    def load_apps(self):
        # Initial load from cache or local
        from utils.remote_config import AppConfigFetcher
        self.fetcher = AppConfigFetcher()
        self.fetcher.config_ready.connect(self.on_apps_loaded)
        self.fetcher.config_error.connect(self.on_apps_error)
        self.fetcher.start()
        return [] # Return empty initially, populated async

    def on_apps_loaded(self, apps):
        self.apps = apps
        self.refresh_list()
        self.append_output("Apps list updated from remote/cache.\n")

    def on_apps_error(self, error):
        self.append_output(f"Error loading apps: {error}\n")

    def refresh_list(self):
        # Clear existing items
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for app in self.apps:
            self.add_app_row(self.scroll_layout, app)
        self.scroll_layout.addStretch()

    def add_app_row(self, layout, app_data):
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Shape.StyledPanel)
        row_layout = QHBoxLayout()
        row_widget.setLayout(row_layout)
        
        lbl_name = QLabel(f"<b>{app_data['name']}</b>")
        lbl_desc = QLabel(app_data['desc'])
        
        btn_install = QPushButton("Install")
        
        # Check if installed
        chk_cmd = app_data.get('check_cmd')
        is_installed = False
        if chk_cmd:
            is_installed = self.check_installed(chk_cmd)
            
        if is_installed:
            btn_install.setText("Installed")
            btn_install.setEnabled(False)
            btn_install.setStyleSheet("background-color: #2ecc71; color: white;") # Green
        else:
            btn_install.clicked.connect(lambda checked, app=app_data: self.install_app(app))
        
        row_layout.addWidget(lbl_name)
        row_layout.addWidget(lbl_desc)
        row_layout.addStretch()
        row_layout.addWidget(btn_install)
        
        layout.addWidget(row_widget)

    def check_installed(self, cmd):
        try:
            # Run the check command silently
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def install_app(self, app_data):
        self.output_area.clear()
        self.append_output(f"Installing {app_data['name']}...\n")
        self.runner.run_command(app_data['cmd'], app_data['args'])

    def append_output(self, text):
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(self.output_area.textCursor().MoveOperation.End)

    def command_finished(self, exit_code):
        self.append_output(f"\nCommand finished with exit code: {exit_code}")
        # Refresh list to update status if installation succeeded
        if exit_code == 0:
            self.refresh_list()

