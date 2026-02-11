from __future__ import annotations
from typing import Iterator
from core.plugins.interface import PluginInterface


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
        """Re-sort _order list by (category_first_seen_index, plugin.order, insertion)."""
        # Stable sort by order field within insertion order
        self._order.sort(key=lambda pid: (
            self._plugins[pid].metadata().category,
            self._plugins[pid].metadata().order,
        ))

    def __iter__(self) -> Iterator[PluginInterface]:
        return iter(self.list_all())

    def __len__(self) -> int:
        return len(self._plugins)
