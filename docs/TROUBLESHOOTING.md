# Troubleshooting Guide

Common issues and solutions for Loofi Fedora Tweaks.

---

## App Won't Start

### PyQt6 is not installed

**Symptom:** `ModuleNotFoundError: No module named 'PyQt6'`

**Fix:**
```bash
sudo dnf install python3-pyqt6
# Or via pip:
pip install PyQt6
```

### Display server issues (Wayland/X11)

**Symptom:** `qt.qpa.plugin: Could not find the Qt platform plugin "wayland"` or similar.

**Fix:**
```bash
# Install the Wayland Qt platform plugin
sudo dnf install qt6-qtwayland

# If using X11, force X11 backend
export QT_QPA_PLATFORM=xcb
loofi
```

If running over SSH or without a display:
```bash
# Check if DISPLAY or WAYLAND_DISPLAY is set
echo $DISPLAY
echo $WAYLAND_DISPLAY

# For headless testing only
export QT_QPA_PLATFORM=offscreen
```

### Permission denied on launch

**Symptom:** `Permission denied` when running `loofi` or the desktop entry.

**Fix:**
```bash
chmod +x /usr/bin/loofi
# Or if installed locally:
chmod +x ~/.local/bin/loofi
```

---

## Tabs Show Errors

### Missing Python dependencies

**Symptom:** A tab displays "Failed to load: No module named 'xxx'" in red text.

**Fix:** Install the missing dependency:
```bash
# Common dependencies
sudo dnf install python3-psutil python3-dbus python3-requests
pip install psutil distro
```

### Tab shows a traceback

**Symptom:** Tab content is replaced with an error message.

This typically means a utility module failed to import. Check the logs:
```bash
# View application logs
journalctl --user -t loofi-fedora-tweaks --since "10 min ago"

# Or check the log file
cat ~/.config/loofi-fedora-tweaks/app.log
```

---

## CLI Commands Fail

### PYTHONPATH not set

**Symptom:** `ModuleNotFoundError` when running `loofi` CLI commands.

**Fix:**
```bash
# Set the path manually
export PYTHONPATH="/usr/share/loofi-fedora-tweaks:$PYTHONPATH"

# Or run from the source directory
cd loofi-fedora-tweaks && python -m cli.main --help
```

### Missing utils module

**Symptom:** `ModuleNotFoundError: No module named 'utils'`

**Fix:** Ensure you are running from the correct directory or the RPM is
properly installed:
```bash
# Check installation
rpm -ql loofi-fedora-tweaks | head -20

# Verify the utils directory exists
ls /usr/share/loofi-fedora-tweaks/utils/
```

---

## RPM Installation Issues

### Package conflicts

**Symptom:** `dnf install` reports conflicts with existing packages.

**Fix:**
```bash
# Check for conflicting packages
rpm -qa | grep loofi

# Remove old version first
sudo dnf remove loofi-fedora-tweaks
sudo dnf install ./loofi-fedora-tweaks-*.rpm
```

### RPM won't install on Fedora Atomic/Silverblue

**Symptom:** `rpm-ostree` rejects the package or it disappears after reboot.

**Fix:**
```bash
# On atomic systems, use rpm-ostree
sudo rpm-ostree install ./loofi-fedora-tweaks-*.rpm
systemctl reboot

# Or layer it
sudo rpm-ostree install --allow-inactive ./loofi-fedora-tweaks-*.rpm
```

### Signature verification failure

**Symptom:** `Package ... is not signed`

**Fix:**
```bash
# Install without GPG check (for local builds only)
sudo dnf install --nogpgcheck ./loofi-fedora-tweaks-*.rpm
```

---

## Plugin Loading Failures

### Plugin not discovered

**Symptom:** Your plugin does not appear in `loofi plugins list`.

**Checklist:**
1. Plugin directory is under `plugins/` (not nested deeper)
2. Directory contains `plugin.py` or `__init__.py`
3. Directory name does not start with `_` or `.`

