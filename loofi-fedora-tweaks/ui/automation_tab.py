"""
Automation Tab - Consolidated Scheduler + Replicator interface.
Part of v11.0 "Aurora Update" - merges Scheduler and Replicator tabs.

Sub-tabs:
- Scheduler: Manage scheduled automation tasks (cleanup, updates, sync, presets)
- Replicator: Export system config as Ansible playbooks and Kickstart files
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QDialog, QFormLayout, QComboBox, QLineEdit,
    QCheckBox, QTabWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs, CONTENT_MARGINS
from core.plugins.metadata import PluginMetadata
from utils.scheduler import TaskScheduler, ScheduledTask, TaskAction, TaskSchedule
from utils.ansible_export import AnsibleExporter
from utils.kickstart import KickstartGenerator
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
        self.cmb_action.addItem(self.tr("System Cleanup"), TaskAction.CLEANUP.value)
        self.cmb_action.addItem(self.tr("Check for Updates"), TaskAction.UPDATE_CHECK.value)
        self.cmb_action.addItem(self.tr("Sync Config to Cloud"), TaskAction.SYNC_CONFIG.value)
        self.cmb_action.addItem(self.tr("Apply Preset"), TaskAction.APPLY_PRESET.value)
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
        self.cmb_schedule.addItem(self.tr("Hourly"), TaskSchedule.HOURLY.value)
        self.cmb_schedule.addItem(self.tr("Daily"), TaskSchedule.DAILY.value)
        self.cmb_schedule.addItem(self.tr("Weekly"), TaskSchedule.WEEKLY.value)
        self.cmb_schedule.addItem(self.tr("On System Boot"), TaskSchedule.ON_BOOT.value)
        self.cmb_schedule.addItem(self.tr("On Battery"), TaskSchedule.ON_BATTERY.value)
        self.cmb_schedule.addItem(self.tr("On AC Power"), TaskSchedule.ON_AC.value)
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


class AutomationTab(BaseTab):
    """Consolidated Automation tab: Scheduler + Replicator."""

    _METADATA = PluginMetadata(
        id="automation",
        name="Automation",
        description="Schedule tasks and replicate system configurations automatically.",
        category="Automation",
        icon="⏰",
        badge="",
        order=20,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        self.init_ui()

        # Refresh scheduler data
        self.refresh_all()

    def init_ui(self):
        """Initialize the UI with sub-tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*CONTENT_MARGINS)

        # Sub-tab widget
        self.sub_tabs = QTabWidget()
        configure_top_tabs(self.sub_tabs)
        layout.addWidget(self.sub_tabs)

        # Sub-tab 1: Scheduler (from SchedulerTab)
        self.sub_tabs.addTab(
            self._create_scheduler_tab(), self.tr("Scheduler")
        )

        # Sub-tab 2: Replicator (from ReplicatorTab)
        self.sub_tabs.addTab(
            self._create_replicator_tab(), self.tr("Replicator")
        )

        # Shared output area at bottom
        self.add_output_section(layout)

    # ================================================================
    # SCHEDULER SUB-TAB (from SchedulerTab)
    # ================================================================

    def _create_scheduler_tab(self) -> QWidget:
        """Create the Scheduler sub-tab content."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel(self.tr("Scheduler"))
        header.setObjectName("header")
        layout.addWidget(header)

        layout.addWidget(QLabel(self.tr(
            "Automate tasks like cleanup, updates, and syncing."
        )))

        # Service status
        self._create_service_section(layout)

        # Task list
        self._create_tasks_section(layout)

        layout.addStretch()
        return widget

    def _create_service_section(self, parent_layout):
        """Create the service status section."""
        group = QGroupBox(self.tr("Background Service"))
        layout = QHBoxLayout(group)

        self.lbl_service_status = QLabel()
        layout.addWidget(self.lbl_service_status)

        layout.addStretch()

        self.btn_service_toggle = QPushButton()
        self.btn_service_toggle.clicked.connect(self.toggle_service)
        layout.addWidget(self.btn_service_toggle)

        parent_layout.addWidget(group)

    def _create_tasks_section(self, parent_layout):
        """Create the task list section."""
        group = QGroupBox(self.tr("Scheduled Tasks"))
        layout = QVBoxLayout(group)

        # Task list
        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(200)
        layout.addWidget(self.task_list)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_add = QPushButton(self.tr("Add Task"))
        btn_add.clicked.connect(self.add_task)
        btn_layout.addWidget(btn_add)

        btn_toggle = QPushButton(self.tr("Toggle Selected"))
        btn_toggle.clicked.connect(self.toggle_task)
        btn_layout.addWidget(btn_toggle)

        btn_run = QPushButton(self.tr("Run Now"))
        btn_run.clicked.connect(self.run_task_now)
        btn_layout.addWidget(btn_run)

        btn_delete = QPushButton(self.tr("Delete"))
        btn_delete.clicked.connect(self.delete_task)
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)
        parent_layout.addWidget(group)

    # -- Scheduler actions --

    def refresh_all(self):
        """Refresh service status and task list."""
        self.refresh_service_status()
        self.refresh_task_list()

    def refresh_service_status(self):
        """Update service status display."""
        is_enabled = TaskScheduler.is_service_enabled()
        is_running = TaskScheduler.is_service_running()

        if is_running:
            self.lbl_service_status.setText(self.tr("Service is running"))
            self.lbl_service_status.setStyleSheet("color: #3dd68c; font-weight: bold;")
            self.btn_service_toggle.setText(self.tr("Stop Service"))
        elif is_enabled:
            self.lbl_service_status.setText(self.tr("Service is enabled but not running"))
            self.lbl_service_status.setStyleSheet("color: #e8b84d; font-weight: bold;")
            self.btn_service_toggle.setText(self.tr("Start Service"))
        else:
            self.lbl_service_status.setText(self.tr("Service is not enabled"))
            self.lbl_service_status.setStyleSheet("color: #e8556d; font-weight: bold;")
            self.btn_service_toggle.setText(self.tr("Enable & Start"))

    def refresh_task_list(self):
        """Update task list display."""
        self.task_list.clear()

        tasks = TaskScheduler.list_tasks()

        if not tasks:
            item = QListWidgetItem(
                self.tr("No scheduled tasks. Click 'Add Task' to create one.")
            )
            item.setForeground(QColor("#9da7bf"))
            self.task_list.addItem(item)
            return

        for task in tasks:
            status = "Enabled" if task.enabled else "Paused"
            schedule_icon = self._get_schedule_icon(task.schedule)
            action_icon = self._get_action_icon(task.action)

            text = self.tr("[{}] {} | {} {} | {} {}").format(
                status, task.name, action_icon, task.action,
                schedule_icon, task.schedule
            )

            if task.last_run:
                text += self.tr(" | Last: {}").format(task.last_run[:16])

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.task_list.addItem(item)

    def _get_schedule_icon(self, schedule: str) -> str:
        """Get icon for schedule type."""
        icons = {
            "hourly": "Hourly", "daily": "Daily", "weekly": "Weekly",
            "on_boot": "Boot", "on_battery": "Battery", "on_ac": "AC"
        }
        return icons.get(schedule, schedule)

    def _get_action_icon(self, action: str) -> str:
        """Get icon for action type."""
        icons = {
            "cleanup": "Cleanup", "update_check": "Update",
            "sync_config": "Sync", "apply_preset": "Preset"
        }
        return icons.get(action, action)

    def toggle_service(self):
        """Toggle the background service."""
        if TaskScheduler.is_service_running() or TaskScheduler.is_service_enabled():
            if TaskScheduler.disable_service():
                QMessageBox.information(
                    self, self.tr("Service Disabled"),
                    self.tr("Background service has been stopped.")
                )
            else:
                QMessageBox.warning(
                    self, self.tr("Error"),
                    self.tr("Failed to stop service.")
                )
        else:
            if TaskScheduler.enable_service():
                QMessageBox.information(
                    self, self.tr("Service Enabled"),
                    self.tr("Background service is now running.")
                )
            else:
                QMessageBox.warning(
                    self, self.tr("Error"),
                    self.tr("Failed to start service. Make sure the service file is installed.")
                )

        self.refresh_service_status()

    def add_task(self):
        """Open dialog to add a new task."""
        dialog = AddTaskDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            task = dialog.get_task()

            if not task.name:
                QMessageBox.warning(
                    self, self.tr("Invalid Task"),
                    self.tr("Please enter a task name.")
                )
                return

            if TaskScheduler.add_task(task):
                self.refresh_task_list()
                QMessageBox.information(
                    self, self.tr("Task Added"),
                    self.tr("Task '{}' has been scheduled.").format(task.name)
                )
            else:
                QMessageBox.warning(
                    self, self.tr("Error"),
                    self.tr("Failed to add task.")
                )

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
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("Failed to toggle task.")
            )

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
                QMessageBox.warning(
                    self, self.tr("Error"), self.tr("Failed to delete task.")
                )

    # ================================================================
    # REPLICATOR SUB-TAB (from ReplicatorTab)
    # ================================================================

    def _create_replicator_tab(self) -> QWidget:
        """Create the Replicator sub-tab content."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        rep_layout = QVBoxLayout(container)
        rep_layout.setSpacing(15)

        # Header
        header = QLabel(self.tr("Replicator - Infrastructure as Code"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        rep_layout.addWidget(header)

        info = QLabel(self.tr(
            "Export your system configuration to recreate it on any machine.\n"
            "No Loofi needed on the target - just standard tools."
        ))
        info.setWordWrap(True)
        info.setStyleSheet("color: #9da7bf; margin-bottom: 10px;")
        rep_layout.addWidget(info)

        # Ansible section
        rep_layout.addWidget(self._create_ansible_section())

        # Kickstart section
        rep_layout.addWidget(self._create_kickstart_section())

        rep_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_ansible_section(self) -> QGroupBox:
        """Create Ansible export section."""
        group = QGroupBox(self.tr("Ansible Playbook"))
        layout = QVBoxLayout(group)

        desc = QLabel(self.tr(
            "Generate a standard Ansible playbook that installs your packages, "
            "Flatpaks, and applies your settings on any Fedora/RHEL machine."
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        # Options
        opts_layout = QHBoxLayout()

        self.ansible_packages = QCheckBox(self.tr("DNF Packages"))
        self.ansible_packages.setChecked(True)
        opts_layout.addWidget(self.ansible_packages)

        self.ansible_flatpaks = QCheckBox(self.tr("Flatpak Apps"))
        self.ansible_flatpaks.setChecked(True)
        opts_layout.addWidget(self.ansible_flatpaks)

        self.ansible_settings = QCheckBox(self.tr("GNOME Settings"))
        self.ansible_settings.setChecked(True)
        opts_layout.addWidget(self.ansible_settings)

        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # Preview / Export buttons
        btn_layout = QHBoxLayout()

        preview_btn = QPushButton(self.tr("Preview"))
        preview_btn.clicked.connect(self._preview_ansible)
        btn_layout.addWidget(preview_btn)

        export_btn = QPushButton(self.tr("Export"))
        export_btn.setStyleSheet("background-color: #3dd68c; color: #0b0e14; font-weight: bold;")
        export_btn.clicked.connect(self._export_ansible)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_kickstart_section(self) -> QGroupBox:
        """Create Kickstart export section."""
        group = QGroupBox(self.tr("Kickstart File"))
        layout = QVBoxLayout(group)

        desc = QLabel(self.tr(
            "Generate an Anaconda Kickstart file for automated Fedora installation. "
            "Use this with inst.ks= during installation."
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9da7bf;")
        layout.addWidget(desc)

        # Options
        opts_layout = QHBoxLayout()

        self.ks_packages = QCheckBox(self.tr("DNF Packages"))
        self.ks_packages.setChecked(True)
        opts_layout.addWidget(self.ks_packages)

        self.ks_flatpaks = QCheckBox(self.tr("Flatpak Apps"))
        self.ks_flatpaks.setChecked(True)
        opts_layout.addWidget(self.ks_flatpaks)

        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # Preview / Export buttons
        btn_layout = QHBoxLayout()

        preview_btn = QPushButton(self.tr("Preview"))
        preview_btn.clicked.connect(self._preview_kickstart)
        btn_layout.addWidget(preview_btn)

        export_btn = QPushButton(self.tr("Export"))
        export_btn.setStyleSheet("background-color: #3dd68c; color: #0b0e14; font-weight: bold;")
        export_btn.clicked.connect(self._export_kickstart)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    # -- Replicator actions --

    def _preview_ansible(self):
        """Preview the generated Ansible playbook."""
        content = AnsibleExporter.generate_playbook(
            include_packages=self.ansible_packages.isChecked(),
            include_flatpaks=self.ansible_flatpaks.isChecked(),
            include_settings=self.ansible_settings.isChecked()
        )
        self.output_area.setText(content[:3000] + "\n\n... (truncated)")
        self.append_output(
            self.tr("\nPreview generated. Full content will be in exported file.")
        )

    def _export_ansible(self):
        """Export Ansible playbook to file."""
        result = AnsibleExporter.save_playbook(
            include_packages=self.ansible_packages.isChecked(),
            include_flatpaks=self.ansible_flatpaks.isChecked(),
            include_settings=self.ansible_settings.isChecked()
        )

        self.append_output(result.message + "\n")

        if result.success:
            QMessageBox.information(
                self,
                self.tr("Ansible Playbook Exported"),
                self.tr(
                    "Playbook saved to:\n{}\n\n"
                    "Run with:\n"
                    "  cd ~/loofi-playbook\n"
                    "  ansible-playbook site.yml --ask-become-pass"
                ).format(result.data['path'])
            )

    def _preview_kickstart(self):
        """Preview the generated Kickstart file."""
        content = KickstartGenerator.generate_kickstart(
            include_packages=self.ks_packages.isChecked(),
            include_flatpaks=self.ks_flatpaks.isChecked()
        )
        self.output_area.setText(content[:3000] + "\n\n... (truncated)")
        self.append_output(
            self.tr("\nPreview generated. Full content will be in exported file.")
        )

    def _export_kickstart(self):
        """Export Kickstart file."""
        result = KickstartGenerator.save_kickstart(
            include_packages=self.ks_packages.isChecked(),
            include_flatpaks=self.ks_flatpaks.isChecked()
        )

        self.append_output(result.message + "\n")

        if result.success:
            QMessageBox.information(
                self,
                self.tr("Kickstart File Exported"),
                self.tr(
                    "Kickstart saved to:\n{}\n\n"
                    "Use during installation with:\n"
                    "  inst.ks=file:///path/to/loofi.ks"
                ).format(result.data['path'])
            )
