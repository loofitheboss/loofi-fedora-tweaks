"""
Main Window - v25.0 "Plugin Architecture"
26-tab layout sourced from PluginRegistry with sidebar navigation, breadcrumb, and status bar.
"""

import logging
import os

from core.plugins.metadata import CompatStatus, PluginMetadata
from core.plugins.registry import CATEGORY_ICONS
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
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
from ui.lazy_widget import LazyWidget

logger = get_logger(__name__)

# Custom data roles for sidebar items
_ROLE_DESC = Qt.ItemDataRole.UserRole + 1  # Tab description string
_ROLE_BADGE = Qt.ItemDataRole.UserRole + 2  # "recommended" | "advanced" | ""
_ROLE_STATUS = Qt.ItemDataRole.UserRole + 3  # "ok" | "warning" | "error" | ""


class DisabledPluginPage(QWidget):
    """Shown in the content area for plugins that are incompatible with the current system."""

    def __init__(self, meta: PluginMetadata, reason: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(
            f"{meta.icon}  {meta.name} is not available on this system.\n\n{reason}"
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
        self.setWindowTitle(self.tr(f"Loofi Fedora Tweaks v{__version__}"))
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
        self.sidebar.currentItemChanged.connect(self.change_page)
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

        # Initialize Pages
        self.pages = {}

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

    def _build_sidebar_from_registry(self, context: dict) -> None:
        """Source all tabs from PluginRegistry. Replaces 26 hardcoded add_page() calls."""
        from core.plugins.compat import CompatibilityDetector
        from core.plugins.loader import PluginLoader

        detector = CompatibilityDetector()
        loader = PluginLoader(detector=detector)
        loader.load_builtins(context=context)

        registry = PluginRegistry.instance()

        for plugin in registry:
            meta = plugin.metadata()
            compat = plugin.check_compat(detector)
            lazy = self._wrap_in_lazy(plugin)
            self._add_plugin_page(meta, lazy, compat)

    def _wrap_in_lazy(self, plugin: PluginInterface) -> LazyWidget:
        """Wrap plugin.create_widget() in LazyWidget for deferred instantiation."""
        return LazyWidget(plugin.create_widget)

    def _add_plugin_page(
        self,
        meta: PluginMetadata,
        widget: LazyWidget,
        compat: CompatStatus,
    ) -> None:
        """Register a plugin page in the sidebar and content area."""
        self.add_page(
            name=meta.name,
            icon=meta.icon,
            widget=widget,
            category=meta.category,
            description=meta.description,
            badge=meta.badge,
            disabled=not compat.compatible,
            disabled_reason=compat.reason,
        )

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
        """Build a ⭐ Favorites category at the top of the sidebar with pinned tabs."""
        favorites = FavoritesManager.get_favorites()
        if not favorites:
            return

        # Create Favorites category at position 0
        fav_category = QTreeWidgetItem()
        fav_category.setText(0, "⭐ Favorites")
        fav_category.setExpanded(True)
        self.sidebar.insertTopLevelItem(0, fav_category)

        # Find matching page widgets and duplicate entries under Favorites
        for fav_id in favorites:
            for name, widget in self.pages.items():
                # Match by tab name (case-insensitive)
                if name.lower().replace(" ", "_") == fav_id or name.lower() == fav_id:
                    item = QTreeWidgetItem(fav_category)
                    item.setText(0, f"📌  {name}")
                    item.setData(0, _ROLE_DESC, f"Pinned: {name}")

                    # Find the original widget in the content area
                    for i in range(self.sidebar.topLevelItemCount()):
                        cat = self.sidebar.topLevelItem(i)
                        if cat == fav_category:
                            continue
                        for j in range(cat.childCount()):
                            child = cat.child(j)
                            if name in child.text(0) and child.data(
                                0, Qt.ItemDataRole.UserRole
                            ):
                                item.setData(
                                    0,
                                    Qt.ItemDataRole.UserRole,
                                    child.data(0, Qt.ItemDataRole.UserRole),
                                )
                                break
                    break

    def _sidebar_context_menu(self, pos):
        """Show context menu for sidebar items with favorite toggle."""
        item = self.sidebar.itemAt(pos)
        if not item or not item.data(0, Qt.ItemDataRole.UserRole):
            return

        from PyQt6.QtWidgets import QMenu

        # Extract tab name (strip icon prefix and badge suffixes)
        raw_name = item.text(0).replace("  ★", "").replace("  ⚙", "")
        # Remove emoji prefix (first 2-3 chars + spaces)
        parts = raw_name.split("  ", 1)
        tab_name = parts[1] if len(parts) > 1 else raw_name.strip()
        tab_id = tab_name.lower().replace(" ", "_")

        menu = QMenu(self)
        is_fav = FavoritesManager.is_favorite(tab_id)

        if is_fav:
            action = menu.addAction(self.tr("⭐ Remove from Favorites"))
        else:
            action = menu.addAction(self.tr("⭐ Add to Favorites"))

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
        # Build display label for category (with icon prefix if available)
        cat_icon = CATEGORY_ICONS.get(category, "")
        cat_label = f"{cat_icon}  {category}" if cat_icon else category

        # Find or create category item
        category_item = None
        for i in range(self.sidebar.topLevelItemCount()):
            item = self.sidebar.topLevelItem(i)
            if item.text(0) == cat_label or item.data(0, _ROLE_DESC) == category:
                category_item = item
                break

        if not category_item:
            category_item = QTreeWidgetItem(self.sidebar)
            category_item.setText(0, cat_label)
            # Store raw category name
            category_item.setData(0, _ROLE_DESC, category)
            category_item.setExpanded(True)

        # Badge suffix
        badge_suffix = ""
        if badge == "recommended":
            badge_suffix = "  ★"
        elif badge == "advanced":
            badge_suffix = "  ⚙"

        item = QTreeWidgetItem(category_item)
        item.setText(0, f"{icon}  {name}{badge_suffix}")

        # Disabled plugin: show placeholder page and gray out sidebar item
        if disabled:
            placeholder_meta = PluginMetadata(
                id=name.lower().replace(" ", "_"),
                name=name,
                description=description,
                category=category,
                icon=icon,
                badge=badge,
            )
            page_widget = self._wrap_page_widget(
                DisabledPluginPage(placeholder_meta, disabled_reason)
            )
            item.setDisabled(True)
            tooltip = (
                disabled_reason
                if disabled_reason
                else f"{name} is not available on this system."
            )
            item.setToolTip(0, tooltip)
        else:
            page_widget = self._wrap_page_widget(widget)
            item.setData(0, _ROLE_DESC, description)
            item.setData(0, _ROLE_BADGE, badge)
            if description:
                item.setToolTip(0, description)

        # Store widget reference
        item.setData(0, Qt.ItemDataRole.UserRole, page_widget)
        self.content_area.addWidget(page_widget)
        self.pages[name] = widget

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
        # Strip badge suffixes for display
        raw = item.text(0)
        page_name = raw.replace("  ★", "").replace("  ⚙", "")
        desc = item.data(0, _ROLE_DESC) or ""
        self._bc_category.setText(category)
        self._bc_page.setText(page_name)
        self._bc_desc.setText(desc)
        # Store parent item ref for breadcrumb click (v38.0)
        self._bc_parent_item = parent

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
        """Helper for Dashboard and Command Palette to switch tabs."""
        # Search all items
        iterator = QTreeWidgetItemIterator(self.sidebar)
        while iterator.value():
            item = iterator.value()
            # Check if it matches and is a page (has widget data)
            if name in item.text(0) and item.data(0, Qt.ItemDataRole.UserRole):
                self.sidebar.setCurrentItem(item)
                return
            iterator += 1

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
        self.notif_bell.setText("\U0001f514")  # Bell emoji
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
                self._set_tab_status("Maintenance", "warning", "Updates available")
            else:
                self._set_tab_status("Maintenance", "ok", "Up to date")
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to check for updates: %s", e)
            self._set_tab_status("Maintenance", "", "")

        try:
            # Storage: check disk space
            from services.hardware.disk import DiskManager

            usage = DiskManager.get_disk_usage("/")
            if usage and hasattr(usage, "percent_used"):
                if usage.percent_used >= 90:
                    self._set_tab_status(
                        "Storage", "error", f"Disk {usage.percent_used:.0f}% full"
                    )
                elif usage.percent_used >= 75:
                    self._set_tab_status(
                        "Storage", "warning", f"Disk {usage.percent_used:.0f}% used"
                    )
                else:
                    self._set_tab_status("Storage", "ok", "Healthy")
        except (RuntimeError, OSError, ValueError) as e:
            logger.debug("Failed to check disk space: %s", e)
            self._set_tab_status("Storage", "", "")

    def _set_tab_status(self, tab_name: str, status: str, tooltip: str = ""):
        """Set a colored status indicator on a sidebar tab item."""
        # Status dot unicode
        dots = {"ok": "🟢", "warning": "🟡", "error": "🔴"}
        dot = dots.get(status, "")

        iterator = QTreeWidgetItemIterator(self.sidebar)
        while iterator.value():
            item = iterator.value()
            if item is None:
                break
            if item.data(0, Qt.ItemDataRole.UserRole) and tab_name in item.text(0):
                # Strip any existing status dot, add new one
                text = item.text(0)
                for d in dots.values():
                    text = text.replace(f" {d}", "")
                if dot:
                    text = f"{text} {dot}"
                item.setText(0, text)
                item.setData(0, _ROLE_STATUS, status)
                if tooltip:
                    existing = item.data(0, _ROLE_DESC) or ""
                    item.setToolTip(
                        0, f"{existing}\n[{tooltip}]" if existing else tooltip
                    )
                break
            iterator += 1

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
            for page in self.pages.values():
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
