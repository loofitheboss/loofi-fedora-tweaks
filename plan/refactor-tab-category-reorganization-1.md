---
goal: Reorganize tab categories for intuitive navigation, fix category inconsistencies, and improve discoverability
version: 1.0
date_created: 2026-02-17
last_updated: 2026-02-17
owner: Loofi Fedora Tweaks
status: 'Planned'
tags: [refactor, ux, navigation, categories, sidebar]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Restructure the 28-tab sidebar navigation from the current 8 vague categories into clear, technically-named groups that match how users think about system management. Fix orphan categories ("System", "Maintain"), resolve overlapping groupings, and ensure every tab lives in the most logical home. This is a metadata-only refactor — no tab functionality changes, only `_METADATA` category/order/icon/badge fields and the `CATEGORY_ORDER`/`CATEGORY_ICONS` definitions.

## 1. Requirements & Constraints

- **REQ-001**: All 28 tabs must remain functional — no code logic changes, only metadata fields
- **REQ-002**: New categories must use technical, clear naming (not cute/beginner-oriented)
- **REQ-003**: Every tab's `_METADATA.category` must match a key in `CATEGORY_ORDER` (fix orphans)
- **REQ-004**: Category count should stay between 7–9 for sidebar usability
- **REQ-005**: Sidebar search, command palette, favorites, and breadcrumbs must work unchanged
- **REQ-006**: Lazy loading, plugin registration, and `_build_sidebar_from_registry()` must not break
- **SEC-001**: No privilege escalation or subprocess changes — this is a pure UI metadata refactor
- **CON-001**: `core/plugins/registry.py` defines `CATEGORY_ORDER` and `CATEGORY_ICONS` — single source of truth
- **CON-002**: Each tab's `_METADATA` in its `*_tab.py` file is the only place category is assigned
- **CON-003**: Badge values must remain one of: `""`, `"recommended"`, `"advanced"`, `"new"`
- **GUD-001**: Categories should map to mental models: "What kind of thing am I doing?" not "What subsystem?"
- **GUD-002**: Each category should have 2–5 tabs (avoid 1-tab categories or 8-tab dumps)
- **GUD-003**: Emoji icons should be visually distinct and semantically match the category
- **PAT-001**: Follow existing `PluginMetadata` dataclass pattern — frozen, no new fields needed
- **PAT-002**: Maintain `order` field ascending within each category (10, 20, 30...)

## 2. Implementation Steps

### Implementation Phase 1: Define New Category Structure

- GOAL-001: Replace the 8 current categories (+ 2 orphan categories) with a clean, technically-named 8-category structure in `registry.py`

**Proposed Category Restructure:**

| Priority | Old Category | New Category | Icon | Rationale |
|----------|-------------|--------------|------|-----------|
| 0 | Overview | System | 🖥️ | "System" is clearer than "Overview" — this is the system dashboard area |
| 1 | Manage | Packages | 📦 | Rename to match what users actually manage here: software packages |
| 2 | Hardware | Hardware | ⚡ | Keep name, but remove non-hardware tabs (Monitor → System, Gaming → Packages) |
| 3 | Network & Security | Network | 🌐 | Split: network stays here, security gets its own category |
| 4 | _(new)_ | Security | 🛡️ | Promote from sub-category: security/privacy deserves top-level visibility |
| 5 | Personalize | Appearance | 🎨 | "Appearance" is more precise — this is theming, extensions, desktop config |
| 6 | Developer | Tools | 🛠️ | "Tools" is broader and less intimidating — includes dev, AI, virtualization |
| 7 | Automation + Health & Logs | Maintenance | 📋 | Merge automation/health/logs — all about keeping the system running well |

**Proposed Tab Assignments (28 tabs):**

