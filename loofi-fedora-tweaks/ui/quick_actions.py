"""
Quick Actions Bar - Fast access to common system operations.
Part of v15.0 "Nebula".

Provides a searchable dialog with categorized quick actions for
common maintenance, security, hardware, network, and system tasks.
Actions are registered through a singleton QuickActionRegistry and
can be extended by plugins.

Integration:
    from ui.quick_actions import QuickActionsBar, QuickActionRegistry, register_default_actions

    registry = QuickActionRegistry.instance()
    register_default_actions(registry)
    dialog = QuickActionsBar(parent=main_window)
    dialog.exec()
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QWidget,
)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont

from ui.icon_pack import get_qicon


# -----------------------------------------------------------------------
# Data model
# -----------------------------------------------------------------------

@dataclass
class QuickAction:
    """A single quick action entry."""

    name: str
    category: str
    callback: Callable
    description: str
    icon: str
    keywords: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------
# Registry (singleton)
# -----------------------------------------------------------------------

class QuickActionRegistry:
    """Singleton registry holding all available quick actions."""

    _instance: Optional["QuickActionRegistry"] = None

    @classmethod
    def instance(cls) -> "QuickActionRegistry":
        """Return the global singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._actions: List[QuickAction] = []
        self._recent: List[str] = []

    # -- mutation -------------------------------------------------------

    def register(self, action: QuickAction) -> None:
        """Add an action to the registry (no duplicates by name)."""
        if not any(a.name == action.name for a in self._actions):
            self._actions.append(action)

    def unregister(self, name: str) -> None:
        """Remove an action by name."""
        self._actions = [a for a in self._actions if a.name != name]
        self._recent = [n for n in self._recent if n != name]

    # -- queries --------------------------------------------------------

    def get_all(self) -> List[QuickAction]:
        """Return all registered actions."""
        return list(self._actions)

    def get_by_category(self, category: str) -> List[QuickAction]:
        """Return actions matching *category* (case-insensitive)."""
        cat_lower = category.lower()
        return [a for a in self._actions if a.category.lower() == cat_lower]

    def search(self, query: str) -> List[QuickAction]:
        """Fuzzy-search actions by name, category, description, and keywords.

        Simple case-insensitive substring matching.  Results are ordered
        with recently-used matches first, then alphabetical by name.
        """
        if not query:
            return list(self._actions)

        q = query.lower()
        matched: List[QuickAction] = []
        for action in self._actions:
            haystack = " ".join(
                [action.name, action.category, action.description]
                + action.keywords
            ).lower()
            if q in haystack:
                matched.append(action)

        # Partition into recent and non-recent, preserving recent order
        recent_set = set(self._recent)
        recent_matches: List[QuickAction] = []
        other_matches: List[QuickAction] = []
        for action in matched:
            if action.name in recent_set:
                recent_matches.append(action)
            else:
                other_matches.append(action)

        # Sort recent matches by their position in _recent (most recent first)
        recent_order = {name: idx for idx, name in enumerate(self._recent)}
        recent_matches.sort(key=lambda a: recent_order.get(a.name, 999))
        other_matches.sort(key=lambda a: a.name.lower())

        return recent_matches + other_matches

    # -- recents --------------------------------------------------------

    def mark_used(self, name: str) -> None:
        """Move *name* to the front of the recent list (max 10)."""
        if name in self._recent:
            self._recent.remove(name)
        self._recent.insert(0, name)
        self._recent = self._recent[:10]

    def get_recent(self) -> List[QuickAction]:
        """Return actions from the recent list, ordered most-recent first."""
        action_map = {a.name: a for a in self._actions}
        return [action_map[n] for n in self._recent if n in action_map]


# -----------------------------------------------------------------------
# Quick Actions Bar dialog
# -----------------------------------------------------------------------

class QuickActionsBar(QDialog):
    """Searchable dialog for executing quick actions."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._registry = QuickActionRegistry.instance()
        self._init_ui()

    # -- UI setup -------------------------------------------------------

    def _init_ui(self) -> None:
        self.setWindowTitle(self.tr("Quick Actions"))
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            self.tr("Type to search actions...")
        )
        search_font = QFont()
        search_font.setPointSize(13)
        self._search_input.setFont(search_font)
        self._search_input.textChanged.connect(self._on_search)
        layout.addWidget(self._search_input)

        # Category filter
        self._category_combo = QComboBox()
        self._category_combo.addItem(self.tr("All Categories"))
        categories = sorted(
            {a.category for a in self._registry.get_all()}
        )
        for cat in categories:
            self._category_combo.addItem(cat)
        self._category_combo.currentTextChanged.connect(
            self._on_category_changed
        )
        layout.addWidget(self._category_combo)

        # Action list
        self._list_widget = QListWidget()
        self._list_widget.setIconSize(QSize(17, 17))
        self._list_widget.setStyleSheet("""
            QListWidget {
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 10px;
            }
        """)
        self._list_widget.itemActivated.connect(self._on_item_activated)
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list_widget, 1)

        # Status label
        self._status_label = QLabel()
        self._status_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(self._status_label)

        # Initial population
        self._populate(self._registry.get_all())

    # -- population -----------------------------------------------------

    def _populate(self, actions: List[QuickAction]) -> None:
        """Fill the list widget with *actions*."""
        self._list_widget.clear()
        for action in actions:
            item = QListWidgetItem(action.name)
            item.setToolTip(action.description)
            item.setData(Qt.ItemDataRole.UserRole, action)
            item.setIcon(get_qicon(action.icon, size=17))
            self._list_widget.addItem(item)

        if self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

        self._status_label.setText(
            self.tr("{n} action(s)").format(n=len(actions))
        )

    # -- slots ----------------------------------------------------------

    def _on_search(self, text: str) -> None:
        """Filter actions by search query, respecting category filter."""
        results = self._registry.search(text.strip())
        current_cat = self._category_combo.currentText()
        if current_cat != self.tr("All Categories"):
            results = [a for a in results if a.category == current_cat]
        self._populate(results)

    def _on_category_changed(self, category: str) -> None:
        """Filter by category, respecting current search text."""
        query = self._search_input.text().strip()
        if query:
            results = self._registry.search(query)
        else:
            results = self._registry.get_all()

        if category != self.tr("All Categories"):
            results = [a for a in results if a.category == category]
        self._populate(results)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """Execute the action stored in the list item and close."""
        action: Optional[QuickAction] = item.data(Qt.ItemDataRole.UserRole)
        if action is not None:
            self._registry.mark_used(action.name)
            action.callback()
        self.accept()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Same behaviour as activation on click."""
        self._on_item_activated(item)


