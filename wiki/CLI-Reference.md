# CLI Reference

Complete command-line reference for Loofi Fedora Tweaks. All commands support `--json` output for scripting.

---

## Command Format

```bash
loofi-fedora-tweaks --cli <command> [options]
```

**Recommended alias** (add to `~/.bashrc` or `~/.zshrc`):

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

---

## Global Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--json` | Output results in JSON format (machine-readable) | `loofi --json info` |
| `--dry-run` | Preview commands without executing them | `loofi --dry-run cleanup all` |
| `--timeout N` | Set global operation timeout in seconds (default 300) | `loofi --timeout 600 package install firefox` |

---

## System & Health Commands

### `info`
Display system information (version, OS, package manager, Python version).

```bash
loofi info
loofi --json info
```

### `health`
Run comprehensive health check and display overall score (A-F grade).

```bash
loofi health
loofi --json health
```

### `doctor`
Check for missing dependencies and system requirements.

```bash
loofi doctor
```

### `hardware`
Display detailed hardware information (CPU, GPU, RAM, storage).

```bash
loofi hardware
loofi --json hardware
```

### `support-bundle`
Generate diagnostic support bundle for bug reports. Creates a tarball with system info, logs, package list, and hardware details.

```bash
loofi support-bundle
# Output: /tmp/loofi-support-bundle-YYYYMMDD-HHMMSS.tar.gz
```

---

## Maintenance & Cleanup

### `cleanup <target>`
Clean up system files and caches.

**Targets**: `all`, `dnf`, `journal`, `tmp`, `thumbnails`

```bash
# Clean all
loofi cleanup all

# Clean only package cache
loofi cleanup dnf

# Clean journal logs older than 7 days
loofi cleanup journal --days 7

# Clean thumbnail cache
loofi cleanup thumbnails
```

### `tweak <category>`
Apply system tweaks and optimizations.

**Categories**: `power`, `network`, `input`

```bash
# Apply power profile (balanced, performance, power-saver)
loofi tweak power --profile balanced

# Enable TCP BBR congestion control
loofi tweak network --bbr

# Adjust mouse acceleration
loofi tweak input --mouse-accel 2.0
```

### `tuner <action>`
Auto-tuner for system performance.

**Actions**: `analyze`, `apply`, `reset`

```bash
# Analyze system and recommend tuning
loofi tuner analyze

# Apply recommended tuning
loofi tuner apply

# Reset to defaults
loofi tuner reset
```

---

## Updates & Packages

### `updates <action>`
Manage system updates.

**Actions**: `check`, `preview`, `schedule`, `rollback`, `history`

```bash
# Check for available updates
loofi updates check

# Preview what would be updated
loofi updates preview

# Schedule automatic updates
loofi updates schedule --time "03:00"

# Rollback last update (dnf only)
loofi updates rollback

# View update history
loofi updates history
```

### `package <action>`
Package management.

**Actions**: `search`, `install`, `remove`, `list`

```bash
# Search for a package
loofi package search --query firefox --source all

# Install a package
loofi package install firefox

# Remove a package
loofi package remove firefox

# List installed packages
loofi package list --filter user-installed
```

---

## Logs & Services

### `logs <level>`
View system logs filtered by level.

**Levels**: `all`, `errors`, `warnings`, `info`

```bash
# View all logs from last 2 hours
loofi logs all --since "2h ago"

# View only errors
loofi logs errors --since "1d ago"

# Follow logs in real-time
loofi logs all --follow

# Export logs to file
loofi logs errors --since "7d ago" --output /tmp/errors.log
```

### `service <action>`
Manage systemd services.

**Actions**: `list`, `start`, `stop`, `restart`, `enable`, `disable`, `status`

```bash
# List all services
loofi service list

# List only failed services
loofi service list --filter failed

# Restart a service
loofi service restart sshd

# Enable a service at boot
loofi service enable firewalld

# Check service status
loofi service status libvirtd
```

---

## Security & Firewall

### `security-audit`
Run comprehensive security audit (open ports, weak configs, outdated packages).

```bash
loofi security-audit
loofi --json security-audit
```

### `firewall <action>`
Manage firewalld zones, services, and ports.

**Actions**: `list`, `zones`, `ports`, `add-service`, `remove-service`, `add-port`, `remove-port`

```bash
# List all firewall rules
loofi firewall list

# List all zones
loofi firewall zones

# Show open ports
loofi firewall ports

# Add a service
loofi firewall add-service --service http --zone public

# Add a port
loofi firewall add-port --port 8080 --protocol tcp --zone public

# Remove a service
loofi firewall remove-service --service http --zone public
```

### `audit-log`
View privileged action audit trail (added in v35.0.0).