| Tab | Current Category | New Category | New Order | Badge | Reasoning |
|-----|-----------------|--------------|-----------|-------|-----------|
| Dashboard | Overview | System | 10 | recommended | System overview belongs in System |
| System Info | Overview | System | 20 | recommended | Core system information |
| Monitor | Hardware→Overview | System | 30 | | Real-time system monitoring, not hardware-specific |
| Community | Community (orphan!) | System | 40 | | Community hub fits as system-level entry point |
| Software | Manage | Packages | 10 | recommended | Package installation/removal |
| Maintenance | Manage | Packages | 20 | recommended | Updates, cache cleanup = package maintenance |
| Snapshots | Manage | Packages | 30 | advanced | System snapshots tied to package state |
| Storage | Manage | Hardware | 30 | | Disk/filesystem = hardware |
| Hardware | Hardware | Hardware | 10 | recommended | CPU, GPU, fans, battery |
| Performance | Hardware | Hardware | 20 | advanced | Auto-tuner = hardware optimization |
| Gaming | Hardware | Hardware | 40 | | GPU drivers, performance = hardware tuning |
| Network | Network & Security | Network | 10 | | Network config and monitoring |
| Mesh (Loofi Link) | Network & Security | Network | 20 | advanced | Mesh networking |
| Security & Privacy | Network & Security | Security | 10 | recommended | Security hardening, firewall |
| Backup | Maintain (orphan!) | Security | 20 | new | Backups = data protection = security domain |
| Desktop | Personalize | Appearance | 10 | | Window manager, compositor, tiling |
| Extensions | Personalize | Appearance | 20 | new | GNOME/KDE extensions |
| Profiles | Personalize | Appearance | 30 | | Configuration profiles |
| Settings | Personalize | Appearance | 100 | | App settings (stays last) |
| Development | Developer | Tools | 10 | | Containers, dev tools |
| Virtualization | Developer | Tools | 20 | advanced | VMs, GPU passthrough |
| AI Lab | Developer | Tools | 30 | advanced | AI models, voice, knowledge |
| Health Timeline | Health & Logs | Maintenance | 10 | | System health tracking |
| Logs | Health & Logs | Maintenance | 20 | advanced | Log viewer |
| Diagnostics | System (orphan!) | Maintenance | 30 | advanced | Troubleshooting tools |
| Agents | Automation | Maintenance | 40 | | Autonomous monitoring agents |
| Automation | Automation | Maintenance | 50 | | Scheduled tasks, replication |
| Teleport | Automation | Maintenance | 60 | advanced | Workspace state capture/restore |

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Update `CATEGORY_ORDER` dict in `core/plugins/registry.py` — replace 8 old keys with 8 new keys: System(0), Packages(1), Hardware(2), Network(3), Security(4), Appearance(5), Tools(6), Maintenance(7) | | |
| TASK-002 | Update `CATEGORY_ICONS` dict in `core/plugins/registry.py` — map new category names to emoji icons: System→🖥️, Packages→📦, Hardware→⚡, Network→🌐, Security→🛡️, Appearance→🎨, Tools→🛠️, Maintenance→📋 | | |
| TASK-003 | Verify `main_window.py` uses `CATEGORY_ORDER` and `CATEGORY_ICONS` dynamically (no hardcoded category strings) — confirm no code changes needed there | | |

### Implementation Phase 2: Update Tab Metadata — System & Packages Categories

- GOAL-002: Update `_METADATA` in each tab file for the System and Packages category tabs (7 tabs total)

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | `ui/dashboard_tab.py` — change `_METADATA.category` from `"Overview"` to `"System"`, keep order=10, icon=🏠 | | |
| TASK-005 | `ui/system_info_tab.py` — change `_METADATA.category` from `"Overview"` to `"System"`, keep order=20 | | |
| TASK-006 | `ui/monitor_tab.py` — change `_METADATA.category` from `"Hardware"` to `"System"`, set order=30 | | |
| TASK-007 | `ui/community_tab.py` — change `_METADATA.category` from `"Community"` to `"System"`, set order=40 | | |
| TASK-008 | `ui/software_tab.py` — change `_METADATA.category` from `"Manage"` to `"Packages"`, keep order=10 | | |
| TASK-009 | `ui/maintenance_tab.py` — change `_METADATA.category` from `"Manage"` to `"Packages"`, keep order=20 | | |
| TASK-010 | `ui/snapshot_tab.py` — change `_METADATA.category` from `"Manage"` to `"Packages"`, keep order=30 | | |

### Implementation Phase 3: Update Tab Metadata — Hardware & Network & Security Categories