# -----------------------------------------------------------------------
# Default actions
# -----------------------------------------------------------------------

def register_default_actions(registry: QuickActionRegistry, main_window=None) -> None:
    """Register the built-in set of quick actions.

    When *main_window* is provided, callbacks navigate to the relevant tab.
    Otherwise, callbacks are no-ops (for test/headless use).
    """

    def _nav(tab_name: str) -> Callable:
        """Return a callback that switches to *tab_name* via MainWindow."""
        if main_window is not None and hasattr(main_window, "switch_to_tab"):
            return lambda: main_window.switch_to_tab(tab_name)
        return lambda: tab_name

    defaults: List[QuickAction] = [
        # -- Maintenance --
        QuickAction(
            name="Update System",
            category="Maintenance",
            callback=_nav("Updates"),
            description="Run a full system update via the package manager",
            icon="update",
            keywords=["dnf", "upgrade", "packages", "rpm-ostree"],
        ),
        QuickAction(
            name="Clean DNF Cache",
            category="Maintenance",
            callback=_nav("Cleanup"),
            description="Clear the DNF package cache to free disk space",
            icon="cleanup",
            keywords=["cache", "cleanup", "disk", "space"],
        ),
        QuickAction(
            name="Trim SSD",
            category="Maintenance",
            callback=_nav("Cleanup"),
            description="Run fstrim to optimize SSD performance",
            icon="storage-disk",
            keywords=["fstrim", "ssd", "discard", "optimize"],
        ),
        QuickAction(
            name="Vacuum Journals",
            category="Maintenance",
            callback=_nav("Cleanup"),
            description="Vacuum systemd journal logs to reclaim space",
            icon="logs",
            keywords=["journal", "vacuum", "log", "journalctl", "systemd"],
        ),
        # -- Security --
        QuickAction(
            name="Run Security Scan",
            category="Security",
            callback=_nav("Security"),
            description="Perform a security audit of the system",
            icon="security-shield",
            keywords=["audit", "hardening", "scan", "security"],
        ),
        QuickAction(
            name="Check Open Ports",
            category="Security",
            callback=_nav("Security"),
            description="List all open network ports on this machine",
            icon="search",
            keywords=["port", "scan", "network", "firewall", "ss"],
        ),
        QuickAction(
            name="Toggle Firewall",
            category="Security",
            callback=_nav("Security"),
            description="Enable or disable the system firewall (firewalld)",
            icon="security-shield",
            keywords=["firewall", "firewalld", "enable", "disable"],
        ),
        # -- Hardware --
        QuickAction(
            name="Auto-Tune Performance",
            category="Hardware",
            callback=_nav("Hardware"),
            description="Apply optimized hardware-specific performance settings",
            icon="hardware-performance",
            keywords=["tune", "performance", "cpu", "governor", "turbo"],
        ),
        QuickAction(
            name="Show CPU Governor",
            category="Hardware",
            callback=_nav("Hardware"),
            description="Display the current CPU frequency scaling governor",
            icon="cpu-performance",
            keywords=["cpu", "governor", "frequency", "scaling"],
        ),
        QuickAction(
            name="Show Battery Status",
            category="Hardware",
            callback=_nav("HP Tweaks"),
            description="Show battery charge level and health information",
            icon="hardware-performance",
            keywords=["battery", "charge", "health", "power"],
        ),
        # -- Network --
        QuickAction(
            name="Show DNS Config",
            category="Network",
            callback=_nav("Network"),
            description="Display the currently configured DNS resolvers",
            icon="network-connectivity",
            keywords=["dns", "nameserver", "resolver", "resolv.conf"],
        ),
        QuickAction(
            name="Flush DNS Cache",
            category="Network",
            callback=_nav("Network"),
            description="Flush the local DNS resolver cache",
            icon="network-traffic",
            keywords=["dns", "flush", "cache", "resolved"],
        ),
        # -- System --
        QuickAction(
            name="View System Info",
            category="System",
            callback=_nav("System Info"),
            description="Show detailed hardware and OS information",
            icon="info",
            keywords=["info", "hardware", "os", "kernel", "specs"],
        ),
        QuickAction(
            name="Show Disk Usage",
            category="System",
            callback=_nav("Storage"),
            description="Display disk usage summary for all mounted volumes",
            icon="storage-disk",
            keywords=["disk", "usage", "df", "storage", "mount"],
        ),
        QuickAction(
            name="Create Snapshot",
            category="System",
            callback=_nav("Snapshots"),
            description="Create a system snapshot via Timeshift or Snapper",
            icon="logs",
            keywords=["snapshot", "timeshift", "snapper", "backup", "btrfs"],
        ),
    ]

    for action in defaults:
        registry.register(action)