```bash
# Verify plugin structure
ls -la loofi-fedora-tweaks/plugins/my_plugin/
# Should show: __init__.py  plugin.json  plugin.py
```

### Plugin blocked by version check

**Symptom:** Log says "Plugin X requires app >= Y.Z.0"

**Fix:** Update Loofi to at least the required version, or lower the
`min_app_version` in the plugin's `plugin.json` if you know it is compatible.

### Plugin has unrecognized permissions

**Symptom:** `check_permissions()` returns items in the "denied" list.

**Fix:** Only use valid permissions in `plugin.json`:
```
network, filesystem, sudo, clipboard, notifications
```

Remove any unrecognized permission strings from the manifest.

### Import errors inside plugin

**Symptom:** `Failed to load plugin X: No module named 'Y'`

**Fix:**
```bash
# Check what the plugin requires
cat plugins/my_plugin/plugin.json

# Install missing dependencies
pip install <missing-package>
```

---

## Virtualization Tab Issues

### KVM not available

**Symptom:** "KVM acceleration not available" or VMs run very slowly.

**Fix:**
```bash
# Check if KVM is supported
lscpu | grep Virtualization
# Should show: VT-x (Intel) or AMD-V (AMD)

# Check if kvm modules are loaded
lsmod | grep kvm

# Load the module
sudo modprobe kvm_intel  # Intel
sudo modprobe kvm_amd    # AMD

# Install virtualization group
sudo dnf group install virtualization

# Ensure your user is in the libvirt group
sudo usermod -aG libvirt $USER
newgrp libvirt
```

### libvirtd not running

**Symptom:** "Failed to connect to libvirt" or VM list is empty.

**Fix:**
```bash
sudo systemctl enable --now libvirtd
sudo systemctl status libvirtd
```

---

## AI Lab Issues

### Ollama not installed

**Symptom:** AI Lab tab shows "Ollama not found" or CLI returns
"Ollama is not installed."

**Fix:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start the service
systemctl --user enable --now ollama
# Or system-wide:
sudo systemctl enable --now ollama

# Verify
ollama --version
ollama list
```

### No GPU acceleration

**Symptom:** Model inference is very slow (CPU only).

**Fix:**
```bash
# Check for NVIDIA GPU
nvidia-smi

# Install NVIDIA container toolkit if needed
sudo dnf install nvidia-driver cuda-toolkit

# Check Ollama GPU detection
ollama run llama3.2 "test" 2>&1 | head -5
```

### RAG indexing fails

**Symptom:** `rag-index` command returns an error.

**Fix:**
```bash
# Ensure the index directory exists and is writable
mkdir -p ~/.config/loofi-fedora-tweaks/rag-index
ls -la ~/.config/loofi-fedora-tweaks/rag-index/
```

---

## Mesh Networking Issues (Loofi Link)

### Avahi not running

**Symptom:** "No peers found" or mDNS discovery fails.

**Fix:**
```bash
# Install and start avahi
sudo dnf install avahi avahi-tools nss-mdns
sudo systemctl enable --now avahi-daemon

# Verify mDNS works
avahi-browse -at | head -10
```

### Firewall blocking discovery

**Symptom:** Peers are not discovered on the local network.

**Fix:**
```bash
# Allow mDNS through firewall
sudo firewall-cmd --permanent --add-service=mdns
sudo firewall-cmd --reload

# Allow Loofi Link port (default 5353 for mDNS + app-specific port)
sudo firewall-cmd --permanent --add-port=9876/tcp
sudo firewall-cmd --reload
```

---

## Performance Auto-Tuner Issues (v15.0)

### Tuner shows "unknown" workload

**Symptom:** `loofi tuner analyze` reports workload as "unknown" or always "idle".

**Fix:**
```bash
# Check if /proc/stat and /proc/meminfo are readable
cat /proc/stat | head -5
cat /proc/meminfo | head -5

