# BaseWorker Migration Guide

## Overview

This guide shows how to migrate ad-hoc QThread subclasses to the standardized `BaseWorker` pattern introduced in v23.0.

## Standard Pattern

### Before (Ad-hoc)

```python
from PyQt6.QtCore import QThread, pyqtSignal

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
```

### After (BaseWorker)

```python
from core.workers import BaseWorker
from typing import Any

class ModelDownloadWorker(BaseWorker):
    """Background worker for model downloads."""

    def __init__(self, model_id: str):
        super().__init__()
        self.model_id = model_id

    def do_work(self) -> Any:
        """Download the model and return the result."""
        result = AIModelManager.download_model(
            self.model_id,
            callback=lambda msg: self.report_progress(msg, 0),
        )
        # Return structured result for finished signal
        return {"success": result.success, "message": result.message}
```

## Signal Protocol Changes

### Old Signal Patterns

Different workers had inconsistent signal signatures:

```python
# Worker 1
finished = pyqtSignal(bool, str)

# Worker 2
finished = pyqtSignal(str)

# Worker 3
finished = pyqtSignal(bool, str, str)

# Worker 4
finished = pyqtSignal(bool, object)
```

### New Standardized Protocol

All workers now use consistent signals:

```python
started = pyqtSignal()                # No parameters
progress = pyqtSignal(str, int)       # message, percentage (0-100)
finished = pyqtSignal(object)         # result (Any type, usually dict)
error = pyqtSignal(str)               # error message
```

## UI Integration Changes

### Before

```python
self.worker = ModelDownloadWorker(model_id)
self.worker.progress.connect(self._on_download_progress)
self.worker.finished.connect(self._on_download_finished)
self.worker.start()

def _on_download_progress(self, message: str):
    self.log(message)

def _on_download_finished(self, success: bool, message: str):
    if success:
        self.log(f"Success: {message}")
    else:
        self.log(f"Error: {message}")
```

### After

```python
self.worker = ModelDownloadWorker(model_id)
self.worker.started.connect(lambda: self.log("Download started..."))
self.worker.progress.connect(self._on_download_progress)
self.worker.finished.connect(self._on_download_finished)
self.worker.error.connect(self._on_download_error)
self.worker.start()

def _on_download_progress(self, message: str, percentage: int):
    self.log(f"{message} ({percentage}%)")
    if hasattr(self, 'progress_bar'):
        self.progress_bar.setValue(percentage)

def _on_download_finished(self, result: dict):
    self.log(f"Success: {result['message']}")

def _on_download_error(self, error_msg: str):
    self.log(f"Error: {error_msg}")
```

## Cancellation Support

### Adding Cancellation

```python
class LongRunningWorker(BaseWorker):
    def do_work(self) -> Any:
        total_steps = 100
        for i in range(total_steps):
            # Check cancellation periodically
            if self.is_cancelled():
                return None

            # Do work
            process_step(i)

            # Report progress
            self.report_progress(f"Step {i+1}/{total_steps}", (i+1) * 100 // total_steps)

        return {"completed": True}
```

### UI Cancellation Button

```python
self.worker = LongRunningWorker()
self.cancel_button.clicked.connect(self.worker.cancel)
self.worker.finished.connect(lambda: self.cancel_button.setEnabled(False))
self.worker.error.connect(lambda _: self.cancel_button.setEnabled(False))
self.worker.start()
```

## Error Handling

Errors are automatically caught and emitted via the `error` signal:

```python
class RiskyWorker(BaseWorker):
    def do_work(self) -> Any:
        # No need for try/except - BaseWorker handles it
        result = risky_operation()
        if not result:
            raise ValueError("Operation failed")
        return result
```

## Result Types

Use dictionaries or dataclasses for complex results:

```python
from dataclasses import dataclass, asdict

@dataclass
class DownloadResult:
    success: bool
    file_path: str
    size_bytes: int
    duration_seconds: float

class DownloadWorker(BaseWorker):
    def do_work(self) -> dict:
        # Do download...
        result = DownloadResult(
            success=True,
            file_path="/tmp/model.bin",
            size_bytes=1024000,
            duration_seconds=5.2
        )
        return asdict(result)
```

## Migration Checklist

