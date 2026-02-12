## Loofi Fedora Tweaks v25.0.2

Patch release focused on reliability and CI/testability for the plugin architecture.

### Fixed

- Removed hard runtime Qt dependency from `core/plugins/interface.py` so non-UI plugin/core imports work in headless environments.
- Hardened `ui/base_tab.py` inheritance fallback to avoid metaclass/MRO failures when Qt types are mocked.
- Updated `tests/test_frameless_mode_flag.py` to skip cleanly when PyQt6 system libraries are unavailable.
- Updated stale legacy test assertions to reflect plugin-driven tab registration and current version metadata.

### Validation

- `1824 passed`, `122 skipped` test outcomes on the release branch.
- Lint is clean with project flake8 configuration.

Tag: `v25.0.2`
