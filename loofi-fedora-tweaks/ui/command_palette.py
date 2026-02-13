"""
Command Palette - Global fuzzy search across all features.
Part of v11.0 "Aurora Update".

Provides a Ctrl+K searchable overlay that lets users jump to any
feature or tab in the application.  The palette uses simple
case-insensitive substring matching across feature names and keywords.

Integration:
    palette = CommandPalette(on_action=main_window.switch_to_tab, parent=main_window)
    palette.exec()
"""

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeyEvent

from utils.log import get_logger

logger = get_logger(__name__)

# Maximum results displayed at once
_MAX_RESULTS = 10


# -----------------------------------------------------------------------
# Feature registry
# -----------------------------------------------------------------------

def _build_feature_registry() -> list[dict]:
    """Return the static list of searchable features.

    Each entry has:
        name      - human-readable feature name
        category  - tab / section it belongs to
        keywords  - list of extra search tokens
        action    - tab name string passed to the on_action callback
    """
    return [
        # Home
        {"name": "Dashboard", "category": "Home", "keywords": ["home", "overview", "welcome", "status"], "action": "Home"},
        {"name": "System Overview", "category": "Home", "keywords": ["health", "summary", "quick actions"], "action": "Home"},

        # System Info
        {"name": "Hardware Info", "category": "System Info", "keywords": ["hardware", "dmi", "model", "specs"], "action": "System Info"},
        {"name": "OS Details", "category": "System Info", "keywords": ["fedora", "os", "version", "kernel", "release"], "action": "System Info"},

        # System Monitor (Performance + Processes tabs)
        {"name": "CPU Usage", "category": "System Monitor", "keywords": ["cpu", "load", "processor", "cores", "frequency"], "action": "Performance"},
        {"name": "Memory", "category": "System Monitor", "keywords": ["ram", "memory", "swap", "usage"], "action": "Performance"},
        {"name": "Disk I/O", "category": "System Monitor", "keywords": ["disk", "io", "read", "write", "storage"], "action": "Performance"},
        {"name": "Network Traffic", "category": "System Monitor", "keywords": [
            "network", "bandwidth", "traffic", "rx", "tx"], "action": "Performance"},
        {"name": "Processes", "category": "System Monitor", "keywords": ["process", "pid", "top", "htop", "running"], "action": "Processes"},
        {"name": "Kill Process", "category": "System Monitor", "keywords": ["kill", "terminate", "signal", "stop process"], "action": "Processes"},

        # Maintenance (Updates + Cleanup)
        {"name": "Update System", "category": "Maintenance", "keywords": ["update", "upgrade", "dnf", "system", "packages"], "action": "Updates"},
        {"name": "Update Flatpaks", "category": "Maintenance", "keywords": ["flatpak", "update", "flatpaks", "flathub"], "action": "Updates"},
        {"name": "Firmware Update", "category": "Maintenance", "keywords": ["firmware", "fwupd", "bios", "uefi"], "action": "Updates"},
        {"name": "Clean DNF Cache", "category": "Maintenance", "keywords": ["clean", "cache", "dnf", "cleanup", "disk space"], "action": "Cleanup"},
        {"name": "Vacuum Journal", "category": "Maintenance", "keywords": ["journal", "vacuum", "log", "journalctl", "systemd"], "action": "Cleanup"},
        {"name": "SSD Trim", "category": "Maintenance", "keywords": ["trim", "ssd", "fstrim", "discard", "optimize"], "action": "Cleanup"},
        {"name": "Remove Unused Packages", "category": "Maintenance", "keywords": ["autoremove", "orphan", "unused", "cleanup"], "action": "Cleanup"},
        {"name": "Rebuild RPM DB", "category": "Maintenance", "keywords": ["rpmdb", "rpm", "rebuild", "database", "repair"], "action": "Cleanup"},

        # Hardware (HP Tweaks / Hardware tab)
        {"name": "CPU Governor", "category": "Hardware", "keywords": ["cpu", "governor",
                                                                      "frequency", "scaling", "performance", "powersave"], "action": "Hardware"},
        {"name": "Power Profile", "category": "Hardware", "keywords": [
            "power", "profile", "battery", "balanced", "performance", "saver"], "action": "HP Tweaks"},
        {"name": "GPU Mode", "category": "Hardware", "keywords": ["gpu", "nvidia",
                                                                  "integrated", "hybrid", "optimus", "graphics"], "action": "Hardware"},
        {"name": "Fan Control", "category": "Hardware", "keywords": ["fan", "nbfc", "cooling", "temperature", "thermal"], "action": "HP Tweaks"},
        {"name": "Battery Limit", "category": "Hardware", "keywords": ["battery",
                                                                       "charge", "limit", "health", "80%", "threshold"], "action": "HP Tweaks"},
        {"name": "Audio Restart", "category": "Hardware", "keywords": ["audio", "pipewire", "pulseaudio", "sound", "restart"], "action": "HP Tweaks"},
        {"name": "Fingerprint", "category": "Hardware", "keywords": ["fingerprint",
                                                                     "fprintd", "biometric", "enroll", "sensor"], "action": "HP Tweaks"},

        # Software (Apps tab)
        {"name": "Install Apps", "category": "Software", "keywords": ["apps", "install", "software", "packages", "essential"], "action": "Apps"},
        {"name": "RPM Fusion", "category": "Software", "keywords": ["rpmfusion", "rpm", "fusion", "free", "nonfree", "repo"], "action": "Repos"},
        {"name": "Flathub", "category": "Software", "keywords": ["flathub", "flatpak", "remote", "repo"], "action": "Repos"},
        {"name": "Multimedia Codecs", "category": "Software", "keywords": [
            "codecs", "multimedia", "h264", "h265", "mp3", "video", "audio"], "action": "Apps"},
        {"name": "COPR Repos", "category": "Software", "keywords": ["copr", "repository", "third-party", "ppa"], "action": "Repos"},

        # Security & Privacy
        {"name": "Security Score", "category": "Security & Privacy", "keywords": [
            "security", "score", "audit", "hardening", "rating"], "action": "Security"},
        {"name": "Port Auditor", "category": "Security & Privacy", "keywords": [
            "port", "scan", "auditor", "open ports", "firewall"], "action": "Security"},
        {"name": "USB Guard", "category": "Security & Privacy", "keywords": ["usb", "guard", "badusb", "device", "block"], "action": "Security"},
        {"name": "Sandbox", "category": "Security & Privacy", "keywords": [
            "sandbox", "firejail", "bubblewrap", "isolation", "container"], "action": "Security"},
        {"name": "Firewall", "category": "Security & Privacy", "keywords": ["firewall", "firewalld", "zone", "ports", "rules"], "action": "Security"},
        {"name": "Telemetry", "category": "Security & Privacy", "keywords": [
            "telemetry", "privacy", "tracking", "analytics", "disable"], "action": "Privacy"},

        # Network
        {"name": "DNS Provider", "category": "Network", "keywords": ["dns", "nameserver",
                                                                     "cloudflare", "google", "quad9", "resolver"], "action": "Network"},
        {"name": "MAC Randomization", "category": "Network", "keywords": ["mac", "address", "random", "privacy", "network"], "action": "Network"},
        {"name": "Network Monitor", "category": "Network", "keywords": ["network",
                                                                        "monitor", "bandwidth", "traffic", "connection"], "action": "Network"},

        # Gaming
        {"name": "GameMode", "category": "Gaming", "keywords": ["gamemode", "game", "mode", "performance", "feral"], "action": "Gaming"},
        {"name": "MangoHud", "category": "Gaming", "keywords": ["mangohud", "fps", "overlay", "monitoring", "benchmark"], "action": "Gaming"},
        {"name": "Proton", "category": "Gaming", "keywords": ["proton", "steam", "compatibility", "windows", "wine"], "action": "Gaming"},
        {"name": "Wine", "category": "Gaming", "keywords": ["wine", "windows", "compatibility", "prefix"], "action": "Gaming"},
        {"name": "Shader Cache", "category": "Gaming", "keywords": ["shader", "cache", "compile", "vulkan", "mesa"], "action": "Gaming"},
        {"name": "Steam", "category": "Gaming", "keywords": ["steam", "valve", "store", "gaming", "launcher"], "action": "Gaming"},

        # Desktop (Director + Theming)
        {"name": "Window Manager", "category": "Desktop", "keywords": ["window", "manager", "kwin", "mutter", "compositor"], "action": "Director"},
        {"name": "Tiling Presets", "category": "Desktop", "keywords": [
            "tiling", "layout", "preset", "grid", "snap", "quarter"], "action": "Director"},
        {"name": "Theming", "category": "Desktop", "keywords": ["theme", "gtk", "qt", "dark", "light", "catppuccin", "adwaita"], "action": "Theming"},
        {"name": "Icons", "category": "Desktop", "keywords": ["icons", "icon theme", "papirus", "adwaita"], "action": "Theming"},
        {"name": "Fonts", "category": "Desktop", "keywords": ["fonts", "font", "nerd", "fira", "jetbrains", "typography"], "action": "Theming"},

        # Development (Containers + Developer)
        {"name": "Containers", "category": "Development", "keywords": ["container", "podman", "docker", "oci", "image"], "action": "Containers"},
        {"name": "Distrobox", "category": "Development", "keywords": ["distrobox",
                                                                      "toolbox", "container", "dev", "environment"], "action": "Containers"},
        {"name": "Podman", "category": "Development", "keywords": ["podman", "container", "pod", "compose", "runtime"], "action": "Containers"},
        {"name": "VS Code", "category": "Development", "keywords": ["vscode", "code", "editor", "ide", "microsoft"], "action": "Developer"},
        {"name": "Developer Tools", "category": "Development", "keywords": [
            "developer", "tools", "git", "gcc", "make", "build", "sdk"], "action": "Developer"},

        # AI Lab
        {"name": "Ollama", "category": "AI Lab", "keywords": ["ollama", "llm", "local", "ai", "model", "inference"], "action": "AI Lab"},
        {"name": "AI Models", "category": "AI Lab", "keywords": ["model", "llama", "mistral", "download", "ai", "weights"], "action": "AI Lab"},
        {"name": "Chat", "category": "AI Lab", "keywords": ["chat", "conversation", "ai", "assistant", "prompt"], "action": "AI Lab"},

        # Automation (Scheduler + Replicator + Presets/Marketplace)
        {"name": "Scheduler", "category": "Automation", "keywords": ["schedule", "timer", "cron", "systemd", "task"], "action": "Scheduler"},
        {"name": "Cron Jobs", "category": "Automation", "keywords": ["cron", "job", "periodic", "timer", "automated"], "action": "Scheduler"},
        {"name": "Replicator", "category": "Automation", "keywords": ["replicator",
                                                                      "export", "import", "backup", "iac", "ansible"], "action": "Replicator"},
        {"name": "Ansible Export", "category": "Automation", "keywords": [
            "ansible", "playbook", "export", "automation", "yaml"], "action": "Replicator"},

        # Community (Presets + Marketplace)
        {"name": "Presets", "category": "Community", "keywords": ["preset", "profile", "configuration", "share", "community"], "action": "Presets"},
        {"name": "Marketplace", "category": "Community", "keywords": ["marketplace",
                                                                      "community", "share", "download", "preset"], "action": "Marketplace"},

        # Diagnostics (Watchtower + Boot)
        {"name": "Watchtower", "category": "Diagnostics", "keywords": [
            "watchtower", "diagnostic", "health", "check", "doctor"], "action": "Watchtower"},
        {"name": "Boot Analysis", "category": "Diagnostics", "keywords": ["boot", "startup", "systemd-analyze", "blame", "time"], "action": "Boot"},
        {"name": "Kernel Params", "category": "Diagnostics", "keywords": ["kernel", "parameter", "cmdline", "grub", "boot"], "action": "Boot"},
    ]


