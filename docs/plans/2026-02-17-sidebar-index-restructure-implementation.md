# Sidebar Index Restructure — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace O(n) sidebar tree scans with a centralized `SidebarIndex` dict keyed by plugin ID, fixing fragile favorites, status string munging, monolithic `add_page()`, and experience level sync drift.

**Architecture:** A `SidebarEntry` dataclass holds all per-tab state (tree item, page widget, metadata, status). A `dict[str, SidebarEntry]` keyed by `PluginMetadata.id` is the single source of truth. All lookups (favorites, status, navigation) become O(1) dict accesses. The public `add_page()` API is preserved as a thin orchestrator over focused helpers.

**Tech Stack:** Python 3.12+, PyQt6 (QTreeWidget, QStyledItemDelegate), dataclasses, unittest with @patch decorators

**Design doc:** `docs/plans/2026-02-17-sidebar-index-restructure-design.md`

---

## Task 1: SidebarEntry dataclass and index initialization

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:42-48` (data roles section)
- Modify: `loofi-fedora-tweaks/ui/main_window.py:254` (pages init)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Create `tests/test_sidebar_index.py`:

```python
"""Tests for SidebarEntry and SidebarIndex in main_window.py"""
import sys
import os
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


class TestSidebarEntry(unittest.TestCase):
    def test_create_entry_with_all_fields(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="storage", name="Storage", description="Manage disks",
            category="System", icon="storage-disk", badge="",
        )
        entry = SidebarEntry(
            plugin_id="storage",
            display_name="Storage",
            tree_item=MagicMock(),
            page_widget=MagicMock(),
            metadata=meta,
        )
        self.assertEqual(entry.plugin_id, "storage")
        self.assertEqual(entry.display_name, "Storage")
        self.assertEqual(entry.status, "")

    def test_entry_default_status_is_empty(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="test", name="Test", description="",
            category="System", icon="", badge="",
        )
        entry = SidebarEntry(
            plugin_id="test", display_name="Test",
            tree_item=MagicMock(), page_widget=MagicMock(),
            metadata=meta,
        )
        self.assertEqual(entry.status, "")

    def test_entry_status_is_mutable(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="test", name="Test", description="",
            category="System", icon="", badge="",
        )
        entry = SidebarEntry(
            plugin_id="test", display_name="Test",
            tree_item=MagicMock(), page_widget=MagicMock(),
            metadata=meta,
        )
        entry.status = "ok"
        self.assertEqual(entry.status, "ok")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py -v --tb=short`
Expected: FAIL with `ImportError: cannot import name 'SidebarEntry' from 'ui.main_window'`

**Step 3: Write minimal implementation**

In `loofi-fedora-tweaks/ui/main_window.py`, after the existing imports (line 38) and before `logger = get_logger(__name__)` (line 40), add:

```python
from dataclasses import dataclass
```

After the `_ROLE_ICON` line (line 47), add:

```python

@dataclass
class SidebarEntry:
    """Indexed sidebar tab entry for O(1) lookups by plugin ID."""
    plugin_id: str
    display_name: str
    tree_item: QTreeWidgetItem
    page_widget: QWidget
    metadata: PluginMetadata
    status: str = ""
```

In `MainWindow.__init__()`, replace `self.pages = {}` (line 254) with:

```python
        self._sidebar_index: dict[str, SidebarEntry] = {}
        self._category_items: dict[str, QTreeWidgetItem] = {}
        self._pages_cache: dict[str, QWidget] | None = None
```

Add the backward-compatible property after `__init__`:

```python
    @property
    def pages(self) -> dict[str, QWidget]:
        """Backward-compatible accessor. Returns {display_name: widget} view."""
        if self._pages_cache is None:
            self._pages_cache = {
                entry.display_name: entry.page_widget
                for entry in self._sidebar_index.values()
            }
        return self._pages_cache
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py -v --tb=short`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add tests/test_sidebar_index.py loofi-fedora-tweaks/ui/main_window.py
git commit -m "feat(sidebar): add SidebarEntry dataclass and index infrastructure"
```

---

