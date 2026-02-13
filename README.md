# Loofi Fedora Tweaks v32.0.0 "Abyss"

<p align="center">
  <img src="loofi-fedora-tweaks/assets/loofi-fedora-tweaks.png" alt="Loofi Fedora Tweaks Logo" width="128"/>
</p>

<p align="center">
  <strong>Fedora system management in one place</strong><br>
  GUI + CLI + daemon modes, plugin-based tabs, hardware-aware defaults, Atomic-aware behavior.
</p>

<p align="center">
  <a href="https://github.com/loofitheboss/loofi-fedora-tweaks/releases/tag/v32.0.0">
    <img src="https://img.shields.io/badge/Release-v32.0.0-blue?style=for-the-badge&logo=github" alt="Release v32.0.0"/>
  </a>
  <img src="https://img.shields.io/badge/Fedora-43-blue?style=for-the-badge&logo=fedora" alt="Fedora 43"/>
  <img src="https://img.shields.io/badge/Python-3.12+-green?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Package-RPM-orange?style=for-the-badge&logo=redhat" alt="RPM package"/>
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

## What Is New in v32.0.0?

`v32.0.0 "Abyss"` is a full visual redesign — new theme, reorganized navigation, and polished UI across every tab:

- **Loofi Abyss theme** — Purpose-built dark palette (`#0b0e14` base, `#39c5cf` teal accent, `#b78eff` header purple) with matching light variant. Replaces Catppuccin.
- **Activity-based categories** — 10 categories consolidated to 8 logical groups: Overview, Manage, Hardware, Network & Security, Personalize, Developer, Automation, Health & Logs.
- **Category icons** — Emoji prefixes on sidebar category headers for instant visual scanning.
- **Sidebar collapse toggle** — `≡` / `✕` button to collapse/expand the sidebar; remembers state.
- **Deterministic tab ordering** — Explicit `CATEGORY_ORDER` dict enforces consistent sidebar sort across sessions.
- **QSS overhaul** — Both `modern.qss` and `light.qss` rewritten from scratch; dead `style.qss` removed.
- **Color migration** — All inline Catppuccin hex codes replaced across 30+ source files (notifications, health score, quick actions, and more).

Full notes: [`docs/releases/RELEASE-NOTES-v32.0.0.md`](docs/releases/RELEASE-NOTES-v32.0.0.md)

---

## What Is New in v31.0.0?

Full notes: [`docs/releases/RELEASE-NOTES-v31.0.0.md`](docs/releases/RELEASE-NOTES-v31.0.0.md)

---

## What Is New in v29.0.0?

`v29.0.0` delivers the usability features originally scoped in v22.0, plus cross-cutting UX polish:

- **Centralized error handler** — Global `sys.excepthook` override catches unhandled errors, shows recovery hints for known `LoofiError` types.
- **Confirmation dialogs** — `ConfirmActionDialog` for dangerous operations with undo hints, snapshot checkbox, and "don't ask again" toggle.
- **Notification toasts** — Animated slide-in notifications with category-based colors and auto-hide.
- **Sidebar search** — Enhanced to match tab descriptions, badges, and categories (not just names).
- **Status indicators** — Live colored dots on Maintenance/Storage sidebar items showing update availability and disk usage.
- **Theme-aware sparklines** — Dashboard SparkLine widget reads palette colors instead of hardcoded values.
- **CORS lockdown** — Web API restricted to localhost origins only.
- **Settings reset per group** — "Reset Appearance" and "Reset Behavior" buttons in Settings tab.
- **Keyboard accessibility** — Sidebar keyboard focus restored with StrongFocus policy.
- **95 new tests** across 5 test files covering all v29 features.
- **3846+ total tests** across 151 test files with 76.8% line coverage.

Full notes: [`docs/releases/RELEASE-NOTES-v29.0.0.md`](docs/releases/RELEASE-NOTES-v29.0.0.md)

---

## Installation

### Quick Install (Repository Script)

```bash
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

### Install From a Release RPM

```bash
pkexec dnf install ./loofi-fedora-tweaks-*.noarch.rpm
```

### Run From Source

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

## Built-In Tabs

| Category | Tabs |
|----------|------|
| 🏠 Overview | Home, System Info, System Monitor |
| 📦 Manage | Software, Maintenance, Snapshots, Virtualization |
| 🔧 Hardware | Hardware, Performance, Storage, Gaming |
| 🌐 Network & Security | Network, Loofi Link, Security & Privacy |
| 🎨 Personalize | Desktop, Profiles, Settings |
| 💻 Developer | Development, AI Lab, State Teleport |
| 🤖 Automation | Agents, Automation |
| 📊 Health & Logs | Health, Logs, Diagnostics, Community |

---

## Screenshots

Current UI screenshots (v32) are maintained in:

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

### Plugins and Marketplace (v27.x)

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
PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v  # 3968+ passing
```

Lint:

```bash
flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722
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
| CI | `.github/workflows/ci.yml` | Lint, typecheck, test, security, packaging |
| Auto Release | `.github/workflows/auto-release.yml` | Full release: validate → build → tag → publish |

### Auto Release Flow

```
push to master
  → validate (version alignment, packaging scripts)
  → adapter_drift, lint, typecheck, test, security, docs_gate (parallel)
  → build (RPM in Fedora 43 container)
  → auto_tag (creates vX.Y.Z tag if missing)
  → release (publishes GitHub Release with RPM artifact)
```

The pipeline automatically tags and publishes releases when code lands on `master` with a new version in `version.py`. No manual tagging required.

### Manual Release

Use **workflow_dispatch** with the version number for manual control. Set `dry_run: true` to validate without publishing.

---

## License

MIT License.
