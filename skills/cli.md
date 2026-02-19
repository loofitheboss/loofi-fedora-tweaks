# CLI Skills Reference

> All commands support `--json` output format.
> Entry: `loofi-fedora-tweaks --cli <command>`

## Information & Monitoring

| Command | Description |
| --------- | ------------- |
| `info` | System information and version |
| `health` | System health overview with scores |
| `disk` | Disk usage and partition details |
| `processes` | Top processes by CPU/memory |
| `temperature` | CPU and system temperature readings |
| `netmon` | Network interface monitoring |
| `hardware` | Detected hardware profile |
| `doctor` | Dependency checks and diagnostics |
| `health-history` | Historical health metrics |

## System Operations

| Command | Description |
| --------- | ------------- |
| `cleanup` | DNF cache, journal vacuum, SSD trim, autoremove, RPM DB rebuild |
| `tweak` | Power profiles, audio restart, battery charge limits |
| `advanced` | DNF tweaks, TCP BBR, GameMode install, swappiness |
| `network` | DNS provider configuration |
| `boot` | Boot configuration and analysis |
| `updates` | Smart package update management |
| `service` | Systemd service start/stop/restart/enable/disable |
| `package` | Package install/remove/search |
| `firewall` | Firewall zone and rule management |
| `bluetooth` | Bluetooth device management |
| `flatpak-manage` | Flatpak application management |
| `extension` | GNOME Shell extension management |
| `display` | Monitor/display configuration |

## Profiles & Presets

| Command | Description |
| --------- | ------------- |
| `preset` | System preset activation and listing |
| `profile` | System profile save/load/list/activate |
| `focus-mode` | Enable/disable focus mode (domain blocking, DND) |

## Storage & Backup

| Command | Description |
| --------- | ------------- |
| `storage` | Storage management and optimization |
| `snapshot` | Snapshot create/list/restore/delete |
| `backup` | Backup wizard operations |

## Logs & Diagnostics

| Command | Description |
| --------- | ------------- |
| `logs` | Journal filtering, analysis, and export |
| `audit-log` | Security audit log review |
| `security-audit` | Security posture score calculation |

## Virtualization

| Command | Description |
| --------- | ------------- |
| `vm` | Virtual machine lifecycle (create/start/stop/delete) |
| `vfio` | GPU passthrough setup assistant |

## Advanced Features

| Command | Description |
| --------- | ------------- |
| `mesh` | Loofi Link peer discovery on LAN |
| `teleport` | Workspace state capture and restore |
| `tuner` | Performance auto-tuning |
| `ai-models` | Ollama LLM model management |
| `agent` | Autonomous agent control |

## Plugin & Extension Management

| Command | Description |
| --------- | ------------- |
| `plugins` | Plugin install/remove/list/enable/disable |
| `plugin-marketplace` | Browse and install from marketplace |

## Application Management

| Command | Description |
| --------- | ------------- |
| `self-update` | Check for and apply Loofi updates |
| `support-bundle` | Export debug information bundle |

## Usage Examples

```bash
# System health check
loofi-fedora-tweaks --cli health --json

# Clean system caches
loofi-fedora-tweaks --cli cleanup

# Switch to performance power profile
loofi-fedora-tweaks --cli tweak --power performance

# Create system snapshot
loofi-fedora-tweaks --cli snapshot --create "Before update"

# List running VMs
loofi-fedora-tweaks --cli vm --list

# Enable focus mode
loofi-fedora-tweaks --cli focus-mode --enable

# Export support bundle
loofi-fedora-tweaks --cli support-bundle --output /tmp/debug.tar.gz
```
