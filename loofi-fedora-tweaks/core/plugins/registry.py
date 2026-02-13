from __future__ import annotations
from typing import Iterator
from core.plugins.interface import PluginInterface

# Explicit category ordering — controls sidebar top-to-bottom sequence.
# Lower value = higher in sidebar.  Categories not listed sort after all listed ones.
CATEGORY_ORDER: dict[str, int] = {
    "Overview": 0,
    "Manage": 1,
    "Hardware": 2,
    "Network & Security": 3,
    "Personalize": 4,
    "Developer": 5,
    "Automation": 6,
    "Health & Logs": 7,
}

# Category icons — prepended to category headers in the sidebar tree.
CATEGORY_ICONS: dict[str, str] = {
    "Overview": "📊",
    "Manage": "🔧",
    "Hardware": "🖥️",
    "Network & Security": "🌐",
    "Personalize": "🎨",
    "Developer": "🛠️",
    "Automation": "🤖",
    "Health & Logs": "📋",
}


class PluginRegistry:
    """
    Singleton registry holding all registered plugin instances.

    Tabs self-register via PluginLoader. MainWindow sources its
    sidebar entirely from this registry.
    """

    _instance: "PluginRegistry | None" = None

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInterface] = {}  # id -> plugin
        self._order: list[str] = []                      # insertion/sort order

    @classmethod
    def instance(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — for use in tests only."""
        cls._instance = None

    def register(self, plugin: PluginInterface) -> None:
        """
        Register a plugin. Raises ValueError if id is already registered.
        Preserves order by PluginMetadata.order, then insertion order.
        """
        meta = plugin.metadata()
        if meta.id in self._plugins:
            raise ValueError(f"Plugin id already registered: {meta.id!r}")
        self._plugins[meta.id] = plugin
        self._order.append(meta.id)
        self._sort_order()

    def unregister(self, plugin_id: str) -> None:
        """Remove a plugin by id. Silent no-op if not found."""
        self._plugins.pop(plugin_id, None)
        if plugin_id in self._order:
            self._order.remove(plugin_id)

    def get(self, plugin_id: str) -> PluginInterface | None:
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[PluginInterface]:
        """Return all plugins in sorted order."""
        return [self._plugins[pid] for pid in self._order if pid in self._plugins]

    def list_by_category(self, category: str) -> list[PluginInterface]:
        return [p for p in self.list_all() if p.metadata().category == category]

    def categories(self) -> list[str]:
        """Return unique categories in order of first appearance."""
        seen: list[str] = []
        for pid in self._order:
            if pid in self._plugins:
                cat = self._plugins[pid].metadata().category
                if cat not in seen:
                    seen.append(cat)
        return seen

    def _sort_order(self) -> None:
        """Re-sort _order list by (CATEGORY_ORDER rank, plugin.order, insertion)."""
        _fallback = max(CATEGORY_ORDER.values()) + 1 if CATEGORY_ORDER else 0
        self._order.sort(key=lambda pid: (
            CATEGORY_ORDER.get(self._plugins[pid].metadata().category, _fallback),
            self._plugins[pid].metadata().order,
        ))

    def __iter__(self) -> Iterator[PluginInterface]:
        return iter(self.list_all())

    def __len__(self) -> int:
        return len(self._plugins)
