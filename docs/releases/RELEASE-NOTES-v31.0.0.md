# Release Notes — v31.0.0 "Smart UX"

**Release Date:** 2026-02-13

## Highlights

v31.0 focuses on **user experience intelligence** — making the app smarter about what matters and faster to use day-to-day.

### System Health Score

A new dashboard widget aggregates CPU, RAM, disk, uptime, and pending updates into a single 0–100 score with a letter grade (A–F). Actionable recommendations appear automatically when issues are detected.

### Batch Operations

The Software tab now supports selecting multiple packages with checkboxes and installing/removing them in one operation. Works on both traditional Fedora (dnf) and Atomic (rpm-ostree).

### System Report Export

Export your full system information as a Markdown or HTML report from the System Info tab. HTML reports use Catppuccin-themed styling for a polished look.

### Favorite Tabs

Right-click any sidebar item to pin it as a favorite. Pinned tabs appear in a ⭐ Favorites category at the top of the sidebar for quick access.

### Configurable Quick Actions

Dashboard quick action buttons are now configurable and persist across sessions. Default actions: Clean Cache, Update All, Power Profile, Gaming Mode.

### i18n Scaffolding

Translation infrastructure is in place using Qt Linguist. English and Swedish locale stubs are included. Community translations can be contributed via `.ts` files.

### Plugin Template Script

New `scripts/create_plugin.sh` scaffolds a complete plugin directory with metadata, implementation stub, README, and test file.

### Accessibility Level 2

Screen reader support expanded with `setAccessibleName` / `setAccessibleDescription` on sidebar navigation, dashboard controls, and batch operation buttons.

## New Files

| File | Purpose |
| --- | --- |
| `utils/health_score.py` | Health score calculation engine |
| `utils/i18n.py` | i18n manager with Qt Linguist workflow |
| `utils/batch_ops.py` | Batch install/remove/update operations |
| `utils/report_exporter.py` | Markdown/HTML system report export |
| `utils/favorites.py` | Favorite tab persistence |
| `utils/quick_actions_config.py` | Configurable quick actions |
| `scripts/create_plugin.sh` | Plugin scaffolding script |
| `tests/test_health_score.py` | Health score tests (30) |
| `tests/test_i18n.py` | i18n tests (12) |
| `tests/test_batch_ops.py` | Batch ops tests (14) |
| `tests/test_report_exporter.py` | Report exporter tests (10) |
| `tests/test_favorites.py` | Favorites tests (14) |
| `tests/test_quick_actions_config.py` | Quick actions config tests (15) |

## Modified Files

| File | Change |
| --- | --- |
| `ui/dashboard_tab.py` | Health score widget + configurable quick actions |
| `ui/system_info_tab.py` | Export report button + format selector |
| `ui/software_tab.py` | Batch checkboxes + install/remove toolbar |
| `ui/main_window.py` | Favorites sidebar + context menu + a11y |
| `version.py` | 31.0.0 "Smart UX" |
| `loofi-fedora-tweaks.spec` | Version 31.0.0 |

## Testing

- **95 new tests** across 6 test files
- **0 failures**
- All system calls properly mocked
- Lint clean (flake8)

## Upgrade Notes

- No breaking changes from v30.0.
- Favorites config stored at `~/.config/loofi-fedora-tweaks/favorites.json`
- Quick actions config stored at `~/.config/loofi-fedora-tweaks/quick_actions.json`
- Both files are created on first use with sensible defaults