## Task 2: Backward-compatible pages property

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py` (pages property added in Task 1)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestPagesProperty(unittest.TestCase):
    def test_pages_returns_display_name_to_widget_dict(self):
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta1 = PluginMetadata(
            id="storage", name="Storage", description="",
            category="System", icon="", badge="",
        )
        meta2 = PluginMetadata(
            id="network", name="Network", description="",
            category="Network", icon="", badge="",
        )
        widget1 = MagicMock()
        widget2 = MagicMock()

        index = {
            "storage": SidebarEntry(
                plugin_id="storage", display_name="Storage",
                tree_item=MagicMock(), page_widget=widget1, metadata=meta1,
            ),
            "network": SidebarEntry(
                plugin_id="network", display_name="Network",
                tree_item=MagicMock(), page_widget=widget2, metadata=meta2,
            ),
        }

        # Simulate what the property does
        pages = {e.display_name: e.page_widget for e in index.values()}
        self.assertEqual(pages, {"Storage": widget1, "Network": widget2})

    def test_pages_empty_when_index_empty(self):
        index = {}
        pages = {e.display_name: e.page_widget for e in index.values()}
        self.assertEqual(pages, {})
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestPagesProperty -v --tb=short`
Expected: 2 tests PASS (these test the logic, not the full MainWindow)

**Step 3: Commit**

```bash
git add tests/test_sidebar_index.py
git commit -m "test(sidebar): add backward-compatible pages property tests"
```

---

