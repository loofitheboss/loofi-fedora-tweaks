"""
Main Window - v25.0 "Plugin Architecture"
26-tab layout sourced from PluginRegistry with sidebar navigation, breadcrumb, and status bar.
"""

import logging
import os
from dataclasses import dataclass, field

from core.plugins.metadata import CompatStatus, PluginMetadata
from core.plugins.registry import CATEGORY_ICONS
from PyQt6.QtCore import QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFontMetrics, QKeySequence, QPainter, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)
from utils.config_manager import ConfigManager
from utils.favorites import FavoritesManager
from utils.focus_mode import FocusMode
from utils.history import HistoryManager
from utils.log import get_logger
from utils.pulse import PulseThread, SystemPulse
from services.system import SystemManager  # noqa: F401  (re-exported for legacy callers)
from version import __version__

from core.plugins import PluginInterface, PluginRegistry
from ui.icon_pack import get_qicon, icon_tint_variant
from ui.lazy_widget import LazyWidget

logger = get_logger(__name__)

# Custom data roles for sidebar items
_ROLE_DESC = Qt.ItemDataRole.UserRole + 1  # Tab description string
_ROLE_BADGE = Qt.ItemDataRole.UserRole + 2  # "recommended" | "advanced" | ""
_ROLE_STATUS = Qt.ItemDataRole.UserRole + 3  # "ok" | "warning" | "error" | ""
_ROLE_NAME = Qt.ItemDataRole.UserRole + 4  # Raw tab name (without badges/status)
_ROLE_ICON = Qt.ItemDataRole.UserRole + 5  # Semantic icon token


@dataclass
class SidebarEntry:
    """Indexed sidebar tab entry for O(1) lookups by plugin ID."""

    plugin_id: str
    display_name: str
    tree_item: QTreeWidgetItem
    page_widget: QWidget
    metadata: PluginMetadata
    status: str = field(default="")


class SidebarItemDelegate(QStyledItemDelegate):
    """Custom delegate that renders status dots on sidebar tab items."""

    _STATUS_COLORS = {
        "ok": QColor(76, 175, 80),       # green
        "warning": QColor(255, 193, 7),   # amber
        "error": QColor(244, 67, 54),     # red
    }

    def paint(self, painter: "QPainter | None", option: QStyleOptionViewItem, index) -> None:
        """Paint the item, adding a colored status dot on the right when status is set."""
        super().paint(painter, option, index)

        if painter is None:
            return

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


