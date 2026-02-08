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