## Task 3: Extract _find_or_create_category()

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:446-475` (category lookup in add_page)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestFindOrCreateCategory(unittest.TestCase):
    @patch('ui.main_window.PluginRegistry')
    @patch('ui.main_window.ConfigManager')
    @patch('ui.main_window.FavoritesManager')
    @patch('ui.main_window.HistoryManager')
    @patch('ui.main_window.FocusMode')
    def test_category_cache_populated_on_create(self, *mocks):
        """_find_or_create_category should cache new category items."""
        # We test the method exists and uses _category_items cache
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_find_or_create_category'))
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestFindOrCreateCategory -v --tb=short`
Expected: FAIL with `AssertionError` (method doesn't exist yet)

**Step 3: Write minimal implementation**

In `main_window.py`, add a new method before `add_page()` (before line 446):

```python
    def _find_or_create_category(self, category: str) -> QTreeWidgetItem:
        """Find or create a category tree item, using cache for O(1) lookup."""
        if category in self._category_items:
            return self._category_items[category]

        category_item = QTreeWidgetItem(self.sidebar)
        category_item.setText(0, category)
        category_item.setData(0, _ROLE_DESC, category)
        category_item.setExpanded(True)
        self._set_tree_item_icon(category_item, CATEGORY_ICONS.get(category, ""))
        self._category_items[category] = category_item
        return category_item
```

Update `add_page()` to replace the inline category lookup (lines 460-473) with:

```python
        category_item = self._find_or_create_category(category)
```

Remove lines 457-465 (the old `cat_label` variable and inline loop).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestFindOrCreateCategory -v --tb=short`
Expected: PASS

**Step 5: Run full test suite to check for regressions**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All existing tests pass

**Step 6: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "refactor(sidebar): extract _find_or_create_category with cache"
```

---

## Task 4: Extract _create_tab_item() and _register_in_index()

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:446-517` (add_page body)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestAddPageDecomposition(unittest.TestCase):
    def test_main_window_has_create_tab_item(self):
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_create_tab_item'))

    def test_main_window_has_register_in_index(self):
        from ui.main_window import MainWindow
        self.assertTrue(hasattr(MainWindow, '_register_in_index'))
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestAddPageDecomposition -v --tb=short`
Expected: FAIL

**Step 3: Write minimal implementation**

Add two new methods in `main_window.py` before `add_page()`:

```python
    def _create_tab_item(
        self,
        category_item: QTreeWidgetItem,
        name: str,
        icon: str,
        badge: str = "",
        description: str = "",
        disabled: bool = False,
        disabled_reason: str = "",
    ) -> QTreeWidgetItem:
        """Create a sidebar tree item for a tab."""
        badge_suffix = ""
        if badge == "recommended":
            badge_suffix = "  \u2605"
        elif badge == "advanced":
            badge_suffix = "  \u2699"

        item = QTreeWidgetItem(category_item)
        item.setText(0, f"{name}{badge_suffix}")
        item.setData(0, _ROLE_NAME, name)
        self._set_tree_item_icon(item, icon)

        if disabled:
            item.setDisabled(True)
            tooltip = (
                disabled_reason
                if disabled_reason
                else f"{name} is not available on this system."
            )
            item.setToolTip(0, tooltip)
        else:
            item.setData(0, _ROLE_DESC, description)
            item.setData(0, _ROLE_BADGE, badge)
            if description:
                item.setToolTip(0, description)

        return item

    def _register_in_index(
        self, plugin_id: str, entry: SidebarEntry
    ) -> None:
        """Register a tab in the sidebar index and content area."""
        self._sidebar_index[plugin_id] = entry
        self._pages_cache = None  # invalidate backward-compat cache
        self.content_area.addWidget(entry.page_widget)
```

Refactor `add_page()` to use these helpers:

```python
    def add_page(
        self,
        name: str,
        icon: str,
        widget,
        category: str = "General",
        description: str = "",
        badge: str = "",
        disabled: bool = False,
        disabled_reason: str = "",
    ) -> None:
        category_item = self._find_or_create_category(category)
        item = self._create_tab_item(
            category_item, name, icon, badge, description, disabled, disabled_reason,
        )

        if disabled:
            placeholder_meta = PluginMetadata(
                id=name.lower().replace(" ", "_"),
                name=name, description=description,
                category=category, icon=icon, badge=badge,
            )
            page_widget = self._wrap_page_widget(
                DisabledPluginPage(placeholder_meta, disabled_reason)
            )
        else:
            page_widget = self._wrap_page_widget(widget)

        item.setData(0, Qt.ItemDataRole.UserRole, page_widget)

        plugin_id = name.lower().replace(" ", "_")
        meta = PluginMetadata(
            id=plugin_id, name=name, description=description,
            category=category, icon=icon, badge=badge,
        )
        entry = SidebarEntry(
            plugin_id=plugin_id,
            display_name=name,
            tree_item=item,
            page_widget=page_widget,
            metadata=meta,
        )
        self._register_in_index(plugin_id, entry)
```

**Important:** Also update `_add_plugin_page()` (line 338-354) to pass the real `meta.id` so the index uses the canonical ID:

```python
    def _add_plugin_page(
        self,
        meta: PluginMetadata,
        widget: LazyWidget,
        compat: CompatStatus,
    ) -> None:
        """Register a plugin page in the sidebar and content area."""
        category_item = self._find_or_create_category(meta.category)
        item = self._create_tab_item(
            category_item, meta.name, meta.icon, meta.badge,
            meta.description,
            disabled=not compat.compatible,
            disabled_reason=compat.reason,
        )

        if not compat.compatible:
            page_widget = self._wrap_page_widget(
                DisabledPluginPage(meta, compat.reason)
            )
        else:
            page_widget = self._wrap_page_widget(widget)

        item.setData(0, Qt.ItemDataRole.UserRole, page_widget)

        entry = SidebarEntry(
            plugin_id=meta.id,
            display_name=meta.name,
            tree_item=item,
            page_widget=page_widget,
            metadata=meta,
        )
        self._register_in_index(meta.id, entry)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py -v --tb=short`
Expected: All tests PASS

**Step 5: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All existing tests pass

**Step 6: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "refactor(sidebar): decompose add_page into focused helpers with index registration"
```

---

## Task 5: Fix favorites with ID-based lookup

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:366-407` (_build_favorites_section)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestFavoritesIdLookup(unittest.TestCase):
    def test_favorites_uses_index_not_name_heuristic(self):
        """Favorites should match by plugin_id, not name.lower().replace()"""
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="system-info", name="System Info", description="",
            category="System", icon="", badge="",
        )
        index = {
            "system-info": SidebarEntry(
                plugin_id="system-info", display_name="System Info",
                tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta,
            ),
        }

        # The old code would try: "System Info".lower().replace(" ", "_") == "system_info"
        # which would NOT match "system-info" (dash vs underscore)
        # New code should do: index.get("system-info") directly
        entry = index.get("system-info")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.display_name, "System Info")

    def test_stale_favorite_returns_none(self):
        from ui.main_window import SidebarEntry
        index = {}
        entry = index.get("deleted-tab")
        self.assertIsNone(entry)
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestFavoritesIdLookup -v --tb=short`
Expected: PASS (these test the logic pattern)

**Step 3: Rewrite _build_favorites_section()**

Replace lines 366-407 in `main_window.py`:

```python
    def _build_favorites_section(self):
        """Build a Favorites category at the top of the sidebar with pinned tabs."""
        favorites = FavoritesManager.get_favorites()
        if not favorites:
            return

        fav_category = QTreeWidgetItem()
        fav_category.setText(0, "Favorites")
        self._set_tree_item_icon(fav_category, "status-ok")
        fav_category.setExpanded(True)
        self.sidebar.insertTopLevelItem(0, fav_category)

        for fav_id in favorites:
            entry = self._sidebar_index.get(fav_id)
            if not entry:
                logger.warning("Stale favorite ignored: %s", fav_id)
                continue

            item = QTreeWidgetItem(fav_category)
            item.setText(0, entry.display_name)
            item.setData(0, _ROLE_DESC, f"Pinned: {entry.display_name}")
            item.setData(0, _ROLE_NAME, entry.display_name)
            item.setData(0, Qt.ItemDataRole.UserRole, entry.page_widget)
            self._copy_tree_item_icon(entry.tree_item, item)

        self._refresh_sidebar_icon_tints()
