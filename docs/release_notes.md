# Release Notes

## v14.0.0 "Quantum Leap" - February 2026

The Quantum Leap update is a reliability and polish release introducing automatic update checking, a What's New dialog for post-upgrade highlights, full configuration backup/restore/factory-reset management, and plugin lifecycle events.

### Highlights

- **Update Checker**: Automatic update notifications from GitHub releases API
- **What's New Dialog**: Post-upgrade dialog showing release highlights
- **Factory Reset**: Full backup/restore/reset management for all config files
- **Plugin Lifecycle Events**: `on_app_start`, `on_app_quit`, `on_tab_switch` hooks
- **1130+ Tests**: Comprehensive test coverage

### New Features

#### Update Checker

Check for app updates via GitHub releases API:

- Fetches latest release tag and compares with installed version
- `UpdateInfo` dataclass with version comparison and download URL
- Configurable timeout for network requests

#### What's New Dialog

Post-upgrade highlights dialog:

- Shows automatically after version upgrades
- Remembers last-seen version via `SettingsManager`
- Scrollable view with current and previous release notes
- "Don't show again" checkbox

#### Factory Reset & Backup Management

Full configuration backup and restore:

| Operation | Description |
|-----------|-------------|
| **Create Backup** | Snapshot all JSON config files with manifest |
| **List Backups** | Enumerate available backups with metadata |
| **Restore Backup** | Restore config from a named backup |
| **Delete Backup** | Remove old backups |
| **Factory Reset** | Reset to defaults with automatic pre-reset backup |

#### Plugin Lifecycle Events

New hooks for plugin developers:

- `on_app_start` — called when the application starts
- `on_app_quit` — called before application exits
- `on_tab_switch` — called when user switches tabs
- `on_settings_changed` — notified when settings change
- `get_settings_schema` — plugins can declare configurable settings

### New Files

- `utils/update_checker.py` — GitHub releases API update checker
- `utils/factory_reset.py` — Backup/restore/reset management
- `ui/whats_new_dialog.py` — Post-upgrade What's New dialog
- `tests/test_factory_reset.py` — Factory reset unit tests
- `tests/test_update_checker.py` — Update checker unit tests
loofi profile apply gaming      # Apply a profile
loofi profile create myprofile  # Create from current state
loofi profile delete myprofile  # Delete a custom profile

# Health history
loofi health-history show       # Show 24h summary
loofi health-history record     # Record current metrics
loofi health-history export data.json  # Export to JSON
loofi health-history prune      # Delete old data
```

### Shell Completions

New auto-completion scripts for:
- Bash (`completions/loofi.bash`)
- Zsh (`completions/loofi.zsh`)
- Fish (`completions/loofi.fish`)

### Test Coverage

- **839+ tests passing** (up from 564)
- 53 new profile tests
- 46 new health timeline tests
- 37 new UI smoke tests

### Files Added

- `utils/profiles.py` - Profile manager
- `utils/health_timeline.py` - Health metrics tracking
- `ui/profiles_tab.py` - Profiles UI
- `ui/health_timeline_tab.py` - Health Timeline UI
- `completions/loofi.bash` - Bash completions
- `completions/loofi.zsh` - Zsh completions
- `completions/loofi.fish` - Fish completions
- `docs/PLUGIN_SDK.md` - Expanded SDK guide
- `docs/TROUBLESHOOTING.md` - Troubleshooting guide

### Upgrade Notes

- No breaking changes from v12.0.0
- New tabs will appear automatically in the sidebar
- Existing presets and configurations are preserved
- CLI commands are additive (no removed commands)

---

## v12.0.0 "Sovereign Update" - February 2026

Virtualization, mesh networking, and state teleportation.

### Highlights

- VM Quick-Create wizard with preset flavors
- VFIO GPU Passthrough Assistant
- Loofi Link mesh networking
- State Teleport workspace capture/restore
- 18 tabs, 564 tests

---

## v11.0.0 "Aurora Update" - February 2026

Plugin manifests and diagnostics upgrades.

### Highlights

- Plugin manifest support with enable/disable
- Support bundle ZIP export
- Automation validation and dry-run

---

## v10.0.0 "Zenith Update" - February 2026

Major consolidation and modernization.

### Highlights

- Tab consolidation: 25 tabs to 15
- First-run wizard
- Command palette (Ctrl+K)
- Hardware profile auto-detection
- CI/CD pipeline

---

*For full version history, see [CHANGELOG.md](../CHANGELOG.md)*
