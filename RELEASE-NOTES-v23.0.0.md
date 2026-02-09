# v23.0.0 "Architecture Hardening"

**Release Date**: 2026-02-09

Loofi Fedora Tweaks v23.0.0 delivers major architectural improvements focused on code organization, privilege escalation, and service layer refactoring. This release lays the foundation for better maintainability and testability.

## Highlights

- **BaseActionExecutor ABC**: Abstract base class for all executor implementations with built-in pkexec integration
- **Service Layer Organization**: System and hardware services now live in dedicated `services/` directories
- **Centralized Worker Pattern**: BaseWorker QThread pattern in `core/workers/` for non-blocking UI operations
- **Build Scripts Consolidation**: All packaging scripts unified in `scripts/` directory
- **Comprehensive Testing**: 34 new import validation tests ensure backward compatibility
- **Privilege Escalation**: Seamless pkexec support via `privileged=True` parameter

## Architecture Changes

### Executor Layer
- Created `BaseActionExecutor` abstract base class in `core/executor/`
- Refactored `ActionExecutor` to inherit from `BaseActionExecutor`
- Added pkexec integration for privileged operations
- Structured results via `ActionResult` dataclass

### Service Layer Migration
- **System Services** → `services/system/`
  - system.py, services.py, processes.py, process.py
- **Hardware Services** → `services/hardware/`
  - hardware.py, battery.py, disk.py, temperature.py, bluetooth.py, hardware_profiles.py

### Worker Pattern
- Centralized `BaseWorker` QThread pattern in `core/workers/`
- Non-blocking UI operations for long-running tasks
- Consistent error handling and result signals

### Build & Packaging
- Consolidated all build scripts into `scripts/` directory
- `build_rpm.sh` dynamically reads version from `version.py`
- Stubs for `build_flatpak.sh`, `build_appimage.sh`, `build_sdist.sh` (planned for v23.1+)

## Backward Compatibility

- Deprecation shims added in `utils/` for old import paths
- Warnings logged when using deprecated imports
- Old imports will be removed in **v25.0.0**

## Installation

### RPM (Fedora/RHEL)
```bash
wget https://github.com/loofitheboss/loofi-fedora-tweaks/releases/download/v23.0.0/loofi-fedora-tweaks-23.0.0-1.fc43.noarch.rpm
sudo dnf install ./loofi-fedora-tweaks-23.0.0-1.fc43.noarch.rpm
```

### From Source
```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
git checkout v23.0.0
chmod +x scripts/build_rpm.sh
./scripts/build_rpm.sh
sudo dnf install rpmbuild/RPMS/noarch/loofi-fedora-tweaks-23.0.0-1.*.noarch.rpm
```

## Testing

All 1715 tests passing. Run test suite with:
```bash
pytest tests/
```

## Full Changelog

See [CHANGELOG.md](CHANGELOG.md#2300---2026-02-09-architecture-hardening) for complete details.

## What's Next

**v24.0 "Advanced Power Features"** (planned)
- Profiles system with JSON export/import
- Live log panel for operation tracking
- Advanced mode toggle for power users
- System snapshot before destructive operations

---

**Generated with Claude Code**
