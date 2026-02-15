# Screenshot Content Guidelines

This document describes what each screenshot should display for optimal documentation quality.

## General Principles

1. **Show Real Data**: Prefer actual system data over empty states
2. **Highlight Key Features**: Ensure primary UI elements are visible
3. **Maintain Consistency**: Use same window size and theme for all shots
4. **Avoid Clutter**: Don't show unnecessary windows or desktop elements
5. **Privacy First**: No real personal data (hostnames, IPs, user names)

## Screenshot Specifications

### 1. home-dashboard.png
**Tab**: Overview > Home

**Should Show**:
- ✅ Health score with numeric value and status (Good/Warning/Critical)
- ✅ System status cards (CPU, RAM, Disk, Uptime)
- ✅ Quick action buttons (Update, Cleanup, Security Audit, etc.)
- ✅ Recent activity or alerts section
- ✅ Navigation sidebar visible with categories

**Ideal State**:
- Health score: 85-95 (green/good) or 70-84 (yellow/warning) for visual interest
- Some recent activity shown (not completely empty)
- All quick action buttons visible and readable

**What to Avoid**:
- Critical/red health state (unless documenting troubleshooting)
- Completely empty activity section
- Truncated or cut-off buttons

---

### 2. system-monitor.png
**Tab**: Overview > System Monitor

**Should Show**:
- ✅ CPU usage chart/graph with current percentage
- ✅ RAM usage with used/total values
- ✅ Process list with at least 5-10 processes
- ✅ Network activity indicators
- ✅ Disk I/O statistics

**Ideal State**:
- Moderate CPU usage (20-60%) shows activity without alarm
- Process list showing real applications (not just system daemons)
- Sorted by CPU or memory usage (most interesting processes at top)

**What to Avoid**:
- Empty process list
- 0% CPU across the board (looks broken)
- Extremely high usage (99%) unless demonstrating troubleshooting

---

### 3. maintenance-updates.png
**Tab**: Manage > Maintenance

**Should Show**:
- ✅ Updates sub-tab selected
- ✅ Available updates list (packages to update)
- ✅ Update button prominent and visible
- ✅ Last check timestamp
- ✅ System update status (Traditional vs Atomic Fedora indicator if applicable)

**Ideal State**:
- 3-10 available updates (shows functionality without overwhelming)
- Mix of package types (applications, libraries, system packages)
- "Check for Updates" and "Apply Updates" buttons visible

**Alternative States**:
- If no updates available, show "System is up to date" message
- For documentation, having some updates is more useful

**What to Avoid**:
- Hundreds of updates (confusing, looks unmaintained)
- Error states unless documenting troubleshooting

---

### 4. network-overview.png
**Tab**: Network & Security > Network

**Should Show**:
- ✅ Active network connection(s) with status
- ✅ Connection type (Ethernet, WiFi, etc.)
- ✅ IP address information
- ✅ DNS settings section
- ✅ Network controls/buttons

**Ideal State**:
- At least one active connection (green/connected)
- Real network name (not "Wired connection 1" if possible)
- IPv4 and optionally IPv6 addresses visible

**What to Avoid**:
- Showing real public IP addresses
- No connections at all (shows disconnected state)
- Personal WiFi names (use generic or test AP names)

---

### 5. security-privacy.png
**Tab**: Network & Security > Security & Privacy

**Should Show**:
- ✅ Security score prominent at top
- ✅ Firewall status (enabled/disabled)
- ✅ Security audit results or recent scans
- ✅ Privacy controls (telemetry, tracking, etc.)
- ✅ Hardening recommendations if any

**Ideal State**:
- Security score: 75-90 (good but with room for improvement)
- Firewall: Enabled (green checkmark)
- 1-3 recommendations visible (actionable items)

**What to Avoid**:
- Very low security score (<50) unless demonstrating remediation
- Critical vulnerabilities shown without context
- Firewall disabled without explanation

---

### 6. ai-lab-models.png
**Tab**: Developer > AI Lab

**Should Show**:
- ✅ Ollama integration status
- ✅ Available/installed models list
- ✅ Model management controls (download, remove)
- ✅ Model details (size, description)
- ✅ AI features section