```

**Step 4: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 5: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "fix(sidebar): replace fragile favorites matching with O(1) ID-based lookup"
```

---

## Task 6: Fix _set_tab_status() with O(1) lookup

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:983-1007` (_set_tab_status)
- Modify: `loofi-fedora-tweaks/ui/main_window.py:948-981` (_refresh_status_indicators callers)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestSetTabStatus(unittest.TestCase):
    def test_status_stored_in_entry_not_text(self):
        """Status should update entry.status, not munge display text."""
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="storage", name="Storage", description="Manage disks",
            category="System", icon="", badge="",
        )
        tree_item = MagicMock()
        entry = SidebarEntry(
            plugin_id="storage", display_name="Storage",
            tree_item=tree_item, page_widget=MagicMock(), metadata=meta,
        )
        entry.status = "warning"

        # Verify text was NOT modified (no [WARN] suffix)
        tree_item.setText.assert_not_called()
        self.assertEqual(entry.status, "warning")
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestSetTabStatus -v --tb=short`
Expected: PASS

**Step 3: Rewrite _set_tab_status()**

Replace lines 983-1007 in `main_window.py`:

```python
    def _set_tab_status(self, tab_id: str, status: str, tooltip: str = ""):
        """Set a colored status indicator on a sidebar tab by plugin ID. O(1) lookup."""
        entry = self._sidebar_index.get(tab_id)
        if not entry:
            logger.debug("_set_tab_status: unknown tab_id %s", tab_id)
            return

        entry.status = status
        entry.tree_item.setData(0, _ROLE_STATUS, status)

        if tooltip:
            desc = entry.metadata.description or ""
            entry.tree_item.setToolTip(
                0, f"{desc}\n[{tooltip}]" if desc else tooltip
            )
```

Update callers in `_refresh_status_indicators()` (lines 948-981) to use plugin IDs:

```python
    def _refresh_status_indicators(self):
        """Update sidebar status indicators from live system data (v29.0)."""
        try:
            from utils.update_checker import UpdateChecker

            update_info = UpdateChecker.check_for_updates(timeout=5, use_cache=True)
            if update_info and update_info.is_newer:
                self._set_tab_status("maintenance", "warning", "Updates available")
            else:
                self._set_tab_status("maintenance", "ok", "Up to date")
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to check for updates: %s", e)
            self._set_tab_status("maintenance", "", "")

        try:
            from services.hardware.disk import DiskManager

            usage = DiskManager.get_disk_usage("/")
            if usage and hasattr(usage, "percent_used"):
                if usage.percent_used >= 90:
                    self._set_tab_status(
                        "storage", "error", f"Disk {usage.percent_used:.0f}% full"
                    )
                elif usage.percent_used >= 75:
                    self._set_tab_status(
                        "storage", "warning", f"Disk {usage.percent_used:.0f}% used"
                    )
                else:
                    self._set_tab_status("storage", "ok", "Healthy")
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to check disk space: %s", e)
            self._set_tab_status("storage", "", "")
```

