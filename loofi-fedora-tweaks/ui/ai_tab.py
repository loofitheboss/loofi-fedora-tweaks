"""
AI Lab Tab - Local AI and LLM management interface.
Part of v8.1 "Neural" update.

Features:
- AI hardware detection display
- Ollama installation and service management
- Model browser and download
- GPU configuration helpers
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QTextEdit, QScrollArea, QFrame, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from utils.hardware import HardwareManager
from utils.ai import OllamaManager, AIConfigManager


class ModelPullWorker(QThread):
    """Background worker for model downloads."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
    
    def run(self):
        result = OllamaManager.pull_model(
            self.model_name,
            callback=lambda msg: self.progress.emit(msg)
        )
        self.finished.emit(result.success, result.message)


class AITab(QWidget):
    """AI Lab tab for managing local AI/LLM setup."""
    
    def __init__(self):
        super().__init__()
        self.workers = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(self.tr("🧠 AI Lab"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff;")
        layout.addWidget(header)
        
        # Hardware detection
        layout.addWidget(self._create_hardware_section())
        
        # Ollama management
        layout.addWidget(self._create_ollama_section())
        
        # Models
        layout.addWidget(self._create_models_section())
        
        # Output log
        log_group = QGroupBox(self.tr("Output Log"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        layout.addWidget(log_group)
        
        layout.addStretch()
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_hardware_section(self) -> QGroupBox:
        """Create AI hardware detection section."""
        group = QGroupBox(self.tr("🔧 AI Hardware"))
        layout = QVBoxLayout(group)
        
        # Get capabilities
        caps = HardwareManager.get_ai_capabilities()
        summary = HardwareManager.get_ai_summary()
        
        self.hw_label = QLabel(summary)
        self.hw_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.hw_label)
        
        # Detailed info
        details_layout = QHBoxLayout()
        
        items = [
            ("CUDA (NVIDIA)", caps["cuda"]),
            ("ROCm (AMD)", caps["rocm"]),
            ("Intel NPU", caps["npu_intel"]),
            ("AMD NPU", caps["npu_amd"])
        ]
        
        for name, available in items:
            icon = "✅" if available else "❌"
            lbl = QLabel(f"{icon} {name}")
            lbl.setStyleSheet(f"color: {'#82e0aa' if available else '#888'};")
            details_layout.addWidget(lbl)
        
        details_layout.addStretch()
        layout.addLayout(details_layout)
        
        # GPU memory if available
        gpu_mem = AIConfigManager.get_gpu_memory()
        if gpu_mem["total_mb"] > 0:
            mem_label = QLabel(
                f"GPU Memory: {gpu_mem['free_mb']} MB free / {gpu_mem['total_mb']} MB total"
            )
            mem_label.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(mem_label)
        
        # Refresh button
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton(self.tr("🔄 Refresh Detection"))
        refresh_btn.clicked.connect(self._refresh_hardware)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return group
    
    def _create_ollama_section(self) -> QGroupBox:
        """Create Ollama management section."""
        group = QGroupBox(self.tr("🦙 Ollama Runtime"))
        layout = QVBoxLayout(group)
        
        # Status
        status_layout = QHBoxLayout()
        
        installed = OllamaManager.is_installed()
        running = OllamaManager.is_running() if installed else False
        
        install_icon = "✅" if installed else "❌"
        running_icon = "🟢" if running else "🔴"
        
        self.ollama_status = QLabel(
            f"{install_icon} Installed  |  {running_icon} {'Running' if running else 'Stopped'}"
        )
        status_layout.addWidget(self.ollama_status)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        if not installed:
            install_btn = QPushButton(self.tr("📥 Install Ollama"))
            install_btn.clicked.connect(self._install_ollama)
            btn_layout.addWidget(install_btn)
        else:
            if not running:
                start_btn = QPushButton(self.tr("▶️ Start Service"))
                start_btn.clicked.connect(self._start_ollama)
                btn_layout.addWidget(start_btn)
            else:
                stop_btn = QPushButton(self.tr("⏹️ Stop Service"))
                stop_btn.setEnabled(False)  # TODO: implement stop
                btn_layout.addWidget(stop_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Info
        info_label = QLabel(self.tr(
            "Ollama is the recommended way to run local LLMs. "
            "It handles model management and provides a simple API."
        ))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info_label)
        
        return group
    
    def _create_models_section(self) -> QGroupBox:
        """Create model management section."""
        group = QGroupBox(self.tr("📦 Models"))
        layout = QVBoxLayout(group)
        
        # Check if Ollama is available
        if not OllamaManager.is_installed():
            layout.addWidget(QLabel(self.tr("Install Ollama first to manage models.")))
            return group
        
        # Installed models list
        layout.addWidget(QLabel(self.tr("Installed Models:")))
        
        self.models_list = QListWidget()
        self.models_list.setMaximumHeight(120)
        layout.addWidget(self.models_list)
        
        self._refresh_models()
        
        # Model actions
        model_btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton(self.tr("🔄 Refresh"))
        refresh_btn.clicked.connect(self._refresh_models)
        model_btn_layout.addWidget(refresh_btn)
        
        delete_btn = QPushButton(self.tr("🗑️ Delete Selected"))
        delete_btn.clicked.connect(self._delete_model)
        model_btn_layout.addWidget(delete_btn)
        
        model_btn_layout.addStretch()
        layout.addLayout(model_btn_layout)
        
        # Download new model
        layout.addWidget(QLabel(self.tr("Download Model:")))
        
        download_layout = QHBoxLayout()
        
        self.model_combo = QComboBox()
        for model_id, info in OllamaManager.RECOMMENDED_MODELS.items():
            self.model_combo.addItem(
                f"{info['name']} ({info['size']})",
                model_id
            )
        download_layout.addWidget(self.model_combo)
        
        download_btn = QPushButton(self.tr("📥 Download"))
        download_btn.clicked.connect(self._download_model)
        download_layout.addWidget(download_btn)
        
        download_layout.addStretch()
        layout.addLayout(download_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        return group
    
    def _refresh_hardware(self):
        """Refresh hardware detection."""
        summary = HardwareManager.get_ai_summary()
        self.hw_label.setText(summary)
        self.log(self.tr("Hardware detection refreshed."))
    
    def _install_ollama(self):
        """Install Ollama."""
        self.log(self.tr("Installing Ollama... This may take a few minutes."))
        
        # Run in background - simplified for demo
        result = OllamaManager.install()
        self.log(result.message)
        
        if result.success:
            QMessageBox.information(
                self,
                self.tr("Installation Complete"),
                self.tr("Ollama has been installed. Please refresh the tab.")
            )
    
    def _start_ollama(self):
        """Start Ollama service."""
        result = OllamaManager.start_service()
        self.log(result.message)
        
        # Update status
        if result.success:
            self.ollama_status.setText("✅ Installed  |  🟢 Running")
    
    def _refresh_models(self):
        """Refresh installed models list."""
        if not hasattr(self, 'models_list'):
            return
        
        self.models_list.clear()
        models = OllamaManager.list_models()
        
        if not models:
            item = QListWidgetItem(self.tr("No models installed"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.models_list.addItem(item)
        else:
            for model in models:
                item = QListWidgetItem(f"🤖 {model['name']} ({model['size']})")
                item.setData(Qt.ItemDataRole.UserRole, model['name'])
                self.models_list.addItem(item)
    
    def _download_model(self):
        """Download selected model."""
        model_id = self.model_combo.currentData()
        if not model_id:
            return
        
        self.log(self.tr(f"Downloading {model_id}..."))
        self.progress_bar.setVisible(True)
        
        worker = ModelPullWorker(model_id)
        worker.progress.connect(lambda msg: self.log(msg))
        worker.finished.connect(self._on_download_finished)
        self.workers.append(worker)
        worker.start()
    
    def _on_download_finished(self, success: bool, message: str):
        """Handle download completion."""
        self.progress_bar.setVisible(False)
        self.log(message)
        
        if success:
            self._refresh_models()
    
    def _delete_model(self):
        """Delete selected model."""
        current = self.models_list.currentItem()
        if not current:
            self.log(self.tr("No model selected."))
            return
        
        model_name = current.data(Qt.ItemDataRole.UserRole)
        if not model_name:
            return
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr(f"Delete model '{model_name}'?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = OllamaManager.delete_model(model_name)
            self.log(result.message)
            if result.success:
                self._refresh_models()
    
    def log(self, message: str):
        """Add message to log."""
        self.output_text.append(message)