- GOAL-003: Update `_METADATA` for Hardware, Network, and Security category tabs (7 tabs total)

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-011 | `ui/hardware_tab.py` — keep `_METADATA.category` as `"Hardware"`, keep order=10 | | |
| TASK-012 | `ui/performance_tab.py` — keep `_METADATA.category` as `"Hardware"`, keep order=20 | | |
| TASK-013 | `ui/storage_tab.py` — change `_METADATA.category` from `"Manage"` to `"Hardware"`, set order=30 | | |
| TASK-014 | `ui/gaming_tab.py` — keep `_METADATA.category` as `"Hardware"`, set order=40 | | |
| TASK-015 | `ui/network_tab.py` — change `_METADATA.category` from `"Network & Security"` to `"Network"`, keep order=10 | | |
| TASK-016 | `ui/mesh_tab.py` — change `_METADATA.category` from `"Network & Security"` to `"Network"`, set order=20 | | |
| TASK-017 | `ui/security_tab.py` — change `_METADATA.category` from `"Network & Security"` to `"Security"`, set order=10 | | |
| TASK-018 | `ui/backup_tab.py` — change `_METADATA.category` from `"Maintain"` to `"Security"`, set order=20 | | |

### Implementation Phase 4: Update Tab Metadata — Appearance, Tools & Maintenance Categories

- GOAL-004: Update `_METADATA` for Appearance, Tools, and Maintenance category tabs (14 tabs total)

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | `ui/desktop_tab.py` — change `_METADATA.category` from `"Personalize"` to `"Appearance"`, keep order=10 | | |
| TASK-020 | `ui/extensions_tab.py` — change `_METADATA.category` from `"Personalize"` to `"Appearance"`, set order=20 | | |
| TASK-021 | `ui/profiles_tab.py` — change `_METADATA.category` from `"Personalize"` to `"Appearance"`, set order=30 | | |
| TASK-022 | `ui/settings_tab.py` — change `_METADATA.category` from `"Personalize"` to `"Appearance"`, keep order=100 | | |
| TASK-023 | `ui/development_tab.py` — change `_METADATA.category` from `"Developer"` to `"Tools"`, keep order=10 | | |
| TASK-024 | `ui/virtualization_tab.py` — change `_METADATA.category` from `"Developer"` to `"Tools"`, keep order=20 | | |
| TASK-025 | `ui/ai_enhanced_tab.py` — change `_METADATA.category` from `"Developer"` to `"Tools"`, keep order=30 | | |
| TASK-026 | `ui/health_timeline_tab.py` — change `_METADATA.category` from `"Health & Logs"` to `"Maintenance"`, set order=10 | | |
| TASK-027 | `ui/logs_tab.py` — change `_METADATA.category` from `"Health & Logs"` to `"Maintenance"`, set order=20 | | |
| TASK-028 | `ui/diagnostics_tab.py` — change `_METADATA.category` from `"System"` to `"Maintenance"`, set order=30 | | |
| TASK-029 | `ui/agents_tab.py` — change `_METADATA.category` from `"Automation"` to `"Maintenance"`, set order=40 | | |
| TASK-030 | `ui/automation_tab.py` — change `_METADATA.category` from `"Automation"` to `"Maintenance"`, set order=50 | | |
| TASK-031 | `ui/teleport_tab.py` — change `_METADATA.category` from `"Automation"` to `"Maintenance"`, set order=60 | | |

### Implementation Phase 5: Update Command Palette & Tests

