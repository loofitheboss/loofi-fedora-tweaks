# Getting Started

This guide will help you get started with Loofi Fedora Tweaks, whether you prefer the GUI or CLI interface.

---

## Run Modes

Loofi Fedora Tweaks supports four distinct run modes:

| Mode | Command | Use Case |
|------|---------|----------|
| **GUI** | `loofi-fedora-tweaks` | Daily desktop usage with visual interface |
| **CLI** | `loofi-fedora-tweaks --cli <command>` | Scripting, automation, remote administration |
| **Daemon** | `loofi-fedora-tweaks --daemon` | Background scheduled tasks |
| **Web API** | `loofi-fedora-tweaks --web` | Headless/remote integration (optional) |

### Shell Alias Recommendation

For easier CLI usage, add this to your `~/.bashrc` or `~/.zshrc`:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

Then use: `loofi info` instead of `loofi-fedora-tweaks --cli info`

---

## First-Run Wizard

The first time you launch the GUI, a 5-step wizard guides you through initial setup:

| Step | Description |
|------|-------------|
| **1. Welcome** | Introduction to key features and capabilities |
| **2. System Detection** | Auto-detects hardware profile, package manager (dnf vs rpm-ostree), and desktop environment |
| **3. Health Check** | Scans for: disk space, package system health, firewall status, backup tools, SELinux state |
| **4. Recommended Actions** | Suggests fixes for detected issues (e.g., "Enable firewall", "Install backup tool") with risk badges |
| **5. Ready** | Confirms setup is complete and opens the main window |

The wizard creates a profile at `~/.config/loofi-fedora-tweaks/profile.json` and won't appear again unless you delete that file.

---

## GUI Navigation

### Sidebar Categories

The main window features a collapsible sidebar organized into **8 activity-based categories**:

| Icon | Category | Purpose |
|------|----------|---------|
| 🏠 | **Overview** | Dashboard, system info, system monitor |
| 📦 | **Manage** | Software, maintenance, snapshots, virtualization, extensions, backup |
| 🔧 | **Hardware** | Hardware info, performance tuning, storage, gaming |
| 🌐 | **Network & Security** | Network settings, Loofi Link mesh, security & privacy |
| 🎨 | **Personalize** | Desktop customization, profiles, app settings |
| 💻 | **Developer** | Development tools, AI Lab, State Teleport |
| 🤖 | **Automation** | Agents, automation scheduler |
| 📊 | **Health & Logs** | Health timeline, logs viewer, diagnostics, community |

**Tip**: Click the category name to collapse/expand the sidebar for more screen space.

### Key UI Features

- **Sidebar Search**: Type to filter tabs by name
- **Favorites**: Right-click any tab to add it to favorites (quick access at top of sidebar)
- **Command Palette**: Press `Ctrl+K` to open the global command palette for quick navigation and actions
- **Breadcrumb Bar**: Shows current category and tab location
- **Toast Notifications**: Transient success/error messages appear in the status bar
- **Status Bar Undo**: Click the undo button to revert the last privileged action (via `HistoryManager`)

### Tab Anatomy

Most tabs follow this layout:

1. **Header**: Tab title and description
2. **Action Buttons**: Primary actions (e.g., "Refresh", "Install", "Apply")
3. **Content Area**: Forms, tables, cards, or command output
4. **Output Section** (for command tabs): Shows command output with Copy/Save/Cancel toolbar

---

## Quick CLI Tour

### System & Health Commands

```bash
# Display system information
loofi info

# Run health check
loofi health

# Check for missing dependencies
loofi doctor

# View hardware details
loofi hardware

# Generate support bundle (for bug reports)
loofi support-bundle
```

### Maintenance Commands

```bash
# Clean package cache, journal logs, temp files
loofi cleanup all

# Clean journal logs from last 7 days
loofi cleanup journal --days 7

# Apply power profile tweak
loofi tweak power --profile balanced

# Auto-tune system
loofi tuner analyze
loofi tuner apply
```

### Package Management

```bash
# Search for a package
loofi package search --query firefox --source all

# Install a package
loofi package install firefox

# Remove a package
loofi package remove firefox
```

### Logs & Services

```bash
# View error logs from last 2 hours
loofi logs errors --since "2h ago"

# List all failed services
loofi service list --filter failed

# Restart a service
loofi service restart sshd
```

### Security & Network

```bash
# Run security audit
loofi security-audit

# Configure DNS provider
loofi network dns --provider cloudflare

# View firewall ports
loofi firewall ports
```

### JSON Output for Scripting

Add `--json` flag to any command for machine-readable output:

```bash
loofi --json info
loofi --json health
loofi --json package search --query vim
```

Example JSON output:

```json
{
  "version": "40.0.0",
  "codename": "Foundation",
  "python_version": "3.12.1",
  "os": "Fedora 43",
  "package_manager": "dnf"
}
```

### Dry-Run Mode

Test commands without executing them (added in v35.0.0):

```bash
loofi --dry-run cleanup all
```

Output shows what would be executed without making any changes.

---

## GUI Quick Start

### 1. Launch the Application

```bash
loofi-fedora-tweaks
```

### 2. Complete First-Run Wizard

Follow the 5-step wizard to configure your system profile.

### 3. Explore Key Tabs

**For general users:**
- **Home** — Dashboard with system overview and quick actions
- **Maintenance** — Check for updates, clean up disk space
- **Software** — Browse and install applications
- **Network** — Configure Wi-Fi, DNS, and VPN

**For advanced users:**
- **Performance** — Auto-tune system for better performance
- **Virtualization** — Manage VMs and VFIO GPU passthrough
- **AI Lab** — Run local LLMs with Ollama
- **Automation** — Schedule recurring tasks

**For troubleshooting:**
- **Health Timeline** — View system health scores over time
- **Logs** — Search and filter system logs
- **Diagnostics** — Run diagnostic tools and generate support bundles

### 4. Use Command Palette

Press `Ctrl+K` and start typing:
- "update" → Jump to Maintenance Updates
- "firewall" → Open Security Firewall settings
- "cleanup" → Run cleanup actions
- "about" → View app version and credits

---

## Next Steps

- **Explore Tabs**: [GUI Tabs Reference](GUI-Tabs-Reference) — Detailed guide for all 28 tabs
- **Master CLI**: [CLI Reference](CLI-Reference) — Complete command reference with examples
- **Customize**: [Configuration](Configuration) — Themes, quick actions, favorites
- **Troubleshooting**: [Troubleshooting](Troubleshooting) — Common issues and solutions
