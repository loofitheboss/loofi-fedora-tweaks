# Loofi Fedora Tweaks — Advanced Admin Guide

> Version 33.0.0 "Bastion"

Operational runbook for power users and Fedora admins.

---

## 1) Operating Model

Loofi entry modes:

- GUI: `loofi-fedora-tweaks`
- CLI: `loofi-fedora-tweaks --cli ...`
- Daemon: `loofi-fedora-tweaks --daemon`
- Web API: `loofi-fedora-tweaks --web`

Platform behavior:

- Traditional Fedora uses `dnf`
- Atomic Fedora variants use `rpm-ostree`

---

## 2) Privilege and Safety

Privileged workflows rely on:

- `pkexec`
- polkit desktop agent
- installed policy file (`org.loofi.fedora-tweaks.policy`)

Verification:

```bash
which pkexec
pkexec true
ls /usr/share/polkit-1/actions/org.loofi.fedora-tweaks.policy
```

---

## 3) Weekly Maintenance Window

1. Create snapshot baseline
2. Run **Manage → Maintenance → Updates**
3. Run **Manage → Maintenance → Cleanup**
4. Validate **Security & Privacy** score/firewall
5. Review **System Monitor** and **Logs** for regressions

![Maintenance Updates](images/user-guide/maintenance-updates.png)

![Security and Privacy](images/user-guide/security-privacy.png)

---

## 4) Performance Investigation Runbook

1. Inspect **Overview → System Monitor** for process pressure
2. Inspect **Health & Logs → Logs** for recurring faults
3. Check **Hardware → Performance** tuning recommendations
4. Check **Manage → Storage** for disk/SMART concerns

![System Monitor](images/user-guide/system-monitor.png)

---

## 5) Preset and Drift Control

1. Use **Automation → Community** to apply controlled presets
2. Re-check drift after major package/config changes
3. Export profiles before broad rollout

![Community Presets](images/user-guide/community-presets.png)

![Community Marketplace](images/user-guide/community-marketplace.png)

---

## 6) CLI Automation Patterns

Alias:

```bash
alias loofi='loofi-fedora-tweaks --cli'
```

Health snapshot:

```bash
loofi --json info > /tmp/loofi-info.json
loofi --json health > /tmp/loofi-health.json
```

Maintenance pipeline:

```bash
loofi cleanup all
loofi logs errors --since "24h ago"
loofi security-audit
```

Service/package triage:

```bash
loofi service list --filter failed
loofi service status sshd
loofi package recent --days 7
```

---

## 7) Daemon and Web API Notes

Daemon mode:

```bash
loofi-fedora-tweaks --daemon
```

Web API mode:

```bash
loofi-fedora-tweaks --web
```

Admin guidance:

- bind to trusted interfaces only
- enforce network controls and logging
- monitor for unusual execute patterns

---

## 8) Incident Response Quick Playbooks

App fails to start:

```bash
tail -n 200 ~/.local/share/loofi-fedora-tweaks/startup.log
loofi doctor
```

Privilege failures:

```bash
which pkexec
pkexec true
```

Escalation bundle:

```bash
loofi support-bundle
journalctl --user --since "2 hours ago"
```

---

## 9) Data Paths

- `~/.config/loofi-fedora-tweaks/settings.json`
- `~/.config/loofi-fedora-tweaks/profile.json`
- `~/.config/loofi-fedora-tweaks/first_run_complete`
- `~/.local/share/loofi-fedora-tweaks/startup.log`

---

## 10) Cross References

- Beginner: `docs/BEGINNER_QUICK_GUIDE.md`
- Full user guide: `docs/USER_GUIDE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
