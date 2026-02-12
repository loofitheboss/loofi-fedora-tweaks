# Loofi Fedora Tweaks - Beginner Quick Guide

> **Version 26.0.2 "Status Bar UI Hotfix"**  
> Fast onboarding guide for new users.

---

## Who This Is For

Use this guide if you are new to Loofi and want to:

- understand the layout quickly,
- run safe first actions,
- keep your Fedora system healthy without deep tuning.

If you want full details, use `docs/USER_GUIDE.md`.

---

## 1. Install and Launch

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/loofitheboss/loofi-fedora-tweaks/master/install.sh | bash
```

Launch:

```bash
loofi-fedora-tweaks
```

On first launch, complete the wizard (hardware + use-case profile).

---

## 2. Learn the Interface (30 seconds)

Main areas:

- Left sidebar: all categories and tabs.
- Top breadcrumb: where you are (`Category > Tab`).
- Center panel: active tools.
- Bottom bar: shortcuts and version.

![Home Dashboard](images/user-guide/home-dashboard.png)

Useful shortcuts:

- `Ctrl+K` search tabs/features
- `Ctrl+Shift+K` quick actions
- `F1` shortcut help

---

## 3. First 5 Actions to Run

## Action 1: Check System Status

Open:

- `Dashboard -> Home`
- `System -> System Monitor`

Look for:

- High CPU or RAM usage
- Unexpected network traffic

![System Monitor](images/user-guide/system-monitor.png)

## Action 2: Update Safely

Open:

- `Software -> Maintenance -> Updates`

Click:

- `Update All (DNF + Flatpak + Firmware)`

Notes:

- You may be prompted for admin authentication (`pkexec`).
- On Atomic Fedora, update behavior adapts automatically.

![Maintenance Updates](images/user-guide/maintenance-updates.png)

## Action 3: Clean Up Space

Open:

- `Software -> Maintenance -> Cleanup`

Recommended buttons:

- `Clean DNF Cache`
- `Vacuum Journal`
- `SSD Trim` (if SSD)

## Action 4: Run Security Pass

Open:

- `Security -> Security & Privacy`

Use:

- `Refresh Score`
- `Scan Ports`
- Firewall status actions

![Security and Privacy](images/user-guide/security-privacy.png)

## Action 5: Set Basic Preferences

Open:

- `Settings -> Appearance`
- `Settings -> Behavior`

Recommended starter settings:

- Enable update checks on start
- Keep dangerous action confirmations enabled

![Settings Appearance](images/user-guide/settings-appearance.png)

---

## 4. Weekly Routine (Simple)

Once per week:

1. `Maintenance -> Update All`
2. `Maintenance -> Cleanup` actions
3. `Security & Privacy -> Refresh Score`
4. `System Monitor` quick check for heavy processes

---

## 5. Useful CLI (Optional)

If you prefer terminal commands:

```bash
alias loofi='loofi-fedora-tweaks --cli'
loofi info
loofi health
loofi doctor
loofi cleanup all
loofi security-audit
```

---

## 6. When to Use the Full Guide

Open `docs/USER_GUIDE.md` when you need:

- detailed per-tab behavior,
- plugin marketplace workflows,
- daemon/web API usage,
- advanced CLI operations.

For issues, see `docs/TROUBLESHOOTING.md`.