- [ ] Change inheritance from `QThread` to `BaseWorker`
- [ ] Rename `run()` method to `do_work()`
- [ ] Change `do_work()` return type to `Any` instead of `None`
- [ ] Return result data instead of emitting custom `finished` signal
- [ ] Replace custom `progress` signals with `report_progress(msg, pct)`
- [ ] Update UI signal connections to match new protocol
- [ ] Add `started` and `error` signal handlers in UI
- [ ] Add cancellation support if needed (check `is_cancelled()`)
- [ ] Test all success, error, and cancellation paths

## Workers to Migrate

Current ad-hoc workers in codebase:

1. **ui/ai_enhanced_tab.py**:
   - `ModelDownloadWorker` ✅ Example below
   - `IndexBuildWorker`
   - `RecordAudioWorker`
   - `TranscribeWorker`

2. **ui/community_tab.py**:
   - `FetchPresetsThread`
   - `FetchMarketplaceThread`

3. **ui/development_tab.py**:
   - (1 worker - needs verification)

Note: `utils/pulse.py` uses QObject + separate thread for DBus loop, which is a different pattern and should NOT be migrated.

## Example: Complete Migration

### Original (ai_enhanced_tab.py)

```python
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
```

### Migrated Version

```python
from core.workers import BaseWorker
from typing import Any, Dict

class ModelDownloadWorker(BaseWorker):
    """
    Background worker for AI model downloads.

    Downloads models from Hugging Face using AIModelManager.
    Reports download progress and returns structured result.

    Args:
        model_id: Hugging Face model identifier

    Returns:
        dict: {"success": bool, "message": str, "model_id": str}
    """

    def __init__(self, model_id: str):
        super().__init__()
        self.model_id = model_id

    def do_work(self) -> Dict[str, Any]:
        """
        Download the model and return result.

        Checks for cancellation during download and reports progress.
        """
        # Wrap callback to add percentage tracking
        def progress_callback(msg: str):
            if self.is_cancelled():
                return
            # Extract percentage if present in message
            percentage = self._extract_percentage(msg)
            self.report_progress(msg, percentage)

        result = AIModelManager.download_model(
            self.model_id,
            callback=progress_callback,
        )

        return {
            "success": result.success,
            "message": result.message,
            "model_id": self.model_id,
        }

    def _extract_percentage(self, message: str) -> int:
        """Extract percentage from progress message if present."""
        # Simple heuristic: look for "XX%" pattern
        import re
        match = re.search(r'(\d+)%', message)
        return int(match.group(1)) if match else 0
```

### Updated UI Code

```python
# Old
def download_model(self, model_id: str):
    self.worker = ModelDownloadWorker(model_id)
    self.worker.progress.connect(lambda msg: self.output_text.append(msg))
    self.worker.finished.connect(self._on_download_complete)
    self.worker.start()

def _on_download_complete(self, success: bool, message: str):
    if success:
        QMessageBox.information(self, "Success", message)
    else:
        QMessageBox.warning(self, "Error", message)
    self.worker = None

# New
def download_model(self, model_id: str):
    self.worker = ModelDownloadWorker(model_id)
    self.worker.started.connect(lambda: self.output_text.append("Starting download..."))
    self.worker.progress.connect(self._on_download_progress)
    self.worker.finished.connect(self._on_download_complete)
    self.worker.error.connect(self._on_download_error)
    self.worker.start()

def _on_download_progress(self, message: str, percentage: int):
    self.output_text.append(f"{message} ({percentage}%)")
    if hasattr(self, 'download_progress_bar'):
        self.download_progress_bar.setValue(percentage)

def _on_download_complete(self, result: dict):
    QMessageBox.information(
        self,
        "Success",
        f"Model {result['model_id']} downloaded: {result['message']}"
    )
    self.worker = None
    self.refresh_models()

def _on_download_error(self, error_msg: str):
    QMessageBox.warning(self, "Error", error_msg)
    self.worker = None
```

## Benefits

1. **Consistency**: All workers have same signal interface
2. **Safety**: Automatic error handling and logging
3. **Features**: Built-in cancellation and progress reporting
4. **Maintainability**: Single source of truth for worker pattern
5. **Testing**: Easier to mock and test standardized interface
6. **Documentation**: Self-documenting pattern with clear lifecycle
