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

# ── Settings Dialog ──────────────────────────────────────────────────
SETTINGS_THEME = "Switch between light, dark, and system-follow themes"
SETTINGS_LANGUAGE = "UI language — requires restart to take full effect"
SETTINGS_AUTOSTART = "Launch Loofi automatically on login"
SETTINGS_NOTIFICATIONS = "Show desktop notifications for background events"
