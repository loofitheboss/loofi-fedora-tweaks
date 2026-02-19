# Productivity Skills

## Focus Mode

- **Domain blocking** — Block distracting websites via /etc/hosts
- **Process killing** — Automatically close distracting applications
- **Do Not Disturb** — Suppress desktop notifications
- **Timer** — Set focus sessions with automatic deactivation

**Modules:** `utils/focus_mode.py`
**UI:** Desktop Tab
**CLI:** `focus-mode`

## System Profiles

- **Quick-switch profiles** — Gaming, Development, Battery Saver, Server, Presentation
- **Custom profiles** — Create and save custom system configurations
- **Profile import/export** — Share profiles between machines
- **Auto-activation** — Activate profiles based on conditions (power state, time)

**Modules:** `utils/profiles.py`, `core/profiles/`
**UI:** Profiles Tab
**CLI:** `profile`

## System Presets

- **Preset management** — Apply curated system configuration bundles
- **Preset listing** — Browse available presets with descriptions
- **Custom presets** — Create presets from current system state

**Modules:** `utils/presets.py`
**CLI:** `preset`

## State Teleport

- **Workspace capture** — Snapshot current workspace state (open apps, windows, files)
- **State restore** — Recreate workspace from a saved teleport
- **Cross-device transfer** — Move workspace state between devices

**Modules:** `utils/state_teleport.py`
**UI:** Teleport Tab
**CLI:** `teleport`

## Quick Actions & Favorites

- **Quick actions** — Customizable shortcut buttons for frequent operations
- **Favorites** — Pin favorite tools and operations for quick access
- **Command palette** — Ctrl+K keyboard shortcut for instant command search

**Modules:** `utils/quick_actions_config.py`, `utils/favorites.py`, `ui/command_palette.py`
**UI:** Dashboard Tab

## Cloud Sync

- **Configuration sync** — Synchronize settings across devices via cloud storage
- **Selective sync** — Choose which settings to synchronize
- **Conflict resolution** — Handle sync conflicts gracefully

**Modules:** `utils/cloud_sync.py`
**UI:** Settings Tab
