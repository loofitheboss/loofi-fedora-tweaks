---
description: "Performance optimization guidelines for Python/PyQt6 desktop app"
applyTo: "**"
---

# Performance Optimization — Loofi Fedora Tweaks

## General Principles

- **Measure First, Optimize Second** — use `cProfile`, `line_profiler`, or `Py-Spy` to identify real bottlenecks
- **Optimize for the Common Case** — focus on frequently executed code paths
- **Avoid Premature Optimization** — write clear code first, optimize when needed
- **Set Performance Budgets** — GUI startup < 2s, tab load < 500ms

## Python Performance

### Caching

```python
# ✅ Cache expensive lookups
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_lookup(key: str) -> str:
    ...

# ✅ Cache shutil.which() calls (2-5ms each)
@lru_cache(maxsize=32)
def _cached_which(tool: str) -> Optional[str]:
    return shutil.which(tool)
```

### Data Structures

- Use `dict`/`set` for O(1) lookups instead of list scanning
- Use `collections.deque` for append/pop from both ends
- Prefer generators over list comprehensions for large datasets

### Subprocess Performance

- Always set `timeout=N` to prevent hangs
- Use `capture_output=True` instead of separate `stdout=PIPE, stderr=PIPE`
- Batch related subprocess calls when possible

```python
# ❌ BAD: Multiple subprocess calls for related data
name = subprocess.run(["hostname"], capture_output=True, text=True, timeout=5).stdout
kernel = subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=5).stdout

# ✅ GOOD: Single call when possible
info = subprocess.run(["hostnamectl", "--json=short"], capture_output=True, text=True, timeout=5)
```

### Avoid Common Pitfalls

- Never block the GUI thread with synchronous subprocess calls — use `CommandRunner` (QProcess)
- Avoid `import *` — slows module loading
- Avoid creating unnecessary objects in loops
- Use `str.join()` instead of repeated string concatenation

## PyQt6 GUI Performance

### Lazy Loading

- All 28 tabs use lazy loading — don't load until the user navigates to them
- Register via `MainWindow._lazy_tab()` loaders dict

### Rendering

- Minimize widget count — use `QStackedWidget` for tab switching
- Avoid frequent `repaint()`/`update()` calls — batch updates
- Use `QTimer.singleShot()` for deferred updates

```python
# ✅ Defer non-critical UI updates
from PyQt6.QtCore import QTimer
QTimer.singleShot(0, self._populate_list)
```

### Async Operations

```python
# ✅ Never block GUI — use CommandRunner
from utils.command_runner import CommandRunner
self.runner = CommandRunner()
self.runner.finished.connect(self.on_done)
self.runner.run_command(binary, args)
```

## Profiling

```bash
# Profile startup time
python -m cProfile -s cumulative loofi-fedora-tweaks/main.py 2>&1 | head -30

# Profile specific module
python -c "
import cProfile, pstats
cProfile.run('from utils.system import SystemManager; SystemManager.get_system_info()', 'prof.stats')
p = pstats.Stats('prof.stats')
p.sort_stats('cumulative').print_stats(10)
"
```

## Code Review Checklist

- [ ] No blocking I/O on the GUI thread
- [ ] Subprocess calls have `timeout=N`
- [ ] Expensive computations are cached (`@lru_cache`)
- [ ] No O(n²) algorithms where O(n) or O(n log n) would work
- [ ] `shutil.which()` calls are cached
- [ ] SystemManager methods use appropriate caching
- [ ] Large lists use generators or pagination
