# Installation

This guide covers system requirements and installation methods for Loofi Fedora Tweaks.

---

## System Requirements

### Base Requirements

- **Operating System**: Fedora 43 or later (Traditional Workstation or Atomic variants like Silverblue/Kinoite)
- **Python**: 3.12 or later
- **PyQt6**: GUI framework (installable via `dnf` or `pip`)
- **Polkit**: For privilege escalation (`pkexec`)

### Optional Dependencies

The following packages enable specific features but are not required for basic functionality:

| Package | Feature Enabled | Install Command |
|---------|----------------|-----------------|
| `libvirt`, `virt-manager` | Virtualization tab (VM management) | `pkexec dnf install libvirt virt-manager` |
| `ollama` | AI Lab (local LLM inference) | [Ollama Installation](https://ollama.ai/download) |
| `firewalld` | Security & Network tab (firewall rules) | `pkexec dnf install firewalld` |
| `avahi`, `nss-mdns` | Loofi Link (mDNS discovery) | `pkexec dnf install avahi avahi-tools nss-mdns` |
| `gamemode` | Gaming tab (game optimization) | `pkexec dnf install gamemode` |
| `timeshift` or `snapper` | Snapshots tab (system backups) | `pkexec dnf install timeshift` or `snapper` |
| `podman`, `podman-compose` | Development tab (containers) | `pkexec dnf install podman podman-compose` |

---

## Installation Methods

### Method 1: Fedora COPR (Recommended)

The package is published on [Fedora COPR](https://copr.fedorainfracloud.org/coprs/loofitheboss/loofi-fedora-tweaks/). This gives you automatic updates via `dnf`.

```bash
# Enable the COPR repository
sudo dnf copr enable loofitheboss/loofi-fedora-tweaks

# Install the package
sudo dnf install loofi-fedora-tweaks
```

### Method 2: Release RPM

Download the latest RPM from the [Releases page](https://github.com/loofitheboss/loofi-fedora-tweaks/releases):

```bash
# Install with dnf (Traditional Fedora)
sudo dnf install ./loofi-fedora-tweaks-*.noarch.rpm

# Or with rpm-ostree (Atomic Fedora)
rpm-ostree install ./loofi-fedora-tweaks-*.noarch.rpm
systemctl reboot
```

The RPM automatically installs:
- Application files to `/usr/share/loofi-fedora-tweaks/`
- Desktop entry to `/usr/share/applications/`
- Polkit policies to `/usr/share/polkit-1/actions/`
- Shell completions to `/usr/share/bash-completion/completions/`

### Method 3: Run From Source

For development or testing, run directly from the source tree:

```bash
# Clone the repository
git clone https://github.com/loofitheboss/loofi-fedora-tweaks.git
cd loofi-fedora-tweaks

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py
```

For CLI mode:

```bash
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py --cli info
```

---

## Post-Installation

### Verify Installation

Check that the application is working:

```bash
# Display version and system info
loofi-fedora-tweaks --cli info

# Run dependency check
loofi-fedora-tweaks --cli doctor
```

Expected output from `--cli info`:
```
═══════════════════════════════════════════
   Loofi Fedora Tweaks v44.0.0 CLI
═══════════════════════════════════════════
🖥️  System: Traditional Fedora
📦 Package Manager: dnf
⚡ Power Profile: balanced
```

### Optional Shell Alias

For convenience, add an alias to your `~/.bashrc` or `~/.zshrc`:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

Now you can use shorter commands:

```bash
loofi info
loofi health
loofi cleanup all
```

---

## Uninstall

### Uninstall COPR Package

**Traditional Fedora:**

```bash
sudo dnf remove loofi-fedora-tweaks
sudo dnf copr remove loofitheboss/loofi-fedora-tweaks
```

### Uninstall RPM Package

**Traditional Fedora:**

```bash
sudo dnf remove loofi-fedora-tweaks
```

**Atomic Fedora:**

```bash
rpm-ostree uninstall loofi-fedora-tweaks
systemctl reboot
```

### Clean Up User Data

The application stores configuration and logs in `~/.config/loofi-fedora-tweaks/`. To remove all user data:

```bash
rm -rf ~/.config/loofi-fedora-tweaks/
rm -rf ~/.local/share/loofi-fedora-tweaks/
```

### Remove Source Installation

If you installed from source, simply delete the cloned directory:

```bash
rm -rf loofi-fedora-tweaks/
```

---

## Troubleshooting Installation

### PyQt6 Not Found

If you get "No module named 'PyQt6'" errors:

```bash
# Traditional Fedora
pkexec dnf install python3-pyqt6

# Or via pip in a venv
pip install PyQt6
```

### Qt Platform Plugin Errors

If you see "Could not load the Qt platform plugin" errors:

```bash
pkexec dnf install qt6-qtwayland
```

Or force a specific platform:

```bash
QT_QPA_PLATFORM=xcb loofi-fedora-tweaks
```

### Polkit Authentication Fails

Ensure a polkit agent is running:

```bash
# GNOME
ps aux | grep polkit-gnome-authentication-agent

# KDE
ps aux | grep polkit-kde-authentication-agent
```

If no agent is running, install and start one for your desktop environment.

---

## Next Steps

- [Getting Started](Getting-Started) — Learn the basics of GUI and CLI usage
- [GUI Tabs Reference](GUI-Tabs-Reference) — Explore all 28 feature tabs
- [CLI Reference](CLI-Reference) — Master command-line automation