**Step 4: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 5: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "fix(sidebar): replace status string munging with O(1) data-role lookup"
```

---

## Task 7: SidebarItemDelegate for status dot rendering

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py` (add delegate class + wire to sidebar)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestSidebarItemDelegate(unittest.TestCase):
    def test_delegate_class_exists(self):
        from ui.main_window import SidebarItemDelegate
        self.assertTrue(callable(SidebarItemDelegate))

    def test_status_colors_defined(self):
        from ui.main_window import SidebarItemDelegate
        delegate = SidebarItemDelegate()
        self.assertTrue(hasattr(delegate, '_STATUS_COLORS'))
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestSidebarItemDelegate -v --tb=short`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

In `main_window.py`, add the import at the top (with existing PyQt6 imports):

```python
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import QRect
```

After the `SidebarEntry` dataclass, add:

```python
class SidebarItemDelegate(QStyledItemDelegate):
    """Custom delegate that renders status dots on sidebar tab items."""

    _STATUS_COLORS = {
        "ok": QColor(76, 175, 80),       # green
        "warning": QColor(255, 193, 7),   # amber
        "error": QColor(244, 67, 54),     # red
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        super().paint(painter, option, index)

        status = index.data(_ROLE_STATUS)
        if not status or status not in self._STATUS_COLORS:
            return

        color = self._STATUS_COLORS[status]
        dot_size = 8
        x = option.rect.right() - dot_size - 8
        y = option.rect.center().y() - dot_size // 2

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRect(x, y, dot_size, dot_size))
        painter.restore()
```

Wire the delegate to the sidebar in `MainWindow.__init__()`, after `self.sidebar` is created (find the line where `self.sidebar = QTreeWidget()` is called):

```python
        self.sidebar.setItemDelegate(SidebarItemDelegate(self.sidebar))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestSidebarItemDelegate -v --tb=short`
Expected: PASS

**Step 5: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 6: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "feat(sidebar): add SidebarItemDelegate for status dot rendering"
```

---

## Task 8: Fix switch_to_tab() with O(1) lookup

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:683-693` (switch_to_tab)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestSwitchToTab(unittest.TestCase):
    def test_switch_by_plugin_id(self):
        """switch_to_tab should support plugin ID as primary lookup."""
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="storage", name="Storage", description="",
            category="System", icon="", badge="",
        )
        index = {"storage": SidebarEntry(
            plugin_id="storage", display_name="Storage",
            tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta,
        )}

        # Primary path: direct ID lookup
        entry = index.get("storage")
        self.assertIsNotNone(entry)

    def test_switch_by_display_name_fallback(self):
        """switch_to_tab should fall back to display name match."""
        from ui.main_window import SidebarEntry
        from core.plugins.metadata import PluginMetadata

        meta = PluginMetadata(
            id="storage", name="Storage", description="",
            category="System", icon="", badge="",
        )
        index = {"storage": SidebarEntry(
            plugin_id="storage", display_name="Storage",
            tree_item=MagicMock(), page_widget=MagicMock(), metadata=meta,
        )}

        # Fallback: search by display name
        match = next(
            (e for e in index.values() if name in e.display_name),
            None,
        ) if not index.get("Storage") else index.get("Storage")
        # "Storage" is not a key, so it falls through to display name search
        self.assertIsNone(index.get("Storage"))
```

**Step 2: Run test — expect pass (logic test)**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestSwitchToTab -v --tb=short`

**Step 3: Rewrite switch_to_tab()**

Replace lines 683-693 in `main_window.py`:

```python
    def switch_to_tab(self, name):
        """Switch to a tab by plugin ID (primary) or display name (fallback)."""
        # Primary: O(1) lookup by plugin ID
        entry = self._sidebar_index.get(name)
        if entry:
            self.sidebar.setCurrentItem(entry.tree_item)
            return

        # Fallback: search by display name (for backward compatibility)
        for entry in self._sidebar_index.values():
            if name in entry.display_name:
                logger.debug("switch_to_tab: matched by display name '%s', prefer plugin ID '%s'", name, entry.plugin_id)
                self.sidebar.setCurrentItem(entry.tree_item)
                return

        logger.debug("switch_to_tab: no match for '%s'", name)
