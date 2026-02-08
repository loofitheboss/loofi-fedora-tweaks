# Release Notes

## v13.0.0 "Nexus Update" - February 2026

The Nexus Update is a major integration release that brings system profiles for quick-switching configurations, health timeline for tracking metrics over time, and an enhanced plugin SDK.

### Highlights

- **System Profiles**: 5 built-in profiles (Gaming, Development, Battery Saver, Presentation, Server) for one-click system configuration
- **Health Timeline**: SQLite-based metrics tracking with anomaly detection and export capabilities
- **Plugin SDK v2**: Enhanced plugin system with permissions model, update checking, and dependency validation
- **20 Tabs**: New Profiles and Health tabs in the sidebar
- **839+ Tests**: Comprehensive test coverage

### New Features

#### System Profiles

Quick-switch between optimized system configurations:

| Profile | Description |
|---------|-------------|
| **Gaming** | Performance governor, compositor disabled, DND notifications, gamemode |
| **Development** | Schedutil governor, Docker/Podman services enabled |
| **Battery Saver** | Powersave governor, reduced compositor, critical notifications only |
| **Presentation** | Performance governor, screen timeout disabled, DND mode |
| **Server** | Performance governor, headless optimization |

Features:
- Create custom profiles with your preferred settings
- Capture current system state as a new profile
- One-click profile application with confirmation
- Active profile indicator

#### Health Timeline

Track system health metrics over time:

- **Metrics**: CPU temperature, RAM usage, disk usage, load average
- **Storage**: SQLite database with 30-day default retention
- **Anomaly Detection**: Flag values 2+ standard deviations from mean
- **Export**: JSON and CSV export for external analysis
- **Summary**: Min/max/avg statistics per metric type

#### Plugin SDK v2

Enhanced plugin development capabilities:

- **Permissions Model**: Plugins declare required permissions (network, filesystem, system)
- **Update Checking**: Plugins can check for updates via remote manifest URL
- **Dependency Validation**: Manifest-based dependency resolution before load
- **Hello World Example**: Complete example plugin in `plugins/hello_world/`

### CLI Enhancements

New commands for v13.0:

```bash
# Profile management
loofi profile list              # List all profiles
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
