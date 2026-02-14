# v37.0.0 "Pinnacle" — Architecture Spec

## Theme

Smart features and ecosystem expansion. Practical Fedora system management
capabilities: update intelligence, extension management, Flatpak improvements,
boot customization, Wayland-aware display config, backup wizard, and plugin showcase.

## Design Decisions

### Smart Update Manager

- New module: `utils/update_manager.py`
- `UpdateManager` class with `@staticmethod` methods
- `check_updates() → List[UpdateEntry]` — list available updates with metadata
- `preview_conflicts(packages) → List[ConflictEntry]` — simulate install, report dependency conflicts
- `schedule_update(packages, when) → ScheduledUpdate` — schedule unattended update via systemd timer
- `rollback_last() → Tuple[str, List[str], str]` — rollback last transaction (dnf history undo / rpm-ostree rollback)
- `UpdateEntry` dataclass: name, version, old_version, size, repo, severity (security/bugfix/enhancement)
- `ConflictEntry` dataclass: package, conflict_with, reason
- `ScheduledUpdate` dataclass: id, packages, scheduled_time, timer_unit
- Atomic Fedora: uses `rpm-ostree upgrade --preview` for conflict check, `rpm-ostree rollback` for undo
- Traditional: uses `dnf check-update`, `dnf history undo last`
- UI: new section in existing `maintenance_tab.py` (sub-tab or expandable section)
- CLI: `update check`, `update schedule`, `update rollback` subcommands

### Extension Manager

- New module: `utils/extension_manager.py`
- `ExtensionManager` class with desktop-environment-aware logic
- GNOME: `gnome-extensions list/install/enable/disable/remove` via subprocess
- KDE: `plasmapkg2 --list/--install/--remove` via subprocess
- `list_installed() → List[ExtensionEntry]` — installed extensions with enabled/disabled state
- `list_available(query) → List[ExtensionEntry]` — search GNOME Extensions API / KDE Store
- `install(uuid)`, `enable(uuid)`, `disable(uuid)`, `remove(uuid)` — management ops
- `ExtensionEntry` dataclass: uuid, name, description, version, author, enabled, homepage
- Desktop detection: check `$XDG_CURRENT_DESKTOP` or `loginctl show-session`
- UI: new `extensions_tab.py` — browse/search, toggle enable/disable, install/remove buttons
- Falls back gracefully if neither GNOME nor KDE detected

### Flatpak Manager Improvements

- Extend existing `utils/software_utils.py` or create `utils/flatpak_manager.py`
- `get_flatpak_sizes() → List[FlatpakSizeEntry]` — `flatpak list --columns=name,application,size`
- `get_flatpak_permissions(app_id) → List[str]` — parse `flatpak info --show-permissions`
- `find_orphan_runtimes() → List[str]` — runtimes not referenced by any app
- `cleanup_unused()` — `flatpak uninstall --unused`
- `FlatpakSizeEntry` dataclass: name, app_id, size_bytes, runtime
- UI: add section to existing `software_tab.py` — size visualization (bar chart), permission audit list, cleanup button
- CLI: `flatpak sizes`, `flatpak permissions <app>`, `flatpak cleanup` subcommands

### Boot Customization

- New module: `utils/boot_config.py`
- `BootConfigManager` class for GRUB2 configuration
- `get_grub_config() → GrubConfig` — parse `/etc/default/grub`
- `set_timeout(seconds)`, `set_default_kernel(entry)`, `set_theme(theme_path)`
- `list_kernels() → List[KernelEntry]` — parse `grubby --info=ALL`
- `list_themes() → List[str]` — scan `/boot/grub2/themes/`
- `apply_grub_changes()` — run `grub2-mkconfig -o /boot/grub2/grub.cfg` via pkexec
- `GrubConfig` dataclass: timeout, default_entry, theme, cmdline_linux
- `KernelEntry` dataclass: index, title, kernel, initrd, root
- UI: new section in existing `hardware_tab.py` or dedicated `boot_tab.py`
- All mutations via `PrivilegedCommand`

### Wayland Display Config

