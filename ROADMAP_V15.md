# Loofi Fedora Tweaks v15.0.0 "Nebula" — Roadmap

## Vision

v15.0 "Nebula" is a **system intelligence and integration** release that makes Loofi smarter about the system it manages. It introduces a performance auto-tuner, a system snapshot timeline, an integrated log viewer with smart filtering, and a quick-action command bar — all designed to let users understand, optimize, and act on their system faster than ever.

## Release Features

### 1. Performance Auto-Tuner (`utils/auto_tuner.py` + `ui/tuner_section` in Hardware tab)

An intelligent system optimizer that analyzes current workload and recommends/applies performance tweaks.

**Capabilities:**
- Detect current workload profile (idle, compilation, gaming, browsing, server)
- Recommend CPU governor, I/O scheduler, swappiness, and THP settings
- One-click "Optimize Now" that applies recommendations
- History of applied tuning profiles with rollback
- CLI: `loofi tuner analyze`, `loofi tuner apply`, `loofi tuner history`

**Architecture:**
- `utils/auto_tuner.py` — `AutoTuner` class with `@staticmethod` methods
- Reads from `/proc/loadavg`, `/proc/meminfo`, `/sys/block/*/queue/scheduler`
- Uses `PrivilegedCommand` for sysctl and governor changes
- Returns `TuningRecommendation` dataclass

### 2. System Snapshot Timeline (`utils/snapshot_manager.py` + sub-tab in Maintenance)

A unified interface for Timeshift, Snapper, and BTRFS snapshots with a visual timeline.

**Capabilities:**
- Auto-detect available snapshot backends (Timeshift, Snapper, BTRFS)
- List snapshots in chronological timeline
- Create labeled snapshots before risky operations
- Delete old snapshots with retention policy
- Compare snapshot metadata (packages installed, config changes)
- CLI: `loofi snapshot list`, `loofi snapshot create`, `loofi snapshot delete`

**Architecture:**
- `utils/snapshot_manager.py` — `SnapshotManager` with backend detection
- `SnapshotInfo` dataclass with timestamp, label, backend, size
- Integrates with `SafetyManager` for pre-operation snapshots

### 3. Smart Log Viewer (`utils/smart_logs.py` + sub-tab in Diagnostics)

An intelligent journal/log viewer with severity filtering, pattern detection, and plain-English summaries.

**Capabilities:**
- Stream journalctl output with severity color-coding
- Filter by unit, priority, time range, and keyword
- Detect common error patterns (OOM, segfault, disk full, auth failure)
- Show "plain English" summaries for known error patterns
- Export filtered logs to file
- CLI: `loofi logs show`, `loofi logs errors`, `loofi logs export`

**Architecture:**
- `utils/smart_logs.py` — `SmartLogViewer` with pattern matchers
- `LogEntry` dataclass with timestamp, unit, priority, message, pattern_match
- `LogPattern` registry mapping regex patterns to human-readable explanations
- Uses `subprocess` with `journalctl --output=json` for structured parsing

### 4. Quick Actions Bar (`ui/quick_actions.py` + MainWindow integration)

A floating quick-action bar (Ctrl+Shift+K) for power users to execute common operations without navigating tabs.

**Capabilities:**
- Searchable action palette with fuzzy matching
- Grouped by category (Maintenance, Security, Hardware, Network, etc.)
- Recent actions history (last 10)
- Keyboard-driven: type to filter, Enter to execute
- Shows operation description and estimated time
- Extensible: plugins can register custom quick actions

**Architecture:**
- `ui/quick_actions.py` — `QuickActionsBar` (QDialog with QLineEdit + QListWidget)
- `QuickAction` dataclass with name, category, callback, description, icon
- `QuickActionRegistry` singleton for action registration
- Integrated into MainWindow with `Ctrl+Shift+K` shortcut

## Agent Assignments

| Agent | Responsibility |
|-------|---------------|
| **Planner** | Task breakdown, dependency ordering, progress tracking |
| **Builder** | Implementing utils/ business logic modules |
| **Sculptor** | Implementing ui/ tab integrations and CLI commands |
| **Guardian** | Writing tests, verifying quality, running test suite |

## Timeline

1. Create agents and roadmap
2. Implement utils/ layer (auto_tuner, snapshot_manager, smart_logs, quick_actions registry)
3. Implement UI integrations and CLI commands
4. Write comprehensive tests
5. Version bump, changelog, release notes
6. Build RPM and publish GitHub release

## Success Criteria

- All 4 features implemented with utils + UI + CLI layers
- 100+ new tests added
- All existing tests still pass
- RPM builds cleanly
- GitHub release published with full notes
