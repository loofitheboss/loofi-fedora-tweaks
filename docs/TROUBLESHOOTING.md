# Loofi Fedora Tweaks — Troubleshooting

Common issues and fixes for v32.x.

---

## 1) Quick Diagnostics

Run these first:

```bash
loofi-fedora-tweaks --cli doctor
loofi-fedora-tweaks --cli info
loofi-fedora-tweaks --cli support-bundle
```

Optional alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

---

## 2) App Does Not Start

### Missing PyQt6

```bash
pkexec dnf install python3-pyqt6
```

### Qt platform plugin errors (`wayland` / `xcb`)

```bash
pkexec dnf install qt6-qtwayland
QT_QPA_PLATFORM=xcb loofi-fedora-tweaks
```

### Startup crash without clear UI message

```bash
tail -n 200 ~/.local/share/loofi-fedora-tweaks/startup.log
```

---

## 3) CLI Command Fails

### Command not found

Use full command:

```bash
loofi-fedora-tweaks --cli info
```

### Source-run import errors

```bash
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py --cli info
```

---

## 4) Privileged Actions Fail

Symptoms:

- updates/install/remove fail
- service/firewall actions fail
- no auth prompt appears

Checks:

```bash
which pkexec
pkexec true
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
```

Confirm a desktop polkit agent is running.

---

## 5) Atomic vs Traditional Behavior Differences

On Atomic Fedora, maintenance and package behavior uses `rpm-ostree` semantics.

Check detected mode:

```bash
loofi-fedora-tweaks --cli info
```

---

## 6) Plugin Marketplace Issues

Search test:

```bash
loofi-fedora-tweaks --cli plugin-marketplace search --query monitor
```

Install with explicit permissions acceptance:

```bash
loofi-fedora-tweaks --cli plugin-marketplace install <plugin-id> --accept-permissions
```

Inspect metadata first:

```bash
loofi-fedora-tweaks --cli plugin-marketplace info <plugin-id>
```

---

## 7) Virtualization Problems

libvirt status:

```bash
systemctl status libvirtd
pkexec systemctl enable --now libvirtd
```

KVM capability:

```bash
lscpu | grep -i virtualization
lsmod | grep -i kvm
```

---

## 8) Loofi Link Discovery Fails

Check Avahi:

```bash
systemctl status avahi-daemon
pkexec dnf install avahi avahi-tools nss-mdns
pkexec systemctl enable --now avahi-daemon
```

Firewall mDNS allowance:

```bash
pkexec firewall-cmd --permanent --add-service=mdns
pkexec firewall-cmd --reload
```

---

## 9) AI Lab Issues

Check Ollama:

```bash
ollama --version
ollama list
```

Check config/data write access:

```bash
ls -la ~/.config/loofi-fedora-tweaks/
```

---

## 10) Logs and Support Bundle

Export diagnostics:

```bash
loofi-fedora-tweaks --cli support-bundle
journalctl --user --since "1 hour ago"
```

---

## 11) Reporting Issues

Include:

1. Fedora version and desktop environment
2. exact tab/action or command
3. full error output
4. reproduction steps
5. support bundle path

Issues: <https://github.com/loofitheboss/loofi-fedora-tweaks/issues>
