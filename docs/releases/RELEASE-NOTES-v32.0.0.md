# Release Notes — v32.0.0 "Abyss"

**Release date:** 2025-07-13

## Overview

v32.0.0 is a full visual redesign of Loofi Fedora Tweaks. The default theme, navigation categories,
sidebar behavior, and inline color palette have all been rebuilt from scratch.

## Highlights

### Loofi Abyss Theme

- New purpose-built dark palette replacing the Catppuccin color scheme.
- Base: `#0b0e14`, sidebar: `#0d1018`, surface: `#1c2030`, accent: `#39c5cf` (teal),
  header: `#b78eff` (purple), success: `#3dd68c`, warning: `#e8b84d`, error: `#e8556d`,
  text: `#e6edf3`.
- Matching light variant: base `#f4f6f9`, accent `#0e8a93`, header `#7c5ec4`.
- Both `modern.qss` (~560 lines) and `light.qss` rewritten from scratch.

### Activity-Based Navigation

Previous 10 categories consolidated into 8 logical groups:

| Category | Emoji | Tabs |
| ---------- | ------- | ------ |
| Overview | 🏠 | Home, System Info, System Monitor |
| Manage | 📦 | Software, Maintenance, Snapshots, Virtualization |
| Hardware | 🔧 | Hardware, Performance, Storage, Gaming |
| Network & Security | 🌐 | Network, Loofi Link, Security & Privacy |
| Personalize | 🎨 | Desktop, Profiles, Settings |
| Developer | 💻 | Development, AI Lab, State Teleport |
| Automation | 🤖 | Agents, Automation |
| Health & Logs | 📊 | Health, Logs, Diagnostics, Community |

- Explicit `CATEGORY_ORDER` dict in `core/plugins/registry.py` ensures deterministic sort.
- Emoji icons prefixed on category headers in sidebar.

### Sidebar Collapse Toggle

- `≡` / `✕` button at the top of the sidebar to collapse/expand.
- Toggles between 0 and 220px width.

### Color Migration

- 17 Catppuccin hex color codes replaced across 30+ source files.
- Notification toasts, health score grades, quick action buttons all updated.
- Dead `assets/style.qss` removed.

## Changed Files

- `loofi-fedora-tweaks/version.py` — 32.0.0 "Abyss"
- `loofi-fedora-tweaks.spec` — Version 32.0.0
- `core/plugins/registry.py` — CATEGORY_ORDER, CATEGORY_ICONS, updated sort
- `ui/main_window.py` — sidebar collapse toggle, category icon prefixes
- `assets/modern.qss` — full rewrite (Abyss dark)
- `assets/light.qss` — full rewrite (Abyss light)
- `assets/style.qss` — deleted
- `ui/notification_toast.py` — expanded category colors, inline color migration
- `utils/health_score.py` — grade colors updated
- `utils/quick_actions_config.py` — action button colors updated
- All 26 tab metadata files — category and order fields updated
- 30+ Python files — batch sed replacement of inline Catppuccin colors

## Compatibility

- Fedora 43+
- Python 3.12+
- PyQt6 6.x
- No new dependencies added
- Fully backward-compatible settings; no migration required

## Known Issues

- `test_clarity_update.py::test_version_codename` — pre-existing hardcoded codename assertion (cosmetic, does not affect functionality)
