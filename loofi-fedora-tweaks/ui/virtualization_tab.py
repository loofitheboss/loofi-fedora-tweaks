"""
Virtualization Tab - VM management, GPU passthrough, and disposable VMs.
Part of v11.5 "Hypervisor Update".

Three sub-tabs wrapped in a QTabWidget:
  1. VMs       - list, start/stop/delete, Quick-Create wizard
  2. GPU Passthrough - VFIO readiness checklist + step-by-step plan
  3. Disposable      - base image status, launch/cleanup disposable VMs
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QTextEdit, QScrollArea,
    QFrame, QMessageBox, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QDialog, QFormLayout, QSpinBox,
)
from PyQt6.QtCore import Qt

from utils.virtualization import VirtualizationManager
from utils.vm_manager import VMManager, VM_FLAVORS
from utils.vfio import VFIOAssistant
from utils.disposable_vm import DisposableVMManager


class VirtualizationTab(QWidget):
    """Virtualization management tab with VM, VFIO, and Disposable sub-tabs."""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # ---- Top banner: virt status summary ----
        self.banner_label = QLabel(self.tr("Loading virtualization status..."))
        self.banner_label.setStyleSheet(
            "font-size: 12px; padding: 6px; background: #1e1e2e; "
            "border-radius: 4px; color: #cdd6f4;"
        )
        self.banner_label.setWordWrap(True)
        main_layout.addWidget(self.banner_label)

        # ---- Sub-tab widget ----
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_vms_tab(), self.tr("VMs"))
        self.tabs.addTab(self._create_gpu_passthrough_tab(), self.tr("GPU Passthrough"))
        self.tabs.addTab(self._create_disposable_tab(), self.tr("Disposable"))
        main_layout.addWidget(self.tabs)

        # ---- Output log ----
        log_group = QGroupBox(self.tr("Output Log:"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        main_layout.addWidget(log_group)

        # Deferred data load
        self._refresh_banner()

    # ==================================================================
    # Banner
    # ==================================================================

    def _refresh_banner(self):
        """Refresh the top-level virt status banner."""
        try:
            summary = VirtualizationManager.get_summary()
            self.banner_label.setText(summary)
        except Exception:
            self.banner_label.setText(self.tr("Could not query virtualization status."))

    # ==================================================================
    # Sub-tab 1: VMs
    # ==================================================================

    def _create_vms_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(self._refresh_vm_list)
        toolbar.addWidget(refresh_btn)

        quick_create_btn = QPushButton(self.tr("Quick Create"))
        quick_create_btn.clicked.connect(self._show_quick_create_dialog)
        toolbar.addWidget(quick_create_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # VM table
        self.vm_table = QTableWidget(0, 4)
        self.vm_table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("State"),
            self.tr("RAM (MB)"), self.tr("vCPUs"),
        ])
        self.vm_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.vm_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.vm_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        layout.addWidget(self.vm_table)

        # Action buttons
        btn_layout = QHBoxLayout()

        start_btn = QPushButton(self.tr("Start"))
        start_btn.clicked.connect(self._start_selected_vm)
        btn_layout.addWidget(start_btn)

        stop_btn = QPushButton(self.tr("Stop"))
        stop_btn.clicked.connect(self._stop_selected_vm)
        btn_layout.addWidget(stop_btn)

        force_stop_btn = QPushButton(self.tr("Force Stop"))
        force_stop_btn.clicked.connect(self._force_stop_selected_vm)
        btn_layout.addWidget(force_stop_btn)

        delete_btn = QPushButton(self.tr("Delete"))
        delete_btn.clicked.connect(self._delete_selected_vm)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Initial load
        if VMManager.is_available():
            self._refresh_vm_list()

        return widget

    def _refresh_vm_list(self):
        """Reload the VM table from virsh."""
        self.vm_table.setRowCount(0)
        vms = VMManager.list_vms()
        for vm in vms:
            row = self.vm_table.rowCount()
            self.vm_table.insertRow(row)
            self.vm_table.setItem(row, 0, QTableWidgetItem(vm.name))
            self.vm_table.setItem(row, 1, QTableWidgetItem(vm.state))
            self.vm_table.setItem(row, 2, QTableWidgetItem(str(vm.memory_mb)))
            self.vm_table.setItem(row, 3, QTableWidgetItem(str(vm.vcpus)))
        self.log(self.tr("VM list refreshed ({} VMs).").format(len(vms)))

    def _get_selected_vm_name(self) -> str:
        """Return the name of the currently selected VM, or empty string."""
        row = self.vm_table.currentRow()
        if row < 0:
            return ""
        item = self.vm_table.item(row, 0)
        return item.text() if item else ""

    def _start_selected_vm(self):
        name = self._get_selected_vm_name()
        if not name:
            self.log(self.tr("No VM selected."))
            return
        result = VMManager.start_vm(name)
        self.log(result.message)
        if result.success:
            self._refresh_vm_list()

    def _stop_selected_vm(self):
        name = self._get_selected_vm_name()
        if not name:
            self.log(self.tr("No VM selected."))
            return
        result = VMManager.stop_vm(name)
        self.log(result.message)
        if result.success:
            self._refresh_vm_list()

    def _force_stop_selected_vm(self):
        name = self._get_selected_vm_name()
        if not name:
            self.log(self.tr("No VM selected."))
            return
        result = VMManager.force_stop_vm(name)
        self.log(result.message)
        if result.success:
            self._refresh_vm_list()

    def _delete_selected_vm(self):
        name = self._get_selected_vm_name()
        if not name:
            self.log(self.tr("No VM selected."))
            return
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Delete VM '{}'? This cannot be undone.").format(name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            result = VMManager.delete_vm(name, delete_storage=True)
            self.log(result.message)
            if result.success:
                self._refresh_vm_list()

    def _show_quick_create_dialog(self):
        """Open a dialog for Quick-Create VM with flavour selection."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Quick Create VM"))
        dialog.setMinimumWidth(400)
        form = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("my-vm")
        form.addRow(self.tr("VM Name:"), name_edit)

        flavor_combo = QComboBox()
        for key, flavor in VM_FLAVORS.items():
            flavor_combo.addItem(flavor["label"], key)
        form.addRow(self.tr("Flavour:"), flavor_combo)

        ram_spin = QSpinBox()
        ram_spin.setRange(512, 65536)
        ram_spin.setSingleStep(512)
        ram_spin.setSuffix(" MB")
        form.addRow(self.tr("RAM:"), ram_spin)

        vcpu_spin = QSpinBox()
        vcpu_spin.setRange(1, 32)
        form.addRow(self.tr("vCPUs:"), vcpu_spin)

        disk_spin = QSpinBox()
        disk_spin.setRange(5, 500)
        disk_spin.setSuffix(" GB")
        form.addRow(self.tr("Disk:"), disk_spin)

        iso_edit = QLineEdit()
        iso_browse = QPushButton(self.tr("Browse..."))
        iso_layout = QHBoxLayout()
        iso_layout.addWidget(iso_edit)
        iso_layout.addWidget(iso_browse)
        form.addRow(self.tr("ISO:"), iso_layout)

        def browse_iso():
            path, _ = QFileDialog.getOpenFileName(
                dialog, self.tr("Select ISO"), "", self.tr("ISO Images (*.iso)")
            )
            if path:
                iso_edit.setText(path)

        iso_browse.clicked.connect(browse_iso)

        # Sync defaults when flavour changes
        def on_flavor_changed(index):
            key = flavor_combo.currentData()
            f = VM_FLAVORS.get(key, {})
            ram_spin.setValue(f.get("ram_mb", 2048))
            vcpu_spin.setValue(f.get("vcpus", 2))
            disk_spin.setValue(f.get("disk_gb", 20))

        flavor_combo.currentIndexChanged.connect(on_flavor_changed)
        on_flavor_changed(0)

        btn_layout = QHBoxLayout()
        create_btn = QPushButton(self.tr("Create"))
        cancel_btn = QPushButton(self.tr("Cancel"))
        btn_layout.addStretch()
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        form.addRow(btn_layout)

        cancel_btn.clicked.connect(dialog.reject)

        def do_create():
            vm_name = name_edit.text().strip()
            if not vm_name:
                QMessageBox.warning(dialog, self.tr("Error"), self.tr("Please enter a VM name."))
                return
            iso_path = iso_edit.text().strip()
            if not iso_path:
                QMessageBox.warning(dialog, self.tr("Error"), self.tr("Please select an ISO file."))
                return
            flavor_key = flavor_combo.currentData()
            result = VMManager.create_vm(
                vm_name, flavor_key, iso_path,
                ram_mb=ram_spin.value(),
                vcpus=vcpu_spin.value(),
                disk_gb=disk_spin.value(),
            )
            self.log(result.message)
            if result.success:
                dialog.accept()
                self._refresh_vm_list()
            else:
                QMessageBox.warning(dialog, self.tr("Creation Failed"), result.message)

        create_btn.clicked.connect(do_create)
        dialog.exec()

    # ==================================================================
    # Sub-tab 2: GPU Passthrough
    # ==================================================================

    def _create_gpu_passthrough_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)

        # Readiness checklist
        checklist_group = QGroupBox(self.tr("VFIO Readiness Checklist"))
        checklist_layout = QVBoxLayout(checklist_group)
        self.vfio_checklist_labels = {}
        for key, label_text in [
            ("kvm_ok", self.tr("KVM module loaded")),
            ("iommu_ok", self.tr("IOMMU enabled")),
            ("second_gpu", self.tr("Second GPU detected")),
            ("vfio_module", self.tr("VFIO-PCI module available")),
        ]:
            lbl = QLabel(f"[ ? ] {label_text}")
            checklist_layout.addWidget(lbl)
            self.vfio_checklist_labels[key] = lbl
        layout.addWidget(checklist_group)

        check_btn = QPushButton(self.tr("Check Prerequisites"))
        check_btn.clicked.connect(self._check_vfio_prerequisites)
        layout.addWidget(check_btn)

        # GPU candidates
        gpu_group = QGroupBox(self.tr("Passthrough Candidates"))
        gpu_layout = QVBoxLayout(gpu_group)
        self.gpu_list = QListWidget()
        gpu_layout.addWidget(self.gpu_list)

        detect_btn = QPushButton(self.tr("Detect GPUs"))
        detect_btn.clicked.connect(self._detect_gpus)
        gpu_layout.addWidget(detect_btn)
        layout.addWidget(gpu_group)

        # Step plan
        plan_group = QGroupBox(self.tr("Setup Plan"))
        plan_layout = QVBoxLayout(plan_group)
        self.plan_tree = QTreeWidget()
        self.plan_tree.setHeaderLabels([
            self.tr("Step"), self.tr("Description"), self.tr("Reversible"),
        ])
        self.plan_tree.setColumnCount(3)
        plan_layout.addWidget(self.plan_tree)

        gen_plan_btn = QPushButton(self.tr("Generate Plan for Selected GPU"))
        gen_plan_btn.clicked.connect(self._generate_vfio_plan)
        plan_layout.addWidget(gen_plan_btn)
        layout.addWidget(plan_group)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return widget

    def _check_vfio_prerequisites(self):
        prereqs = VFIOAssistant.check_prerequisites()
        for key, lbl in self.vfio_checklist_labels.items():
            status = prereqs.get(key, False)
            icon = "OK" if status else "FAIL"
            text = lbl.text()
            # Trim existing prefix and re-prepend
            text = text.split("] ", 1)[-1]
            lbl.setText(f"[ {icon} ] {text}")
        self.log(self.tr("VFIO prerequisite check complete."))

    def _detect_gpus(self):
        self.gpu_list.clear()
        self._gpu_candidates = VFIOAssistant.get_passthrough_candidates()
        if not self._gpu_candidates:
            self.gpu_list.addItem(self.tr("No passthrough candidates found."))
            return
        for gpu in self._gpu_candidates:
            desc = f"{gpu['slot']} - {gpu['description']} [{gpu['vendor_id']}:{gpu['device_id']}]"
            item = QListWidgetItem(desc)
            item.setData(Qt.ItemDataRole.UserRole, gpu)
            self.gpu_list.addItem(item)
        self.log(self.tr("{} GPU candidate(s) detected.").format(len(self._gpu_candidates)))

    def _generate_vfio_plan(self):
        current = self.gpu_list.currentItem()
        if not current:
            self.log(self.tr("No GPU selected."))
            return
        gpu = current.data(Qt.ItemDataRole.UserRole)
        if not gpu:
            return
        steps = VFIOAssistant.get_step_by_step_plan(gpu)
        self.plan_tree.clear()
        for step in steps:
            item = QTreeWidgetItem([
                str(step["step_number"]),
                step["description"],
                self.tr("Yes") if step["reversible"] else self.tr("No"),
            ])
            self.plan_tree.addTopLevelItem(item)
        self.log(self.tr("VFIO setup plan generated ({} steps).").format(len(steps)))

    # ==================================================================
    # Sub-tab 3: Disposable VMs
    # ==================================================================

    def _create_disposable_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Base image status
        base_group = QGroupBox(self.tr("Base Image"))
        base_layout = QVBoxLayout(base_group)

        self.base_status_label = QLabel()
        base_layout.addWidget(self.base_status_label)
        self._refresh_base_status()

        create_base_btn = QPushButton(self.tr("Create Base Image..."))
        create_base_btn.clicked.connect(self._create_base_image)
        base_layout.addWidget(create_base_btn)
        layout.addWidget(base_group)

        # Active disposables
        active_group = QGroupBox(self.tr("Active Disposable VMs"))
        active_layout = QVBoxLayout(active_group)

        self.disposable_list = QListWidget()
        active_layout.addWidget(self.disposable_list)

        disp_toolbar = QHBoxLayout()
        launch_btn = QPushButton(self.tr("Launch Disposable"))
        launch_btn.clicked.connect(self._launch_disposable)
        disp_toolbar.addWidget(launch_btn)

        refresh_disp_btn = QPushButton(self.tr("Refresh"))
        refresh_disp_btn.clicked.connect(self._refresh_disposable_list)
        disp_toolbar.addWidget(refresh_disp_btn)

        disp_toolbar.addStretch()
        active_layout.addLayout(disp_toolbar)
        layout.addWidget(active_group)

        layout.addStretch()

        self._refresh_disposable_list()
        return widget

    def _refresh_base_status(self):
        if DisposableVMManager.is_base_image_available():
            path = DisposableVMManager.get_base_image_path()
            self.base_status_label.setText(
                self.tr("Base image ready: {}").format(path)
            )
        else:
            self.base_status_label.setText(
                self.tr("No base image found. Create one to use disposable VMs.")
            )

    def _create_base_image(self):
        iso_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select ISO for Base Image"), "",
            self.tr("ISO Images (*.iso)"),
        )
        if not iso_path:
            return
        result = DisposableVMManager.create_base_image(iso_path)
        self.log(result.message)
        self._refresh_base_status()

    def _launch_disposable(self):
        result = DisposableVMManager.launch_disposable()
        self.log(result.message)
        if result.success:
            self._refresh_disposable_list()

    def _refresh_disposable_list(self):
        self.disposable_list.clear()
        names = DisposableVMManager.list_active_disposables()
        if not names:
            self.disposable_list.addItem(self.tr("No active disposable VMs."))
            return
        for name in names:
            self.disposable_list.addItem(name)

    # ==================================================================
    # Output log helper
    # ==================================================================

    def log(self, message: str):
        """Append a message to the output log."""
        self.output_text.append(message)