- GOAL-005: Ensure command palette categories match new structure and all tests pass

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-032 | Audit `ui/command_palette.py` for any hardcoded category names — update if found to match new names | | |
| TASK-033 | Search for hardcoded old category strings across entire codebase (`grep -r "Overview\|Manage\|Personalize\|Developer\|Automation\|Health & Logs\|Network & Security"`) and update any references | | |
| TASK-034 | Run full test suite: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short` — fix any category-related test failures | | |
| TASK-035 | Run lint: `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203` — ensure no regressions | | |

### Implementation Phase 6: Documentation & Polish

- GOAL-006: Update documentation to reflect new category structure

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-036 | Update `ARCHITECTURE.md` — replace old category table with new 8-category structure (System, Packages, Hardware, Network, Security, Appearance, Tools, Maintenance) | | |
| TASK-037 | Update `wiki/GUI-Tabs-Reference.md` — reorganize tab listing by new categories | | |
| TASK-038 | Update `CHANGELOG.md` — add entry for category reorganization under current version | | |
| TASK-039 | Verify sidebar renders correctly: all 8 categories visible, correct emoji icons, tabs sorted by order within each category, no orphan tabs | | |

## 3. Alternatives

- **ALT-001**: Keep current 8 categories but just fix the 3 orphans (Diagnostics→"System", Backup→"Manage", Community→"Overview"). Rejected: misses the opportunity to fix the vague naming and overlapping groups.
- **ALT-002**: Reduce to 5 mega-categories (System, Apps, Security, Customize, Tools). Rejected: too few categories makes each one a dumping ground of 5–8 tabs.
- **ALT-003**: Expand to 10+ categories with fine granularity (separate Monitoring, Automation, AI, Gaming). Rejected: too many sidebar groups creates visual noise and decision fatigue.
- **ALT-004**: Use activity-based naming ("Monitor", "Configure", "Protect"). Rejected: user preferred technical naming style.

## 4. Dependencies

- **DEP-001**: `core/plugins/registry.py` — `CATEGORY_ORDER` and `CATEGORY_ICONS` dictionaries (must be updated first)
- **DEP-002**: `core/plugins/metadata.py` — `PluginMetadata.category` field (no changes needed, just consumes strings)
- **DEP-003**: `ui/main_window.py` — `_build_sidebar_from_registry()`, `add_page()`, `_update_breadcrumb()` (should work unchanged if dynamic)
- **DEP-004**: `ui/command_palette.py` — may contain hardcoded category references
- **DEP-005**: 28 `ui/*_tab.py` files — each contains `_METADATA` with `category` field to update

## 5. Files

- **FILE-001**: `loofi-fedora-tweaks/core/plugins/registry.py` — Update `CATEGORY_ORDER` and `CATEGORY_ICONS`
- **FILE-002**: `loofi-fedora-tweaks/ui/dashboard_tab.py` — category: "Overview" → "System"
- **FILE-003**: `loofi-fedora-tweaks/ui/system_info_tab.py` — category: "Overview" → "System"
- **FILE-004**: `loofi-fedora-tweaks/ui/monitor_tab.py` — category: "Hardware" → "System"
- **FILE-005**: `loofi-fedora-tweaks/ui/community_tab.py` — category: "Community" → "System"
- **FILE-006**: `loofi-fedora-tweaks/ui/software_tab.py` — category: "Manage" → "Packages"
- **FILE-007**: `loofi-fedora-tweaks/ui/maintenance_tab.py` — category: "Manage" → "Packages"
- **FILE-008**: `loofi-fedora-tweaks/ui/snapshot_tab.py` — category: "Manage" → "Packages"
- **FILE-009**: `loofi-fedora-tweaks/ui/storage_tab.py` — category: "Manage" → "Hardware"
- **FILE-010**: `loofi-fedora-tweaks/ui/hardware_tab.py` — no change (stays Hardware)
- **FILE-011**: `loofi-fedora-tweaks/ui/performance_tab.py` — no change (stays Hardware)
- **FILE-012**: `loofi-fedora-tweaks/ui/gaming_tab.py` — no change (stays Hardware, order update only)
- **FILE-013**: `loofi-fedora-tweaks/ui/network_tab.py` — category: "Network & Security" → "Network"
- **FILE-014**: `loofi-fedora-tweaks/ui/mesh_tab.py` — category: "Network & Security" → "Network"
- **FILE-015**: `loofi-fedora-tweaks/ui/security_tab.py` — category: "Network & Security" → "Security"
- **FILE-016**: `loofi-fedora-tweaks/ui/backup_tab.py` — category: "Maintain" → "Security"
- **FILE-017**: `loofi-fedora-tweaks/ui/desktop_tab.py` — category: "Personalize" → "Appearance"
- **FILE-018**: `loofi-fedora-tweaks/ui/extensions_tab.py` — category: "Personalize" → "Appearance"
- **FILE-019**: `loofi-fedora-tweaks/ui/profiles_tab.py` — category: "Personalize" → "Appearance"
- **FILE-020**: `loofi-fedora-tweaks/ui/settings_tab.py` — category: "Personalize" → "Appearance"
- **FILE-021**: `loofi-fedora-tweaks/ui/development_tab.py` — category: "Developer" → "Tools"
- **FILE-022**: `loofi-fedora-tweaks/ui/virtualization_tab.py` — category: "Developer" → "Tools"
- **FILE-023**: `loofi-fedora-tweaks/ui/ai_enhanced_tab.py` — category: "Developer" → "Tools"
- **FILE-024**: `loofi-fedora-tweaks/ui/health_timeline_tab.py` — category: "Health & Logs" → "Maintenance"
- **FILE-025**: `loofi-fedora-tweaks/ui/logs_tab.py` — category: "Health & Logs" → "Maintenance"
- **FILE-026**: `loofi-fedora-tweaks/ui/diagnostics_tab.py` — category: "System" → "Maintenance"
- **FILE-027**: `loofi-fedora-tweaks/ui/agents_tab.py` — category: "Automation" → "Maintenance"
- **FILE-028**: `loofi-fedora-tweaks/ui/automation_tab.py` — category: "Automation" → "Maintenance"
- **FILE-029**: `loofi-fedora-tweaks/ui/teleport_tab.py` — category: "Automation" → "Maintenance"
- **FILE-030**: `loofi-fedora-tweaks/ui/command_palette.py` — audit for hardcoded category strings
- **FILE-031**: `ARCHITECTURE.md` — update category table
- **FILE-032**: `wiki/GUI-Tabs-Reference.md` — reorganize by new categories
- **FILE-033**: `CHANGELOG.md` — add reorganization entry

## 6. Testing

- **TEST-001**: Run full test suite (`pytest tests/ -v`) — all 4349+ tests must pass (no tab functionality changed)
- **TEST-002**: Verify each of the 8 new categories appears in the sidebar with correct emoji icon
- **TEST-003**: Verify no empty categories exist (each has ≥2 tabs)
- **TEST-004**: Verify no orphan tabs (every `_METADATA.category` matches a `CATEGORY_ORDER` key)
- **TEST-005**: Verify sidebar search still filters tabs correctly across new categories
- **TEST-006**: Verify command palette returns results grouped by new category names
- **TEST-007**: Verify breadcrumb shows `New Category › Tab Name` format correctly
- **TEST-008**: Verify favorites still work (pinned tabs survive category rename)
- **TEST-009**: Run `grep -rn` to confirm zero remaining references to old category names in source code
- **TEST-010**: Run flake8 lint — no new warnings

## 7. Risks & Assumptions

- **RISK-001**: Tests may assert specific category strings (e.g., `assertEqual(meta.category, "Overview")`). Mitigation: TASK-034 includes test fixup.
- **RISK-002**: Command palette may have hardcoded category mappings. Mitigation: TASK-032 audits this explicitly.
- **RISK-003**: User muscle memory — users accustomed to old category names may be briefly confused. Mitigation: category reorganization is clearly communicated in CHANGELOG.
- **RISK-004**: Third-party or community plugins referencing old category names. Mitigation: `CATEGORY_ORDER` acts as fallback — unknown categories sort to end, not crash.
- **ASSUMPTION-001**: `main_window.py` uses `CATEGORY_ORDER`/`CATEGORY_ICONS` dynamically (confirmed via code exploration)
- **ASSUMPTION-002**: No tab functionality depends on its category string at runtime (category is display-only metadata)
- **ASSUMPTION-003**: The `order` field is only used for intra-category sorting (confirmed — cross-category order comes from `CATEGORY_ORDER` priority)

## 8. Related Specifications / Further Reading

- `ARCHITECTURE.md` — Current tab layout and layer rules
- `ROADMAP.md` — Version scope and planned work
- `core/plugins/registry.py` — Category definitions (source of truth)
- `core/plugins/metadata.py` — PluginMetadata dataclass
- `.github/instructions/system_hardening_and_stabilization_guide.md` — Stabilization rules (this refactor is safe under Phase 1-2)