# Run with verbose output
loofi --json tuner analyze
```

### Cannot apply tuning recommendations

**Symptom:** "Permission denied" when applying tuner settings.

**Fix:**
```bash
# Tuner settings require root via pkexec
# Verify pkexec is working
pkexec echo "test"

# Check if sysfs paths are writable
ls -la /sys/kernel/mm/transparent_hugepage/enabled
ls -la /proc/sys/vm/swappiness
```

### Governor not changing

**Symptom:** CPU governor stays the same after applying.

**Fix:**
```bash
# Check current governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Check available governors
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors

# Some systems lock governors via power-profiles-daemon
systemctl status power-profiles-daemon
```

---

## Snapshot Manager Issues (v15.0)

### No backends detected

**Symptom:** `loofi snapshot backends` returns empty list.

**Fix:**
```bash
# Install at least one snapshot tool
sudo dnf install snapper        # For BTRFS/LVM snapshots
sudo dnf install timeshift      # For rsync/BTRFS snapshots

# Verify installation
which snapper
which timeshift
which btrfs
```

### Cannot create snapshots

**Symptom:** "Failed to create snapshot" error.

**Fix:**
```bash
# For Snapper: ensure config exists
sudo snapper list-configs
# If empty, create one:
sudo snapper -c root create-config /

# For Timeshift: ensure it's configured
sudo timeshift --list

# For BTRFS: check filesystem type
df -T / | awk '{print $2}'
# Must show 'btrfs' for BTRFS snapshots
```

### Snapshot deletion fails

**Symptom:** Cannot delete snapshots, permission error.

**Fix:**
```bash
# Snapshot operations require root
# Verify polkit policy is installed
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
```

---

## Smart Log Viewer Issues (v15.0)

### No logs returned

**Symptom:** `loofi logs show` returns empty output.

**Fix:**
```bash
# Check if journalctl works
journalctl --no-pager -n 5

# Check if journal persistent storage is enabled
ls /var/log/journal/
# If empty, enable persistent logging:
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

### Pattern matching not finding errors

**Symptom:** `loofi logs errors` reports no patterns matched even when errors exist.

**Fix:**
```bash
# Check if errors exist in journal
journalctl -p err --no-pager -n 20

# Smart logs searches for specific regex patterns
# Some patterns require kernel messages:
journalctl -k --no-pager -n 10
```

### Export fails

**Symptom:** `loofi logs export` gives "Permission denied".

**Fix:**
```bash
# Ensure the target directory is writable
loofi logs export /tmp/my-logs.txt

# Check disk space
df -h /tmp
```

---

## Quick Actions Bar Issues (v15.0)

### Ctrl+Shift+K doesn't open

**Symptom:** Keyboard shortcut doesn't trigger the Quick Actions palette.

**Fix:**
- Ensure the main window has focus
- Check for shortcut conflicts with other applications
- Try using the menu bar to trigger Quick Actions if available

### Custom plugin actions not showing

**Symptom:** Plugin-registered actions don't appear in Quick Actions.

**Fix:**
```bash
# Verify plugin is loaded
loofi plugins list

# Plugin must register actions in on_load():
# from ui.quick_actions import QuickActionRegistry, QuickAction
# registry = QuickActionRegistry()
# registry.register(QuickAction(...))
```

---

## Service Explorer Issues (v16.0)

### Service list is empty

**Symptom:** `loofi service list` returns no services.

**Fix:**
```bash
# Verify systemctl works
systemctl list-units --type=service --no-pager | head

# If running in Flatpak, systemctl may need host access
# The app auto-detects Flatpak and uses flatpak-spawn --host
```

### Cannot start/stop services

**Symptom:** "Failed to start/stop" error message.

**Fix:**
```bash
# System services require polkit authentication
# Ensure pkexec is available
which pkexec

# Check if the polkit policy is installed
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy

# Try manually:
pkexec systemctl start <service-name>
```

### User services not found

**Symptom:** `--user` flag shows no services.

