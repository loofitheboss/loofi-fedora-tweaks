# Loofi Fedora Tweaks v48.0.0 "Sidebar Index"

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Fedora system management in one place</strong><br>
  GUI + CLI + daemon modes, plugin-based tabs, hardware-aware defaults, Atomic-aware behavior.
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v48.0.0">
    <img src="https://img.shields.io/badge/Release-v48.0.0-blue?style=for-the-badge&logo=github" alt="Release v48.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Package-RPM-orange?style=for-the-badge&logo=redhat" alt="RPM package"/>
  <img src="https://img.shields.io/badge/Coverage-82%25-brightgreen?style=for-the-badge&logo=pytest" alt="Coverage 82%"/>
  <a href="https://copr.fedorainfracloud.org/coprs/loofitheboss/loofi-fedora-tweaks/">
    <img src="https://img.shields.io/badge/COPR-loofitheboss%2Floofi--fedora--tweaks-blue?style=for-the-badge&logo=fedora" alt="COPR"/>
  </a>
</p>

---

## What Is Loofi Fedora Tweaks?

Loofi Fedora Tweaks is a desktop control center for Fedora Linux that combines day-to-day maintenance, diagnostics, tuning, networking, security, and automation in one app.

It is designed to be practical for both casual users and advanced users:

- Plugin-based UI with category-organized tabs and lazy loading.
- CLI mode for scripting and remote administration.
- Daemon mode for background automation.
- Optional headless web API mode.
- Privileged actions routed through `pkexec` prompts.
- Automatic detection of Traditional Fedora (`dnf`) and Atomic Fedora (`rpm-ostree`).

---

## What Is New in v48.0.0?

`v48.0.0 "Sidebar Index"` restructures the sidebar architecture with O(1) ID-based lookups:

- **SidebarEntry Dataclass** — Centralized per-tab state container keyed by `PluginMetadata.id` replacing fragile dict lookups.
- **Decomposed add_page()** — Split into `_find_or_create_category()`, `_create_tab_item()`, and `_register_in_index()` focused helpers.
- **Favorites Fix** — O(1) ID-based matching replaces the broken `name.lower().replace()` heuristic. Stale favorites are logged.
- **Status Dot Rendering** — `SidebarItemDelegate` paints colored dots (green/amber/red) instead of `[OK]`/`[WARN]`/`[ERR]` text markers.
- **O(1) Navigation** — `switch_to_tab()` and `_set_tab_status()` use direct index lookups instead of tree iteration.
- **Experience Level Validation** — Build-time warnings for orphaned or advanced-only tab IDs catch sync drift.

Full notes: [`docs/releases/RELEASE-NOTES-v48.0.0.md`](docs/releases/RELEASE-NOTES-v48.0.0.md)

---

## What Is New in v47.0.0?

`v47.0.0 "Experience"` is a UX-focused release making Loofi accessible to beginners while keeping power for advanced users:

- **Experience Level System** — Beginner/Intermediate/Advanced modes that filter sidebar tabs to reduce overwhelm. Configurable in Settings and during first-run wizard.
- **Guided Tour** — Step-by-step spotlight overlay for first-time users introducing the sidebar, dashboard, command palette, settings, and help.
- **Health Score Drill-Down** — Clickable health gauge on dashboard opens a modal with per-component scores, progress bars, and "Fix it →" navigation buttons.
- **Toast Notifications** — Non-intrusive success/error/info toasts on command completion across all tabs (BaseTab integration).
- **Quick Command Registry** — 10 built-in quick commands (system update, cleanup, etc.) accessible from the command palette with ⚡ prefix.
- **Dashboard Undo Card** — Recent actions card with one-click undo capability powered by HistoryManager.
- **Wizard Enhancements** — 6-step wizard with progress bar, experience level selection, and apply feedback.
- **Settings UX** — Help text in all settings sub-tabs and experience level selector in Behavior tab.

Full notes: [`docs/releases/RELEASE-NOTES-v47.0.0.md`](docs/releases/RELEASE-NOTES-v47.0.0.md)

---

## What Is New in v46.0.0?

`v46.0.0 "Navigator"` is a navigation-clarity release focused on discoverability and taxonomy consistency:

- **Category reorganization** — standardized technical categories across sidebar navigation.
- **Metadata alignment** — tab metadata categories/orders are fully aligned with registry definitions.
- **Command palette consistency** — category labels match sidebar taxonomy.
- **Icon system polish** — semantic icon pack with theme-aware tinting and selection-aware sidebar icon contrast.
- **Release pipeline hardening** — v46 workflow specs and race-lock alignment fixed release gate failures.

Full notes: [`docs/releases/RELEASE-NOTES-v46.0.0.md`](docs/releases/RELEASE-NOTES-v46.0.0.md)

---

## What Is New in v43.0.0?

`v43.0.0 "Stabilization-Only"` is a strict hardening release focused on policy enforcement and regression-proofing:

- **Stabilization policy checker added** — AST gate enforces timeout usage, UI subprocess ban, hardcoded executable `dnf` bans, and explicit broad-exception allowlist boundaries.
- **CI/release hardening gate enabled** — checker now runs in `ci.yml`, `auto-release.yml`, and `coverage-gate.yml`.
- **Coverage gates normalized to 80%** across all workflow files.
- **Wizard health checks extracted to utils** — `ui/wizard.py` no longer runs subprocess directly.
- **Remaining executable hardcoded `dnf` invocations removed** from package/update/health/export stacks.

Full notes: [`docs/releases/RELEASE-NOTES-v43.0.0.md`](docs/releases/RELEASE-NOTES-v43.0.0.md)

---

## What Is New in v41.0.0?

`v41.0.0 "Coverage"` is a pure test and CI release — coverage raised from 74% to 80%+, 23 test files created/expanded.

Full notes: [`docs/releases/RELEASE-NOTES-v41.0.0.md`](docs/releases/RELEASE-NOTES-v41.0.0.md)

---

## What Is New in v40.0.0?

`v40.0.0 "Foundation"` is a security hardening release — subprocess timeout enforcement, shell injection elimination, and privilege escalation cleanup.

Full notes: [`docs/releases/RELEASE-NOTES-v40.0.0.md`](docs/releases/RELEASE-NOTES-v40.0.0.md)

---

## What Is New in v39.0.0?

`v39.0.0 "Prism"` completes the services layer migration — zero deprecated imports, zero inline styles, zero DeprecationWarnings.

Full notes: [`docs/releases/RELEASE-NOTES-v39.0.0.md`](docs/releases/RELEASE-NOTES-v39.0.0.md)

---

## Installation

### Install from COPR (Recommended)

