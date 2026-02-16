# Tooltip constants for the Loofi Fedora Tweaks UI
# Centralised here so translations and rewording stay in one place.

# ── Main Window ──────────────────────────────────────────────────────
MAIN_APPLY = "Apply all pending changes to the system"
MAIN_REVERT = "Revert the last batch of applied changes"
MAIN_REFRESH = "Re-scan hardware and reload current values"

# ── Boot Tab ─────────────────────────────────────────────────────────
BOOT_TIMEOUT = "Seconds the GRUB menu waits before auto-booting"
BOOT_DEFAULT_ENTRY = "Kernel entry selected by default at boot"
BOOT_QUIET = "Hide most kernel messages during startup"
BOOT_PLYMOUTH = "Show a graphical splash screen instead of scrolling text"

# ── Hardware Tab ─────────────────────────────────────────────────────
HW_CPU_GOVERNOR = "CPU frequency scaling policy (e.g. performance, powersave)"
HW_GPU_PROFILE = "Power / performance profile for the discrete GPU"
HW_FAN_MODE = "Fan curve preset — auto lets firmware decide"
HW_BACKLIGHT = "Display backlight brightness percentage"

# ── Performance Tab ──────────────────────────────────────────────────
PERF_SWAPPINESS = "How aggressively the kernel swaps out memory (0-200)"
PERF_THP = "Transparent Huge Pages policy (always / madvise / never)"
PERF_ZRAM = "Enable compressed swap in RAM for faster paging"
PERF_SCHEDULER = "I/O scheduler for the root block device"

# ── Diagnostics Tab ──────────────────────────────────────────────────
DIAG_JOURNAL = "Open a live view of the systemd journal"
DIAG_COREDUMPS = "List recent application core-dumps"
DIAG_DISK_HEALTH = "Run a SMART self-test on the selected drive"
DIAG_NETWORK = "Quick connectivity and DNS resolution check"

# ── Mesh / Teleport Tabs ────────────────────────────────────────────
MESH_DISCOVERY = "Scan the local network for other Loofi nodes"
MESH_PAIR = "Pair with a discovered node using a one-time code"
TELEPORT_SEND = "Send the selected file or clipboard to a paired node"
TELEPORT_RECEIVE = "Accept an incoming transfer from a paired node"

# ── Dashboard Tab ──────────────────────────────────────────────────
DASH_HEALTH_SCORE = "Overall system health grade based on CPU, RAM, disk, uptime, and updates"
DASH_QUICK_ACTIONS = "Common actions you can run with one click"
DASH_FOCUS_MODE = "Toggle Focus Mode to silence notifications and reduce distractions"
DASH_SYSTEM_OVERVIEW = "Key system metrics at a glance"

# ── Software Tab ──────────────────────────────────────────────────
SW_SEARCH = "Filter the application list by name or description"
SW_INSTALL = "Install this application using the system package manager"
SW_BATCH_INSTALL = "Install all selected applications in a single transaction"
SW_BATCH_REMOVE = "Remove all selected applications in a single transaction"
SW_RPM_FUSION = "Enable RPM Fusion repositories for additional packages and codecs"
SW_CODECS = "Install multimedia codecs for video and audio playback"
SW_FLATHUB = "Enable the Flathub remote for Flatpak applications"

# ── Maintenance Tab ──────────────────────────────────────────────────
MAINT_CLEANUP = "Remove cached packages and orphaned dependencies"
MAINT_JOURNAL = "Vacuum old systemd journal entries to free disk space"
MAINT_FLATPAK_CLEANUP = "Remove unused Flatpak runtimes and cached data"
MAINT_ORPHANS = "Find and remove packages no longer needed by any installed software"

# ── Desktop Tab ──────────────────────────────────────────────────
DESK_THEME = "Select the GTK / icon / cursor theme for your desktop"
DESK_FONTS = "Configure system fonts, hinting, and antialiasing"
DESK_EXTENSIONS = "Manage GNOME Shell extensions"
DESK_WALLPAPER = "Set the desktop wallpaper"

# ── Development Tab ──────────────────────────────────────────────────
DEV_TOOLBOX = "Create and manage Toolbx development containers"
DEV_VSCODE = "Install or configure Visual Studio Code and extensions"
DEV_LANGUAGES = "Install programming language runtimes and toolchains"
DEV_CONTAINERS = "Manage Podman containers for development workloads"

# ── Settings Dialog ──────────────────────────────────────────────────
SETTINGS_THEME = "Switch between light, dark, and system-follow themes"
SETTINGS_LANGUAGE = "UI language — requires restart to take full effect"
SETTINGS_AUTOSTART = "Launch Loofi automatically on login"
SETTINGS_NOTIFICATIONS = "Show desktop notifications for background events"
