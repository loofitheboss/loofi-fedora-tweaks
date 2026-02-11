# UX Enhancement Plan — v19.0 Phase 2

## Goal
Make the app more user-friendly with better navigation cues, discoverability, and status feedback.

## Changes (3 files)

### 1. `main_window.py` — Navigation & feedback improvements
- **Breadcrumb bar**: Add a header bar above content area showing `Category > Tab Name` + 1-line description
  - Updates on every page change
  - Shows tab description to help users understand what each page does
- **Status bar**: Bottom bar with version badge + keyboard shortcut hints (`Ctrl+K Search | Ctrl+Shift+K Actions | F1 Help`)
- **Tab descriptions**: Store per-tab descriptions in sidebar item data (UserRole+1), displayed in breadcrumb and as tooltips
- **Recommended/Advanced badges**: Tag sidebar items with colored suffixes — green "★" for recommended tabs, gray "⚙" for advanced
- **Category click → auto-select first child**: Instead of just expand/collapse, also navigate to the first child page
- **Sidebar footer**: Version label at bottom of sidebar

### 2. `modern.qss` — Dark theme styles for new elements
- Breadcrumb bar: dark surface, category in muted text, tab name in accent color
- Status bar: subtle background, small text, shortcut hints styled
- Sidebar description sublabel styling (via QSS objectName selectors)

### 3. `light.qss` — Light theme mirror
- Same new element styles adapted for Catppuccin Latte palette

## Tab descriptions & badges
| Tab | Description | Badge |
|-----|------------|-------|
| Home | System overview and quick actions | ★ |
| Agents | Automated system management agents | |
| Automation | Scheduled tasks and cron jobs | |
| System Info | Hardware and OS details | ★ |
| System Monitor | Live CPU, memory, and process monitoring | ★ |
| Health | System health timeline and trends | |
| Logs | Systemd journal and log viewer | ⚙ |
| Hardware | CPU, GPU, fan, and power controls | ★ |
| Performance | Kernel tuning and I/O scheduler | ⚙ |
| Storage | Disk usage and mount management | |
| Software | Package management and repos | ★ |
| Maintenance | System updates and cache cleanup | ★ |
| Snapshots | Btrfs/LVM snapshot management | ⚙ |
| Virtualization | Virtual machines and containers | ⚙ |
| Development | Developer tools and SDKs | |
| Network | Network interfaces and firewall | ★ |
| Loofi Link | Device mesh networking | ⚙ |
| Security & Privacy | Firewall, SELinux, audit tools | ★ |
| Desktop | GNOME/KDE customization | |
| Profiles | User profile and workspace management | |
| Gaming | Game mode and GPU optimization | |
| AI Lab | AI-powered system suggestions | ⚙ |
| State Teleport | System state transfer between machines | ⚙ |
| Diagnostics | System diagnostics and health checks | |
| Community | Community tweaks and shared configs | |
| Settings | App preferences and theme | |

## Success criteria
- Breadcrumb visible on every page showing where user is
- Status bar visible with version + shortcut hints
- Tooltips on every sidebar item
- ★ and ⚙ badges guide new users to recommended vs advanced features
- Category click navigates to first child (smoother UX)
- Both dark and light themes styled consistently