```bash
# View last 20 audit entries
loofi audit-log --count 20

# View all audit entries
loofi audit-log --count 0

# JSON output for parsing
loofi --json audit-log --count 50
```

---

## Network & Storage

### `network <action>`
Network configuration.

**Actions**: `list`, `dns`, `connections`, `wifi-scan`

```bash
# List network interfaces
loofi network list

# Configure DNS provider (cloudflare, google, quad9, custom)
loofi network dns --provider cloudflare

# List active connections
loofi network connections

# Scan for Wi-Fi networks
loofi network wifi-scan
```

### `storage <action>`
Storage and disk management.

**Actions**: `usage`, `disks`, `mounts`, `smart`

```bash
# Display disk usage summary
loofi storage usage

# List all disks
loofi storage disks

# List mount points
loofi storage mounts

# Check SMART health status
loofi storage smart
```

---

## Snapshots & Backup

### `snapshot <action>`
Manage system snapshots (Timeshift or Snapper).

**Actions**: `list`, `create`, `delete`, `restore`

```bash
# List all snapshots
loofi snapshot list

# Create a new snapshot
loofi snapshot create --description "Before system update"

# Delete a snapshot
loofi snapshot delete --id 123

# Restore from snapshot (requires reboot)
loofi snapshot restore --id 123
```

### `backup <action>`
Backup management (added in v37.0.0).

**Actions**: `create`, `list`, `restore`, `delete`

```bash
# Create a backup
loofi backup create --tool timeshift --description "Weekly backup"

# List backups
loofi backup list

# Restore from backup
loofi backup restore --id backup-2026-01-15

# Delete old backup
loofi backup delete --id backup-2025-12-01
```

---

## Virtualization & Containers

### `vm <action>`
Virtual machine management via libvirt.

**Actions**: `list`, `start`, `stop`, `info`, `create`, `delete`

```bash
# List all VMs
loofi vm list

# Start a VM
loofi vm start --name my-vm

# Stop a VM
loofi vm stop --name my-vm

# View VM info
loofi vm info --name my-vm
```

### `vfio <action>`
VFIO GPU passthrough configuration.

**Actions**: `list-gpus`, `bind`, `unbind`, `check`

```bash
# List available GPUs
loofi vfio list-gpus

# Bind GPU to VFIO driver
loofi vfio bind --gpu 0000:01:00.0

# Check VFIO status
loofi vfio check
```

---

## Desktop Extensions & Flatpak

### `extension <action>`
Desktop environment extensions (GNOME/KDE).

**Actions**: `list`, `install`, `enable`, `disable`, `remove`

```bash
# List installed extensions
loofi extension list

# Install an extension
loofi extension install --id dash-to-panel@jderose9.github.com

# Enable an extension
loofi extension enable --id dash-to-panel@jderose9.github.com

# Disable an extension
loofi extension disable --id dash-to-panel@jderose9.github.com
```

### `flatpak-manage <action>`
Flatpak package management.

**Actions**: `list`, `audit`, `orphans`, `cleanup`

```bash
# List all Flatpak apps
loofi flatpak-manage list

# Audit Flatpak sizes
loofi flatpak-manage audit

# Detect orphan runtimes
loofi flatpak-manage orphans

# Clean up unused packages
loofi flatpak-manage cleanup
```

---

## Boot & Hardware

### `boot <action>`
Boot configuration management.

**Actions**: `kernels`, `timeout`, `apply`

```bash
# List installed kernels
loofi boot kernels

# Set GRUB timeout
loofi boot timeout --seconds 5

# Apply GRUB changes
loofi boot apply
```

### `bluetooth <action>`
Bluetooth device management.

**Actions**: `list`, `pair`, `connect`, `disconnect`, `remove`, `scan`

```bash
# List paired devices
loofi bluetooth list

# Scan for devices
loofi bluetooth scan

# Pair a device
loofi bluetooth pair --address AA:BB:CC:DD:EE:FF

# Connect to a device
loofi bluetooth connect --address AA:BB:CC:DD:EE:FF
```

---

## Plugins & Marketplace

### `plugins <action>`
Manage installed plugins.

**Actions**: `list`, `enable`, `disable`, `info`, `update`

```bash
# List all plugins
loofi plugins list

# Enable a plugin
loofi plugins enable my-plugin

# Disable a plugin
loofi plugins disable my-plugin

# Show plugin info
loofi plugins info my-plugin

# Check for plugin updates
loofi plugins update
```

### `plugin-marketplace <action>`
Plugin marketplace operations (added in v27.0.0).

**Actions**: `search`, `info`, `install`, `uninstall`, `update`, `reviews`, `rating`

