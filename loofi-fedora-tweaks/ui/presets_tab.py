from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QMessageBox, QInputDialog, QGroupBox
)
from utils.presets import PresetManager

class PresetsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = PresetManager()
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        layout.addWidget(QLabel("<h2>User Presets</h2>"))
        layout.addWidget(QLabel("Save your current system state (Theme, Power, Battery) and restore it later."))
        
        # List Area
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("Load Selected")
        self.btn_load.clicked.connect(self.load_preset)
        
        self.btn_save = QPushButton("Save Current State")
        self.btn_save.clicked.connect(self.save_preset)
        
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.clicked.connect(self.delete_delete)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        
        layout.addLayout(btn_layout)
        
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        presets = self.manager.list_presets()
        self.list_widget.addItems(presets)

    def save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if ok and name:
            if self.manager.save_preset(name):
                self.refresh_list()
                QMessageBox.information(self, "Success", f"Preset '{name}' saved successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to save preset.")

    def load_preset(self):
        item = self.list_widget.currentItem()
        if not item:
            return
            
        name = item.text()
        data = self.manager.load_preset(name)
        if data:
            QMessageBox.information(self, "Success", f"Preset '{name}' loaded.\nThemes applied.")
        else:
            QMessageBox.warning(self, "Error", f"Failed to load preset '{name}'.")

    def delete_delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
            
        name = item.text()
        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete preset '{name}'?")
        if confirm == QMessageBox.StandardButton.Yes:
            if self.manager.delete_preset(name):
                self.refresh_list()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete preset.")
