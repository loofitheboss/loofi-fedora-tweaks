# Architecture Spec — v31.0.0 "Smart UX"

## Overview

v31.0 adds intelligent UX features: system health scoring, internationalization scaffolding, batch operations, export reports, plugin scaffolding, favorite tabs, configurable quick actions, and accessibility improvements.

## New Modules

### 1. `utils/health_score.py` — HealthScoreManager

Aggregates system metrics into a single 0–100 health score.

**Inputs:**

- CPU load (from `utils/monitor.py`)
- RAM usage (from `utils/monitor.py`)
- Disk usage (from `utils/disk.py`)
- Pending updates count
- System uptime
- Battery health (if applicable)

**Scoring formula:**

```text
score = w_cpu * (100 - cpu_pct) + w_ram * (100 - ram_pct) + w_disk * (100 - disk_pct) + w_uptime * uptime_score + w_updates * update_score
```

Weights: cpu=0.25, ram=0.20, disk=0.20, uptime=0.15, updates=0.20

**Returns:** `HealthScore` dataclass with `score: int`, `grade: str` (A/B/C/D/F), `components: dict`, `recommendations: list[str]`

### 2. `utils/i18n.py` — I18nManager

Manages Qt Linguist translation workflow.

**Design:**

- `get_translator(locale: str) -> QTranslator` — loads `.qm` file from `resources/translations/`
- `available_locales() -> list[str]` — scans translations dir
- `set_locale(app: QApplication, locale: str)` — installs translator
- Default locale from `~/.config/loofi-fedora-tweaks/settings.json`
- Ships with `en` (source) and `sv` (Swedish) `.ts` files

### 3. `utils/batch_ops.py` — BatchOpsManager

Handles batch install/remove operations for Software and Maintenance tabs.

**Design:**

- `batch_install(packages: list[str]) -> Tuple[str, List[str], str]` — returns operation tuple
- `batch_remove(packages: list[str]) -> Tuple[str, List[str], str]`
- `batch_update() -> Tuple[str, List[str], str]`
- Uses `PrivilegedCommand.dnf()` internally, respects Atomic branching

### 4. `utils/report_exporter.py` — ReportExporter

Exports system information as Markdown or HTML.

**Design:**

- `export_markdown(info: dict) -> str` — returns formatted Markdown string
- `export_html(info: dict) -> str` — wraps Markdown in styled HTML template
- `save_report(path: str, format: str, info: dict)` — writes to file
- `gather_system_info() -> dict` — collects all system info for export

### 5. `utils/favorites.py` — FavoritesManager

Persists favorite/pinned tabs.

**Design:**

- `get_favorites() -> list[str]` — returns list of tab IDs
- `add_favorite(tab_id: str)` — adds to favorites
- `remove_favorite(tab_id: str)` — removes from favorites
- `is_favorite(tab_id: str) -> bool`
- Storage: `~/.config/loofi-fedora-tweaks/favorites.json`

### 6. `utils/quick_actions_config.py` — QuickActionsConfig

Configurable quick actions grid on Dashboard.

**Design:**

- `get_actions() -> list[dict]` — returns configured actions
- `set_actions(actions: list[dict])` — saves configured actions
- `default_actions() -> list[dict]` — returns default 4 actions
- Each action: `{"id": str, "label": str, "icon": str, "color": str, "target_tab": str}`
- Storage: `~/.config/loofi-fedora-tweaks/quick_actions.json`

## UI Changes

### Dashboard Tab

- Add `HealthScoreWidget` card between header and live metrics
- Widget shows circular gauge with score number, grade letter, and color
- Quick actions grid reads from `QuickActionsConfig` instead of hardcoded buttons
- Add "Configure" button to quick actions section

### System Info Tab

- Add "Export Report" button (Markdown/HTML dropdown)
- Uses `ReportExporter` to generate and save

### Software Tab

- Add batch selection checkboxes to package list
- Add "Install Selected" / "Remove Selected" buttons
- Uses `BatchOpsManager`

### Sidebar (MainWindow)

- Add star/pin icon next to favorite tabs
- Favorites section at top of sidebar (pinned items)
- Right-click context menu: "Add to Favorites" / "Remove from Favorites"

## Scripts

### `scripts/create_plugin.sh`

Scaffold a new plugin directory with:

- `plugin.py` (extends `LoofiPlugin`)
- `metadata.json`
- `README.md`
- `tests/test_plugin.py`

## Accessibility

- `setAccessibleName()` on all QPushButton, QLineEdit, QComboBox, QCheckBox
- `setAccessibleDescription()` on complex widgets
- Tab order verification across all tabs

## i18n File Structure

```text
loofi-fedora-tweaks/resources/translations/
├── en.ts        (source strings)
├── sv.ts        (Swedish translation)
└── README.md    (how to add new locales)
```

## Dependencies

- v30.0 distribution infrastructure (baseline)
- No new external dependencies