```bash
# Search for plugins
loofi plugin-marketplace search --query backup

# Get plugin details
loofi plugin-marketplace info backup-manager

# Install a plugin
loofi plugin-marketplace install backup-manager --accept-permissions

# Uninstall a plugin
loofi plugin-marketplace uninstall backup-manager

# Update all marketplace plugins
loofi plugin-marketplace update

# View reviews
loofi plugin-marketplace reviews backup-manager --limit 10

# Get rating
loofi plugin-marketplace rating backup-manager
```

---

## AI & Automation

### `ai-models <action>`
Manage AI models via Ollama.

**Actions**: `list`, `pull`, `remove`, `info`

```bash
# List installed models
loofi ai-models list

# Download a model
loofi ai-models pull llama3

# Remove a model
loofi ai-models remove codellama

# Show model info
loofi ai-models info mistral
```

### `agent <action>`
AI agent management.

**Actions**: `list`, `start`, `stop`, `status`, `logs`

```bash
# List all agents
loofi agent list

# Start an agent
loofi agent start --name backup-agent

# Check agent status
loofi agent status --name backup-agent

# View agent logs
loofi agent logs --name backup-agent
```

### `focus-mode <action>`
Distraction-free focus mode.

**Actions**: `start`, `stop`, `status`

```bash
# Start focus mode (blocks distracting sites)
loofi focus-mode start --duration 60

# Stop focus mode
loofi focus-mode stop

# Check status
loofi focus-mode status
```

---

## Profiles & Presets

### `profile <action>`
User profile management.

**Actions**: `list`, `create`, `switch`, `delete`, `export`, `import`

```bash
# List profiles
loofi profile list

# Create a new profile
loofi profile create --name gaming

# Switch to a profile
loofi profile switch --name gaming

# Export profile
loofi profile export --name work --output /tmp/work-profile.json

# Import profile
loofi profile import --file /tmp/work-profile.json
```

### `preset <action>`
Community configuration presets.

**Actions**: `list`, `apply`, `info`

```bash
# List available presets
loofi preset list

# Apply a preset
loofi preset apply --name gaming-optimized

# Show preset details
loofi preset info --name gaming-optimized
```

---

## Diagnostics & Monitoring

### `processes`
Display running processes with resource usage.

```bash
loofi processes
loofi processes --sort cpu
loofi processes --sort memory
loofi --json processes
```

### `temperature`
Display CPU and GPU temperatures.

```bash
loofi temperature
loofi --json temperature
```

### `netmon`
Network traffic monitoring.

```bash
loofi netmon --duration 60
loofi --json netmon --duration 30
```

### `health-history`
View health score history.

```bash
# Last 7 days
loofi health-history --days 7

# Last 30 days
loofi health-history --days 30

# JSON output for graphing
loofi --json health-history --days 90
```

---

## JSON Output Examples

All commands support `--json` flag for machine-readable output:

```bash
# System info
$ loofi --json info
{
  "version": "40.0.0",
  "codename": "Foundation",
  "python_version": "3.12.1",
  "os": "Fedora 43",
  "package_manager": "dnf"
}

# Health check
$ loofi --json health
{
  "overall_score": 92,
  "grade": "A",
  "categories": {
    "disk": {"score": 95, "status": "healthy"},
    "cpu": {"score": 88, "status": "healthy"},
    "memory": {"score": 90, "status": "healthy"},
    "services": {"score": 94, "status": "healthy"}
  }
}

# Package search
$ loofi --json package search --query firefox
{
  "results": [
    {
      "name": "firefox",
      "version": "122.0-1.fc43",
      "summary": "Mozilla Firefox Web browser",
      "repo": "fedora"
    }
  ]
}
```

---

## Scripting Tips

### Check Command Exit Codes

```bash
if loofi health > /dev/null; then
    echo "System is healthy"
else
    echo "Health issues detected"
fi
```

### Parse JSON Output with `jq`

```bash
# Get health score
loofi --json health | jq -r '.overall_score'

# List failed services
loofi --json service list --filter failed | jq -r '.services[].name'

# Get disk usage percentage
loofi --json storage usage | jq -r '.usage_percent'
```

### Automated Maintenance Script

```bash
#!/bin/bash
# Daily maintenance script

# Check health
SCORE=$(loofi --json health | jq -r '.overall_score')

if [ "$SCORE" -lt 80 ]; then
    echo "Health score low ($SCORE), running cleanup..."
    loofi cleanup all
    loofi tuner apply
fi

# Update system
loofi updates check && loofi updates preview
```

---

## Next Steps

- [GUI Tabs Reference](GUI-Tabs-Reference) — Visual interface for all CLI commands
- [Configuration](Configuration) — Configure CLI defaults and aliases
- [Troubleshooting](Troubleshooting) — CLI-specific troubleshooting tips
