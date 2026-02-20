# Release Notes — v50.0.0 "Forge"

**Release Date**: 2026-02-20
**Theme**: Quality Hardening & Code Forge

## Summary

v50.0 "Forge" is a pure quality hardening release that forges stronger foundations
across four pillars: test coverage expansion for 5 previously untested modules,
exception narrowing for the last 4 broad handlers, module docstring completion for
9 utils modules, and a general coverage push toward the 80% CI threshold.

## What's New

### Test Coverage Expansion

| Module | Before | Tests Added | Key Coverage |
| --- | --- | --- | --- |
| `utils/action_result.py` | 0% | 13 tests | Creation, serialization, factory methods, `from_dict` roundtrip |
| `utils/errors.py` | 0% | 21 tests | All 8 LoofiError subclasses, attributes, inheritance hierarchy |
| `utils/event_simulator.py` | 0% | 22 tests | All simulate methods with mocked EventBus |
| `utils/presets.py` | 0% | 23 tests | CRUD, sanitize_name, community presets, power profile helpers |
| `utils/remote_config.py` | 0% | 12 tests | Remote fetch, cache hit, local fallback, error emission |

**Total: 91 new test methods across 5 test files.**

### Exception Narrowing

| File | Line | Narrowed To |
| --- | --- | --- |
| `utils/error_handler.py` | L71 | `(ImportError, RuntimeError, OSError, ValueError, TypeError)` |
| `utils/error_handler.py` | L112 | `(RuntimeError, TypeError, AttributeError, OSError)` |
| `utils/event_bus.py` | L174 | `(RuntimeError, TypeError, ValueError, AttributeError)` |
| `utils/daemon.py` | L213 | `(ImportError, AttributeError, OSError)` |
| `utils/daemon.py` | L254 | `(OSError, RuntimeError, ValueError, subprocess.SubprocessError)` |
| `ui/lazy_widget.py` | L57 | `(ImportError, TypeError, RuntimeError, AttributeError)` |

Zero broad `except Exception` handlers remain in the 4 target files.

### Module Documentation

Added Google-style module-level docstrings to 9 utils modules that previously lacked them:

- `utils/__init__.py` — Utility package re-exports and shared helpers
- `utils/action_executor.py` — Backward-compatibility shim for ActionExecutor
- `utils/action_result.py` — Backward-compatibility shim for ActionResult
- `utils/command_runner.py` — Async command execution via QProcess
- `utils/fingerprint.py` — Fingerprint enrollment worker using fprintd
- `utils/history.py` — Action history tracking with JSON persistence
- `utils/operations.py` — Backward-compatibility shim for operation classes
- `utils/presets.py` — Preset management for system configuration snapshots
- `utils/remote_config.py` — Remote app catalog fetcher with caching

### Coverage Push

- 91 new test methods contribute to overall coverage improvement
- CI threshold: 80%
- All new tests follow `@patch` decorator pattern with module-under-test namespace

## Upgrade Notes

No breaking changes. This is a quality-only release with no functional changes.
