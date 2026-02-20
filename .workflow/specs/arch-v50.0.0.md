# Architecture Spec - v50.0.0 "Forge"

## Design Rationale

v50.0.0 is a quality hardening release focused on four pillars: (1) closing the remaining
5 untested modules with dedicated test suites, (2) narrowing the 4 remaining broad
`except Exception` handlers, (3) adding module-level docstrings to 9 utils modules that
lack them, and (4) a general coverage push targeting the 80% CI threshold.

No architectural changes or new features — pure quality forging.

## Scope

### 1. Test Coverage Expansion — 5 Untested Modules

| Module | Current Coverage | Target |
|--------|-----------------|--------|
| `utils/action_result.py` | 0% (no test file) | Dedicated test suite |
| `utils/errors.py` | 0% (no test file) | Dedicated test suite |
| `utils/event_simulator.py` | 0% (no test file) | Dedicated test suite |
| `utils/presets.py` | 0% (no test file) | Dedicated test suite |
| `utils/remote_config.py` | 0% (no test file) | Dedicated test suite |

### 2. Exception Narrowing — 4 Remaining Sites

| File | Line | Current | Target |
|------|------|---------|--------|
| `utils/error_handler.py` | ~112 | `except Exception as e:` | Narrow to specific types |
| `utils/event_bus.py` | ~174 | `except Exception as e:` | Narrow to specific types |
| `utils/daemon.py` | ~254 | `except Exception as e:` | Narrow to specific types |
| `ui/lazy_widget.py` | ~57 | `except Exception as e:` | Narrow to specific types |

### 3. Module Docstrings — 9 Utils Modules

Missing module-level docstrings: `__init__.py`, `action_executor.py`, `action_result.py`,
`command_runner.py`, `fingerprint.py`, `history.py`, `operations.py`, `presets.py`,
`remote_config.py`.

### 4. Coverage Push

Additional test expansion for modules with low coverage to push overall above 80%.

## Key Decisions

### Quality-Only Release

No new features, no architectural changes. All work improves existing code quality,
test coverage, and documentation consistency.

### Exception Narrowing Strategy

Each broad handler will be analyzed for what exceptions actually occur in that context.
Replace with the most specific types possible while maintaining error resilience at
boundary layers (error_handler, event_bus callbacks, daemon main loop).

### Docstring Standard

Google-style docstrings with one-line summary. Module-level docstrings describe the
module's purpose and key exports.

## Risks

- `utils/daemon.py` broad handler is in the main daemon loop — narrowing must preserve
  daemon resilience. Consider keeping a final catch-all at the outermost boundary with
  explicit logging.
- Coverage push may require identifying additional low-coverage modules beyond the 5
  currently untested ones.

