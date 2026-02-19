# Storage & Backup Skills

## Disk Management

- **Disk usage** — Per-partition and per-directory space usage
- **Mount points** — List and manage filesystem mount points
- **Filesystem info** — Type, label, UUID, options for each partition
- **Disk health** — S.M.A.R.T. status and attribute monitoring

**Modules:** `utils/storage.py`, `services/hardware/disk.py`
**UI:** Storage Tab
**CLI:** `disk`, `storage`

## SSD Optimization

- **TRIM** — Run fstrim to reclaim unused blocks
- **Scheduler tuning** — Set optimal I/O scheduler for SSD vs HDD
- **Write optimization** — Configure noatime and other mount options

**Modules:** `core/executor/operations.py` (CleanupOps)
**UI:** Maintenance Tab, Storage Tab
**CLI:** `cleanup`

## Snapshot Management

- **Multi-backend** — Support for Timeshift, Snapper, and native Btrfs snapshots
- **Create snapshots** — Pre-change system snapshots with descriptions
- **Restore snapshots** — Rollback to any saved snapshot
- **List/Delete** — Browse and manage existing snapshots
- **Auto-prompt** — Prompt for snapshot before risky operations

**Modules:** `utils/snapshot_manager.py`, `utils/safety.py`
**UI:** Snapshot Tab
**CLI:** `snapshot`

## Backup Wizard

- **Guided backup** — Step-by-step backup creation wizard
- **Destination selection** — Local, external drive, or network target
- **Incremental backups** — Only backup changed files
- **Restore wizard** — Guided restoration from backup

**UI:** Backup Tab
**CLI:** `backup`

## Action History

- **Change logging** — Record all system modifications with undo commands
- **Undo support** — Reverse previous actions using stored undo commands
- **History limit** — Rolling window of last 50 actions

**Modules:** `utils/history.py`

## Configuration Drift Detection

- **Baseline comparison** — Detect changes from known-good configuration
- **Drift reporting** — List files and settings that have drifted
- **Auto-remediation** — Optionally restore drifted settings

**Modules:** `utils/drift.py`

## Support Bundle Export

- **Debug bundle** — Collect system info, logs, and config for support
- **Anonymization** — Strip sensitive data from exports
- **Report generation** — Generate formatted system reports

**Modules:** `utils/report_exporter.py`, `core/export.py`
**CLI:** `support-bundle`