The package is published on [Fedora COPR](https://copr.fedorainfracloud.org/coprs/loofitheboss/loofi-fedora-tweaks/). This gives you automatic updates via `dnf`.

```bash
sudo dnf copr enable loofitheboss/loofi-fedora-tweaks
sudo dnf install loofi-fedora-tweaks
```

To uninstall:

```bash
sudo dnf remove loofi-fedora-tweaks
sudo dnf copr remove loofitheboss/loofi-fedora-tweaks
```

### Install from a Release RPM

Download the `.noarch.rpm` from the [Releases](https://github.com/loofitheboss/loofi-fedora-tweaks/releases) page:

```bash
sudo dnf install ./loofi-fedora-tweaks-*.noarch.rpm
```

### Run from Source

```bash
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py
```

---

## Run Modes

| Mode | Command | Use case |
|------|---------|----------|
| GUI | `loofi-fedora-tweaks` | Daily desktop usage |
| CLI | `loofi-fedora-tweaks --cli <command>` | Scripting and quick actions |
| Daemon | `loofi-fedora-tweaks --daemon` | Background scheduled tasks |
| Web API | `loofi-fedora-tweaks --web` | Headless/remote integration |

Optional shell alias for convenience:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

---

## Icon System

- Semantic icon IDs are used across sidebar categories, tabs, dashboard quick actions, and command surfaces.
- Runtime icon resolution/tinting is handled by `loofi-fedora-tweaks/ui/icon_pack.py`.
- Asset locations (kept mirrored for dev/runtime packaging):
  - `assets/icons/`
  - `loofi-fedora-tweaks/assets/icons/`
- Pack structure:
  - `svg/` source icons
  - `png/16`, `png/20`, `png/24`, `png/32` raster fallbacks
  - `icon-map.json` semantic id map

---

## Built-In Tabs

| Category | Tabs |
|----------|------|
| System | Home, System Info, System Monitor, Community |
| Packages | Software, Maintenance, Snapshots |
| Hardware | Hardware, Performance, Storage, Gaming |
| Network | Network, Loofi Link |
| Security | Security & Privacy, Backup |
| Appearance | Desktop, Profiles, Extensions, Settings |
| Tools | Development, AI Lab, Virtualization |
| Maintenance | Agents, Automation, Diagnostics, Health, Logs, State Teleport |

---

## Screenshots

Current UI screenshots (v46.0.0) are maintained in:

- [`docs/images/user-guide/README.md`](docs/images/user-guide/README.md)

Preview gallery:

![Home Dashboard](docs/images/user-guide/home-dashboard.png)
![System Monitor](docs/images/user-guide/system-monitor.png)
![Maintenance Updates](docs/images/user-guide/maintenance-updates.png)

---

## CLI Quick Examples

All commands below assume either:

- `loofi-fedora-tweaks --cli ...`, or
- alias `loofi='loofi-fedora-tweaks --cli'`

### System and Health

```bash
loofi info
loofi health
loofi doctor
loofi hardware
loofi support-bundle
```

### Maintenance and Tuning

```bash
loofi cleanup all
loofi cleanup journal --days 7
loofi tweak power --profile balanced
loofi tuner analyze
loofi tuner apply
```

### Logs, Services, Packages

```bash
loofi logs errors --since "2h ago"
loofi service list --filter failed
loofi service restart sshd
loofi package search --query firefox --source all
```

### Security, Network, Storage

```bash
loofi security-audit
loofi network dns --provider cloudflare
loofi storage usage
loofi firewall ports
```

### Plugins and Marketplace

```bash
loofi plugins list
loofi plugin-marketplace search --query monitor
loofi plugin-marketplace info cool-plugin
loofi plugin-marketplace install cool-plugin --accept-permissions
loofi plugin-marketplace reviews cool-plugin --limit 10
loofi plugin-marketplace rating cool-plugin
```

### JSON Output for Automation

```bash
loofi --json info
loofi --json health
loofi --json package search --query vim
```

---

## Requirements

- Fedora 43+
- Python 3.12+
- PyQt6
- polkit (`pkexec`)

Optional features may require extra packages (for example: virtualization tools, Ollama, firewalld, avahi).

---

## Documentation

- Beginner quick guide: [`docs/BEGINNER_QUICK_GUIDE.md`](docs/BEGINNER_QUICK_GUIDE.md)
- User guide: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
- Advanced admin guide: [`docs/ADVANCED_ADMIN_GUIDE.md`](docs/ADVANCED_ADMIN_GUIDE.md)
- Troubleshooting: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- Contributing: [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)
- Plugin SDK: [`docs/PLUGIN_SDK.md`](docs/PLUGIN_SDK.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- Documentation index: [`docs/README.md`](docs/README.md)

---

## Development Quick Start

Run tests:

```bash
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v  # 5895 tests collected
```

Lint:

```bash
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203
```

Type check:

```bash
mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary --warn-return-any
```

Security scan:

```bash
bandit -r loofi-fedora-tweaks/ -ll -ii --skip B103,B104,B108,B310,B404,B603,B602
```

Build RPM:

```bash
bash scripts/build_rpm.sh
```

---

## CI/CD Pipeline

Every push to `master` and every pull request runs through two pipelines:

| Pipeline | File | Purpose |
|----------|------|---------|
| CI | `.github/workflows/ci.yml` | Lint, typecheck, test, security, plus required Fedora review gate |
| Auto Release | `.github/workflows/auto-release.yml` | Full release: validate → fedora_review → build → tag → publish |
| COPR Publish | `.github/workflows/copr-publish.yml` | Build SRPM and submit to Fedora COPR |

### Auto Release Flow

```
push to master
  → validate (version alignment, packaging scripts)
  → adapter_drift, lint, typecheck, test, security, docs_gate, fedora_review (parallel)
  → build (RPM in Fedora 43 container)
  → auto_tag (creates vX.Y.Z tag if missing)
  → release (publishes GitHub Release with RPM artifact)
  → copr-publish (builds SRPM and submits to Fedora COPR)
```

`fedora_review` runs `python3 scripts/check_fedora_review.py`, which requires `fedora-review`
and validates lightweight health probes (`fedora-review -V` and `fedora-review -d`).

The pipeline automatically tags and publishes releases when code lands on `master` with a new version in `version.py`. No manual tagging required.

### Manual Release

Use **workflow_dispatch** with the version number for manual control. Set `dry_run: true` to validate without publishing.

---

## License

MIT License.
