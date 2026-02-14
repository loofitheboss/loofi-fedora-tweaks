# Atomic Fedora Support

Guide to using Loofi Fedora Tweaks on Atomic Fedora variants (Silverblue, Kinoite, etc.).

---

## Overview

Loofi Fedora Tweaks fully supports both **Traditional Fedora** (dnf-based) and **Atomic Fedora** (rpm-ostree-based) variants.

### Detection

The application auto-detects the package manager at startup:

```python
from utils.system import SystemManager

# Detect if running on Atomic Fedora
if SystemManager.is_atomic():
    print("Running on Atomic Fedora")
    
# Get package manager
pm = SystemManager.get_package_manager()  # "dnf" or "rpm-ostree"
```

**Detection method**: Checks for `/run/ostree-booted` file

---

## Behavioral Differences

### Package Operations

| Operation | Traditional Fedora (dnf) | Atomic Fedora (rpm-ostree) |
|-----------|-------------------------|----------------------------|
| **Install** | `pkexec dnf install -y <pkg>` | `pkexec rpm-ostree install <pkg>` + reboot prompt |
| **Remove** | `pkexec dnf remove -y <pkg>` | `pkexec rpm-ostree uninstall <pkg>` + reboot prompt |
| **Update** | `pkexec dnf upgrade -y` | `pkexec rpm-ostree upgrade` + reboot prompt |
| **Clean** | `pkexec dnf clean all` | `pkexec rpm-ostree cleanup -b` (base only) |
| **Rollback** | `pkexec dnf history undo last` | `pkexec rpm-ostree rollback` + reboot |

### Reboot Requirements

Most Atomic Fedora package operations require a reboot to apply changes:

```bash
# After installing a package
rpm-ostree install firefox
# Output: "Run 'systemctl reboot' to start a reboot"
```

The GUI displays a notification:
> ⚠️ **Reboot required** — Changes will take effect after reboot

### Layered Packages

Atomic Fedora uses **package layering** on top of the base image:

```bash
# List layered packages
rpm-ostree status

# Example output:
# State: idle
# Deployments:
# ● fedora:fedora/43/x86_64/silverblue
#    Version: 43.20260214.0 (2026-02-14)
#    BaseCommit: abc123...
#    LayeredPackages: firefox vim htop
```

**Maintenance Tab** shows layered packages in the **Overlays** section on Atomic systems.

---

## Developer Rules

### 1. Never Hardcode `dnf`

**Wrong:**
```python
subprocess.run(["pkexec", "dnf", "install", "-y", "firefox"], timeout=600)
```

**Correct:**
```python
from utils.commands import PrivilegedCommand

binary, args, desc = PrivilegedCommand.dnf("install", "firefox")
subprocess.run([binary] + args, timeout=600)
```

`PrivilegedCommand.dnf()` automatically selects `dnf` or `rpm-ostree` based on system detection.

### 2. Use SystemManager for Detection

**Always check the package manager:**

```python
from utils.system import SystemManager

pm = SystemManager.get_package_manager()

if pm == "rpm-ostree":
    # Atomic-specific logic (e.g., show reboot prompt)
    pass
elif pm == "dnf":
    # Traditional-specific logic
    pass
```

### 3. Branch on Atomic vs Traditional

All package operations must branch on system type:

```python
@staticmethod
def install_package(package: str) -> Tuple[str, List[str], str]:
    pm = SystemManager.get_package_manager()
    
    if pm == "rpm-ostree":
        return (
            "pkexec",
            ["rpm-ostree", "install", package],
            f"Installing {package} (reboot required)..."
        )
    else:
        return (
            "pkexec",
            ["dnf", "install", "-y", package],
            f"Installing {package}..."
        )
```

### 4. Test Both Paths

All tests must cover both dnf and rpm-ostree code paths:

```python
@patch('utils.mymodule.SystemManager.get_package_manager')
@patch('utils.mymodule.subprocess.run')
def test_install_atomic(self, mock_run, mock_get_pm):
    """Test package installation on Atomic Fedora."""
    mock_get_pm.return_value = 'rpm-ostree'
    mock_run.return_value = MagicMock(returncode=0)
    
    result = MyModule.install_package('foo')
    
    # Should use rpm-ostree
    self.assertIn('rpm-ostree', str(result))
    
@patch('utils.mymodule.SystemManager.get_package_manager')
@patch('utils.mymodule.subprocess.run')
def test_install_traditional(self, mock_run, mock_get_pm):
    """Test package installation on Traditional Fedora."""
    mock_get_pm.return_value = 'dnf'
    mock_run.return_value = MagicMock(returncode=0)
    
    result = MyModule.install_package('foo')
    
    # Should use dnf
    self.assertIn('dnf', str(result))
```

---

## Maintenance Tab on Atomic

The Maintenance tab adapts its interface on Atomic Fedora:

### Updates Section

- Shows **staged deployments** (pending reboot)
- Displays **bootable deployments** (current + previous)
- "Rollback" button visible (reverts to previous deployment)

### Cleanup Section

