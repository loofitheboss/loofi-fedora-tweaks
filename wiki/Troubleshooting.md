# Troubleshooting

Common issues and solutions for Loofi Fedora Tweaks.

---

## Quick Diagnostics

Run these commands first for troubleshooting:

```bash
# Check system compatibility
loofi-fedora-tweaks --cli doctor

# Display system information
loofi-fedora-tweaks --cli info

# Generate support bundle (for bug reports)
loofi-fedora-tweaks --cli support-bundle
```

**Optional alias** (add to `~/.bashrc` or `~/.zshrc`):

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

---

## App Doesn't Start

### 1. Missing PyQt6

**Symptom**: `ModuleNotFoundError: No module named 'PyQt6'`

**Solution**:

```bash
# Traditional Fedora
pkexec dnf install python3-pyqt6

# Or via pip in venv
python3 -m venv .venv
source .venv/bin/activate
pip install PyQt6
```

### 2. Qt Platform Plugin Errors

**Symptom**: `Could not load the Qt platform plugin "wayland"`

**Solution**:

```bash
# Install Wayland support
pkexec dnf install qt6-qtwayland

# Or force X11 platform
QT_QPA_PLATFORM=xcb loofi-fedora-tweaks
```

### 3. Startup Crash (No UI)

**Symptom**: App starts but crashes immediately with no error message

**Solution**:

```bash
# Check startup log
tail -n 200 ~/.local/share/loofi-fedora-tweaks/startup.log

# Run with debug output
loofi-fedora-tweaks --debug
```

Common causes:
- Corrupted config file: `rm -rf ~/.config/loofi-fedora-tweaks/`
- Missing dependencies: `loofi-fedora-tweaks --cli doctor`
- Qt version mismatch: Reinstall PyQt6

---

## CLI Command Fails

### 1. Command Not Found

**Symptom**: `bash: loofi-fedora-tweaks: command not found`

**Solution**:

```bash
# If installed from RPM
which loofi-fedora-tweaks

# If missing, reinstall
pkexec dnf reinstall loofi-fedora-tweaks

# If running from source
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py --cli info
```

### 2. Import Errors

**Symptom**: `ModuleNotFoundError` when running from source

**Solution**:

```bash
# Ensure PYTHONPATH is set
PYTHONPATH=loofi-fedora-tweaks python3 loofi-fedora-tweaks/main.py --cli info

# Or run from project root
cd loofi-fedora-tweaks/
./run.sh --cli info
```

---

## Privileged Actions Fail

### 1. Authentication Dialog Doesn't Appear

**Symptom**: Updates/installs/firewall changes silently fail

**Checks**:

```bash
# Verify pkexec exists
which pkexec

# Test pkexec manually
pkexec true

# Check polkit policies
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.*.policy
```

**Solution**:

```bash
# Ensure polkit agent is running
# For GNOME
ps aux | grep polkit-gnome-authentication-agent

# For KDE
ps aux | grep polkit-kde-authentication-agent

# If missing, install and start
pkexec dnf install polkit-gnome
/usr/libexec/polkit-gnome-authentication-agent-1 &
```

### 2. "Not authorized" Errors

**Symptom**: `Error: Not authorized to perform operation`

**Solution**:

```bash
# Reinstall polkit policies (from RPM)
pkexec dnf reinstall loofi-fedora-tweaks

# Or copy policies manually (from source)
sudo cp config/org.loofi.fedora-tweaks.*.policy /usr/share/polkit-1/actions/
```

---

## Virtualization Issues

### 1. libvirtd Not Running

**Symptom**: Virtualization tab shows "libvirt not available"

**Solution**:

```bash
# Check status
systemctl status libvirtd

# Enable and start
pkexec systemctl enable --now libvirtd

# Add user to libvirt group
pkexec usermod -aG libvirt $USER

# Log out and back in for group change
```

### 2. KVM Not Available

**Symptom**: VMs fail to start, "KVM acceleration not available"

**Checks**:

```bash
# Check CPU virtualization support
lscpu | grep -i virtualization
# Should show: VT-x (Intel) or AMD-V (AMD)

# Check KVM modules
lsmod | grep -i kvm
# Should show: kvm_intel or kvm_amd
```

**Solution**:

```bash
# Load KVM modules
pkexec modprobe kvm_intel  # Intel
pkexec modprobe kvm_amd    # AMD

# Enable in BIOS if not shown in lscpu
```

---

## Loofi Link Issues

### 1. No Devices Discovered

**Symptom**: Mesh tab shows "No devices found"

**Checks**:

```bash
# Check Avahi daemon
systemctl status avahi-daemon

# Check firewall (mDNS port 5353)
pkexec firewall-cmd --list-services | grep mdns
```

**Solution**:

```bash
# Install Avahi
pkexec dnf install avahi avahi-tools nss-mdns

# Enable and start daemon
pkexec systemctl enable --now avahi-daemon

# Allow mDNS in firewall
pkexec firewall-cmd --permanent --add-service=mdns
pkexec firewall-cmd --reload
```

### 2. Discovery Works But Connection Fails

**Solution**:

```bash
# Check firewall for Loofi port (default 9527)
pkexec firewall-cmd --permanent --add-port=9527/tcp
pkexec firewall-cmd --reload

# Test local connectivity
nc -zv <device-ip> 9527
```

---

## AI Lab Issues

### 1. Ollama Not Found

**Symptom**: AI Lab tab shows "Ollama not installed"

**Solution**:

```bash
# Check if installed
ollama --version

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Verify
ollama list
```

### 2. Model Download Fails

**Symptom**: "Failed to pull model" errors

**Checks**:

```bash
# Check disk space
df -h ~

# Check Ollama service
systemctl --user status ollama

# Check network connectivity
curl -I https://ollama.ai
```

**Solution**:

```bash
# Restart Ollama service
systemctl --user restart ollama

# Manually pull model
ollama pull llama3

# Check Ollama logs
journalctl --user -u ollama -n 50
```

---

## Network Tab Issues

### 1. Wi-Fi Scan Returns Empty

**Solution**:

```bash
# Check NetworkManager
systemctl status NetworkManager

# Manual scan with nmcli
nmcli device wifi list

# Restart NetworkManager
pkexec systemctl restart NetworkManager
```

### 2. DNS Changes Don't Apply

**Solution**:

```bash
# Verify NetworkManager DNS mode
cat /etc/NetworkManager/NetworkManager.conf | grep dns

# Restart NetworkManager
pkexec systemctl restart NetworkManager

# Clear DNS cache
pkexec resolvectl flush-caches
```

---

## Update/Package Issues

### 1. DNF Locked

**Symptom**: "DNF is locked by another process"

**Solution**:

```bash
# Check for running DNF processes
ps aux | grep dnf

# Wait for other operations to complete
# Or force kill (not recommended)
pkexec killall dnf

# Clean DNF lock
pkexec rm -f /var/lib/dnf/LOCK
```

### 2. Atomic Fedora: Reboot Required

**Not an issue** — Atomic Fedora requires reboot after package operations:

```bash
# Check pending deployment
rpm-ostree status

# Reboot to apply
systemctl reboot
```

---

## Performance Issues

### 1. High CPU Usage

**Symptom**: App uses excessive CPU

**Solution**:

```bash
# Check running processes
loofi-fedora-tweaks --cli processes --sort cpu

# Disable unused tabs (in Settings)
# Reduce monitoring frequency (System Monitor refresh rate)
```

### 2. High Memory Usage

**Solution**:

```bash
# Check memory usage
loofi-fedora-tweaks --cli processes --sort memory

# Restart app to clear cache
pkexec killall loofi-fedora-tweaks
loofi-fedora-tweaks
```

---

## Plugin Issues

### 1. Plugin Won't Load

**Solution**:

```bash
# Check plugin structure
ls -la plugins/my-plugin/

# Required files:
# - plugin.json
# - plugin.py

# Check plugin logs
tail -n 50 ~/.local/share/loofi-fedora-tweaks/plugins.log

# Test plugin manually
loofi-fedora-tweaks --cli plugins list
```

### 2. Marketplace Search Fails

**Solution**:

```bash
# Check network connectivity
curl -I https://plugins.loofi.fedora-tweaks.example.com

# Verify firewall allows HTTPS
pkexec firewall-cmd --list-services | grep https

# Clear plugin cache
rm -rf ~/.cache/loofi-fedora-tweaks/plugins/
```

---

## Logs & Diagnostics

### View Application Logs

```bash
# Startup log
tail -f ~/.local/share/loofi-fedora-tweaks/startup.log

# Plugin log
tail -f ~/.local/share/loofi-fedora-tweaks/plugins.log

# Audit log (privileged actions)
tail -f ~/.config/loofi-fedora-tweaks/audit.jsonl

# System journal (if running as service)
journalctl --user -u loofi-fedora-tweaks -f
```

### Generate Support Bundle

```bash
loofi-fedora-tweaks --cli support-bundle
# Creates: /tmp/loofi-support-bundle-YYYYMMDD-HHMMSS.tar.gz
```

**Bundle includes:**
- System information
- Application logs
- Package list
- Hardware details
- Configuration files (sanitized)

---

## Reporting Issues

When reporting bugs on GitHub, include:

1. **Fedora version** and desktop environment:
   ```bash
   cat /etc/fedora-release
   echo $XDG_CURRENT_DESKTOP
   ```

2. **Application version**:
   ```bash
   loofi-fedora-tweaks --cli info
   ```

3. **Exact steps to reproduce**

4. **Expected vs actual behavior**

5. **Error logs**:
   ```bash
   loofi-fedora-tweaks --cli support-bundle
   ```

6. **System health**:
   ```bash
   loofi-fedora-tweaks --cli doctor
   loofi-fedora-tweaks --cli health
   ```

**Issue tracker**: https://github.com/loofitheboss/loofi-fedora-tweaks/issues

---

## Next Steps

- [FAQ](FAQ) — Frequently asked questions
- [Installation](Installation) — Reinstall or verify installation
- [CLI Reference](CLI-Reference) — Diagnostic commands
- [Contributing](Contributing) — Report bugs