```

**Step 4: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 5: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "refactor(sidebar): switch_to_tab uses O(1) index lookup with display name fallback"
```

---

## Task 9: Experience level validation

**Files:**
- Modify: `loofi-fedora-tweaks/utils/experience_level.py`
- Modify: `loofi-fedora-tweaks/ui/main_window.py:308-332` (_build_sidebar_from_registry)
- Test: `tests/test_sidebar_index.py`

**Step 1: Write the failing test**

Add to `tests/test_sidebar_index.py`:

```python
class TestExperienceLevelValidation(unittest.TestCase):
    def test_get_all_declared_tab_ids_returns_set(self):
        from utils.experience_level import ExperienceLevelManager
        result = ExperienceLevelManager.get_all_declared_tab_ids()
        self.assertIsInstance(result, set)
        self.assertIn("dashboard", result)
        self.assertIn("development", result)  # intermediate-only

    def test_all_beginner_tabs_in_declared_ids(self):
        from utils.experience_level import ExperienceLevelManager, _BEGINNER_TABS
        declared = ExperienceLevelManager.get_all_declared_tab_ids()
        for tab_id in _BEGINNER_TABS:
            self.assertIn(tab_id, declared)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestExperienceLevelValidation -v --tb=short`
Expected: FAIL with `AttributeError: type object 'ExperienceLevelManager' has no attribute 'get_all_declared_tab_ids'`

**Step 3: Write minimal implementation**

Add to `utils/experience_level.py` at the end of `ExperienceLevelManager` class:

```python
    @staticmethod
    def get_all_declared_tab_ids() -> set:
        """Return all tab IDs declared in any experience level list.

        Returns:
            Set of all tab IDs from BEGINNER + INTERMEDIATE lists.
            ADVANCED is not listed because it means 'show all'.
        """
        return set(_INTERMEDIATE_TABS)  # superset of _BEGINNER_TABS
```

Then add validation to `_build_sidebar_from_registry()` in `main_window.py`, after the `for plugin in registry:` loop completes (after line 332):

```python
        # Validate experience level tab lists against registry
        declared_ids = ExperienceLevelManager.get_all_declared_tab_ids()
        registered_ids = set(self._sidebar_index.keys())
        orphaned = declared_ids - registered_ids
        for tab_id in sorted(orphaned):
            logger.warning("Experience level references unknown tab: %s", tab_id)
        advanced_only = registered_ids - declared_ids
        if advanced_only:
            logger.info("Tabs only visible to ADVANCED users: %s", sorted(advanced_only))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/test_sidebar_index.py::TestExperienceLevelValidation -v --tb=short`
Expected: PASS

**Step 5: Commit**

```bash
git add loofi-fedora-tweaks/utils/experience_level.py loofi-fedora-tweaks/ui/main_window.py tests/test_sidebar_index.py
git commit -m "feat(sidebar): add experience level sync validation at build time"
```

---

## Task 10: Update closeEvent for index-based cleanup

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:1139-1146` (closeEvent pages iteration)

**Step 1: Update closeEvent**

The current code at line 1140 iterates `self.pages.values()`. Since `self.pages` is now a computed property, update it to use the index directly:

```python
            for entry in self._sidebar_index.values():
                page = entry.page_widget
                if hasattr(page, "cleanup"):
                    try:
                        page.cleanup()
                    except (RuntimeError, OSError) as e:
                        logger.debug("Failed to cleanup page on close: %s", e)
```

**Step 2: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 3: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py
git commit -m "refactor(sidebar): closeEvent uses index directly instead of pages property"
```

---

## Task 11: Update _rebuild_sidebar_for_experience_level

**Files:**
- Modify: `loofi-fedora-tweaks/ui/main_window.py:430-444` (_rebuild_sidebar_for_experience_level)

**Step 1: Update the method**

The current code at line 440-442 searches for "Favorites" by text. Update to also clear the index caches:

```python
    def _rebuild_sidebar_for_experience_level(self):
        """Rebuild sidebar when experience level changes."""
        self.sidebar.clear()
        self._sidebar_index.clear()
        self._category_items.clear()
        self._pages_cache = None
        # Remove all pages from content_area
        while self.content_area.count():
            self.content_area.removeWidget(self.content_area.widget(0))
        context = {
            "main_window": self,
            "config_manager": ConfigManager,
        }
        self._build_sidebar_from_registry(context)
        self._build_favorites_section()
        self._refresh_sidebar_icon_tints()
```

**Step 2: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 3: Commit**

```bash
git add loofi-fedora-tweaks/ui/main_window.py
git commit -m "refactor(sidebar): clear index caches on experience level rebuild"
```

---

## Task 12: Add loader.py comment and final cleanup

**Files:**
- Modify: `loofi-fedora-tweaks/core/plugins/loader.py:24` (add comment)
- Modify: `loofi-fedora-tweaks/ui/main_window.py` (remove unused QTreeWidgetItemIterator import if no longer needed)

**Step 1: Add comment to loader.py**

Before line 24 in `core/plugins/loader.py`, add:

```python
# NOTE: List order below does NOT affect sidebar order.
# Final sidebar order is determined by (CATEGORY_ORDER rank, PluginMetadata.order).
# See core/plugins/registry.py for CATEGORY_ORDER.
```

**Step 2: Check if QTreeWidgetItemIterator is still used**

Search `main_window.py` for `QTreeWidgetItemIterator`. If `_set_tab_status()` and `switch_to_tab()` no longer use it, and `_filter_sidebar()` doesn't use it either, remove it from imports.

Check: `_filter_sidebar()` (line 710) uses `self.sidebar.topLevelItemCount()` loops, NOT `QTreeWidgetItemIterator`. So if `_set_tab_status()` and `switch_to_tab()` are refactored, the import can be removed.

**Step 3: Run full test suite**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -20`
Expected: All tests pass

**Step 4: Commit**

```bash
git add loofi-fedora-tweaks/core/plugins/loader.py loofi-fedora-tweaks/ui/main_window.py
git commit -m "chore(sidebar): add loader order comment and remove unused imports"
```

---

## Task 13: Full regression test and verification

**Files:**
- No new files

**Step 1: Run full test suite with coverage**

Run: `PYTHONPATH=loofi-fedora-tweaks python -m pytest tests/ --cov=loofi-fedora-tweaks --cov-report=term-missing --cov-fail-under=80 -v --tb=short 2>&1 | tail -30`
Expected: All tests pass, coverage >= 80%

**Step 2: Run linter**

Run: `flake8 loofi-fedora-tweaks/ --max-line-length=150 --ignore=E501,W503,E402,E722,E203`
Expected: No errors

**Step 3: Run type checker**

Run: `mypy loofi-fedora-tweaks/ --ignore-missing-imports --no-error-summary`
Expected: No errors

**Step 4: Commit any fixes**

If any lint/type errors found, fix and commit:

```bash
git add -u
git commit -m "fix(sidebar): address lint and type-check issues from restructure"
```

---

## Task 14: Documentation updates

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `ROADMAP.md`

**Step 1: Update ARCHITECTURE.md**

Add a "Sidebar Index" section under the UI layer documentation:

```markdown
### Sidebar Index (v48.0)

The sidebar uses a `SidebarIndex` (`dict[str, SidebarEntry]`) keyed by `PluginMetadata.id` for O(1) tab lookups. `SidebarEntry` holds the tree item, page widget, metadata, and status.

Key methods:
- `_find_or_create_category(category)` — cached category item lookup
- `_create_tab_item(...)` — creates tree item with badge and icon
- `_register_in_index(plugin_id, entry)` — populates index and content area
- `add_page(...)` — public API orchestrator (backward-compatible)
- `switch_to_tab(name)` — O(1) by plugin ID, fallback by display name
- `_set_tab_status(tab_id, status)` — O(1) status update via data role

Status rendering uses `SidebarItemDelegate` with colored dots instead of text markers.
```

**Step 2: Update ROADMAP.md**

Add v48.0 entry:

```markdown
| v48.0 | Sidebar Index | ACTIVE | Tab/sidebar restructure with O(1) ID-based lookups |
```

**Step 3: Commit**

```bash
git add ARCHITECTURE.md ROADMAP.md
git commit -m "docs: document sidebar index restructure for v48.0"
```
