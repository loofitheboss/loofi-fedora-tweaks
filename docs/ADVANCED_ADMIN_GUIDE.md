# Loofi Fedora Tweaks - Advanced Admin/Operator Guide

> **Version 26.0.2 "Status Bar UI Hotfix"**  
> Operational guidance for power users, workstation admins, and Fedora operators.

---

## Scope

This guide focuses on:

- safe execution of privileged actions,
- repeatable maintenance workflows,
- CLI automation patterns,
- Atomic vs traditional Fedora behavior,
- incident response and recovery playbooks.

For first-time onboarding, use `docs/BEGINNER_QUICK_GUIDE.md`.

---

## 1. Operating Model

Loofi is a multi-mode operations tool:

- GUI: daily interactive control plane
- CLI (`--cli`): script-friendly command surface
- Daemon (`--daemon`): background automation
- Web API (`--web`): headless integration endpoint

The UI is plugin-driven:

- tabs are loaded through plugin metadata/registry,
- widgets are lazy-loaded when first shown,
- compatibility checks can disable unsupported plugins safely.

Operational impact:

- startup stays fast on feature-rich deployments,
- unsupported features fail closed in UI instead of crashing startup.

---

## 2. Privilege and Safety Pipeline

Privileged operations rely on `pkexec` and polkit prompts.

Typical action path:

1. UI action -> utility/operation function
2. command runner executes asynchronously
3. output streamed into tab log
4. exit/error returned to UI

Hard requirements for reliable operation:

- `pkexec` available in path
- active desktop polkit agent for GUI prompts
- policy file installed (`org.loofi.fedora-tweaks.policy`)

Safety behavior to rely on:

- confirmation dialogs for dangerous actions
- snapshot-first prompts in some high-risk paths

---

## 3. Variant-Aware Operations (dnf vs rpm-ostree)

Loofi auto-detects platform mode:

- traditional Fedora: `dnf`
- Atomic variants: `rpm-ostree`

### Traditional Fedora

Recommended sequence:

1. `Maintenance -> Updates` (or `loofi cleanup`/package commands)
2. `Maintenance -> Cleanup`
3. `Security & Privacy` verification

### Atomic Fedora

Additional considerations:

- layered package management via `Maintenance -> Overlays`
- reboot frequently required after deployment changes
- validate pending deployment state after updates

Use this after major update windows:

```bash
loofi-fedora-tweaks --cli info
```

Look for Atomic system type and pending deployment flags.

---

## 4. Advanced GUI Runbooks

## Runbook A - Weekly Maintenance Window

1. **Snapshots**: create pre-change snapshot.
2. **Maintenance -> Updates**: execute update all.
3. **Maintenance -> Cleanup**: cache/journal/trim tasks.
4. **Security & Privacy**: refresh score + port scan.
5. **System Monitor**: watch for regressions (CPU/memory/process anomalies).

Reference screens:

![Maintenance Updates](images/user-guide/maintenance-updates.png)

![Security and Privacy](images/user-guide/security-privacy.png)

## Runbook B - Performance Degradation Investigation

1. **System Monitor**: identify high CPU or memory consumers.
2. **Logs**: inspect recent error bursts and patterns.
3. **Performance**: detect workload and evaluate tuning recommendation.
4. **Storage**: check disk usage/health if I/O latency appears.

Reference screen:

![System Monitor](images/user-guide/system-monitor.png)

## Runbook C - Configuration Drift Control

1. **Community -> Marketplace**: apply known baseline preset.
2. **Community -> Drift**: check for deviation periodically.
3. Export current preset/profile bundles before large changes.

Reference screens:

![Community Presets](images/user-guide/community-presets.png)

![Community Marketplace](images/user-guide/community-marketplace.png)

---

## 5. CLI Automation Patterns

Define shell alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

### Health Snapshot Script Pattern

```bash
loofi --json info > /tmp/loofi-info.json
loofi --json health > /tmp/loofi-health.json
loofi --json disk > /tmp/loofi-disk.json
```

### Maintenance Pipeline Pattern

```bash
loofi cleanup all
loofi logs errors --since "24h ago"
loofi security-audit
```

### Service/Package Triage Pattern

```bash
loofi service list --filter failed
loofi service status sshd
loofi package recent --days 7
```

### Profile Change Control Pattern

```bash
loofi profile export-all profiles-backup.json --include-builtins
loofi profile apply gaming
loofi profile import-all profiles-backup.json --overwrite
```

---

## 6. Plugin and Marketplace Operations

Two separate workflows exist:

- Community preset marketplace (GUI in Community tab)
- Plugin marketplace (CLI: `plugin-marketplace`)

### Plugin Lifecycle Commands

```bash
loofi plugins list
loofi plugin-marketplace search --query monitor
loofi plugin-marketplace info plugin-id
loofi plugin-marketplace install plugin-id --accept-permissions
loofi plugin-marketplace update plugin-id
loofi plugin-marketplace uninstall plugin-id
```

### Operational Guardrails

- verify plugin metadata before install (`info`)
- review requested permissions before acceptance
- prefer staged rollout on non-critical machines first

---

## 7. Daemon and Web API Operations

### Daemon Mode

```bash
loofi-fedora-tweaks --daemon
```

Use for persistent scheduling/automation without GUI session interaction.

### Web API Mode

```bash
loofi-fedora-tweaks --web
```

Admin guidance:

- expose only on trusted network boundaries,
- keep authentication and network controls strict,
- monitor logs for failed auth or unusual execute patterns.

---

## 8. Incident Response Playbooks

## Playbook 1 - App Fails to Start

1. inspect startup log:

```bash
tail -n 200 ~/.local/share/loofi-fedora-tweaks/startup.log
```

2. verify PyQt6/platform deps.
3. run CLI diagnostics:

```bash
loofi-fedora-tweaks --cli doctor
```

## Playbook 2 - Privileged Actions Failing

```bash
which pkexec
pkexec true
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
```

If checks pass, confirm session polkit agent availability.

## Playbook 3 - Support Escalation Bundle

```bash
loofi-fedora-tweaks --cli support-bundle
journalctl --user --since "2 hours ago"
```

Attach both outputs to issue reports.

---

## 9. Operational Data Paths

Key files:

- `~/.config/loofi-fedora-tweaks/settings.json`
- `~/.config/loofi-fedora-tweaks/profile.json`
- `~/.config/loofi-fedora-tweaks/first_run_complete`
- `~/.local/share/loofi-fedora-tweaks/startup.log`

Use these for backup/restore and forensic troubleshooting.

---

## 10. Admin Checklist

Before major changes:

1. export profiles and/or snapshots
2. capture baseline health (`--json info/health`)
3. schedule maintenance window

After major changes:

1. verify updates completed successfully
2. run security score + port checks
3. inspect logs for high-severity errors
4. confirm system behavior under normal workload

---

## 11. Cross-Reference Docs

- Beginner onboarding: `docs/BEGINNER_QUICK_GUIDE.md`
- Full user walkthrough: `docs/USER_GUIDE.md`
- Troubleshooting details: `docs/TROUBLESHOOTING.md`
- Contributor workflows: `docs/CONTRIBUTING.md`
