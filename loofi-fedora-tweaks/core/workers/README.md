# Workers Module (v23.0 Architecture Hardening)

Standardized QThread worker pattern for background tasks in Loofi Fedora Tweaks.

## Quick Start

```python
from core.workers import BaseWorker
from typing import Any

class MyWorker(BaseWorker):
    def __init__(self, param: str):
        super().__init__()
        self.param = param

    def do_work(self) -> Any:
        # Check cancellation
        if self.is_cancelled():
            return None

        # Do work
        self.report_progress("Processing...", 50)
        result = process_something(self.param)

        return {"success": True, "data": result}

# Usage in UI
worker = MyWorker("value")
worker.started.connect(lambda: print("Started"))
worker.progress.connect(lambda msg, pct: print(f"{msg} - {pct}%"))
worker.finished.connect(lambda result: handle_result(result))
worker.error.connect(lambda msg: show_error(msg))
worker.start()

# To cancel
worker.cancel()
```

## Files

- **`base_worker.py`**: `BaseWorker` abstract base class
- **`example_worker.py`**: Example implementations (download, processing)
- **`MIGRATION_GUIDE.md`**: Detailed migration guide for existing workers
- **`README.md`**: This file

## Signal Protocol

All workers emit these signals:

- **`started()`**: Emitted when work begins
- **`progress(str, int)`**: Progress updates (message, percentage 0-100)
- **`finished(object)`**: Emitted on success with result data
- **`error(str)`**: Emitted on error with error message

## Features

- Automatic error handling and logging
- Built-in cancellation support
- Progress reporting
- Thread-safe result passing
- Consistent lifecycle

## Migration

See `MIGRATION_GUIDE.md` for full migration instructions from ad-hoc QThread workers.

## Workers to Migrate

### Priority 1 (Most Used)
- `ui/ai_enhanced_tab.py`: `ModelDownloadWorker`, `IndexBuildWorker`, `RecordAudioWorker`, `TranscribeWorker`
- `ui/community_tab.py`: `FetchPresetsThread`, `FetchMarketplaceThread`

### Priority 2
- `ui/development_tab.py`: 1 worker (needs verification)

### No Migration Needed
- `utils/pulse.py`: Uses QObject + separate thread for DBus loop (different pattern)

## Testing

Run tests:
```bash
pytest tests/test_base_worker_simple.py -v
```

See example workers in `example_worker.py` for testing patterns.