- New module: `utils/wayland_display.py`
- `WaylandDisplayManager` class
- GNOME: use `gsettings` for `org.gnome.desktop.interface scaling-factor`, `org.gnome.mutter experimental-features`
- KDE: use `kscreen-doctor` for output config
- `get_displays() → List[DisplayInfo]` — connected monitors with resolution, scale, position
- `set_scaling(display, factor)` — integer or fractional scaling
- `set_position(display, x, y)` — multi-monitor layout
- `DisplayInfo` dataclass: name, resolution, scale, position, refresh_rate, primary
- UI: add section to `desktop_tab.py` — display arrangement, scaling slider, fractional toggle
- Wayland-only features gated by `$XDG_SESSION_TYPE == "wayland"` check

### System Backup Wizard

- New module: `utils/backup_wizard.py`
- `BackupWizard` class wrapping Timeshift and Snapper
- `detect_backup_tool() → str` — check for timeshift, snapper, or neither
- `create_snapshot(tool, description) → SnapshotResult`
- `list_snapshots(tool) → List[SnapshotEntry]`
- `restore_snapshot(tool, snapshot_id)` — guided restore with confirmation
- `SnapshotEntry` dataclass: id, date, description, tool, size
- `SnapshotResult` dataclass: success, snapshot_id, message
- UI: new `backup_tab.py` — step-by-step wizard with QStackedWidget pages
- Step 1: detect available tool, Step 2: configure, Step 3: create snapshot, Step 4: verify
- CLI: `backup create`, `backup list`, `backup restore <id>` subcommands

### Plugin Showcase

- Extend existing `utils/plugin_marketplace.py`
- `get_curated_plugins() → List[CuratedPlugin]` — featured community plugins
- `get_plugin_quality(plugin_id) → QualityReport` — ratings, download count, version freshness
- `CuratedPlugin` dataclass: id, name, description, author, rating, downloads, featured
- `QualityReport` dataclass: rating_avg, total_ratings, downloads, last_updated, verified
- UI: add "Featured" section in existing marketplace tab — curated grid with rating badges

### First-Run Wizard v2

- Extend existing `ui/wizard.py`
- Add system health check page: disk space, package manager status, security baseline
- Add recommended actions: update system, enable firewall, configure backups
- Each recommendation is actionable (one-click apply) with risk level badge
- Auto-detect hardware profile and suggest relevant optimizations
- Store wizard completion in `~/.config/loofi-fedora-tweaks/wizard_v2.json`

## Module Map

```
utils/update_manager.py       # Smart update management (check, schedule, rollback)
utils/extension_manager.py    # GNOME/KDE extension management
utils/flatpak_manager.py      # Flatpak size, permissions, cleanup
utils/boot_config.py          # GRUB2 configuration management
utils/wayland_display.py      # Wayland display scaling and layout
utils/backup_wizard.py        # Backup wizard (Timeshift/Snapper)
utils/plugin_marketplace.py   # Extended: curated plugins, quality reports
ui/extensions_tab.py          # Extension browser tab
ui/backup_tab.py              # Backup wizard tab
ui/wizard.py                  # Extended: health check + recommended actions
ui/software_tab.py            # Extended: Flatpak size/permissions sections
ui/hardware_tab.py            # Extended: boot config section (or boot_tab.py)
ui/desktop_tab.py             # Extended: Wayland display config section
cli/main.py                   # New subcommands: update, flatpak, backup, extensions
```

## Layer Rules

- All business logic in `utils/` — tabs and CLI are consumers only
- All subprocess calls via `PrivilegedCommand` with `timeout` parameter
- All privileged actions audit-logged via `utils/audit.py`
- Safe mode checks in all mutation paths
- Risk classification for all new actions in `utils/risk.py`
- Config backup before destructive operations

## Dependencies

- v36.0.0 Horizon (safe mode, risk classification, config backup, API security, perf optimization)
- Existing: `utils/operations.py`, `utils/software_utils.py`, `utils/snapshot_manager.py`
- Existing: `ui/maintenance_tab.py`, `ui/software_tab.py`, `ui/desktop_tab.py`
- System: `gnome-extensions` / `plasmapkg2`, `flatpak`, `grubby`, `grub2-mkconfig`, `gsettings` / `kscreen-doctor`