class DisabledPluginPage(QWidget):
    """Shown in the content area for plugins that are incompatible with the current system."""

    def __init__(self, meta: PluginMetadata, reason: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(
            f"{meta.name} is not available on this system.\n\n{reason}"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("disabledPluginLabel")
        layout.addWidget(label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize logger for this class
        self.logger = logging.getLogger(__name__)

        # Check frameless mode feature flag
        frameless_enabled = self._get_frameless_mode_flag()

        if frameless_enabled:
            self.logger.warning(
                "Frameless mode requested but not yet fully implemented. "
                "Using native title bar. Set ui.frameless_mode=false or "
                "unset LOOFI_FRAMELESS to disable this warning."
            )
            # Stub: future frameless implementation would go here
            # For now, keep native title bar even when flag is True

        # Keep native title-bar decorations enabled.
        # This avoids KDE/Wayland/X11 edge-cases where client content can
        # appear to bleed into the top chrome when frameless/custom hints are used.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
        self.setWindowFlag(Qt.WindowType.CustomizeWindowHint, False)
        self.setWindowTitle(
            self.tr("Loofi Fedora Tweaks v%1").replace("%1", __version__)
        )
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        # HiDPI safety: compute scalable dimensions from font metrics
        fm = QFontMetrics(self.font())
        self._line_height = fm.height()

        # Initialize Pulse event listener
        self.pulse = None
        self.pulse_thread = None
        self._start_pulse_listener()

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Layout (Horizontal: Sidebar | Content)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # Sidebar container with search
        sidebar_container = QWidget()
        # HiDPI: 15*line_height = approx 240px at 1x DPI
        sidebar_width = int(self._line_height * 15)
        sidebar_container.setFixedWidth(sidebar_width)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 10, 0, 0)
        sidebar_layout.setSpacing(0)

        # Search box
        from PyQt6.QtWidgets import QLineEdit

        self.sidebar_search = QLineEdit()
        self.sidebar_search.setPlaceholderText(self.tr("Search tabs..."))
        self.sidebar_search.setClearButtonEnabled(True)
        self.sidebar_search.setAccessibleName(self.tr("Search tabs"))
        self.sidebar_search.setAccessibleDescription(
            self.tr("Filter sidebar tabs by name or description")
        )
        # HiDPI: 2*line_height + padding (4+10)*2 = approx 36px at 1x DPI
        search_height = int(self._line_height * 2 + 28)
        self.sidebar_search.setFixedHeight(search_height)
        self.sidebar_search.setStyleSheet(
            "QLineEdit { margin: 5px 10px; border-radius: 8px; padding: 4px 10px; }"
        )
        self.sidebar_search.textChanged.connect(self._filter_sidebar)
        sidebar_layout.addWidget(self.sidebar_search)

        # Sidebar collapse toggle
        self._sidebar_toggle = QPushButton("◀")
        self._sidebar_toggle.setObjectName("sidebarToggle")
        self._sidebar_toggle.setFixedHeight(int(self._line_height * 2))
        self._sidebar_toggle.setToolTip(self.tr("Collapse sidebar"))
        self._sidebar_toggle.clicked.connect(self._toggle_sidebar)
        sidebar_layout.addWidget(self._sidebar_toggle)

        # Track sidebar expanded width and state
        self._sidebar_container = sidebar_container
        self._sidebar_expanded_width = sidebar_width
        self._sidebar_collapsed = False

        # Sidebar tree
        self.sidebar = QTreeWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.sidebar.setHeaderHidden(True)
        self.sidebar.setAccessibleName(self.tr("Navigation sidebar"))
        self.sidebar.setIndentation(20)
        self.sidebar.setRootIsDecorated(True)
        self.sidebar.setUniformRowHeights(True)
        self.sidebar.setAnimated(True)
        self.sidebar.setIconSize(QSize(17, 17))
        self.sidebar.currentItemChanged.connect(self.change_page)
        self.sidebar.currentItemChanged.connect(self._on_sidebar_selection_changed)
        self.sidebar.setItemDelegate(SidebarItemDelegate(self.sidebar))
        # v31.0: Context menu for favorites
        self.sidebar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sidebar.customContextMenuRequested.connect(self._sidebar_context_menu)
        sidebar_layout.addWidget(self.sidebar)

        # Sidebar footer
        sidebar_footer = QLabel(f"v{__version__}")
        sidebar_footer.setObjectName("sidebarFooter")
        sidebar_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # HiDPI: 2*line_height = approx 28px at 1x DPI
        footer_height = int(self._line_height * 2)
        sidebar_footer.setFixedHeight(footer_height)
        sidebar_layout.addWidget(sidebar_footer)

        main_layout.addWidget(sidebar_container)

        # Right side: breadcrumb + content + status bar
        right_side = QVBoxLayout()
        right_side.setContentsMargins(0, 0, 0, 0)
        right_side.setSpacing(0)

        # Breadcrumb bar
        self._breadcrumb_frame = QFrame()
        self._breadcrumb_frame.setObjectName("breadcrumbBar")
        # HiDPI: 3*line_height = approx 44px at 1x DPI
        breadcrumb_height = int(self._line_height * 3)
        self._breadcrumb_frame.setFixedHeight(breadcrumb_height)
        bc_layout = QHBoxLayout(self._breadcrumb_frame)
        bc_layout.setContentsMargins(16, 0, 16, 0)
        self._bc_category = QPushButton("")
        self._bc_category.setObjectName("bcCategory")
        self._bc_category.setFlat(True)
        self._bc_category.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bc_category.clicked.connect(self._on_breadcrumb_category_click)
        self._bc_sep = QLabel("  ›  ")
        self._bc_sep.setObjectName("bcSep")
        self._bc_page = QLabel("")
        self._bc_page.setObjectName("bcPage")
        self._bc_desc = QLabel("")
        self._bc_desc.setObjectName("bcDesc")
        bc_layout.addWidget(self._bc_category)
        bc_layout.addWidget(self._bc_sep)
        bc_layout.addWidget(self._bc_page)
        bc_layout.addSpacing(12)
        bc_layout.addWidget(self._bc_desc)
        bc_layout.addStretch()
        right_side.addWidget(self._breadcrumb_frame)

        # Content Area
        self.content_area = QStackedWidget()
        right_side.addWidget(self.content_area)

        # Status bar
        self._status_frame = QFrame()
        self._status_frame.setObjectName("statusBar")
        # HiDPI: 2*line_height = approx 28px at 1x DPI
        status_height = int(self._line_height * 2)
        self._status_frame.setFixedHeight(status_height)
        sb_layout = QHBoxLayout(self._status_frame)
        sb_layout.setContentsMargins(12, 0, 12, 0)
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        sb_layout.addWidget(self._status_label)

        # Undo button (v38.0)
        self._undo_btn = QPushButton(self.tr("↩ Undo"))
        self._undo_btn.setObjectName("undoButton")
        self._undo_btn.setVisible(False)
        self._undo_btn.setToolTip(self.tr("Undo last action"))
        self._undo_btn.clicked.connect(self._on_undo_clicked)
        sb_layout.addWidget(self._undo_btn)

        sb_layout.addStretch()
        shortcuts_hint = QLabel(
            self.tr("Ctrl+K Search  |  Ctrl+Shift+K Actions  |  F1 Help")
        )
        shortcuts_hint.setObjectName("statusHints")
        sb_layout.addWidget(shortcuts_hint)
        version_lbl = QLabel(f"v{__version__}")
        version_lbl.setObjectName("statusVersion")
        sb_layout.addWidget(version_lbl)
        right_side.addWidget(self._status_frame)

        main_layout.addLayout(right_side)

        # Initialize sidebar index infrastructure
        self._sidebar_index: dict[str, SidebarEntry] = {}
        self._category_items: dict[str, QTreeWidgetItem] = {}
        self._pages_cache: dict[str, QWidget] | None = None

        # Build sidebar from PluginRegistry (v25.0 plugin architecture)
        context = {
            "main_window": self,
            "config_manager": ConfigManager,  # class, not instance
            "executor": None,  # populated after executor init
        }
        self._build_sidebar_from_registry(context)

        # v31.0: Build favorites section at top of sidebar
        self._build_favorites_section()

        # Expand first category by default (Dashboard)
        if self.sidebar.topLevelItemCount() > 0:
            first = self.sidebar.topLevelItem(0)
            first.setExpanded(True)
            if first.childCount() > 0:
                self.sidebar.setCurrentItem(first.child(0))

        # v15.0 Nebula - Quick Actions Bar (Ctrl+Shift+K)
        self._setup_quick_actions()

        # Select first item
        if self.sidebar.topLevelItemCount() > 0:
            first_category = self.sidebar.topLevelItem(0)
            if first_category.childCount() > 0:
                self.sidebar.setCurrentItem(first_category.child(0))

        # System Tray
        self.setup_tray()
        self.check_dependencies()

        # Ctrl+K Command Palette shortcut
        self._setup_command_palette_shortcut()

        # v13.5 UX Polish - keyboard shortcuts
        self._setup_keyboard_shortcuts()

        # v13.5 UX Polish - notification bell
        self._setup_notification_bell()

        # v29.0 - Status indicators refresh (every 30s)
        from PyQt6.QtCore import QTimer

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status_indicators)
        self._status_timer.start(30000)
        # Delay initial refresh to avoid startup slowdown
        QTimer.singleShot(5000, self._refresh_status_indicators)

        # First-run wizard
        self._check_first_run()

    @property
    def pages(self) -> dict[str, QWidget]:
        """Backward-compatible accessor. Returns {display_name: widget} view."""
        if self._pages_cache is None:
            self._pages_cache = {
                entry.display_name: entry.page_widget
                for entry in self._sidebar_index.values()
            }
        return self._pages_cache

    @pages.setter
    def pages(self, value: dict) -> None:
        """Backward-compatible setter. Accepts a plain dict (e.g. in tests) and stores it as the cache."""
        # Always (re)initialize real dicts — avoids _Dummy leaking in from test stubs
        if not isinstance(getattr(self, "_sidebar_index", None), dict):
            self._sidebar_index = {}
        if not isinstance(getattr(self, "_category_items", None), dict):
            self._category_items = {}
        self._pages_cache = value

    def _build_sidebar_from_registry(self, context: dict) -> None:
        """Source all tabs from PluginRegistry. Replaces 26 hardcoded add_page() calls."""
        from core.plugins.compat import CompatibilityDetector
        from core.plugins.loader import PluginLoader

        detector = CompatibilityDetector()
        loader = PluginLoader(detector=detector)
        loader.load_builtins(context=context)

        registry = PluginRegistry.instance()

        # Experience level filtering
        from utils.experience_level import ExperienceLevelManager
        from utils.favorites import FavoritesManager

        level = ExperienceLevelManager.get_level()
        favorites = FavoritesManager.get_favorites()

        for plugin in registry:
            meta = plugin.metadata()
            if not ExperienceLevelManager.is_tab_visible(meta.id, level, favorites):
                continue
            compat = plugin.check_compat(detector)
            lazy = self._wrap_in_lazy(plugin)
            self._add_plugin_page(meta, lazy, compat)

        # Validate experience level tab lists against registry
        declared_ids = ExperienceLevelManager.get_all_declared_tab_ids()
        registered_ids = set(self._sidebar_index.keys())
        orphaned = declared_ids - registered_ids
        for tab_id in sorted(orphaned):
            logger.warning("Experience level references unknown tab: %s", tab_id)
        advanced_only = registered_ids - declared_ids
        if advanced_only:
            logger.info("Tabs only visible to ADVANCED users: %s", sorted(advanced_only))

    def _wrap_in_lazy(self, plugin: PluginInterface) -> LazyWidget:
        """Wrap plugin.create_widget() in LazyWidget for deferred instantiation."""
        return LazyWidget(plugin.create_widget)

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
            badge_suffix = "  ★"
        elif badge == "advanced":
            badge_suffix = "  ⚙"

        item = QTreeWidgetItem(category_item)
        item.setText(0, f"{name}{badge_suffix}")
        item.setData(0, _ROLE_NAME, name)
        self._set_tree_item_icon(item, icon)

        if disabled:
            item.setDisabled(True)
            tooltip = disabled_reason if disabled_reason else f"{name} is not available on this system."
            item.setToolTip(0, tooltip)
        else:
            item.setData(0, _ROLE_DESC, description)
            item.setData(0, _ROLE_BADGE, badge)
            if description:
                item.setToolTip(0, description)

        return item

    def _register_in_index(self, plugin_id: str, entry: "SidebarEntry", scroll_widget: "QWidget | None" = None) -> None:
        """Register a tab in the sidebar index and content area.

        Args:
            plugin_id: Canonical plugin identifier (key in _sidebar_index).
            entry: SidebarEntry holding the original (unwrapped) page widget.
            scroll_widget: Wrapped scroll-area widget to add to the content stack.
                           When None, entry.page_widget is added directly.
        """
        self._sidebar_index[plugin_id] = entry
        self._pages_cache = None  # invalidate backward-compat cache
        target = scroll_widget if scroll_widget is not None else entry.page_widget
        self.content_area.addWidget(target)

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
            meta.description, disabled=not compat.compatible, disabled_reason=compat.reason,
        )
        if not compat.compatible:
            page_widget = self._wrap_page_widget(DisabledPluginPage(meta, compat.reason))
        else:
            page_widget = self._wrap_page_widget(widget)
        item.setData(0, Qt.ItemDataRole.UserRole, page_widget)
        entry = SidebarEntry(
            plugin_id=meta.id,
            display_name=meta.name,
            tree_item=item,
            page_widget=widget,
            metadata=meta,
        )
        self._register_in_index(meta.id, entry, scroll_widget=page_widget)

    def _start_pulse_listener(self):
        """Initialize and start the Pulse event listener."""
        try:
            self.pulse = SystemPulse()
            self.pulse_thread = PulseThread(self.pulse)
            self.pulse.moveToThread(self.pulse_thread)
            self.pulse_thread.start()
        except (RuntimeError, OSError) as e:
            logger.debug("Failed to start pulse listener: %s", e)

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
            item.setData(0, Qt.ItemDataRole.UserRole, entry.tree_item.data(0, Qt.ItemDataRole.UserRole))
            self._copy_tree_item_icon(entry.tree_item, item)

        self._refresh_sidebar_icon_tints()

    def _sidebar_context_menu(self, pos):
        """Show context menu for sidebar items with favorite toggle."""
        item = self.sidebar.itemAt(pos)
        if not item or not item.data(0, Qt.ItemDataRole.UserRole):
            return

        from PyQt6.QtWidgets import QMenu

        tab_name = item.data(0, _ROLE_NAME)
        if not tab_name:
            tab_name = item.text(0).replace("  ★", "").replace("  ⚙", "").strip()
        tab_id = str(tab_name).lower().replace(" ", "_")

        menu = QMenu(self)
        is_fav = FavoritesManager.is_favorite(tab_id)

        if is_fav:
            action = menu.addAction(self.tr("Remove from Favorites"))
        else:
            action = menu.addAction(self.tr("Add to Favorites"))

        result = menu.exec(self.sidebar.mapToGlobal(pos))
        if result == action:
            FavoritesManager.toggle_favorite(tab_id)
            self._rebuild_favorites_section()

    def _rebuild_favorites_section(self):
        """Remove and rebuild the favorites section."""
        # Remove existing favorites category
        for i in range(self.sidebar.topLevelItemCount()):
            item = self.sidebar.topLevelItem(i)
            if item and "Favorites" in item.text(0):
                self.sidebar.takeTopLevelItem(i)
                break
        self._build_favorites_section()
        self._refresh_sidebar_icon_tints()

    def _rebuild_sidebar_for_experience_level(self):
        """Rebuild sidebar when experience level changes."""
        self.sidebar.clear()
        self._sidebar_index.clear()
        self._category_items.clear()
        self._pages_cache = None
        while self.content_area.count():
            w = self.content_area.widget(0)
            self.content_area.removeWidget(w)
        context = {
            "main_window": self,
            "config_manager": ConfigManager,
        }
        self._build_sidebar_from_registry(context)
        self._build_favorites_section()
        self._refresh_sidebar_icon_tints()

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
        item = self._create_tab_item(category_item, name, icon, badge, description, disabled, disabled_reason)

        if disabled:
            placeholder_meta = PluginMetadata(
                id=name.lower().replace(" ", "_"), name=name, description=description,
                category=category, icon=icon, badge=badge,
            )
            page_widget = self._wrap_page_widget(DisabledPluginPage(placeholder_meta, disabled_reason))
        else:
            page_widget = self._wrap_page_widget(widget)

        item.setData(0, Qt.ItemDataRole.UserRole, page_widget)

        plugin_id = name.lower().replace(" ", "_")
        meta = PluginMetadata(id=plugin_id, name=name, description=description, category=category, icon=icon, badge=badge)
        entry = SidebarEntry(
            plugin_id=plugin_id, display_name=name, tree_item=item,
            page_widget=widget, metadata=meta,
        )
        self._register_in_index(plugin_id, entry, scroll_widget=page_widget)

    def _wrap_page_widget(self, widget: QWidget) -> QScrollArea:
        """
        Wrap a page widget in a scroll area.

        Prevents dense tabs from being vertically compressed on smaller
        displays; users can scroll instead of seeing clipped/collapsed controls.
        """
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        return scroll

    def change_page(self, current, previous):
        if not current:
            return

        widget = current.data(0, Qt.ItemDataRole.UserRole)
        if widget:
            self.content_area.setCurrentWidget(widget)
            self._update_breadcrumb(current)
        else:
            # Category item: expand and auto-select first child
            if current.childCount() > 0:
                current.setExpanded(True)
                self.sidebar.setCurrentItem(current.child(0))

    def _update_breadcrumb(self, item):
        """Update breadcrumb bar with current category > page."""
        parent = item.parent()
        # Use raw category name (stored in _ROLE_DESC on category items) for clean breadcrumb
        category = ""
        if parent:
            category = parent.data(0, _ROLE_DESC) or parent.text(0)
        page_name = item.data(0, _ROLE_NAME)
        if not page_name:
            raw = item.text(0)
            page_name = raw.replace("  ★", "").replace("  ⚙", "")
        page_name = str(page_name)
        desc = item.data(0, _ROLE_DESC) or ""
        self._bc_category.setText(category)
        self._bc_page.setText(page_name)
        self._bc_desc.setText(desc)
        # Store parent item ref for breadcrumb click (v38.0)
        self._bc_parent_item = parent

    def _set_tree_item_icon(self, item: QTreeWidgetItem, icon_value: str) -> None:
        """Apply bundled icon-pack icon to a tree item when available."""
        if not icon_value:
            return
        item.setData(0, _ROLE_ICON, icon_value)
        self._apply_tree_item_icon(item)

    def _apply_tree_item_icon(self, item: QTreeWidgetItem) -> None:
        """Apply the correct icon tint for the item's current selection state."""
        icon_value = item.data(0, _ROLE_ICON)
        if not icon_value:
            return
        selected = self._is_sidebar_item_selected(item)
        tint = icon_tint_variant(str(icon_value), selected=selected)
        icon = get_qicon(str(icon_value), size=17, tint=tint)
        if hasattr(item, "setIcon"):
            try:
                item.setIcon(0, icon)
            except (TypeError, ValueError):
                logger.debug("Failed to apply tree icon", exc_info=True)

    def _copy_tree_item_icon(self, source: QTreeWidgetItem, target: QTreeWidgetItem) -> None:
        """Copy an existing icon from source to target item when supported."""
        icon_value = source.data(0, _ROLE_ICON)
        if icon_value:
            target.setData(0, _ROLE_ICON, icon_value)
            self._apply_tree_item_icon(target)
            return
        if not hasattr(source, "icon") or not hasattr(target, "setIcon"):
            return
        try:
            target.setIcon(0, source.icon(0))
        except (TypeError, ValueError):
            logger.debug("Failed to copy tree icon", exc_info=True)

    def _is_sidebar_item_selected(self, item: QTreeWidgetItem) -> bool:
        """Return True when item is current row or current row's parent category."""
        current = self.sidebar.currentItem() if hasattr(self, "sidebar") else None
        if current is None:
            return False
        if current is item:
            return True
        if item.parent() is None and current.parent() is item:
            return True
        return False

    def _refresh_sidebar_icon_tints(self) -> None:
        """Reapply icon variants after selection changes."""
        iterator = QTreeWidgetItemIterator(self.sidebar)
        while iterator.value():
            item = iterator.value()
            if item is None:
                break
            if item.data(0, _ROLE_ICON):
                self._apply_tree_item_icon(item)
            iterator += 1

    def _on_sidebar_selection_changed(self, current, previous) -> None:
        """Keep sidebar icon tint hierarchy in sync with the selected row."""
        self._refresh_sidebar_icon_tints()

    def _on_breadcrumb_category_click(self):
        """Navigate to the first page of the current breadcrumb category."""
        parent = getattr(self, "_bc_parent_item", None)
        if parent and parent.childCount() > 0:
            parent.setExpanded(True)
            self.sidebar.setCurrentItem(parent.child(0))

    def set_status(self, text: str):
        """Set status bar message (can be called from any tab)."""
        self._status_label.setText(text)

    def show_undo_button(self, description: str = ""):
        """Show the undo button in the status bar after an undoable action."""
        if description:
            self._status_label.setText(self.tr("✓ ") + description)
        self._undo_btn.setVisible(True)

    def _on_undo_clicked(self):
        """Execute undo via HistoryManager and update status."""
        try:
            hm = HistoryManager()
            result = hm.undo_last_action()
            if result.success:
                self.show_status_toast(result.message)
            else:
                self.show_status_toast(result.message, error=True)
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Undo failed: %s", e)
            self.show_status_toast(self.tr("Undo failed"), error=True)
        self._undo_btn.setVisible(False)

    def show_status_toast(
        self, message: str, error: bool = False, duration: int = 3000
    ):
        """Show a temporary status-bar toast notification (v38.0)."""
        self._status_label.setText(message)
        if error:
            self._status_label.setProperty("toast", "error")
        else:
            self._status_label.setProperty("toast", "success")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(duration, self._clear_toast)

    def _clear_toast(self):
        """Clear toast styling from the status bar."""
        self._status_label.setText("")
        self._status_label.setProperty("toast", "")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def switch_to_tab(self, name):
        """Switch to a tab by plugin ID (primary) or display name (fallback)."""
        entry = self._sidebar_index.get(name)
        if entry:
            self.sidebar.setCurrentItem(entry.tree_item)
            return

        # Fallback: search by display name
        for entry in self._sidebar_index.values():
            if name in entry.display_name:
                logger.debug(
                    "switch_to_tab: matched by display name '%s', prefer plugin ID '%s'",
                    name,
                    entry.plugin_id,
                )
                self.sidebar.setCurrentItem(entry.tree_item)
                return

        logger.debug("switch_to_tab: no match for '%s'", name)

    def _setup_command_palette_shortcut(self):
        """Register Ctrl+K shortcut for the command palette."""
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self._show_command_palette)

    def _show_command_palette(self):
        """Show the command palette dialog."""
        try:
            from ui.command_palette import CommandPalette

            palette = CommandPalette(self.switch_to_tab, self)
            palette.exec()
        except ImportError:
            logger.debug("Command palette module not available", exc_info=True)

    def _filter_sidebar(self, text: str):
        """Filter sidebar items by name, description, badge, and category."""
        search = text.lower()

        # Iterate top-level categories
        for i in range(self.sidebar.topLevelItemCount()):
            category = self.sidebar.topLevelItem(i)
            category_visible = False

            # Check children (name + description + badge data)
            for j in range(category.childCount()):
                child = category.child(j)
                name_match = search in child.text(0).lower()
                desc = (child.data(0, _ROLE_DESC) or "").lower()
                desc_match = search in desc
                badge = (child.data(0, _ROLE_BADGE) or "").lower()
                badge_match = search in badge
                if name_match or desc_match or badge_match:
                    child.setHidden(False)
                    category_visible = True
                else:
                    child.setHidden(True)

            # Check category itself
            if search in category.text(0).lower():
                category_visible = True
                for j in range(category.childCount()):
                    category.child(j).setHidden(False)

            category.setHidden(not category_visible)
            if category_visible:
                category.setExpanded(True)

    def _toggle_sidebar(self):
        """Toggle sidebar between expanded and collapsed states."""
        if self._sidebar_collapsed:
            self._sidebar_container.setFixedWidth(self._sidebar_expanded_width)
            self.sidebar.setVisible(True)
            self.sidebar_search.setVisible(True)
            self._sidebar_toggle.setText("◀")
            self._sidebar_toggle.setToolTip(self.tr("Collapse sidebar"))
            self._sidebar_collapsed = False
        else:
            self._sidebar_container.setFixedWidth(int(self._line_height * 3))
            self.sidebar.setVisible(False)
            self.sidebar_search.setVisible(False)
            self._sidebar_toggle.setText("▶")
            self._sidebar_toggle.setToolTip(self.tr("Expand sidebar"))
            self._sidebar_collapsed = True

    def _setup_keyboard_shortcuts(self):
        """Register keyboard shortcuts for tab navigation."""
        # Ctrl+1 through Ctrl+9 - switch to category 1-9
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda idx=i - 1: self._select_category(idx))

        # Ctrl+Tab - next tab
        next_tab = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab.activated.connect(self._select_next_item)

        # Ctrl+Shift+Tab - previous tab
        prev_tab = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab.activated.connect(self._select_prev_item)

        # Ctrl+Q - Quit
        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.quit_app)

        # F1 - Show shortcut help
        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self._show_shortcut_help)

    def _select_category(self, index: int):
        if index < self.sidebar.topLevelItemCount():
            item = self.sidebar.topLevelItem(index)
            self.sidebar.setCurrentItem(item)
            item.setExpanded(True)

    def _select_next_item(self):
        current = self.sidebar.currentItem()
        if not current:
            return

        # Try to find next item below
        next_item = self.sidebar.itemBelow(current)
        if next_item:
            self.sidebar.setCurrentItem(next_item)
        else:
            # Wrap around to top
            if self.sidebar.topLevelItemCount() > 0:
                self.sidebar.setCurrentItem(self.sidebar.topLevelItem(0))

    def _select_prev_item(self):
        current = self.sidebar.currentItem()
        if not current:
            return

        # Try to find item above
        prev_item = self.sidebar.itemAbove(current)
        if prev_item:
            self.sidebar.setCurrentItem(prev_item)
        else:
            # Wrap around to bottom
            last_top = self.sidebar.topLevelItem(self.sidebar.topLevelItemCount() - 1)
            # Find last visible item
            while last_top.childCount() > 0 and last_top.isExpanded():
                last_top = last_top.child(last_top.childCount() - 1)
            self.sidebar.setCurrentItem(last_top)

    def _show_shortcut_help(self):
        """Show keyboard shortcuts help dialog."""
        from PyQt6.QtWidgets import QMessageBox

        shortcuts = (
            "Ctrl+K — Command Palette\n"
            "Ctrl+Shift+K — Quick Actions\n"
            "Ctrl+1..9 — Switch to tab 1-9\n"
            "Ctrl+Tab — Next tab\n"
            "Ctrl+Shift+Tab — Previous tab\n"
            "Ctrl+Q — Quit\n"
            "F1 — This help"
        )
        QMessageBox.information(self, self.tr("Keyboard Shortcuts"), shortcuts)

    def _setup_notification_bell(self):
        """Add notification bell with unread count badge to the breadcrumb bar."""
        from PyQt6.QtWidgets import QToolButton

        self.notif_panel = None
        self._toast_widget = None

        # Bell button
        self.notif_bell = QToolButton()
        self.notif_bell.setText("")
        self.notif_bell.setIcon(get_qicon("notifications", size=17))
        self.notif_bell.setIconSize(QSize(17, 17))
        self.notif_bell.setStyleSheet(
            "QToolButton { border: none; font-size: 20px; padding: 5px; }"
            "QToolButton:hover { background-color: #1c2030; border-radius: 6px; }"
        )
        self.notif_bell.clicked.connect(self._toggle_notification_panel)

        # Unread count badge (overlays bell button)
        self._notif_badge = QLabel("0")
        self._notif_badge.setStyleSheet(
            "background-color: #e8556d; color: #0b0e14; border-radius: 8px; "
            "padding: 1px 6px; font-size: 10px; font-weight: bold;"
        )
        self._notif_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notif_badge.setFixedHeight(16)
        self._notif_badge.setVisible(False)

        # Add bell first, then badge — badge appears as overlay to the right
        bc_layout = self._breadcrumb_frame.layout()
        if bc_layout:
            bc_layout.addWidget(self.notif_bell)
            bc_layout.addWidget(self._notif_badge)

        # Timer to refresh unread count (every 5s)
        from PyQt6.QtCore import QTimer

        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._refresh_notif_badge)
        self._notif_timer.start(5000)
        self._refresh_notif_badge()

    def _toggle_notification_panel(self):
        """Toggle the notification panel."""
        if self.notif_panel is None:
            from ui.notification_panel import NotificationPanel

            self.notif_panel = NotificationPanel(self)

        if self.notif_panel.isVisible():
            self.notif_panel.hide()
        else:
            self.notif_panel.refresh()

            # v35.0 Fortress: Improved edge-clipping prevention
            panel = self.notif_panel
            panel_w = panel.PANEL_WIDTH
            margin = panel.EDGE_MARGIN
            breadcrumb_bottom = self._breadcrumb_frame.geometry().bottom()
            status_height = (
                self._status_frame.height() if hasattr(self, "_status_frame") else 0
            )
            window_w = self.width()
            window_h = self.height()

            # X: right-aligned, clamped to window edges
            x = max(margin, window_w - panel_w - margin)

            # Y: below breadcrumb bar
            y = breadcrumb_bottom + margin

            # Available height: from y to bottom minus status bar and margin
            available_h = window_h - y - status_height - margin
            capped_h = max(
                panel.MIN_HEIGHT,
                min(panel.sizeHint().height(), available_h, panel.MAX_HEIGHT),
            )

            panel.setFixedHeight(capped_h)
            panel.move(x, y)
            panel.show()
            panel.raise_()
        self._refresh_notif_badge()

    def _refresh_notif_badge(self):
        """Update the unread notification count badge."""
        try:
            from utils.notification_center import NotificationCenter

            nc = NotificationCenter()
            count = nc.get_unread_count()
            if count > 0:
                self._notif_badge.setText(str(min(count, 99)))
                self._notif_badge.setVisible(True)
            else:
                self._notif_badge.setVisible(False)
        except (RuntimeError, ValueError, TypeError) as e:
            logger.debug("Failed to refresh notification badge: %s", e)
            self._notif_badge.setVisible(False)

    def show_toast(self, title: str, message: str, category: str = "general"):
        """Show an animated toast notification at the top-right."""
        try:
            from ui.notification_toast import NotificationToast

            if self._toast_widget is None:
                self._toast_widget = NotificationToast(self)
            self._toast_widget.show_toast(title, message, category)
            # Refresh badge since a new notification likely exists
            self._refresh_notif_badge()
        except (RuntimeError, ImportError) as e:
            logger.debug("Failed to show toast notification: %s", e)

    def _refresh_status_indicators(self):
        """Update sidebar status indicators from live system data (v29.0)."""
        try:
            # Maintenance: check for updates
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
            # Storage: check disk space
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

    def _setup_quick_actions(self):
        """Register Ctrl+Shift+K shortcut for Quick Actions bar."""
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+K"), self)
        shortcut.activated.connect(self._show_quick_actions)

    def _show_quick_actions(self):
        """Show the Quick Actions bar."""
        try:
            from ui.quick_actions import (
                QuickActionRegistry,
                QuickActionsBar,
                register_default_actions,
            )

            registry = QuickActionRegistry.instance()
            if not registry.get_all():
                register_default_actions(registry, main_window=self)
            bar = QuickActionsBar(self)
            bar.exec()
        except ImportError:
            logger.debug("Quick actions module not available", exc_info=True)

    def _check_first_run(self):
        """Show first-run wizard if this is the first launch."""
        config_dir = os.path.expanduser("~/.config/loofi-fedora-tweaks")
        first_run_file = os.path.join(config_dir, "first_run_complete")

        if not os.path.exists(first_run_file):
            try:
                from ui.wizard import FirstRunWizard

                wizard = FirstRunWizard(self)
                wizard.exec()
            except ImportError:
                logger.debug("First-run wizard module not available", exc_info=True)

        # Launch guided tour if not yet completed (v47.0)
        try:
            from utils.guided_tour import GuidedTourManager
            if GuidedTourManager.needs_tour():
                from ui.tour_overlay import TourOverlay
                self._tour_overlay = TourOverlay(self)
                self._tour_overlay.tour_completed.connect(
                    lambda: self.show_toast(
                        self.tr("Welcome"),
                        self.tr("Tour complete! Explore at your own pace."),
                        "general",
                    )
                )
                QTimer.singleShot(500, self._tour_overlay.start)
        except (ImportError, RuntimeError) as e:
            logger.debug("Guided tour not available: %s", e)

    def setup_tray(self):
        from PyQt6.QtGui import QAction, QIcon
        from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            icon_path = os.path.join(
                os.path.dirname(__file__), "..", "assets", "loofi-fedora-tweaks.png"
            )
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
            else:
                self.tray_icon.setIcon(
                    self.style().standardIcon(
                        self.style().StandardPixmap.SP_ComputerIcon
                    )
                )

            tray_menu = QMenu()
            show_action = QAction(self.tr("Show"), self)
            show_action.triggered.connect(self.show)

            # Focus Mode toggle
            self.focus_action = QAction(self.tr("Focus Mode"), self)
            self.focus_action.setCheckable(True)
            self.focus_action.setChecked(FocusMode.is_active())
            self.focus_action.triggered.connect(self._toggle_focus_mode)

            quit_action = QAction(self.tr("Quit"), self)
            quit_action.triggered.connect(self.quit_app)

            tray_menu.addAction(show_action)
            tray_menu.addSeparator()
            tray_menu.addAction(self.focus_action)
            tray_menu.addSeparator()
            tray_menu.addAction(quit_action)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
        else:
            self.tray_icon = None

    def _toggle_focus_mode(self):
        """Toggle Focus Mode from tray."""
        result = FocusMode.toggle()
        self.focus_action.setChecked(FocusMode.is_active())

        if self.tray_icon:
            message = result.get("message", "Focus Mode toggled")
            self.tray_icon.showMessage(
                self.tr("Focus Mode"),
                message,
                self.tray_icon.MessageIcon.Information,
                2000,
            )

    def quit_app(self):
        # Stop Pulse listener
        if self.pulse_thread:
            self.pulse_thread.stop()

        if self.tray_icon:
            self.tray_icon.hide()
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()

    def closeEvent(self, event):
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                self.tr("Loofi Fedora Tweaks"),
                self.tr("Minimized to tray."),
                self.tray_icon.MessageIcon.Information,
                2000,
            )
            event.ignore()
        else:
            # Clean up page resources (timers, schedulers)
            for entry in self._sidebar_index.values():
                page = entry.page_widget
                if hasattr(page, "cleanup"):
                    try:
                        page.cleanup()
                    except (RuntimeError, OSError) as e:
                        logger.debug("Failed to cleanup page on close: %s", e)
            event.accept()

    def check_dependencies(self):
        import shutil

        critical = ["dnf", "pkexec"]
        missing = [tool for tool in critical if not shutil.which(tool)]
        if missing:
            self.show_doctor()

    def show_doctor(self):
        from ui.doctor import DependencyDoctor

        doctor = DependencyDoctor(self)
        doctor.exec()

    # ==================== v13.5 Theme Management ====================

    def load_theme(self, name: str = "dark") -> None:
        """
        Load and apply a QSS theme by name.

        Supported names: ``"dark"`` (modern.qss), ``"light"`` (light.qss),
        and ``"highcontrast"`` (highcontrast.qss).
        Falls back silently to no stylesheet if the file is missing.
        """
        theme_map = {
            "dark": "modern.qss",
            "light": "light.qss",
            "highcontrast": "highcontrast.qss",
        }
        filename = theme_map.get(name, "modern.qss")
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        qss_path = os.path.join(assets_dir, filename)

        try:
            with open(qss_path, "r") as fh:
                stylesheet = fh.read()
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if isinstance(app, QApplication):
                app.setStyleSheet(stylesheet)
        except OSError:
            logger.debug("Failed to load theme stylesheet", exc_info=True)

    @staticmethod
    def detect_system_theme() -> str:
        """
        Detect the system colour-scheme preference via
        ``gsettings`` (GNOME / GTK) and return ``"dark"`` or ``"light"``.

        Returns ``"dark"`` when detection fails.
        """
        from utils.desktop_utils import DesktopUtils

        return DesktopUtils.detect_color_scheme()

    def _get_frameless_mode_flag(self) -> bool:
        """
        Check if frameless window mode is requested.

        Priority:
        1. Config file: ui.frameless_mode key
        2. Environment variable: LOOFI_FRAMELESS=1

        Returns:
            True if frameless mode is enabled, False otherwise (default).
        """
        # Check config file first
        config = ConfigManager.load_config()
        if config is not None:
            ui_settings = config.get("ui", {})
            if "frameless_mode" in ui_settings:
                return bool(ui_settings["frameless_mode"])

        # Fallback to environment variable
        env_value = os.environ.get("LOOFI_FRAMELESS", "").strip()
        return env_value == "1"
