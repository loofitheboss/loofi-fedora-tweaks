"""
Maintenance Tab - Consolidated tab merging Updates, Cleanup, and Overlays.
Part of v11.0 "Aurora Update".

Uses QTabWidget for sub-navigation to preserve all features from the
original UpdatesTab, CleanupTab, and OverlaysTab.
The Overlays sub-tab is only shown on Atomic (rpm-ostree) systems.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QGroupBox, QProgressBar, QTabWidget, QListWidget, QListWidgetItem,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs
from utils.command_runner import CommandRunner
from utils.system import SystemManager
from core.plugins.metadata import PluginMetadata

import shutil


# ---------------------------------------------------------------------------
# Sub-tab: Updates
# ---------------------------------------------------------------------------

class _UpdatesSubTab(QWidget):
    """Sub-tab containing all system update functionality.

    Preserves every feature from the original UpdatesTab:
    - Update All (DNF + Flatpak + Firmware) with sequential queue
    - Individual DNF / Flatpak / Firmware update buttons
    - Kernel Management (list / remove old kernels)
    - Progress bar with status text
    - Output log
    """

    def __init__(self):
        super().__init__()
        self.package_manager = SystemManager.get_package_manager()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("System Updates"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)

        # Update All Button (Prominent)
        self.btn_update_all = QPushButton(
            self.tr("\U0001f504 Update All (DNF + Flatpak + Firmware)")
        )
        self.btn_update_all.setStyleSheet(
            "font-size: 14px; padding: 10px; "
            "background-color: #3daee9; color: white;"
        )
        self.btn_update_all.clicked.connect(self.run_update_all)
        layout.addWidget(self.btn_update_all)

        # Individual Update Buttons
        btn_layout = QHBoxLayout()

        if self.package_manager == "rpm-ostree":
            self.btn_dnf = QPushButton(self.tr("Update System (rpm-ostree)"))
        else:
            self.btn_dnf = QPushButton(self.tr("Update System (DNF)"))
        self.btn_dnf.clicked.connect(self.run_dnf_update)
        btn_layout.addWidget(self.btn_dnf)

        self.btn_flatpak = QPushButton(self.tr("Update Flatpaks"))
        self.btn_flatpak.clicked.connect(self.run_flatpak_update)
        btn_layout.addWidget(self.btn_flatpak)

        self.btn_fw = QPushButton(self.tr("Update Firmware"))
        self.btn_fw.clicked.connect(self.run_fw_update)
        btn_layout.addWidget(self.btn_fw)

        layout.addLayout(btn_layout)

        # Kernel Management Group
        kernel_group = QGroupBox(self.tr("Kernel Management"))
        kernel_layout = QHBoxLayout()
        kernel_group.setLayout(kernel_layout)

        btn_list_kernels = QPushButton(self.tr("List Installed Kernels"))
        btn_list_kernels.clicked.connect(
            lambda: self.run_single_command(
                "rpm", ["-qa", "kernel"],
                self.tr("Listing Installed Kernels...")
            )
        )
        kernel_layout.addWidget(btn_list_kernels)

        btn_remove_old = QPushButton(self.tr("Remove Old Kernels"))
        btn_remove_old.clicked.connect(
            lambda: self.run_single_command(
                "pkexec", ["dnf", "remove", "--oldinstallonly", "-y"],
                self.tr("Removing Old Kernels...")
            )
        )
        kernel_layout.addWidget(btn_remove_old)

        layout.addWidget(kernel_group)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v")
        layout.addWidget(self.progress_bar)

        # Output Area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

        # Command runner
        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.progress_update.connect(self.update_progress)
        self.runner.finished.connect(self.command_finished)

        self.update_queue = []
        self.current_update_index = 0

    # -- Progress ----------------------------------------------------------

    def update_progress(self, percent, status):
        if percent == -1:
            if self.progress_bar.value() == 0 or self.progress_bar.value() == 100:
                self.progress_bar.setRange(0, 0)  # Indeterminate
            self.progress_bar.setFormat(f"{status}")
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{percent}% - {status}")

    # -- Individual update actions -----------------------------------------

    @staticmethod
    def _system_update_step(package_manager):
        if package_manager == "rpm-ostree":
            return ("pkexec", ["rpm-ostree", "upgrade"], "Starting System Upgrade...")
        return (
            "pkexec",
            [package_manager, "update", "-y"],
            "Starting System Update...",
        )

    def run_dnf_update(self):
        from utils.safety import SafetyManager

        if self.package_manager == "dnf" and SafetyManager.check_dnf_lock():
            QMessageBox.warning(
                self,
                self.tr("Update Locked"),
                self.tr(
                    "Another package manager (DNF/RPM) is currently running.\n"
                    "Please wait for it to finish."
                ),
            )
            return

        action_name = (
            self.tr("System Upgrade (rpm-ostree)")
            if self.package_manager == "rpm-ostree"
            else self.tr("System Update (DNF)")
        )

        if not SafetyManager.confirm_action(self, action_name):
            return

        self.start_process()
        cmd, args, desc = self._system_update_step(self.package_manager)
        self.append_output(self.tr(desc) + "\n")
        self.runner.run_command(cmd, args)

    def run_flatpak_update(self):
        self.start_process()
        self.append_output(self.tr("Starting Flatpak Update...\n"))
        self.runner.run_command("flatpak", ["update", "-y"])

    def run_fw_update(self):
        from utils.safety import SafetyManager

        if not SafetyManager.confirm_action(self, self.tr("Firmware Update")):
            return

        self.start_process()
        self.append_output(self.tr("Starting Firmware Update...\n"))
        self.runner.run_command("pkexec", ["fwupdmgr", "update", "-y"])

    # -- Update All (sequential queue) -------------------------------------

    def run_update_all(self):
        from utils.safety import SafetyManager

        if self.package_manager == "dnf" and SafetyManager.check_dnf_lock():
            QMessageBox.warning(
                self,
                self.tr("Update Locked"),
                self.tr("Another package manager is running.\nPlease wait."),
            )
            return

        if not SafetyManager.confirm_action(self, self.tr("Full System Update")):
            return

        self.start_process()
        self.update_queue = [
            self._system_update_step(self.package_manager),
            ("flatpak", ["update", "-y"],
             self.tr("Starting Flatpak Update...")),
            ("pkexec", ["fwupdmgr", "update", "-y"],
             self.tr("Starting Firmware Update...")),
        ]
        self.current_update_index = 0
        cmd, args, desc = self.update_queue[0]
        self.append_output(self.tr(desc) + "\n")
        self.runner.run_command(cmd, args)

    # -- Helpers -----------------------------------------------------------

    def start_process(self):
        self.output_area.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - Waiting...")
        self.btn_dnf.setEnabled(False)
        self.btn_flatpak.setEnabled(False)
        self.btn_fw.setEnabled(False)
        self.btn_update_all.setEnabled(False)

    def append_output(self, text):
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )

    def command_finished(self, exit_code):
        self.append_output(
            self.tr("\nCommand finished with exit code: {}").format(exit_code)
        )

        # Handle sequential update-all queue
        if (self.update_queue
                and self.current_update_index < len(self.update_queue) - 1):
            self.current_update_index += 1
            cmd, args, desc = self.update_queue[self.current_update_index]
            self.append_output(f"\n\n{desc}\n")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(f"0% - {desc}")
            self.runner.run_command(cmd, args)
        else:
            self.update_queue = []
            self.current_update_index = 0
            self.btn_dnf.setEnabled(True)
            self.btn_flatpak.setEnabled(True)
            self.btn_fw.setEnabled(True)
            self.btn_update_all.setEnabled(True)
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat(self.tr("100% - Done"))

    def run_single_command(self, cmd, args, description):
        self.output_area.clear()
        self.progress_bar.setValue(0)
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

# ---------------------------------------------------------------------------
# Sub-tab: Cleanup
# ---------------------------------------------------------------------------


class _CleanupSubTab(QWidget):
    """Sub-tab containing all cleanup and maintenance functionality.

    Preserves every feature from the original CleanupTab:
    - Clean DNF Cache
    - Remove Unused Packages (autoremove, with DNF lock check)
    - Vacuum Journal (2 weeks)
    - SSD Trim (fstrim)
    - Rebuild RPM Database
    - Timeshift snapshot check
    - Output log
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Output Area (Shared)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)

        self.runner = CommandRunner()
        self.runner.output_received.connect(self.append_output)
        self.runner.finished.connect(self.command_finished)

        # Cleanup Group
        cleanup_group = QGroupBox(self.tr("Cleanup"))
        cleanup_layout = QVBoxLayout()
        cleanup_group.setLayout(cleanup_layout)

        btn_dnf_clean = QPushButton(self.tr("Clean DNF Cache"))
        btn_dnf_clean.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["dnf", "clean", "all"],
                self.tr("Cleaning DNF Cache...")
            )
        )
        cleanup_layout.addWidget(btn_dnf_clean)

        btn_autoremove = QPushButton(self.tr("Remove Unused Packages (Risky)"))
        btn_autoremove.setStyleSheet("color: #f38ba8;")
        btn_autoremove.clicked.connect(self.run_autoremove)
        cleanup_layout.addWidget(btn_autoremove)

        btn_journal = QPushButton(self.tr("Vacuum Journal (2 weeks)"))
        btn_journal.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["journalctl", "--vacuum-time=2weeks"],
                self.tr("Vacuuming Journal...")
            )
        )
        cleanup_layout.addWidget(btn_journal)

        layout.addWidget(cleanup_group)

        # Maintenance Group
        maint_group = QGroupBox(self.tr("Maintenance"))
        maint_layout = QVBoxLayout()
        maint_group.setLayout(maint_layout)

        btn_trim = QPushButton(self.tr("SSD Trim (fstrim)"))
        btn_trim.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["fstrim", "-av"],
                self.tr("Trimming SSD...")
            )
        )
        maint_layout.addWidget(btn_trim)

        btn_rpmdb = QPushButton(self.tr("Rebuild RPM Database"))
        btn_rpmdb.clicked.connect(
            lambda: self.run_command(
                "pkexec", ["rpm", "--rebuilddb"],
                self.tr("Rebuilding RPM Database...")
            )
        )
        maint_layout.addWidget(btn_rpmdb)

        # Timeshift Check
        ts_layout = QHBoxLayout()
        btn_check_ts = QPushButton(self.tr("Check for Timeshift Snapshots"))
        btn_check_ts.clicked.connect(self.check_timeshift)
        ts_layout.addWidget(btn_check_ts)
        maint_layout.addLayout(ts_layout)

        layout.addWidget(maint_group)
        layout.addWidget(QLabel(self.tr("Output Log:")))
        layout.addWidget(self.output_area)

    def check_timeshift(self):
        if shutil.which("timeshift"):
            self.run_command(
                "pkexec", ["timeshift", "--list"],
                self.tr("Checking Timeshift Snapshots...")
            )
        else:
            self.append_output(
                self.tr("Timeshift not found. Please install it for system safety.\n")
            )

    def run_autoremove(self):
        from utils.safety import SafetyManager

        if SafetyManager.check_dnf_lock():
            QMessageBox.warning(
                self,
                self.tr("Update Locked"),
                self.tr("Another package manager is running."),
            )
            return

        if SafetyManager.confirm_action(
            self, self.tr("Remove Unused Packages (Risky)")
        ):
            self.run_command(
                "pkexec", ["dnf", "autoremove", "-y"],
                self.tr("Removing unused packages...")
            )

    def run_command(self, cmd, args, description):
        self.output_area.clear()
        self.append_output(f"{description}\n")
        self.runner.run_command(cmd, args)

    def append_output(self, text):
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )
        self.output_area.insertPlainText(text)
        self.output_area.moveCursor(
            self.output_area.textCursor().MoveOperation.End
        )

    def command_finished(self, exit_code):
        self.append_output(
            self.tr("\nCommand finished with exit code: {}").format(exit_code)
        )