# -----------------------------------------------------------------------
# Command Palette dialog
# -----------------------------------------------------------------------

class CommandPalette(QDialog):
    """Fast, fuzzy-search command palette triggered via Ctrl+K."""

    def __init__(
        self,
        on_action: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._on_action = on_action
        self._registry = _build_feature_registry()
        self._visible_entries: list[dict] = []

        self._setup_ui()
        self._populate_results("")  # show all initially

    # -- UI setup -------------------------------------------------------

    def _setup_ui(self):
        self.setWindowTitle(self.tr("Command Palette"))
        self.setFixedSize(600, 400)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Popup
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Dark overlay style
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0e14;
                border: 1px solid #2d3348;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            self.tr("Search features... (Ctrl+K)")
        )
        input_font = QFont()
        input_font.setPointSize(14)
        self._search_input.setFont(input_font)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1c2030;
                color: #e6edf3;
                border: 1px solid #5c6578;
                border-radius: 8px;
                padding: 10px 14px;
                selection-background-color: #39c5cf;
            }
            QLineEdit:focus {
                border: 1px solid #39c5cf;
            }
        """)
        self._search_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._search_input)

        # Results count hint
        self._lbl_hint = QLabel()
        self._lbl_hint.setStyleSheet("color: #6c7086; font-size: 11px; padding-left: 4px;")
        layout.addWidget(self._lbl_hint)

        # Results list
        self._results_list = QListWidget()
        self._results_list.setStyleSheet("""
            QListWidget {
                background-color: #0b0e14;
                color: #e6edf3;
                border: none;
                outline: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin: 1px 0px;
            }
            QListWidget::item:selected {
                background-color: #1c2030;
                color: #39c5cf;
            }
            QListWidget::item:hover {
                background-color: #2a2b3d;
            }
        """)
        self._results_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._results_list.itemActivated.connect(self._activate_item)
        self._results_list.itemClicked.connect(self._activate_item)
        layout.addWidget(self._results_list, 1)

        # Footer hint
        footer = QLabel(
            self.tr("\u2191\u2193 Navigate    \u23ce Enter    Esc Close")
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #5c6578; font-size: 10px; padding-top: 2px;")
        layout.addWidget(footer)

        # Center on parent
        if self.parent():
            parent_geom = self.parent().geometry()
            x = parent_geom.x() + (parent_geom.width() - self.width()) // 2
            y = parent_geom.y() + (parent_geom.height() - self.height()) // 3
            self.move(x, y)

    # -- Search / filter ------------------------------------------------

    def _on_text_changed(self, text: str):
        self._populate_results(text.strip())

    def _populate_results(self, query: str):
        """Filter the registry and update the list widget."""
        self._results_list.clear()
        self._visible_entries.clear()

        if not query:
            filtered = self._registry[:_MAX_RESULTS]
        else:
            query_lower = query.lower()
            scored: list[tuple[int, dict]] = []
            for entry in self._registry:
                score = self._match_score(entry, query_lower)
                if score > 0:
                    scored.append((score, entry))
            scored.sort(key=lambda t: t[0], reverse=True)
            filtered = [entry for _, entry in scored[:_MAX_RESULTS]]

        for entry in filtered:
            display_text = f"{entry['category']}  \u203a  {entry['name']}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._results_list.addItem(item)
            self._visible_entries.append(entry)

        # Select first result
        if self._results_list.count() > 0:
            self._results_list.setCurrentRow(0)

        # Update hint
        total_matches = len(filtered)
        if not query:
            self._lbl_hint.setText(
                self.tr("Showing {n} of {total} features").format(
                    n=total_matches, total=len(self._registry)
                )
            )
        elif total_matches == 0:
            self._lbl_hint.setText(self.tr("No results found"))
        else:
            self._lbl_hint.setText(
                self.tr("{n} result(s)").format(n=total_matches)
            )

    @staticmethod
    def _match_score(entry: dict, query_lower: str) -> int:
        """Return a relevance score (0 = no match, higher = better).

        Scoring rules:
          - Exact match on name start     -> 100
          - Substring in name             ->  80
          - Exact match on category start ->  60
          - Substring in category         ->  40
          - Substring in any keyword      ->  30
          - No match                      ->   0
        """
        name_lower = entry["name"].lower()
        cat_lower = entry["category"].lower()

        if name_lower.startswith(query_lower):
            return 100
        if query_lower in name_lower:
            return 80
        if cat_lower.startswith(query_lower):
            return 60
        if query_lower in cat_lower:
            return 40
        for kw in entry.get("keywords", []):
            if query_lower in kw.lower():
                return 30
        return 0

    # -- Activation -----------------------------------------------------

    def _activate_item(self, item: QListWidgetItem):
        """Trigger the on_action callback for the selected feature."""
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry and callable(self._on_action):
            tab_name = entry.get("action", "")
            if tab_name:
                logger.info(
                    "Command palette: switching to '%s' (feature: %s)",
                    tab_name,
                    entry.get("name", ""),
                )
                self._on_action(tab_name)
        self.accept()

    # -- Key handling ---------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        """Handle Up/Down arrows, Enter, and Escape."""
        key = event.key()

        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current = self._results_list.currentItem()
            if current:
                self._activate_item(current)
            return

        if key == Qt.Key.Key_Down:
            row = self._results_list.currentRow()
            if row < self._results_list.count() - 1:
                self._results_list.setCurrentRow(row + 1)
            return

        if key == Qt.Key.Key_Up:
            row = self._results_list.currentRow()
            if row > 0:
                self._results_list.setCurrentRow(row - 1)
            return

        # Anything else goes to the search input
        super().keyPressEvent(event)
