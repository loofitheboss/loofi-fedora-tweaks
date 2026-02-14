# Release Notes — v37.0.0 "Pinnacle"

**Release date**: 2025-07-21
**Codename**: Pinnacle
**Type**: Feature expansion

---

## Highlights

v37.0.0 "Pinnacle" is a feature expansion release that adds smart update management, desktop extension handling, Flatpak audit tools, boot configuration, Wayland display settings, and a backup wizard — all accessible from both GUI and CLI.

---

## New Backend Modules (7)

| Module | Description |
|--------|-------------|
| `utils/update_manager.py` | Smart update checking, conflict preview, scheduling (systemd timer), rollback, history |
| `utils/extension_manager.py` | GNOME/KDE extension management — list, install, enable, disable, remove |
| `utils/flatpak_manager.py` | Flatpak size audit, permissions inspection, orphan runtime detection, bulk cleanup |
| `utils/boot_config.py` | GRUB config viewer/editor, kernel listing, timeout setting, grub2-mkconfig apply |
| `utils/wayland_display.py` | Wayland session info, display enumeration, fractional scaling toggle |
| `utils/backup_wizard.py` | Auto-detect Timeshift/Snapper/restic, create/list/restore/delete snapshots |
| `utils/risk.py` | RiskLevel enum, RiskEntry dataclass, RiskRegistry singleton with revert instructions |

---

## New UI Tabs (2)

- **Extensions Tab** — Search bar, status filter, extensions table with enable/disable/install/remove buttons. Uses `ExtensionManager` backend.
- **Backup Tab** — 3-page stacked wizard: detect backup tools → configure → manage snapshots. Uses `BackupWizard` backend.

---

## Extended Existing Tabs (5)

| Tab | Addition |
|-----|----------|
| Maintenance | Smart Updates sub-tab — check updates, preview conflicts, schedule, rollback |
| Software | Flatpak Manager sub-tab — size audit, orphan detection, permission inspection, cleanup |
| Hardware | Boot Configuration card — kernel list, GRUB config viewer, timeout editor |
| Desktop | Display sub-tab — session info, display list, fractional scaling toggle |
| Community | Featured Plugins sub-tab — curated plugin directory with ratings and downloads |

---

## First-Run Wizard v2

Upgraded from 3-step to 5-step:

1. Welcome (existing)
2. Profile selection (existing)
3. Theme selection (existing)
4. **System Health Check** (NEW) — disk space, package state, firewall, backup tool, SELinux
5. **Recommended Actions** (NEW) — risk-badged actions with opt-in checkboxes

Uses v2 sentinel file (`wizard_v2.json`) so existing users get the new wizard on next launch.

---

## New CLI Commands (6)

```bash
loofi updates check|conflicts|schedule|rollback|history
loofi extension list|install|remove|enable|disable
loofi flatpak-manage sizes|permissions|orphans|cleanup
loofi boot config|kernels|timeout|apply
loofi display list|session|fractional-on|fractional-off
loofi backup detect|create|list|restore|delete|status
```

All commands support `--json` and `--dry-run` flags.

---

## Risk Registry

Centralized risk assessment for all privileged actions:

- `RiskLevel.LOW` — read-only or easily reversible (display scaling, snapshot create, flatpak cleanup)
- `RiskLevel.MEDIUM` — state-modifying but recoverable (extension install, snapshot delete)
- `RiskLevel.HIGH` — potentially destructive (update rollback, GRUB apply, snapshot restore)

Each entry includes action ID, description, risk level, and optional revert instructions.

---

## Plugin Marketplace Extensions

Added curated plugin support to `PluginMarketplace`:

- `CuratedPlugin` dataclass (name, author, description, rating, downloads, url)
- `QualityReport` dataclass (rating, last_updated, download_count, has_tests, has_docs)
- `get_curated_plugins()` and `get_plugin_quality()` methods

---

## Test Suite

- **76 new tests** across 9 files
- All v37 backend modules fully tested with mocked system calls
- UI source-level tests validate tab structure and widget presence
- CLI handler tests verify all 6 new subcommands

---

## Files Changed

### New Files (14)
- `utils/update_manager.py`
- `utils/extension_manager.py`
- `utils/flatpak_manager.py`
- `utils/boot_config.py`
- `utils/wayland_display.py`
- `utils/backup_wizard.py`
- `utils/risk.py`
- `ui/extensions_tab.py`
- `ui/backup_tab.py`
- `tests/test_update_manager.py`
- `tests/test_extension_manager.py`
- `tests/test_flatpak_manager.py`
- `tests/test_boot_config.py`
- `tests/test_wayland_display.py`
- `tests/test_backup_wizard.py`
- `tests/test_risk.py`
- `tests/test_extensions_tab.py`
- `tests/test_cli_v37.py`

### Modified Files (8)
- `utils/plugin_marketplace.py` — Added CuratedPlugin, QualityReport
- `ui/maintenance_tab.py` — Added Smart Updates sub-tab
- `ui/software_tab.py` — Added Flatpak Manager sub-tab
- `ui/hardware_tab.py` — Added Boot Configuration card
- `ui/desktop_tab.py` — Added Display sub-tab
- `ui/community_tab.py` — Added Featured Plugins sub-tab
- `ui/wizard.py` — Upgraded to 5-step wizard v2
- `cli/main.py` — Added 6 new subcommands + subparsers
- `core/plugins/loader.py` — Registered ExtensionsTab and BackupTab

---

## Upgrade Notes

- Tab count increased from 26 to 28
- First-run wizard v2 will re-trigger for users who completed v1
- No breaking changes to existing CLI commands or APIs
- All new CLI commands follow existing patterns (`--json`, `--dry-run`)