**Fix:**
```bash
# User services require the user instance
systemctl --user list-units --type=service

# If running from a different user context, ensure
# XDG_RUNTIME_DIR is set
echo $XDG_RUNTIME_DIR
```

---

## Package Explorer Issues (v16.0)

### Search returns no results

**Symptom:** `loofi package search --query <term>` returns nothing.

**Fix:**
```bash
# Verify DNF works
dnf search <term>

# Check if dnf is in PATH
which dnf

# On Atomic Fedora, dnf may have limited search;
# rpm-ostree search is not available, but dnf search still works
```

### Install fails with permission error

**Symptom:** Package install fails with pkexec/permission error.

**Fix:**
```bash
# Ensure polkit agent is running (for GUI)
# On KDE: /usr/libexec/polkit-kde-authentication-agent-1
# On GNOME: /usr/libexec/polkit-gnome-authentication-agent-1

# Flatpak installs don't require root:
loofi package install org.gnome.Calculator
```

### Flatpak packages not showing

**Symptom:** Only RPM packages appear in search/list.

**Fix:**
```bash
# Verify flatpak is installed
which flatpak

# Check if remotes are configured
flatpak remotes

# Add flathub if missing:
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

---

## Firewall Manager Issues (v16.0)

### "firewall-cmd not found"

**Symptom:** `loofi firewall status` says firewall-cmd is not available.

**Fix:**
```bash
# Install firewalld
sudo dnf install firewalld

# Start and enable
sudo systemctl enable --now firewalld
```

### Cannot open/close ports

**Symptom:** Port operations fail with permission errors.

**Fix:**
```bash
# Port operations use pkexec firewall-cmd
# Ensure polkit is working
pkexec firewall-cmd --list-ports

# Check firewalld is running
sudo systemctl status firewalld
```

### Firewall status shows stopped

**Symptom:** `loofi firewall status` reports firewall is not running.

**Fix:**
```bash
# Start firewalld
sudo systemctl start firewalld

# Or via the app:
# loofi firewall status will show "Stopped"
# Use pkexec systemctl start firewalld
```

---

## Performance Issues

### App is slow to start

**Cause:** All 18 tabs importing at once (should not happen with lazy loading).

**Fix:**
```bash
# Check startup time
time loofi --version

# Profile imports
python -c "
import time
start = time.time()
import sys
sys.path.insert(0, 'loofi-fedora-tweaks')
from ui.main_window import MainWindow
print(f'Import time: {time.time() - start:.2f}s')
"
```

If slow, check for heavy modules in plugin `on_load()` or top-level imports.

### High CPU usage

**Symptom:** Loofi consumes excessive CPU in the background.

**Fix:**
```bash
# Check which thread is busy
top -H -p $(pgrep -f loofi)

# The Pulse system event listener may be polling too fast
# Disable Pulse if not needed via tray icon -> Focus Mode
```

### High memory usage

**Symptom:** Memory grows over time.

**Fix:**
```bash
# Check memory per process
ps aux | grep loofi

# Restart the app to clear cached tab widgets
# Lazy-loaded tabs are created once and persist in memory
```

---

## How to Report Bugs

If you cannot resolve an issue, please file a bug report:

1. **Gather system info:**
   ```bash
   cat /etc/fedora-release
   uname -r
   python3 --version
   pip show PyQt6 2>/dev/null || rpm -q python3-pyqt6
   loofi --version 2>/dev/null || echo "CLI not available"
   ```

2. **Collect logs:**
   ```bash
   journalctl --user -t loofi-fedora-tweaks --since "1 hour ago" > /tmp/loofi-logs.txt
   cat ~/.config/loofi-fedora-tweaks/app.log >> /tmp/loofi-logs.txt 2>/dev/null
   ```

3. **Steps to reproduce:** Describe exactly what you did, what you expected,
   and what actually happened.

4. **Open an issue** on the GitHub repository with the above information
   attached. Include your Fedora version, desktop environment (GNOME/KDE/etc.),
   and display server (Wayland/X11).