# ---------------------------------------------------------------------------
# Sub-tab: Overlays (Atomic / rpm-ostree only)
# ---------------------------------------------------------------------------

class _OverlaysSubTab(QWidget):
    """Sub-tab for managing rpm-ostree layered packages.

    Only instantiated on Fedora Atomic systems (Silverblue, Kinoite, etc.).
    Preserves every feature from the original OverlaysTab:
    - Info card showing system variant
    - Layered packages list with refresh
    - Remove selected / Reset to base image
    - Pending-reboot warning and reboot button
    """

    def __init__(self):
        super().__init__()
        from utils.package_manager import PackageManager

        self.pkg_manager = PackageManager()
        self.reboot_runner = CommandRunner()
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Header
        header = QLabel(self.tr("System Overlays (rpm-ostree)"))
        header.setObjectName("header")
        layout.addWidget(header)

        # Info Card
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)

        variant = SystemManager.get_variant_name()
        info_label = QLabel(
            self.tr("\U0001f4e6 System: Fedora {} (Immutable)").format(variant)
        )
        info_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_layout.addWidget(info_label)

        desc_label = QLabel(self.tr(
            "Layered packages are RPMs installed on top of the base OS image.\n"
            "Changes require a reboot to fully apply."
        ))
        desc_label.setStyleSheet("color: #a6adc8;")
        info_layout.addWidget(desc_label)

        # Pending Reboot Warning
        self.reboot_warning = QLabel(
            self.tr("\u26a0\ufe0f Pending changes require reboot!")
        )
        self.reboot_warning.setStyleSheet(
            "color: #f9e2af; font-weight: bold;"
        )
        self.reboot_warning.setVisible(False)
        info_layout.addWidget(self.reboot_warning)

        layout.addWidget(info_frame)

        # Layered Packages List
        packages_group = QGroupBox(self.tr("Layered Packages"))
        packages_layout = QVBoxLayout(packages_group)

        self.packages_list = QListWidget()
        self.packages_list.setMinimumHeight(200)
        packages_layout.addWidget(self.packages_list)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_refresh = QPushButton(self.tr("\U0001f504 Refresh"))
        self.btn_refresh.clicked.connect(self.refresh_list)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_remove = QPushButton(self.tr("\u2796 Remove Selected"))
        self.btn_remove.setObjectName("dangerAction")
        self.btn_remove.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.btn_remove)

        btn_layout.addStretch()

        self.btn_reset = QPushButton(self.tr("\U0001f5d1\ufe0f Reset to Base Image"))
        self.btn_reset.setObjectName("dangerAction")
        self.btn_reset.clicked.connect(self.reset_to_base)
        btn_layout.addWidget(self.btn_reset)

        packages_layout.addLayout(btn_layout)
        layout.addWidget(packages_group)

        # Reboot Button
        self.btn_reboot = QPushButton(
            self.tr("\U0001f501 Reboot to Apply Changes")
        )
        self.btn_reboot.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #eba0ac;
            }
        """)
        self.btn_reboot.clicked.connect(self.reboot_system)
        self.btn_reboot.setVisible(False)
        layout.addWidget(self.btn_reboot)

        layout.addStretch()

    def refresh_list(self):
        """Refresh the list of layered packages."""
        self.packages_list.clear()

        packages = SystemManager.get_layered_packages()

        if packages:
            for pkg in packages:
                item = QListWidgetItem(f"\U0001f4e6 {pkg}")
                self.packages_list.addItem(item)
        else:
            item = QListWidgetItem(
                self.tr("No layered packages (clean base image)")
            )
            item.setForeground(QColor("#a6adc8"))
            self.packages_list.addItem(item)

        # Check for pending reboot
        has_pending = SystemManager.has_pending_deployment()
        self.reboot_warning.setVisible(has_pending)
        self.btn_reboot.setVisible(has_pending)

    def remove_selected(self):
        """Remove the selected layered package."""
        selected = self.packages_list.currentItem()
        if not selected:
            QMessageBox.warning(
                self,
                self.tr("No Selection"),
                self.tr("Please select a package to remove."),
            )
            return

        # Extract package name (remove emoji prefix)
        pkg_name = selected.text().replace("\U0001f4e6 ", "").strip()

        if "No layered" in pkg_name:
            return

        reply = QMessageBox.question(
            self,
            self.tr("Confirm Removal"),
            self.tr(
                "Remove '{}' from system overlays?\n\nThis requires a reboot."
            ).format(pkg_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = self.pkg_manager.remove([pkg_name])
            if result.success:
                QMessageBox.information(
                    self, self.tr("Success"), result.message
                )
                self.refresh_list()
            else:
                QMessageBox.critical(self, self.tr("Error"), result.message)

    def reset_to_base(self):
        """Reset to base image, removing all layered packages."""
        reply = QMessageBox.warning(
            self,
            self.tr("\u26a0\ufe0f Reset to Base Image"),
            self.tr(
                "This will REMOVE ALL layered packages and reset to the "
                "clean base image.\n\nAre you absolutely sure?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = self.pkg_manager.reset_to_base()
            if result.success:
                QMessageBox.information(
                    self,
                    self.tr("Reset Complete"),
                    self.tr(
                        "System reset to base image.\n\n"
                        "Please reboot to apply changes."
                    ),
                )
                self.refresh_list()
            else:
                QMessageBox.critical(self, self.tr("Error"), result.message)

    def reboot_system(self):
        """Offer to reboot the system."""
        reply = QMessageBox.question(
            self,
            self.tr("Reboot Now?"),
            self.tr("Reboot now to apply pending changes?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.reboot_runner.run_command("systemctl", ["reboot"])


# ---------------------------------------------------------------------------
# Main consolidated tab
# ---------------------------------------------------------------------------

class MaintenanceTab(BaseTab):
    """Consolidated maintenance tab merging Updates, Cleanup, and Overlays.

    Uses a QTabWidget for sub-navigation.  The Overlays sub-tab is only
    shown when the system is detected as Atomic (rpm-ostree based).
    """

    _METADATA = PluginMetadata(
        id="maintenance",
        name="Maintenance",
        description="System updates, cache cleanup, and overlay management for Fedora.",
        category="Software",
        icon="🔧",
        badge="recommended",
        order=20,
    )

    def metadata(self) -> PluginMetadata:
        return self._METADATA

    def create_widget(self) -> QWidget:
        return self

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        configure_top_tabs(self.tabs)
        self.tabs.addTab(_UpdatesSubTab(), self.tr("Updates"))
        self.tabs.addTab(_CleanupSubTab(), self.tr("Cleanup"))

        if SystemManager.is_atomic():
            self.tabs.addTab(_OverlaysSubTab(), self.tr("Overlays"))

        layout.addWidget(self.tabs)
