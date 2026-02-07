"""
Scheduler Tab - UI for managing scheduled automation tasks.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QDialog, QFormLayout, QComboBox, QLineEdit,
    QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.scheduler import TaskScheduler, ScheduledTask, TaskAction, TaskSchedule
import uuid


class AddTaskDialog(QDialog):
    """Dialog for adding a new scheduled task."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Add Scheduled Task"))
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # Task name
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText(self.tr("e.g., Daily Cleanup"))
        layout.addRow(self.tr("Task Name:"), self.txt_name)
        
        # Action
        self.cmb_action = QComboBox()
        self.cmb_action.addItem(self.tr("🧹 System Cleanup"), TaskAction.CLEANUP.value)
        self.cmb_action.addItem(self.tr("📦 Check for Updates"), TaskAction.UPDATE_CHECK.value)
        self.cmb_action.addItem(self.tr("☁️ Sync Config to Cloud"), TaskAction.SYNC_CONFIG.value)
        self.cmb_action.addItem(self.tr("💾 Apply Preset"), TaskAction.APPLY_PRESET.value)
        self.cmb_action.currentIndexChanged.connect(self.on_action_changed)
        layout.addRow(self.tr("Action:"), self.cmb_action)
        
        # Preset selector (for apply_preset action)
        self.cmb_preset = QComboBox()
        self.load_presets()
        self.cmb_preset.setVisible(False)
        self.lbl_preset = QLabel(self.tr("Preset:"))
        self.lbl_preset.setVisible(False)
        layout.addRow(self.lbl_preset, self.cmb_preset)
        
        # Schedule
        self.cmb_schedule = QComboBox()
        self.cmb_schedule.addItem(self.tr("⏰ Hourly"), TaskSchedule.HOURLY.value)
        self.cmb_schedule.addItem(self.tr("📅 Daily"), TaskSchedule.DAILY.value)
        self.cmb_schedule.addItem(self.tr("📆 Weekly"), TaskSchedule.WEEKLY.value)
        self.cmb_schedule.addItem(self.tr("🚀 On System Boot"), TaskSchedule.ON_BOOT.value)
        self.cmb_schedule.addItem(self.tr("🔋 On Battery"), TaskSchedule.ON_BATTERY.value)
        self.cmb_schedule.addItem(self.tr("🔌 On AC Power"), TaskSchedule.ON_AC.value)
        self.cmb_schedule.setCurrentIndex(1)  # Default to daily
        layout.addRow(self.tr("Schedule:"), self.cmb_schedule)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_cancel = QPushButton(self.tr("Cancel"))
        btn_cancel.clicked.connect(self.reject)
        
        btn_add = QPushButton(self.tr("Add Task"))
        btn_add.clicked.connect(self.accept)
        btn_add.setDefault(True)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_add)
        layout.addRow(btn_layout)
    
    def load_presets(self):
        """Load available presets into combo box."""
        from utils.presets import PresetManager
        manager = PresetManager()
        presets = manager.list_presets()
        self.cmb_preset.addItems(presets)
    
    def on_action_changed(self, index):
        """Show/hide preset selector based on action."""
        is_preset = self.cmb_action.currentData() == TaskAction.APPLY_PRESET.value
        self.cmb_preset.setVisible(is_preset)
        self.lbl_preset.setVisible(is_preset)
    
    def get_task(self) -> ScheduledTask:
        """Get the configured task."""
        preset_name = None
        if self.cmb_action.currentData() == TaskAction.APPLY_PRESET.value:
            preset_name = self.cmb_preset.currentText()
        
        return ScheduledTask(
            id=str(uuid.uuid4())[:8],
            name=self.txt_name.text(),
            action=self.cmb_action.currentData(),
            schedule=self.cmb_schedule.currentData(),
            enabled=True,
            preset_name=preset_name
        )


