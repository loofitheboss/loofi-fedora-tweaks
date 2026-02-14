"""
Diagnostics Tab - Consolidated tab merging Watchtower and Boot.
Part of v11.0 "Aurora Update".

Uses QTabWidget for sub-navigation to preserve all features from the
original WatchtowerTab (services, boot analysis, journal) and
BootTab (kernel parameters, ZRAM, Secure Boot).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QComboBox, QMenu, QMessageBox,
    QSlider, QLineEdit, QCheckBox, QInputDialog
)
from PyQt6.QtCore import Qt

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs, CONTENT_MARGINS
from utils.services import ServiceManager, UnitScope, UnitState
from utils.boot_analyzer import BootAnalyzer
from utils.journal import JournalManager
from core.plugins.metadata import PluginMetadata
from utils.kernel import KernelManager
from utils.zram import ZramManager
from utils.secureboot import SecureBootManager


# ---------------------------------------------------------------------------
# Sub-tab: Watchtower
# ---------------------------------------------------------------------------

class _WatchtowerSubTab(QWidget):
    """Sub-tab with system diagnostics and service management.

    Preserves every feature from the original WatchtowerTab:
    - Services browser with filter (Gaming / Failed / Active / All User)
    - Right-click context menu: Start, Stop, Restart, Mask, Unmask
    - Boot analysis with time summary, slow services, optimisation tips
    - Journal viewer with error counts, failed services, panic log export
    - Internal QTabWidget for its own three sub-sections
    """

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialise the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel(
            self.tr("\U0001f52d Watchtower - System Diagnostics")
        )
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; "
            "color: #a277ff; padding: 10px;"
        )
        layout.addWidget(header)

        # Internal sub-tabs for different diagnostic areas
        self.tabs = QTabWidget()
        configure_top_tabs(self.tabs)
        self.tabs.addTab(
            self._create_services_tab(),
            self.tr("\U0001f527 Services"),
        )
        self.tabs.addTab(
            self._create_boot_tab(),
            self.tr("\u26a1 Boot Analysis"),
        )
        self.tabs.addTab(
            self._create_journal_tab(),
            self.tr("\U0001f4cb Journal"),
        )

        layout.addWidget(self.tabs)

    # ==================== Services ========================================

    def _create_services_tab(self) -> QWidget:
        """Create the services management sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel(self.tr("Filter:")))

        self.service_filter = QComboBox()
        self.service_filter.setAccessibleName(self.tr("Service filter"))
        self.service_filter.addItem(
            self.tr("\U0001f3ae Gaming Services"), "gaming"
        )
        self.service_filter.addItem(
            self.tr("\u274c Failed Services"), "failed"
        )
        self.service_filter.addItem(
            self.tr("\u2705 Active Services"), "active"
        )
        self.service_filter.addItem(
            self.tr("\U0001f4e6 All User Services"), "all"
        )
        self.service_filter.currentIndexChanged.connect(
            self._refresh_services
        )
        filter_layout.addWidget(self.service_filter)

        filter_layout.addStretch()

        refresh_btn = QPushButton(self.tr("\U0001f504 Refresh"))
        refresh_btn.setAccessibleName(self.tr("Refresh services"))
        refresh_btn.clicked.connect(self._refresh_services)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # Service tree
        self.service_tree = QTreeWidget()
        self.service_tree.setHeaderLabels([
            self.tr("Service"),
            self.tr("Status"),
            self.tr("Description"),
        ])
        self.service_tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.service_tree.customContextMenuRequested.connect(
            self._show_service_menu
        )
        self.service_tree.setColumnWidth(0, 250)
        self.service_tree.setColumnWidth(1, 100)
        layout.addWidget(self.service_tree)

        # Status log
        self.service_log = QTextEdit()
        self.service_log.setReadOnly(True)
        self.service_log.setMaximumHeight(100)
        layout.addWidget(self.service_log)

        self._refresh_services()
        return widget

    # ==================== Boot Analysis ===================================

    def _create_boot_tab(self) -> QWidget:
        """Create the boot analysis sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Boot stats summary
        stats_group = QGroupBox(self.tr("Boot Time Summary"))
        stats_layout = QVBoxLayout(stats_group)

        self.boot_stats_label = QLabel()
        self.boot_stats_label.setWordWrap(True)
        stats_layout.addWidget(self.boot_stats_label)

        # Visual bars for boot phases
        self.boot_bars_layout = QVBoxLayout()
        stats_layout.addLayout(self.boot_bars_layout)

        layout.addWidget(stats_group)

        # Slow services
        slow_group = QGroupBox(self.tr("Slowest Services (>5s)"))
        slow_layout = QVBoxLayout(slow_group)

        self.slow_services_list = QTextEdit()
        self.slow_services_list.setReadOnly(True)
        slow_layout.addWidget(self.slow_services_list)

        layout.addWidget(slow_group)

        # Optimisation suggestions
        opt_group = QGroupBox(
            self.tr("\U0001f4a1 Optimization Suggestions")
        )
        opt_layout = QVBoxLayout(opt_group)

        self.suggestions_label = QLabel()
        self.suggestions_label.setWordWrap(True)
        opt_layout.addWidget(self.suggestions_label)

        layout.addWidget(opt_group)

        # Refresh button
        refresh_btn = QPushButton(self.tr("\U0001f504 Analyze Boot"))
        refresh_btn.setAccessibleName(self.tr("Analyze Boot"))
        refresh_btn.clicked.connect(self._refresh_boot_analysis)
        layout.addWidget(refresh_btn)

        self._refresh_boot_analysis()
        return widget

    # ==================== Journal =========================================

    def _create_journal_tab(self) -> QWidget:
        """Create the journal viewer sub-tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Quick diagnostic
        diag_group = QGroupBox(self.tr("\U0001f3e5 Quick Diagnostic"))
        diag_layout = QHBoxLayout(diag_group)

        self.error_count_label = QLabel()
        diag_layout.addWidget(self.error_count_label)

        self.failed_count_label = QLabel()
        diag_layout.addWidget(self.failed_count_label)

        diag_layout.addStretch()

        layout.addWidget(diag_group)

        # Journal output
        journal_group = QGroupBox(self.tr("Recent Errors"))
        journal_layout = QVBoxLayout(journal_group)

        self.journal_output = QTextEdit()
        self.journal_output.setReadOnly(True)
        self.journal_output.setStyleSheet("font-family: monospace;")
        journal_layout.addWidget(self.journal_output)

        layout.addWidget(journal_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton(self.tr("\U0001f504 Refresh"))
        refresh_btn.setAccessibleName(self.tr("Refresh journal"))
        refresh_btn.clicked.connect(self._refresh_journal)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        panic_btn = QPushButton(self.tr("\U0001f198 Export Panic Log"))
        panic_btn.setAccessibleName(self.tr("Export Panic Log"))
        panic_btn.setStyleSheet(
            "background-color: #dc3545; color: white; font-weight: bold;"
        )
        panic_btn.clicked.connect(self._export_panic_log)
        btn_layout.addWidget(panic_btn)

        bundle_btn = QPushButton(self.tr("\U0001f4e6 Export Support Bundle"))
        bundle_btn.setAccessibleName(self.tr("Export Support Bundle"))
        bundle_btn.clicked.connect(self._export_support_bundle)
        btn_layout.addWidget(bundle_btn)

        layout.addLayout(btn_layout)

        self._refresh_journal()
        return widget

    # ==================== Service logic ===================================

    def _refresh_services(self):
        """Refresh the services list."""
        self.service_tree.clear()
        filter_type = self.service_filter.currentData()

        # Get user services
        services = ServiceManager.list_units(UnitScope.USER, filter_type)

        # Add gaming services from system scope too
        if filter_type == "gaming":
            services.extend(
                ServiceManager.list_units(UnitScope.SYSTEM, filter_type)
            )

        for service in services:
            item = QTreeWidgetItem([
                service.name,
                self._state_to_emoji(service.state),
                service.description[:50] if service.description else "",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, service)
            self.service_tree.addTopLevelItem(item)

        self.service_log.append(
            self.tr("Loaded {} services").format(len(services))
        )

    def _state_to_emoji(self, state: UnitState) -> str:
        """Convert service state to display string."""
        mapping = {
            UnitState.ACTIVE: "\u2705 active",
            UnitState.INACTIVE: "\u26aa inactive",
            UnitState.FAILED: "\u274c failed",
            UnitState.ACTIVATING: "\U0001f504 starting",
            UnitState.UNKNOWN: "\u2753 unknown",
        }
        return mapping.get(state, "\u2753")

    def _show_service_menu(self, position):
        """Show context menu for service actions."""
        item = self.service_tree.itemAt(position)
        if not item:
            return

        service = item.data(0, Qt.ItemDataRole.UserRole)
        if not service:
            return

        menu = QMenu()

        if service.state == UnitState.ACTIVE:
            stop_action = menu.addAction(
                self.tr("\u23f9\ufe0f Stop")
            )
            stop_action.triggered.connect(
                lambda: self._service_action("stop", service)
            )

            restart_action = menu.addAction(
                self.tr("\U0001f504 Restart")
            )
            restart_action.triggered.connect(
                lambda: self._service_action("restart", service)
            )
        else:
            start_action = menu.addAction(
                self.tr("\u25b6\ufe0f Start")
            )
            start_action.triggered.connect(
                lambda: self._service_action("start", service)
            )

        menu.addSeparator()

        mask_action = menu.addAction(
            self.tr("\U0001f6ab Mask (Disable)")
        )
        mask_action.triggered.connect(
            lambda: self._service_action("mask", service)
        )

        unmask_action = menu.addAction(
            self.tr("\u2705 Unmask")
        )
        unmask_action.triggered.connect(
            lambda: self._service_action("unmask", service)
        )

        menu.exec(self.service_tree.viewport().mapToGlobal(position))

    def _service_action(self, action: str, service):
        """Execute a service action."""
        actions = {
            "start": ServiceManager.start_unit,
            "stop": ServiceManager.stop_unit,
            "restart": ServiceManager.restart_unit,
            "mask": ServiceManager.mask_unit,
            "unmask": ServiceManager.unmask_unit,
        }

        func = actions.get(action)
        if func:
            result = func(service.name, service.scope)
            self.service_log.append(result.message)
            if result.success:
                self._refresh_services()

    # ==================== Boot analysis logic ==============================

    def _refresh_boot_analysis(self):
        """Refresh boot analysis data."""
        stats = BootAnalyzer.get_boot_stats()

        # Stats summary
        if stats.total_time:
            summary = f"Total boot time: {stats.total_time:.1f}s\n"
            if stats.firmware_time:
                summary += f"  \u2022 Firmware: {stats.firmware_time:.1f}s\n"
            if stats.loader_time:
                summary += f"  \u2022 Bootloader: {stats.loader_time:.1f}s\n"
            if stats.kernel_time:
                summary += f"  \u2022 Kernel: {stats.kernel_time:.1f}s\n"
            if stats.userspace_time:
                summary += f"  \u2022 Userspace: {stats.userspace_time:.1f}s"
            self.boot_stats_label.setText(summary)
        else:
            self.boot_stats_label.setText(
                self.tr(
                    "Unable to analyze boot "
                    "(run as user, after first boot)"
                )
            )

        # Slow services
        slow = BootAnalyzer.get_slow_services()
        if slow:
            slow_text = "\n".join(
                f"\U0001f422 {s.service}: {s.time_seconds:.1f}s"
                for s in slow[:10]
            )
            self.slow_services_list.setText(slow_text)
        else:
            self.slow_services_list.setText(
                self.tr("No services taking >5s to start")
            )

        # Suggestions
        suggestions = BootAnalyzer.get_optimization_suggestions()
        self.suggestions_label.setText("\n".join(suggestions))

    # ==================== Journal logic ====================================

    def _refresh_journal(self):
        """Refresh journal diagnostic view."""
        diag = JournalManager.get_quick_diagnostic()

        self.error_count_label.setText(
            self.tr("\u26a0\ufe0f Errors: {}").format(diag["error_count"])
        )
        self.failed_count_label.setText(
            self.tr("\u274c Failed Services: {}").format(
                len(diag["failed_services"])
            )
        )

        # Show recent errors
        errors = JournalManager.get_boot_errors()
        self.journal_output.setText(
            errors if errors else self.tr("No errors in current boot")
        )

    def _export_panic_log(self):
        """Export panic log for forum support."""
        result = JournalManager.export_panic_log()

        if result.success:
            QMessageBox.information(
                self,
                self.tr("Panic Log Exported"),
                self.tr(
                    "Log saved to:\n{path}\n\n"
                    "You can share this file when asking for help online."
                ).format(path=result.data["path"]),
            )
        else:
            QMessageBox.warning(
                self, self.tr("Export Failed"), result.message
            )

    def _export_support_bundle(self):
        """Export support bundle ZIP."""
        result = JournalManager.export_support_bundle()

        if result.success:
            QMessageBox.information(
                self,
                self.tr("Support Bundle Exported"),
                self.tr(
                    "Bundle saved to:\n{path}\n\n"
                    "Share this ZIP file when reporting issues."
                ).format(path=result.data["path"]),
            )
        else:
            QMessageBox.warning(
                self, self.tr("Export Failed"), result.message
            )


# ---------------------------------------------------------------------------
# Sub-tab: Boot (Kernel, ZRAM, Secure Boot)
# ---------------------------------------------------------------------------

class _BootSubTab(QWidget):
    """Sub-tab for kernel parameters, ZRAM, and Secure Boot management.

    Preserves every feature from the original BootTab:
    - Current kernel cmdline display
    - Common parameter quick-add checkboxes (AMD GPU, Intel IOMMU,
      NVIDIA modesetting, mitigations, watchdog)
    - Custom parameter add/remove
    - GRUB backup / restore
    - ZRAM configuration (size slider, compression algorithm)
    - Secure Boot status and MOK key generation / enrollment
    - Output log
    """

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        """Initialise the UI components."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Kernel Parameters Section
        layout.addWidget(self.create_kernel_section())

        # ZRAM Section
        layout.addWidget(self.create_zram_section())

        # Secure Boot Section
        layout.addWidget(self.create_secureboot_section())

        # Output Log
        output_group = QGroupBox(self.tr("Output Log:"))
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_group)

        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*CONTENT_MARGINS)
        main_layout.addWidget(scroll)

    # ==================== Kernel Section ==================================

    def create_kernel_section(self) -> QGroupBox:
        """Create the kernel parameters section."""
        group = QGroupBox(self.tr("\u2699\ufe0f Kernel Parameters"))
        layout = QVBoxLayout(group)

        # Current parameters display
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel(self.tr("Current cmdline:")))
        self.current_params_label = QLabel()
        self.current_params_label.setWordWrap(True)
        self.current_params_label.setStyleSheet(
            "color: #9da7bf; font-size: 11px;"
        )
        current_layout.addWidget(self.current_params_label, 1)
        layout.addLayout(current_layout)

        # Common parameters checkboxes
        params_group = QGroupBox(self.tr("Quick Add Parameters"))
        params_layout = QVBoxLayout(params_group)

        self.param_checkboxes = {}
        common_params = [
            ("amdgpu.ppfeaturemask=0xffffffff",
             self.tr("AMD GPU: Enable all power features")),
            ("intel_iommu=on",
             self.tr("Intel IOMMU: GPU passthrough support")),
            ("nvidia-drm.modeset=1",
             self.tr("NVIDIA: Kernel modesetting")),
            ("mitigations=off",
             self.tr("\u26a0\ufe0f Disable CPU mitigations (unsafe but faster)")),
            ("nowatchdog",
             self.tr("Disable watchdog (reduce interrupts)")),
        ]

        for param, desc in common_params:
            cb = QCheckBox(desc)
            cb.setAccessibleName(desc)
            cb.setProperty("param", param)
            cb.stateChanged.connect(
                lambda state, p=param: self.on_param_toggled(p, state)
            )
            self.param_checkboxes[param] = cb
            params_layout.addWidget(cb)

        layout.addWidget(params_group)

        # Custom parameter input
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel(self.tr("Custom:")))
        self.custom_param_input = QLineEdit()
        self.custom_param_input.setAccessibleName(self.tr("Custom kernel parameter"))
        self.custom_param_input.setPlaceholderText("e.g., mem=4G")
        custom_layout.addWidget(self.custom_param_input)

        add_btn = QPushButton(self.tr("Add"))
        add_btn.setAccessibleName(self.tr("Add custom parameter"))
        add_btn.clicked.connect(self.add_custom_param)
        custom_layout.addWidget(add_btn)

        remove_btn = QPushButton(self.tr("Remove"))
        remove_btn.setAccessibleName(self.tr("Remove custom parameter"))
        remove_btn.clicked.connect(self.remove_custom_param)
        custom_layout.addWidget(remove_btn)

        layout.addLayout(custom_layout)

        # Backup/Restore
        backup_layout = QHBoxLayout()
        backup_btn = QPushButton(self.tr("\U0001f4e6 Backup GRUB"))
        backup_btn.setAccessibleName(self.tr("Backup GRUB"))
        backup_btn.clicked.connect(self.backup_grub)
        backup_layout.addWidget(backup_btn)

        restore_btn = QPushButton(self.tr("\u267b\ufe0f Restore Backup"))
        restore_btn.setAccessibleName(self.tr("Restore Backup"))
        restore_btn.clicked.connect(self.restore_grub)
        backup_layout.addWidget(restore_btn)

        backup_layout.addStretch()
        layout.addLayout(backup_layout)

        return group

    # ==================== ZRAM Section ====================================

    def create_zram_section(self) -> QGroupBox:
        """Create the ZRAM configuration section."""
        group = QGroupBox(self.tr("\U0001f4be ZRAM (Compressed Swap)"))
        layout = QVBoxLayout(group)

        # Status
        status_layout = QHBoxLayout()
        self.zram_status_label = QLabel()
        status_layout.addWidget(self.zram_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Size slider
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel(self.tr("Size (% of RAM):")))

        self.zram_slider = QSlider(Qt.Orientation.Horizontal)
        self.zram_slider.setAccessibleName(self.tr("ZRAM size percent of RAM"))
        self.zram_slider.setMinimum(25)
        self.zram_slider.setMaximum(150)
        self.zram_slider.setValue(100)
        self.zram_slider.setTickInterval(25)
        self.zram_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zram_slider.valueChanged.connect(self.on_zram_slider_changed)
        size_layout.addWidget(self.zram_slider)

        self.zram_size_label = QLabel("100%")
        self.zram_size_label.setMinimumWidth(50)
        size_layout.addWidget(self.zram_size_label)

        layout.addLayout(size_layout)

        # Algorithm
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel(self.tr("Compression:")))

        self.zram_algo_combo = QComboBox()
        self.zram_algo_combo.setAccessibleName(self.tr("ZRAM compression algorithm"))
        for algo, desc in ZramManager.ALGORITHMS.items():
            self.zram_algo_combo.addItem(f"{algo} - {desc}", algo)
        algo_layout.addWidget(self.zram_algo_combo, 1)

        layout.addLayout(algo_layout)

        # Apply button
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton(self.tr("\u2705 Apply ZRAM Settings"))
        apply_btn.setAccessibleName(self.tr("Apply ZRAM Settings"))
        apply_btn.clicked.connect(self.apply_zram)
        btn_layout.addWidget(apply_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    # ==================== Secure Boot Section =============================

    def create_secureboot_section(self) -> QGroupBox:
        """Create the Secure Boot section."""
        group = QGroupBox(self.tr("\U0001f510 Secure Boot (MOK Management)"))
        layout = QVBoxLayout(group)

        # Status
        self.sb_status_label = QLabel()
        layout.addWidget(self.sb_status_label)

        # Key status
        self.mok_status_label = QLabel()
        layout.addWidget(self.mok_status_label)

        # Actions
        btn_layout = QHBoxLayout()

        generate_btn = QPushButton(self.tr("\U0001f511 Generate MOK Key"))
        generate_btn.setAccessibleName(self.tr("Generate MOK Key"))
        generate_btn.clicked.connect(self.generate_mok_key)
        btn_layout.addWidget(generate_btn)

        enroll_btn = QPushButton(self.tr("\U0001f4dd Enroll Key"))
        enroll_btn.setAccessibleName(self.tr("Enroll Key"))
        enroll_btn.clicked.connect(self.enroll_mok_key)
        btn_layout.addWidget(enroll_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Help text
        help_label = QLabel(self.tr(
            "\u2139\ufe0f MOK keys are needed to sign third-party kernel "
            "modules (NVIDIA, VirtualBox) when Secure Boot is enabled."
        ))
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #9da7bf; font-size: 11px;")
        layout.addWidget(help_label)

        return group

    # ==================== Refresh helpers =================================

    def refresh_all(self):
        """Refresh all sections with current data."""
        self.refresh_kernel()
        self.refresh_zram()
        self.refresh_secureboot()

    def refresh_kernel(self):
        """Refresh kernel parameters display."""
        current = KernelManager.get_current_params()
        self.current_params_label.setText(
            " ".join(current[:10])
            + ("..." if len(current) > 10 else "")
        )

        # Update checkboxes
        for param, cb in self.param_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(KernelManager.has_param(param))
            cb.blockSignals(False)

    def refresh_zram(self):
        """Refresh ZRAM status."""
        config = ZramManager.get_current_config()
        usage = ZramManager.get_current_usage()

        status_parts = []
        if config.enabled:
            status_parts.append(f"\u2705 {self.tr('Active')}")
            if usage:
                status_parts.append(f"{usage[0]}MB / {usage[1]}MB")
        else:
            status_parts.append(f"\u26aa {self.tr('Inactive')}")

        status_parts.append(
            f"{config.size_percent}% RAM ({config.size_mb}MB)"
        )
        status_parts.append(f"{config.algorithm}")

        self.zram_status_label.setText(" | ".join(status_parts))

        self.zram_slider.blockSignals(True)
        self.zram_slider.setValue(config.size_percent)
        self.zram_slider.blockSignals(False)
        self.zram_size_label.setText(f"{config.size_percent}%")

        # Set algorithm combobox
        idx = self.zram_algo_combo.findData(config.algorithm)
        if idx >= 0:
            self.zram_algo_combo.setCurrentIndex(idx)

    def refresh_secureboot(self):
        """Refresh Secure Boot status."""
        status = SecureBootManager.get_status()

        if status.secure_boot_enabled:
            self.sb_status_label.setText(
                f"\U0001f512 {self.tr('Secure Boot: Enabled')}"
            )
        else:
            self.sb_status_label.setText(
                f"\U0001f513 {self.tr('Secure Boot: Disabled')}"
            )

        if SecureBootManager.has_keys():
            self.mok_status_label.setText(
                f"\U0001f511 {self.tr('MOK Key: Generated')}"
            )
        else:
            self.mok_status_label.setText(
                f"\u26aa {self.tr('MOK Key: Not generated')}"
            )

        if status.pending_mok:
            self.mok_status_label.setText(
                self.mok_status_label.text()
                + f" ({self.tr('Pending enrollment')})"
            )

    def log(self, message: str):
        """Add message to output log."""
        self.output_text.append(message)

    # ==================== Kernel actions ==================================

    def on_param_toggled(self, param: str, state: int):
        """Handle parameter checkbox toggle."""
        if state == Qt.CheckState.Checked.value:
            result = KernelManager.add_param(param)
        else:
            result = KernelManager.remove_param(param)

        self.log(result.message)
        if not result.success:
            self.refresh_kernel()  # Revert checkbox

    def add_custom_param(self):
        """Add a custom kernel parameter."""
        param = self.custom_param_input.text().strip()
        if param:
            result = KernelManager.add_param(param)
            self.log(result.message)
            self.custom_param_input.clear()
            self.refresh_kernel()

    def remove_custom_param(self):
        """Remove a custom kernel parameter."""
        param = self.custom_param_input.text().strip()
        if param:
            result = KernelManager.remove_param(param)
            self.log(result.message)
            self.custom_param_input.clear()
            self.refresh_kernel()

    def backup_grub(self):
        """Create GRUB backup."""
        result = KernelManager.backup_grub()
        self.log(result.message)
        if result.backup_path:
            self.log(
                self.tr("Saved to: {}").format(result.backup_path)
            )

    def restore_grub(self):
        """Restore GRUB from backup."""
        backups = KernelManager.get_backups()
        if not backups:
            self.log(self.tr("No backups available."))
            return

        # Show backup selection
        items = [str(b.name) for b in backups[:10]]
        item, ok = QInputDialog.getItem(
            self,
            self.tr("Select Backup"),
            self.tr("Choose a backup to restore:"),
            items, 0, False,
        )

        if ok and item:
            backup_path = KernelManager.BACKUP_DIR / item
            result = KernelManager.restore_backup(str(backup_path))
            self.log(result.message)

    # ==================== ZRAM actions ====================================

    def on_zram_slider_changed(self, value: int):
        """Update ZRAM size label."""
        self.zram_size_label.setText(f"{value}%")

    def apply_zram(self):
        """Apply ZRAM settings."""
        size = self.zram_slider.value()
        algo = self.zram_algo_combo.currentData()

        result = ZramManager.set_config(size, algo)
        self.log(result.message)
        self.refresh_zram()

    # ==================== Secure Boot actions ==============================

    def generate_mok_key(self):
        """Generate new MOK signing key."""
        password, ok = QInputDialog.getText(
            self,
            self.tr("MOK Password"),
            self.tr(
                "Enter a password (8+ chars) for the MOK key.\n"
                "You'll need this during reboot enrollment:"
            ),
            QLineEdit.EchoMode.Password,
        )

        if ok and password:
            if len(password) < 8:
                self.log(
                    self.tr("Password too short (minimum 8 characters).")
                )
                return

            result = SecureBootManager.generate_key(password)
            self.log(result.message)
            self.refresh_secureboot()

    def enroll_mok_key(self):
        """Enroll MOK key for Secure Boot."""
        if not SecureBootManager.has_keys():
            self.log(self.tr("No MOK key found. Generate one first."))
            return

        password, ok = QInputDialog.getText(
            self,
            self.tr("MOK Password"),
            self.tr("Enter your MOK password to queue enrollment:"),
            QLineEdit.EchoMode.Password,
        )

        if ok and password:
            result = SecureBootManager.import_key(password)
            self.log(result.message)

            if result.requires_reboot:
                QMessageBox.information(
                    self,
                    self.tr("Reboot Required"),
                    self.tr(
                        "MOK enrollment queued.\n\n"
                        "On next reboot, follow the blue MOK Manager "
                        "prompts to complete enrollment."
                    ),
                )

            self.refresh_secureboot()


# ---------------------------------------------------------------------------
# Main consolidated tab
# ---------------------------------------------------------------------------

class DiagnosticsTab(BaseTab):
    """Consolidated diagnostics tab merging Watchtower and Boot.

    Uses a QTabWidget for sub-navigation between the Watchtower
    diagnostic suite (services, boot analysis, journal) and the Boot
    configuration panel (kernel params, ZRAM, Secure Boot).
    """

    _METADATA = PluginMetadata(
        id="diagnostics",
        name="Diagnostics",
        description="System diagnostics including service health, boot analysis, and journal review.",
        category="Developer",
        icon="🔭",
        badge="",
        order=40,
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
        self.tabs.addTab(_WatchtowerSubTab(), self.tr("Watchtower"))
        self.tabs.addTab(_BootSubTab(), self.tr("Boot"))

        layout.addWidget(self.tabs)
