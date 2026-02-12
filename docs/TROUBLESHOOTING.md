# Troubleshooting Guide

Common issues and fixes for Loofi Fedora Tweaks v26.x.

---

## Quick Diagnostics First

Run these before deep troubleshooting:

```bash
loofi-fedora-tweaks --cli doctor
loofi-fedora-tweaks --cli info
loofi-fedora-tweaks --cli support-bundle
```

If CLI feels verbose, create an alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

---

## App Does Not Start

### `ModuleNotFoundError: No module named 'PyQt6'`

Install PyQt6:

```bash
pkexec dnf install python3-pyqt6
```

### Qt platform plugin errors (`wayland` / `xcb`)

Install Wayland plugin package:

```bash
pkexec dnf install qt6-qtwayland
```

For temporary X11 fallback:

```bash
QT_QPA_PLATFORM=xcb loofi-fedora-tweaks
```

### Startup crash with no visible error

Check startup log:

```bash
tail -n 200 ~/.local/share/loofi-fedora-tweaks/startup.log
```

---

## CLI Command Fails

### `loofi: command not found`

Default binary is `loofi-fedora-tweaks`. Use:

```bash
loofi-fedora-tweaks --cli info
```

Or define:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

### Running from source gives import errors

Run with proper `PYTHONPATH`:

```bash
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py --cli info
```

---

## Privileged Action Fails

Symptoms:

- update/install/remove actions fail
- service/firewall operations fail
- permission prompts do not appear

Checks:

```bash
which pkexec
pkexec true
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
```

Also ensure your desktop session has a running polkit authentication agent.

---

## Updates or Cleanup Behave Differently on Atomic

On Atomic Fedora variants, package layering and updates use `rpm-ostree` semantics.

- This is expected behavior.
- `Maintenance -> Overlays` appears only on Atomic-capable systems.
- Reboot may be required after some system updates.

Check detected mode:

```bash
loofi-fedora-tweaks --cli info
```

---

## Plugin Marketplace Issues

### Search or info returns nothing

Check network and query:

```bash
loofi-fedora-tweaks --cli plugin-marketplace search --query monitor
```

### Install requires permission acceptance

Use non-interactive consent flag:

```bash
loofi-fedora-tweaks --cli plugin-marketplace install <plugin-id> --accept-permissions
```

### Reviews or ratings fail

Verify plugin ID first:

```bash
loofi-fedora-tweaks --cli plugin-marketplace info <plugin-id>
```

---

## Virtualization Problems

### No VMs shown or libvirt errors

```bash
systemctl status libvirtd
systemctl list-units --type=service | rg libvirt
```

Enable libvirt if needed:

```bash
pkexec systemctl enable --now libvirtd
```

### KVM acceleration unavailable

```bash
lscpu | rg Virtualization
lsmod | rg kvm
```

---

## Networking / Loofi Link Discovery Fails

### No peers discovered

Check mDNS services:

```bash
systemctl status avahi-daemon
```

Install/start Avahi if missing:

```bash
pkexec dnf install avahi avahi-tools nss-mdns
pkexec systemctl enable --now avahi-daemon
```

### Firewall may block discovery

```bash
pkexec firewall-cmd --permanent --add-service=mdns
pkexec firewall-cmd --reload
```

---

## AI Lab Issues

### Ollama not found

Install and start Ollama separately, then reopen Loofi.

Quick check:

```bash
ollama --version
ollama list
```

### Voice or knowledge indexing errors

Check write permissions in user config area:

```bash
ls -la ~/.config/loofi-fedora-tweaks/
```

---

## Logs, Export, and Support Bundle

### Log export fails with permission errors

Export to a user-writable path:

```bash
loofi-fedora-tweaks --cli logs export /tmp/loofi-logs.txt
```

### Collect diagnostics for bug reports

```bash
loofi-fedora-tweaks --cli support-bundle
journalctl --user --since "1 hour ago"
```

---

## Still Stuck?

Open a GitHub issue and include:

1. Fedora version and desktop environment
2. Exact command or tab/action used
3. Full error output
4. Reproduction steps
5. Support bundle path

Issues: <https://github.com/loofitheboss/loofi-fedora-tweaks/issues>