**Ideal State**:
- 2-4 models in list (e.g., llama2, codellama, mistral)
- At least one model installed/available
- Clear download/manage buttons

**Alternative States**:
- If no Ollama installed, show installation prompt
- Empty state with "Get started" guidance is acceptable

**What to Avoid**:
- Dozens of models (cluttered)
- Error messages unless documenting troubleshooting

---

### 7. community-presets.png
**Tab**: Automation > Community

**Should Show**:
- ✅ Presets sub-tab selected
- ✅ List of available community presets
- ✅ Preset descriptions/categories
- ✅ Apply/install buttons
- ✅ Preset metadata (author, rating, downloads)

**Ideal State**:
- 5-10 presets visible
- Mix of categories (Performance, Security, Development, Gaming)
- Clear descriptions and call-to-action buttons

**What to Avoid**:
- Empty preset list
- Presets with no descriptions
- Overly long names that get truncated

---

### 8. community-marketplace.png
**Tab**: Automation > Community

**Should Show**:
- ✅ Marketplace sub-tab selected
- ✅ Plugin cards/tiles with icons
- ✅ Plugin names, descriptions, ratings
- ✅ Install buttons
- ✅ Search/filter controls

**Ideal State**:
- 6-12 plugin cards visible
- Mix of plugin types (monitoring, automation, utilities)
- Star ratings and download counts visible
- Professional-looking plugin icons

**What to Avoid**:
- Empty marketplace
- Plugins with missing icons (broken images)
- All plugins showing identical layouts

---

### 9. settings-appearance.png
**Tab**: Personalize > Settings

**Should Show**:
- ✅ Appearance sub-tab selected
- ✅ Theme selector (Dark/Light/Auto)
- ✅ Color scheme options
- ✅ Font size controls
- ✅ Window behavior settings

**Ideal State**:
- Abyss Dark theme selected (our default)
- Theme preview visible
- Multiple theme options in dropdown/selector
- Clear apply/save buttons

**What to Avoid**:
- Light theme (unless specifically demonstrating theme switching)
- Cut-off settings sections
- Apply button out of view

---

## Additional Screenshots (Priority 3)

### extensions-tab.png
**Tab**: Manage > Extensions (new in v37)

**Should Show**:
- Extension list with names and descriptions
- Enable/disable toggles
- Extension status indicators
- Management buttons

### backup-tab.png
**Tab**: Manage > Backup (new in v37)

**Should Show**:
- Backup destinations
- Last backup timestamp
- Create backup button
- Restore options

### diagnostics-tab.png
**Tab**: Developer > Diagnostics

**Should Show**:
- System checks/health tests
- Diagnostic results (pass/fail/warning)
- Support bundle generation
- Log export options

### agents-tab.png
**Tab**: Automation > Agents

**Should Show**:
- Local agent dashboard
- Agent status (running/stopped)
- Agent controls (start/stop/configure)
- Agent activity/logs

---

## Technical Checklist

Before saving each screenshot:

- [ ] Window size is consistent (1280x800 or 1440x900)
- [ ] Abyss Dark theme is active
- [ ] No personal information visible
- [ ] Primary UI elements are not cut off
- [ ] Loading states are complete (no spinners)
- [ ] No mouse cursor visible
- [ ] No desktop clutter in background
- [ ] File will be saved as PNG
- [ ] Filename matches specification exactly

## Post-Processing

After capturing all screenshots:

```bash
# Optimize file size
cd docs/images/user-guide/
optipng -o5 *.png

# Verify sizes
ls -lh *.png
# All should be < 200KB

# Test in documentation
grip ../USER_GUIDE.md
grip ../../README.md
```

## Quality Standards

A good screenshot should:
- Load quickly (< 200KB)
- Be readable at 100% zoom
- Show the app in a realistic usage state
- Help users identify the tab/feature
- Demonstrate value of the feature

A great screenshot also:
- Shows the feature in action (not just empty states)
- Uses realistic but privacy-safe example data
- Highlights the most important UI elements
- Makes the feature appealing to new users
