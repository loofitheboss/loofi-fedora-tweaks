## Loofi Fedora Tweaks v25.0.1

Hotfix release for the v25 plugin architecture rollout.

### Fixed

- Restored tab/plugin startup on newer PyQt6 environments.
  - Removed `ABC` metaclass coupling from `PluginInterface` to avoid `QWidget` metaclass conflicts.
  - Removed `pyqtWrapperType` dependency from `BaseTab` for broader PyQt6 compatibility.
- Reduced startup log noise in constrained/sandboxed environments.
  - Expected DBus access failures now log as info-level fallback, not warnings.

### Impact

- Sidebar and content tabs load correctly again (`26` built-in tabs).
- App still falls back to polling mode when DBus is unavailable, with cleaner logs.
- No functional changes to tab behavior beyond startup compatibility and logging clarity.

### Technical Notes

Files changed:
- `loofi-fedora-tweaks/core/plugins/interface.py`
- `loofi-fedora-tweaks/ui/base_tab.py`
- `loofi-fedora-tweaks/utils/pulse.py`
- `loofi-fedora-tweaks/version.py`
- `CHANGELOG.md`

Tag: `v25.0.1`