class SchedulerTab(QWidget):
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # Header
        header = QLabel(self.tr("⏰ Scheduler"))
        header.setObjectName("header")
        layout.addWidget(header)
        
        layout.addWidget(QLabel(self.tr("Automate tasks like cleanup, updates, and syncing.")))
        
        # Service status
        self.create_service_section(layout)
        
        # Task list
        self.create_tasks_section(layout)
        
        # Refresh data
        self.refresh_all()
    
    def create_service_section(self, parent_layout):
        """Create the service status section."""
        group = QGroupBox(self.tr("🔧 Background Service"))
        layout = QHBoxLayout(group)
        
        self.lbl_service_status = QLabel()
        layout.addWidget(self.lbl_service_status)
        
        layout.addStretch()
        
        self.btn_service_toggle = QPushButton()
        self.btn_service_toggle.clicked.connect(self.toggle_service)
        layout.addWidget(self.btn_service_toggle)
        
        parent_layout.addWidget(group)
    
    def create_tasks_section(self, parent_layout):
        """Create the task list section."""
        group = QGroupBox(self.tr("📋 Scheduled Tasks"))
        layout = QVBoxLayout(group)
        
        # Task list
        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(200)
        layout.addWidget(self.task_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton(self.tr("➕ Add Task"))
        btn_add.clicked.connect(self.add_task)
        btn_layout.addWidget(btn_add)
        
        btn_toggle = QPushButton(self.tr("⏯️ Toggle Selected"))
        btn_toggle.clicked.connect(self.toggle_task)
        btn_layout.addWidget(btn_toggle)
        
        btn_run = QPushButton(self.tr("▶️ Run Now"))
        btn_run.clicked.connect(self.run_task_now)
        btn_layout.addWidget(btn_run)
        
        btn_delete = QPushButton(self.tr("🗑️ Delete"))
        btn_delete.clicked.connect(self.delete_task)
        btn_layout.addWidget(btn_delete)
        
        layout.addLayout(btn_layout)
        parent_layout.addWidget(group)
    
    def refresh_all(self):
        """Refresh service status and task list."""
        self.refresh_service_status()
        self.refresh_task_list()
    
    def refresh_service_status(self):
        """Update service status display."""
        is_enabled = TaskScheduler.is_service_enabled()
        is_running = TaskScheduler.is_service_running()
        
        if is_running:
            self.lbl_service_status.setText(self.tr("✅ Service is running"))
            self.lbl_service_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.btn_service_toggle.setText(self.tr("⏹️ Stop Service"))
        elif is_enabled:
            self.lbl_service_status.setText(self.tr("⚠️ Service is enabled but not running"))
            self.lbl_service_status.setStyleSheet("color: #f9e2af; font-weight: bold;")
            self.btn_service_toggle.setText(self.tr("▶️ Start Service"))
        else:
            self.lbl_service_status.setText(self.tr("❌ Service is not enabled"))
            self.lbl_service_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
            self.btn_service_toggle.setText(self.tr("▶️ Enable & Start"))
    
    def refresh_task_list(self):
        """Update task list display."""
        self.task_list.clear()
        
        tasks = TaskScheduler.list_tasks()
        
        if not tasks:
            item = QListWidgetItem(self.tr("No scheduled tasks. Click 'Add Task' to create one."))
            item.setForeground(Qt.GlobalColor.gray)
            self.task_list.addItem(item)
            return
        
        for task in tasks:
            status = "✅" if task.enabled else "⏸️"
            schedule_icon = self.get_schedule_icon(task.schedule)
            action_icon = self.get_action_icon(task.action)
            
            text = f"{status} {task.name}  |  {action_icon} {task.action}  |  {schedule_icon} {task.schedule}"
            
            if task.last_run:
                text += f"  |  Last: {task.last_run[:16]}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.task_list.addItem(item)
    
    def get_schedule_icon(self, schedule: str) -> str:
        icons = {
            "hourly": "⏰", "daily": "📅", "weekly": "📆",
            "on_boot": "🚀", "on_battery": "🔋", "on_ac": "🔌"
        }
        return icons.get(schedule, "📋")
    
    def get_action_icon(self, action: str) -> str:
        icons = {
            "cleanup": "🧹", "update_check": "📦",
            "sync_config": "☁️", "apply_preset": "💾"
        }
        return icons.get(action, "⚙️")
    
    def toggle_service(self):
        """Toggle the background service."""
        if TaskScheduler.is_service_running() or TaskScheduler.is_service_enabled():
            if TaskScheduler.disable_service():
                QMessageBox.information(self, self.tr("Service Disabled"), self.tr("Background service has been stopped."))
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to stop service."))
        else:
            if TaskScheduler.enable_service():
                QMessageBox.information(self, self.tr("Service Enabled"), self.tr("Background service is now running."))
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to start service. Make sure the service file is installed."))
        
        self.refresh_service_status()
    
    def add_task(self):
        """Open dialog to add a new task."""
        dialog = AddTaskDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task = dialog.get_task()
            
            if not task.name:
                QMessageBox.warning(self, self.tr("Invalid Task"), self.tr("Please enter a task name."))
                return
            
            if TaskScheduler.add_task(task):
                self.refresh_task_list()
                QMessageBox.information(self, self.tr("Task Added"), self.tr("Task '{}' has been scheduled.").format(task.name))
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to add task."))
    
    def toggle_task(self):
        """Toggle the selected task on/off."""
        item = self.task_list.currentItem()
        if not item:
            return
        
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
        
        new_state = not task.enabled
        if TaskScheduler.enable_task(task.id, new_state):
            self.refresh_task_list()
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to toggle task."))
    
    def run_task_now(self):
        """Run the selected task immediately."""
        item = self.task_list.currentItem()
        if not item:
            return
        
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
        
        confirm = QMessageBox.question(
            self, self.tr("Run Task Now?"),
            self.tr("Run '{}' immediately?").format(task.name)
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            success, message = TaskScheduler.execute_task(task)
            
            if success:
                QMessageBox.information(self, self.tr("Task Complete"), message)
            else:
                QMessageBox.warning(self, self.tr("Task Failed"), message)
            
            self.refresh_task_list()
    
    def delete_task(self):
        """Delete the selected task."""
        item = self.task_list.currentItem()
        if not item:
            return
        
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
        
        confirm = QMessageBox.question(
            self, self.tr("Delete Task?"),
            self.tr("Delete scheduled task '{}'?").format(task.name)
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            if TaskScheduler.remove_task(task.id):
                self.refresh_task_list()
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to delete task."))