- **DNF cache** option hidden (not applicable)
- **rpm-ostree cleanup** option shown instead
  - Removes old deployments
  - Cleans base refs

### Overlays Section (Atomic only)

Lists all layered packages:
- Package name
- Version
- Size
- "Remove" button per package

---

## CLI on Atomic

CLI commands automatically adapt to Atomic systems:

```bash
# Install package (auto-detects rpm-ostree)
loofi-fedora-tweaks --cli package install firefox
# Output: "Installing firefox (reboot required)..."

# Update system
loofi-fedora-tweaks --cli updates check
# Output shows rpm-ostree upgrade available

# Rollback to previous deployment
loofi-fedora-tweaks --cli updates rollback

# List layered packages
loofi-fedora-tweaks --cli package list --filter layered
```

---

## Limitations on Atomic

Some operations behave differently or are unavailable on Atomic Fedora:

### Not Available
- **DNF history**: rpm-ostree doesn't support transaction history like dnf
- **DNF tweaks**: Configurations like `fastestmirror` don't apply to rpm-ostree
- **Package groups**: rpm-ostree doesn't support group installs

### Different Behavior
- **Updates are atomic**: System rolls back on update failure
- **Reboot required**: Most package changes require reboot
- **Base image immutable**: Can't modify base system files directly
- **Layered packages have overhead**: Each layered package increases update time

---

## Benefits of Atomic

### Advantages
1. **Rollback support**: Revert to previous system state easily
2. **Atomic updates**: Updates are all-or-nothing (no partial failures)
3. **Immutable base**: Harder to break the base system
4. **Reduced attack surface**: Base image is read-only
5. **Container-first**: Optimized for Flatpak and toolbox

### Use Cases
- **Development workstations** — Use toolbox for dev environments
- **Kiosk systems** — Immutable base prevents tampering
- **Testing** — Easy rollback after experimenting
- **Security-focused** — Reduced attack surface

---

## Toolbox and Flatpak

Atomic Fedora encourages **Toolbox** (containerized CLI environments) and **Flatpak** (GUI apps):

### Toolbox

```bash
# Create a toolbox (Traditional Fedora userspace in container)
toolbox create --distro fedora --release 43

# Enter toolbox
toolbox enter

# Inside toolbox, dnf works normally
sudo dnf install nodejs golang rust
```

### Flatpak

Loofi's **Flatpak Manager** (Software tab → Flatpak) provides:
- Size audit
- Orphan detection
- Permission inspection
- Bulk cleanup

---

## Migration from Traditional to Atomic

### Rebasing to Atomic

Fedora supports rebasing Traditional → Atomic:

```bash
# Install rpm-ostree
sudo dnf install rpm-ostree

# Rebase to Silverblue (GNOME)
rpm-ostree rebase fedora:fedora/43/x86_64/silverblue

# Or Kinoite (KDE)
rpm-ostree rebase fedora:fedora/43/x86_64/kinoite

# Reboot
systemctl reboot
```

### Post-Migration

1. **Reinstall layered packages**: rpm-ostree doesn't preserve dnf-installed packages
2. **Move dev tools to toolbox**: Create a toolbox for development
3. **Install Flatpaks**: Use Flatpak for GUI applications
4. **Update Loofi settings**: Loofi auto-detects the change

---

## Troubleshooting Atomic

### Check rpm-ostree Status

```bash
rpm-ostree status
```

Shows:
- Current deployment
- Staged deployments (pending reboot)
- Previous deployments (rollback targets)
- Layered packages
- Base commit

### Rollback Issues

If system won't boot after update:

1. **Reboot and select previous deployment** from GRUB menu
2. **Pin current deployment** (prevents automatic cleanup):
   ```bash
   rpm-ostree deploy --retain
   ```
3. **Report issue** and stay on working deployment

### Package Conflicts

If package layering fails:

```bash
# Check for conflicts
rpm-ostree install --dry-run <package>

# Force refresh metadata
rpm-ostree refresh-md

# Clean up failed transactions
rpm-ostree cleanup -p
```

---

## FAQ

### Q: Can I use dnf on Atomic Fedora?

**A:** No. The base system is managed by rpm-ostree. Use Toolbox for dnf-based environments.

### Q: Do I need to reboot after every package install?

**A:** Yes, for layered packages. Flatpaks don't require reboot.

### Q: Can I switch back to Traditional Fedora?

**A:** Yes, but it requires a reinstall. You cannot rebase from Atomic to Traditional.

### Q: Why is Loofi showing "rpm-ostree" instead of "dnf"?

**A:** You're running an Atomic Fedora variant. This is expected and fully supported.

### Q: How do I update my system?

**CLI:**
```bash
loofi-fedora-tweaks --cli updates check
loofi-fedora-tweaks --cli updates preview
# GUI prompts for reboot
```

**Manual:**
```bash
rpm-ostree upgrade
systemctl reboot
```

---

## Next Steps

- [Installation](Installation) — Installing on Atomic Fedora
- [Architecture](Architecture) — Understanding package manager detection
- [Security Model](Security-Model) — Privilege escalation on Atomic
- [Troubleshooting](Troubleshooting) — Atomic-specific issues
