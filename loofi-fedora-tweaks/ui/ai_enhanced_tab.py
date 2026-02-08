"""
AI Enhanced Tab - Consolidated "AI Lab" with sub-tabs for Models, Voice, and Knowledge.
Part of v11.1-v11.3 "AI Polish" updates.

Provides:
- Models sub-tab: installed/available models, RAM estimates, download buttons
- Voice sub-tab: microphone status, record button, transcription output
- Knowledge sub-tab: indexing status, index/clear buttons, search field
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QTextEdit, QScrollArea, QFrame, QMessageBox, QProgressBar,
    QTabWidget, QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from utils.ai_models import AIModelManager, RECOMMENDED_MODELS
from utils.voice import VoiceManager, WHISPER_MODELS
from utils.context_rag import ContextRAGManager


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class ModelDownloadWorker(QThread):
    """Background worker for model downloads."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, model_id: str):
        super().__init__()
        self.model_id = model_id

    def run(self):
        result = AIModelManager.download_model(
            self.model_id,
            callback=lambda msg: self.progress.emit(msg),
        )
        self.finished.emit(result.success, result.message)


class IndexBuildWorker(QThread):
    """Background worker for building the RAG index."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def run(self):
        result = ContextRAGManager.build_index(
            callback=lambda msg: self.progress.emit(msg),
        )
        self.finished.emit(result.success, result.message)


class RecordAudioWorker(QThread):
    """Background worker for audio recording."""
    finished = pyqtSignal(str)

    def __init__(self, duration: int):
        super().__init__()
        self.duration = duration

    def run(self):
        path = VoiceManager.record_audio(duration_seconds=self.duration)
        self.finished.emit(path)


class TranscribeWorker(QThread):
    """Background worker for transcription."""
    finished = pyqtSignal(bool, str, str)

    def __init__(self, audio_path: str, model: str):
        super().__init__()
        self.audio_path = audio_path
        self.model = model

    def run(self):
        result = VoiceManager.transcribe(self.audio_path, self.model)
        text = result.data.get("text", "") if result.data else ""
        self.finished.emit(result.success, result.message, text)


# ---------------------------------------------------------------------------
# Main enhanced tab
# ---------------------------------------------------------------------------

class AIEnhancedTab(QWidget):
    """AI Lab enhanced tab with sub-tabs for Models, Voice, and Knowledge."""

    def __init__(self):
        super().__init__()
        self._workers = []
        self._last_recording_path = ""
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI with sub-tab navigation."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel(self.tr("AI Lab - Enhanced"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #a277ff; padding: 10px;")
        layout.addWidget(header)

        # Sub-tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("aiEnhancedTabs")
        self.tab_widget.addTab(self._create_models_tab(), self.tr("Models"))
        self.tab_widget.addTab(self._create_voice_tab(), self.tr("Voice"))
        self.tab_widget.addTab(self._create_knowledge_tab(), self.tr("Knowledge"))
        layout.addWidget(self.tab_widget)

        # Shared output log
        log_group = QGroupBox(self.tr("Output Log"))
        log_layout = QVBoxLayout(log_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        log_layout.addWidget(self.output_text)
        layout.addWidget(log_group)

    # ------------------------------------------------------------------
    # Models sub-tab
    # ------------------------------------------------------------------

    def _create_models_tab(self) -> QWidget:
        """Create the Models management sub-tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # System RAM info
        ram_mb = AIModelManager.get_system_ram()
        ram_group = QGroupBox(self.tr("System RAM"))
        ram_layout = QVBoxLayout(ram_group)

        self.ram_label = QLabel(
            self.tr("Total RAM: {} MB ({:.1f} GB)").format(ram_mb, ram_mb / 1024)
            if ram_mb > 0
            else self.tr("Unable to detect system RAM")
        )
        ram_layout.addWidget(self.ram_label)

        if ram_mb > 0:
            rec = AIModelManager.get_recommended_model(ram_mb)
            if rec:
                rec_label = QLabel(
                    self.tr("Recommended model: {} ({})").format(rec["name"], rec["size"])
                )
                rec_label.setStyleSheet("color: #82e0aa; font-weight: bold;")
                ram_layout.addWidget(rec_label)

        layout.addWidget(ram_group)

        # Installed models
        installed_group = QGroupBox(self.tr("Installed Models"))
        installed_layout = QVBoxLayout(installed_group)

        self.models_list = QListWidget()
        self.models_list.setMaximumHeight(140)
        installed_layout.addWidget(self.models_list)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton(self.tr("Refresh"))
        refresh_btn.clicked.connect(self._refresh_models)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        installed_layout.addLayout(btn_layout)
        layout.addWidget(installed_group)

        self._refresh_models()

        # Available models catalog
        catalog_group = QGroupBox(self.tr("Available Models"))
        catalog_layout = QVBoxLayout(catalog_group)

        for model_id, info in RECOMMENDED_MODELS.items():
            row = QHBoxLayout()
            label = QLabel(
                self.tr("{} - {} | RAM: {} MB | {}").format(
                    info["name"], info["size"], info["ram_required"], info["description"]
                )
            )
            label.setWordWrap(True)
            row.addWidget(label, stretch=1)

            dl_btn = QPushButton(self.tr("Download"))
            dl_btn.setProperty("model_id", model_id)
            dl_btn.clicked.connect(lambda checked, mid=model_id: self._download_model(mid))
            row.addWidget(dl_btn)

            catalog_layout.addLayout(row)

        # Progress bar
        self.model_progress = QProgressBar()
        self.model_progress.setVisible(False)
        self.model_progress.setRange(0, 0)
        catalog_layout.addWidget(self.model_progress)

        layout.addWidget(catalog_group)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _refresh_models(self):
        """Refresh the installed models list."""
        if not hasattr(self, "models_list"):
            return
        self.models_list.clear()

        models = AIModelManager.get_installed_models()
        if not models:
            item = QListWidgetItem(self.tr("No models installed"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.models_list.addItem(item)
        else:
            for model in models:
                ram_est = AIModelManager.estimate_ram_usage(model["name"])
                item = QListWidgetItem(
                    self.tr("{} ({}) - Est. RAM: {} MB").format(
                        model["name"], model["size"], ram_est
                    )
                )
                item.setData(Qt.ItemDataRole.UserRole, model["name"])
                self.models_list.addItem(item)

    def _download_model(self, model_id: str):
        """Start downloading a model in the background."""
        self._log(self.tr("Downloading {}...").format(model_id))
        self.model_progress.setVisible(True)

        worker = ModelDownloadWorker(model_id)
        worker.progress.connect(lambda msg: self._log(msg))
        worker.finished.connect(self._on_model_download_finished)
        self._workers.append(worker)
        worker.start()

    def _on_model_download_finished(self, success: bool, message: str):
        """Handle model download completion."""
        self.model_progress.setVisible(False)
        self._log(message)
        if success:
            self._refresh_models()

    # ------------------------------------------------------------------
    # Voice sub-tab
    # ------------------------------------------------------------------

    def _create_voice_tab(self) -> QWidget:
        """Create the Voice sub-tab for speech-to-text."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Status section
        status_group = QGroupBox(self.tr("Voice Status"))
        status_layout = QVBoxLayout(status_group)

        whisper_avail = VoiceManager.is_available()
        recording_avail = VoiceManager.is_recording_available()

        self.whisper_status = QLabel(
            self.tr("whisper.cpp: {}").format(
                self.tr("Available") if whisper_avail else self.tr("Not installed")
            )
        )
        status_layout.addWidget(self.whisper_status)

        self.recording_status = QLabel(
            self.tr("Recording tools: {}").format(
                self.tr("Available") if recording_avail else self.tr("Not found (arecord/parecord)")
            )
        )
        status_layout.addWidget(self.recording_status)

        # Microphone
        mic_info = VoiceManager.check_microphone()
        mic_text = (
            self.tr("Microphone: {} device(s) detected").format(len(mic_info["devices"]))
            if mic_info["available"]
            else self.tr("Microphone: Not detected")
        )
        self.mic_label = QLabel(mic_text)
        status_layout.addWidget(self.mic_label)

        layout.addWidget(status_group)

        # Recording section
        record_group = QGroupBox(self.tr("Record and Transcribe"))
        record_layout = QVBoxLayout(record_group)

        # Model selector
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel(self.tr("Whisper Model:")))
        self.whisper_model_combo = QComboBox()
        for model_name, info in WHISPER_MODELS.items():
            self.whisper_model_combo.addItem(
                self.tr("{} ({} MB RAM)").format(info["name"], info["ram_required"]),
                model_name,
            )
        model_row.addWidget(self.whisper_model_combo)
        model_row.addStretch()
        record_layout.addLayout(model_row)

        # Duration selector
        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel(self.tr("Duration (seconds):")))
        self.duration_spin = QSpinBox()
        self.duration_spin.setMinimum(1)
        self.duration_spin.setMaximum(30)
        self.duration_spin.setValue(5)
        dur_row.addWidget(self.duration_spin)
        dur_row.addStretch()
        record_layout.addLayout(dur_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.record_btn = QPushButton(self.tr("Record"))
        self.record_btn.clicked.connect(self._record_audio)
        btn_row.addWidget(self.record_btn)

        self.transcribe_btn = QPushButton(self.tr("Transcribe Last Recording"))
        self.transcribe_btn.clicked.connect(self._transcribe_last)
        self.transcribe_btn.setEnabled(False)
        btn_row.addWidget(self.transcribe_btn)

        btn_row.addStretch()
        record_layout.addLayout(btn_row)

        # Transcription output
        record_layout.addWidget(QLabel(self.tr("Transcription:")))
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setMaximumHeight(120)
        record_layout.addWidget(self.transcription_text)

        layout.addWidget(record_group)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _record_audio(self):
        """Start recording audio in the background."""
        duration = self.duration_spin.value()
        self._log(self.tr("Recording for {} seconds...").format(duration))
        self.record_btn.setEnabled(False)

        worker = RecordAudioWorker(duration)
        worker.finished.connect(self._on_recording_finished)
        self._workers.append(worker)
        worker.start()

    def _on_recording_finished(self, path: str):
        """Handle recording completion."""
        self.record_btn.setEnabled(True)
        if path:
            self._last_recording_path = path
            self.transcribe_btn.setEnabled(True)
            self._log(self.tr("Recording saved to: {}").format(path))
        else:
            self._log(self.tr("Recording failed. Check microphone and recording tools."))

    def _transcribe_last(self):
        """Transcribe the last recorded audio."""
        if not self._last_recording_path:
            self._log(self.tr("No recording available. Record audio first."))
            return

        model = self.whisper_model_combo.currentData()
        self._log(self.tr("Transcribing with model '{}'...").format(model))
        self.transcribe_btn.setEnabled(False)

        worker = TranscribeWorker(self._last_recording_path, model)
        worker.finished.connect(self._on_transcription_finished)
        self._workers.append(worker)
        worker.start()

    def _on_transcription_finished(self, success: bool, message: str, text: str):
        """Handle transcription completion."""
        self.transcribe_btn.setEnabled(True)
        if success:
            self.transcription_text.setPlainText(text)
            self._log(self.tr("Transcription complete."))
        else:
            self._log(self.tr("Transcription failed: {}").format(message))

    # ------------------------------------------------------------------
    # Knowledge sub-tab
    # ------------------------------------------------------------------

    def _create_knowledge_tab(self) -> QWidget:
        """Create the Knowledge sub-tab for RAG indexing and search."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # Index status
        status_group = QGroupBox(self.tr("Index Status"))
        status_layout = QVBoxLayout(status_group)

        stats = ContextRAGManager.get_index_stats()
        indexed = ContextRAGManager.is_indexed()

        self.index_status_label = QLabel(
            self.tr("Index: {} files, {} chunks ({} bytes)").format(
                stats["total_files"], stats["total_chunks"], stats["index_size_bytes"]
            )
            if indexed
            else self.tr("No index built yet")
        )
        status_layout.addWidget(self.index_status_label)

        self.index_path_label = QLabel(
            self.tr("Index location: {}").format(ContextRAGManager.get_index_path())
        )
        self.index_path_label.setStyleSheet("color: #888; font-size: 11px;")
        status_layout.addWidget(self.index_path_label)

        # Action buttons
        idx_btn_row = QHBoxLayout()

        self.build_index_btn = QPushButton(self.tr("Build Index"))
        self.build_index_btn.clicked.connect(self._build_index)
        idx_btn_row.addWidget(self.build_index_btn)

        self.clear_index_btn = QPushButton(self.tr("Clear Index"))
        self.clear_index_btn.clicked.connect(self._clear_index)
        idx_btn_row.addWidget(self.clear_index_btn)

        self.refresh_stats_btn = QPushButton(self.tr("Refresh Stats"))
        self.refresh_stats_btn.clicked.connect(self._refresh_index_stats)
        idx_btn_row.addWidget(self.refresh_stats_btn)

        idx_btn_row.addStretch()
        status_layout.addLayout(idx_btn_row)

        layout.addWidget(status_group)

        # Search section
        search_group = QGroupBox(self.tr("Search Knowledge Base"))
        search_layout = QVBoxLayout(search_group)

        query_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Enter search query..."))
        self.search_input.returnPressed.connect(self._search_index)
        query_row.addWidget(self.search_input)

        search_btn = QPushButton(self.tr("Search"))
        search_btn.clicked.connect(self._search_index)
        query_row.addWidget(search_btn)

        search_layout.addLayout(query_row)

        # Results
        search_layout.addWidget(QLabel(self.tr("Results:")))
        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        self.search_results.setMaximumHeight(200)
        search_layout.addWidget(self.search_results)

        layout.addWidget(search_group)

        # Indexable files preview
        files_group = QGroupBox(self.tr("Indexable Files"))
        files_layout = QVBoxLayout(files_group)

        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(150)
        files_layout.addWidget(self.files_list)

        scan_btn = QPushButton(self.tr("Scan Files"))
        scan_btn.clicked.connect(self._scan_files)
        files_layout.addWidget(scan_btn)

        layout.addWidget(files_group)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_index(self):
        """Build the RAG index in the background."""
        self._log(self.tr("Building index..."))
        self.build_index_btn.setEnabled(False)

        worker = IndexBuildWorker()
        worker.progress.connect(lambda msg: self._log(msg))
        worker.finished.connect(self._on_index_build_finished)
        self._workers.append(worker)
        worker.start()

    def _on_index_build_finished(self, success: bool, message: str):
        """Handle index build completion."""
        self.build_index_btn.setEnabled(True)
        self._log(message)
        self._refresh_index_stats()

    def _clear_index(self):
        """Clear the RAG index."""
        reply = QMessageBox.question(
            self,
            self.tr("Clear Index"),
            self.tr("Are you sure you want to clear the knowledge index?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = ContextRAGManager.clear_index()
            self._log(result.message)
            self._refresh_index_stats()

    def _refresh_index_stats(self):
        """Refresh index statistics display."""
        stats = ContextRAGManager.get_index_stats()
        indexed = ContextRAGManager.is_indexed()

        if indexed:
            self.index_status_label.setText(
                self.tr("Index: {} files, {} chunks ({} bytes)").format(
                    stats["total_files"], stats["total_chunks"], stats["index_size_bytes"]
                )
            )
        else:
            self.index_status_label.setText(self.tr("No index built yet"))

    def _search_index(self):
        """Search the knowledge index."""
        query = self.search_input.text().strip()
        if not query:
            return

        results = ContextRAGManager.search_index(query)
        self.search_results.clear()

        if not results:
            self.search_results.setPlainText(self.tr("No results found."))
            return

        output_lines = []
        for i, r in enumerate(results, 1):
            output_lines.append(
                self.tr("--- Result {} (score: {}) ---").format(i, r["relevance_score"])
            )
            output_lines.append(self.tr("File: {}").format(r["file_path"]))
            output_lines.append(r["chunk"][:200])
            output_lines.append("")

        self.search_results.setPlainText("\n".join(output_lines))

    def _scan_files(self):
        """Scan for indexable files and display them."""
        self.files_list.clear()
        files = ContextRAGManager.scan_indexable_files()

        for f in files:
            status = self.tr("OK") if f["indexable"] else self.tr("Skipped")
            size_kb = f["size"] // 1024 if f["size"] > 0 else 0
            item = QListWidgetItem(
                self.tr("[{}] {} ({} KB)").format(status, f["path"], size_kb)
            )
            self.files_list.addItem(item)

        self._log(self.tr("Found {} files ({} indexable)").format(
            len(files), sum(1 for f in files if f["indexable"])
        ))

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _log(self, message: str):
        """Append a message to the shared output log."""
        self.output_text.append(message)
