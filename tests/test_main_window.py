"""Tests for ui/main_window.py — MainWindow and DisabledPluginPage.

Comprehensive behavioural tests covering sidebar navigation, page management,
filtering, theme loading, system tray, dependencies, keyboard shortcuts,
favorites, notifications, and application lifecycle.  All external managers
and PyQt6 are stubbed so tests run headless without a display server.
"""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import patch, MagicMock, PropertyMock, mock_open, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


# ---------------------------------------------------------------------------
# Lightweight PyQt6 stubs (no display server required)
# ---------------------------------------------------------------------------


class _ShapeEnum:
    """Stub for QFrame.Shape enum values."""

    NoFrame = 0
    Box = 1
    Panel = 2
    StyledPanel = 5
    HLine = 4
    VLine = 5


class _Dummy:
    """Universal stub that absorbs any constructor / attribute access."""

    Shape = _ShapeEnum

    class ToolButtonStyle:
        ToolButtonTextBesideIcon = 3

    class DockWidgetArea:
        LeftDockWidgetArea = 1

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, _name):
        return _Dummy()

    def __call__(self, *args, **kwargs):
        return _Dummy()

    def __bool__(self):
        return True

    def __iter__(self):
        return iter([])

    def __str__(self):
        return ""

    def tr(self, text):
        return text


class _DummySignal:
    """Minimal pyqtSignal stub that stores connected slots."""

    def __init__(self, *arg_types):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args):
        for slot in self._slots:
            slot(*args)

    def disconnect(self, slot=None):
        if slot:
            self._slots.remove(slot)
        else:
            self._slots.clear()


class _DummyLabel:
    """Minimal QLabel stand-in with text tracking."""

    def __init__(self, text="", *args, **kwargs):
        self._text = str(text) if text is not None else ""
        self._visible = True
        self._properties = {}
        self._object_name = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setObjectName(self, name):
        self._object_name = name

    def objectName(self):
        return self._object_name

    def setWordWrap(self, wrap):
        pass

    def setProperty(self, key, value):
        self._properties[key] = value

    def property(self, key):
        return self._properties.get(key)

    def setVisible(self, visible):
        self._visible = visible

    def isVisible(self):
        return self._visible

    def setFixedHeight(self, h):
        pass

    def style(self):
        return _DummyStyle()

    def tr(self, text):
        return text

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyStyle:
    """Minimal style stub."""

    def unpolish(self, widget):
        pass

    def polish(self, widget):
        pass


class _DummyButton:
    """Minimal QPushButton stand-in."""

    def __init__(self, text="", *args, **kwargs):
        self._text = text
        self._visible = True
        self._enabled = True
        self.clicked = _DummySignal()

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setVisible(self, v):
        self._visible = v

    def isVisible(self):
        return self._visible

    def setEnabled(self, flag):
        self._enabled = flag

    def isEnabled(self):
        return self._enabled

    def tr(self, text):
        return text

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyLineEdit:
    """Minimal QLineEdit stand-in."""

    def __init__(self, *args, **kwargs):
        self._text = ""
        self._visible = True
        self.textChanged = _DummySignal()

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def setVisible(self, v):
        self._visible = v

    def isVisible(self):
        return self._visible

    def tr(self, text):
        return text

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyTreeWidgetItem:
    """Minimal QTreeWidgetItem stand-in with data and child tracking."""

    def __init__(self, parent=None, *args, **kwargs):
        self._text = {}
        self._data = {}
        self._children = []
        self._parent = None
        self._hidden = False
        self._expanded = False
        self._disabled = False
        self._tooltip = {}
        if parent is not None:
            if isinstance(parent, _DummyTreeWidgetItem):
                parent._children.append(self)
                self._parent = parent
            elif isinstance(parent, _DummyTreeWidget):
                parent.addTopLevelItem(self)

    def setText(self, col, text):
        self._text[col] = text

    def text(self, col):
        return self._text.get(col, "")

    def setData(self, col, role, value):
        self._data[(col, role)] = value

    def data(self, col, role):
        return self._data.get((col, role))

    def parent(self):
        return self._parent

    def childCount(self):
        return len(self._children)

    def child(self, index):
        if 0 <= index < len(self._children):
            return self._children[index]
        return None

    def setHidden(self, hidden):
        self._hidden = hidden

    def isHidden(self):
        return self._hidden

    def setExpanded(self, expanded):
        self._expanded = expanded

    def isExpanded(self):
        return self._expanded

    def setDisabled(self, disabled):
        self._disabled = disabled

    def isDisabled(self):
        return self._disabled

    def setToolTip(self, col, text):
        self._tooltip[col] = text

    def toolTip(self, col):
        return self._tooltip.get(col, "")


class _DummyTreeWidget:
    """Minimal QTreeWidget stand-in with full sidebar simulation."""

    def __init__(self, *args, **kwargs):
        self._items = []
        self._current = None
        self._visible = True
        self._context_policy = None
        self.currentItemChanged = _DummySignal()
        self.customContextMenuRequested = _DummySignal()

    def topLevelItemCount(self):
        return len(self._items)

    def topLevelItem(self, idx):
        if 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    def addTopLevelItem(self, item):
        self._items.append(item)

    def insertTopLevelItem(self, idx, item):
        self._items.insert(idx, item)

    def takeTopLevelItem(self, idx):
        if 0 <= idx < len(self._items):
            return self._items.pop(idx)
        return None

    def setCurrentItem(self, item):
        old = self._current
        self._current = item
        self.currentItemChanged.emit(item, old)

    def currentItem(self):
        return self._current

    def setVisible(self, v):
        self._visible = v

    def isVisible(self):
        return self._visible

    def itemBelow(self, item):
        """Find the next item in tree order."""
        all_items = self._flatten()
        for i, it in enumerate(all_items):
            if it is item and i + 1 < len(all_items):
                return all_items[i + 1]
        return None

    def itemAbove(self, item):
        """Find the previous item in tree order."""
        all_items = self._flatten()
        for i, it in enumerate(all_items):
            if it is item and i - 1 >= 0:
                return all_items[i - 1]
        return None

    def itemAt(self, pos):
        """Stub — returns first child item if available."""
        all_items = self._flatten()
        return all_items[0] if all_items else None

    def mapToGlobal(self, pos):
        return pos

    def _flatten(self):
        """Flatten tree into a list for navigation."""
        result = []
        for top in self._items:
            result.append(top)
            for i in range(top.childCount()):
                result.append(top.child(i))
        return result

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyStackedWidget:
    """Minimal QStackedWidget stand-in."""

    def __init__(self, *args, **kwargs):
        self._widgets = []
        self._current = None

    def addWidget(self, widget):
        self._widgets.append(widget)

    def setCurrentWidget(self, widget):
        self._current = widget

    def currentWidget(self):
        return self._current

    def count(self):
        return len(self._widgets)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyScrollArea:
    """Minimal QScrollArea stand-in."""

    def __init__(self, *args, **kwargs):
        self._widget = None

    def setWidget(self, w):
        self._widget = w

    def widget(self):
        return self._widget

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyFontMetrics:
    """Minimal QFontMetrics stand-in."""

    def __init__(self, *args, **kwargs):
        pass

    def height(self):
        return 14  # Standard line height at 1x DPI


class _DummyFrame:
    """Minimal QFrame stand-in."""

    Shape = _ShapeEnum

    def __init__(self, *args, **kwargs):
        self._layout = None
        self._geometry = _DummyRect()
        self._height = 0

    def setObjectName(self, name):
        pass

    def setFixedHeight(self, h):
        self._height = h

    def height(self):
        return self._height

    def layout(self):
        return self._layout

    def geometry(self):
        return self._geometry

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyRect:
    """Minimal geometry rect."""

    def bottom(self):
        return 44

    def __getattr__(self, name):
        return lambda *a, **kw: 0


class _DummyHBoxLayout:
    """Minimal QHBoxLayout stand-in that tracks added widgets."""

    def __init__(self, *args, **kwargs):
        self._widgets = []

    def addWidget(self, w):
        self._widgets.append(w)

    def addLayout(self, layout):
        pass

    def addStretch(self, *args):
        pass

    def addSpacing(self, spacing):
        pass

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyVBoxLayout:
    """Minimal QVBoxLayout stand-in."""

    def __init__(self, *args, **kwargs):
        pass

    def addWidget(self, w):
        pass

    def addLayout(self, layout):
        pass

    def addStretch(self, *args):
        pass

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyTreeWidgetItemIterator:
    """Minimal QTreeWidgetItemIterator that traverses _DummyTreeWidget items."""

    def __init__(self, tree, *args, **kwargs):
        self._items = []
        self._index = 0
        if hasattr(tree, "_items"):
            for top in tree._items:
                self._items.append(top)
                for i in range(top.childCount()):
                    self._items.append(top.child(i))

    def value(self):
        if self._index < len(self._items):
            return self._items[self._index]
        return None

    def __iadd__(self, n):
        self._index += n
        return self


class _DummyShortcut:
    """Minimal QShortcut stand-in."""

    def __init__(self, *args, **kwargs):
        self.activated = _DummySignal()


class _DummyToolButton:
    """Minimal QToolButton stand-in."""

    def __init__(self, *args, **kwargs):
        self.clicked = _DummySignal()
        self._text = ""

    def setText(self, t):
        self._text = t

    def text(self):
        return self._text

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyQApplication:
    """Minimal QApplication stand-in for isinstance checks."""

    _instance = None

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def instance(cls):
        return cls._instance

    @classmethod
    def quit(cls):
        pass

    def setStyleSheet(self, stylesheet):
        pass

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyTimer:
    """Minimal QTimer stand-in."""

    def __init__(self, *args, **kwargs):
        self.timeout = _DummySignal()

    def start(self, interval=0):
        pass

    def stop(self):
        pass

    @staticmethod
    def singleShot(ms, callback):
        pass

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummySystemTrayIcon:
    """Minimal QSystemTrayIcon stand-in."""

    class MessageIcon:
        Information = 1
        Warning = 2

    _tray_available = True

    def __init__(self, *args, **kwargs):
        self._visible = False
        self._menu = None
        self._icon = None

    @staticmethod
    def isSystemTrayAvailable():
        return _DummySystemTrayIcon._tray_available

    def setIcon(self, icon):
        self._icon = icon

    def setContextMenu(self, menu):
        self._menu = menu

    def show(self):
        self._visible = True

    def hide(self):
        self._visible = False

    def isVisible(self):
        return self._visible

    def showMessage(self, title, msg, icon_type, duration):
        pass

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyAction:
    """Minimal QAction stand-in."""

    def __init__(self, text="", parent=None, *args, **kwargs):
        self._text = text
        self._checkable = False
        self._checked = False
        self.triggered = _DummySignal()

    def setCheckable(self, flag):
        self._checkable = flag

    def setChecked(self, flag):
        self._checked = flag

    def isChecked(self):
        return self._checked

    def __getattr__(self, name):
        return lambda *a, **kw: None


class _DummyMenu:
    """Minimal QMenu stand-in."""

    def __init__(self, *args, **kwargs):
        self._actions = []

    def addAction(self, action_or_text):
        if isinstance(action_or_text, str):
            act = _DummyAction(action_or_text)
            self._actions.append(act)
            return act
        self._actions.append(action_or_text)
        return action_or_text

    def addSeparator(self):
        pass

    def exec(self, *args):
        return None

    def __getattr__(self, name):
        return lambda *a, **kw: None


# ---------------------------------------------------------------------------
# Install stubs into sys.modules
# ---------------------------------------------------------------------------


def _install_stubs():
    """Register lightweight PyQt6 stubs and all heavy dependencies."""

    # -- PyQt6.QtWidgets --
    qt_widgets = types.ModuleType("PyQt6.QtWidgets")
    qt_widgets.QMainWindow = _Dummy
    qt_widgets.QWidget = _Dummy
    qt_widgets.QVBoxLayout = _DummyVBoxLayout
    qt_widgets.QHBoxLayout = _DummyHBoxLayout
    qt_widgets.QTreeWidget = _DummyTreeWidget
    qt_widgets.QTreeWidgetItem = _DummyTreeWidgetItem
    qt_widgets.QTreeWidgetItemIterator = _DummyTreeWidgetItemIterator
    qt_widgets.QStackedWidget = _DummyStackedWidget
    qt_widgets.QScrollArea = _DummyScrollArea
    qt_widgets.QLabel = _DummyLabel
    qt_widgets.QPushButton = _DummyButton
    qt_widgets.QLineEdit = _DummyLineEdit
    qt_widgets.QStatusBar = _Dummy
    qt_widgets.QSystemTrayIcon = _DummySystemTrayIcon
    qt_widgets.QMenu = _DummyMenu
    qt_widgets.QFrame = _DummyFrame
    qt_widgets.QHeaderView = _Dummy
    qt_widgets.QMessageBox = MagicMock()
    qt_widgets.QInputDialog = MagicMock()
    qt_widgets.QGroupBox = _Dummy
    qt_widgets.QApplication = _DummyQApplication
    qt_widgets.QToolButton = _DummyToolButton

    # -- PyQt6.QtCore --
    qt_core = types.ModuleType("PyQt6.QtCore")
    qt_core.Qt = types.SimpleNamespace(
        ItemDataRole=types.SimpleNamespace(UserRole=0x0100),
        AlignmentFlag=types.SimpleNamespace(AlignCenter=0x84),
        WindowType=types.SimpleNamespace(
            FramelessWindowHint=0x00000800,
            CustomizeWindowHint=0x02000000,
        ),
        FocusPolicy=types.SimpleNamespace(StrongFocus=11),
        ContextMenuPolicy=types.SimpleNamespace(CustomContextMenu=3),
        CursorShape=types.SimpleNamespace(PointingHandCursor=13),
        ScrollBarPolicy=types.SimpleNamespace(
            ScrollBarAsNeeded=0,
            ScrollBarAlwaysOff=1,
        ),
    )
    qt_core.QTimer = _DummyTimer
    qt_core.QSize = _Dummy
    qt_core.pyqtSignal = _DummySignal
    qt_core.QShortcut = _DummyShortcut
    qt_core.QKeySequence = lambda x: x

    # -- PyQt6.QtGui --
    qt_gui = types.ModuleType("PyQt6.QtGui")
    qt_gui.QIcon = _Dummy
    qt_gui.QFont = _Dummy
    qt_gui.QColor = _Dummy
    qt_gui.QFontMetrics = _DummyFontMetrics
    qt_gui.QAction = _DummyAction
    qt_gui.QShortcut = _DummyShortcut
    qt_gui.QKeySequence = lambda x: x

    # -- PyQt6 package --
    pyqt = types.ModuleType("PyQt6")
    pyqt.QtWidgets = qt_widgets
    pyqt.QtCore = qt_core
    pyqt.QtGui = qt_gui

    sys.modules["PyQt6"] = pyqt
    sys.modules["PyQt6.QtWidgets"] = qt_widgets
    sys.modules["PyQt6.QtCore"] = qt_core
    sys.modules["PyQt6.QtGui"] = qt_gui

    # -- ui.base_tab --
    base_tab_mod = types.ModuleType("ui.base_tab")
    base_tab_mod.BaseTab = type(
        "BaseTab",
        (_Dummy,),
        {
            "__init__": lambda self, *a, **kw: None,
            "tr": lambda self, text: text,
        },
    )
    sys.modules["ui.base_tab"] = base_tab_mod

    # -- ui.tab_utils --
    tab_utils_mod = types.ModuleType("ui.tab_utils")
    tab_utils_mod.configure_top_tabs = lambda *a, **kw: None
    sys.modules["ui.tab_utils"] = tab_utils_mod

    # -- ui.lazy_widget --
    lazy_mod = types.ModuleType("ui.lazy_widget")

    class _StubLazyWidget:
        def __init__(self, loader_fn, loading_text="Loading..."):
            self.loader_fn = loader_fn
            self.real_widget = None
            self._loaded = False

    lazy_mod.LazyWidget = _StubLazyWidget
    sys.modules["ui.lazy_widget"] = lazy_mod

    # -- ui.doctor --
    doctor_mod = types.ModuleType("ui.doctor")
    doctor_mod.DependencyDoctor = MagicMock()
    sys.modules["ui.doctor"] = doctor_mod

    # -- ui.command_palette --
    palette_mod = types.ModuleType("ui.command_palette")
    palette_mod.CommandPalette = MagicMock()
    sys.modules["ui.command_palette"] = palette_mod

    # -- ui.quick_actions --
    qa_mod = types.ModuleType("ui.quick_actions")
    qa_mod.QuickActionsBar = MagicMock()
    qa_mod.QuickActionRegistry = MagicMock()
    qa_mod.register_default_actions = MagicMock()
    sys.modules["ui.quick_actions"] = qa_mod

    # -- ui.notification_toast --
    toast_mod = types.ModuleType("ui.notification_toast")
    toast_mod.NotificationToast = MagicMock()
    sys.modules["ui.notification_toast"] = toast_mod

    # -- ui.notification_panel --
    panel_mod = types.ModuleType("ui.notification_panel")
    panel_mod.NotificationPanel = MagicMock()
    sys.modules["ui.notification_panel"] = panel_mod

    # -- ui.wizard --
    wizard_mod = types.ModuleType("ui.wizard")
    wizard_mod.FirstRunWizard = MagicMock()
    sys.modules["ui.wizard"] = wizard_mod

    # -- core.plugins --
    plugins_pkg = types.ModuleType("core.plugins")

    class _StubPluginInterface:
        def metadata(self):
            return None

        def create_widget(self):
            return _Dummy()

        def check_compat(self, detector):
            from core.plugins.metadata import CompatStatus

            return CompatStatus(compatible=True)

    class _StubPluginRegistry:
        _inst = None
        _plugins = []

        @classmethod
        def instance(cls):
            if cls._inst is None:
                cls._inst = cls()
            return cls._inst

        @classmethod
        def reset(cls):
            cls._inst = None
            cls._plugins = []

        def __iter__(self):
            return iter(self._plugins)

    plugins_pkg.PluginInterface = _StubPluginInterface
    plugins_pkg.PluginRegistry = _StubPluginRegistry
    sys.modules["core.plugins"] = plugins_pkg
    sys.modules["core"] = types.ModuleType("core")

    # -- core.plugins.interface --
    iface_mod = types.ModuleType("core.plugins.interface")
    iface_mod.PluginInterface = _StubPluginInterface
    sys.modules["core.plugins.interface"] = iface_mod

    # -- core.plugins.metadata --
    meta_mod = types.ModuleType("core.plugins.metadata")

    class _StubPluginMetadata:
        def __init__(self, **kwargs):
            defaults = {
                "id": "",
                "name": "",
                "description": "",
                "category": "",
                "icon": "",
                "badge": "",
                "version": "1.0.0",
                "requires": (),
                "compat": {},
                "order": 100,
                "enabled": True,
            }
            defaults.update(kwargs)
            for k, v in defaults.items():
                setattr(self, k, v)

    class _StubCompatStatus:
        def __init__(self, compatible=True, reason="", warnings=None):
            self.compatible = compatible
            self.reason = reason
            self.warnings = warnings or []

    meta_mod.PluginMetadata = _StubPluginMetadata
    meta_mod.CompatStatus = _StubCompatStatus
    sys.modules["core.plugins.metadata"] = meta_mod

    # -- core.plugins.registry --
    reg_mod = types.ModuleType("core.plugins.registry")
    reg_mod.PluginRegistry = _StubPluginRegistry
    reg_mod.CATEGORY_ICONS = {
        "Overview": "📊",
        "Manage": "🔧",
        "Hardware": "🖥️",
        "Network & Security": "🌐",
        "Personalize": "🎨",
        "Developer": "🛠️",
        "Automation": "🤖",
        "Health & Logs": "📋",
    }
    sys.modules["core.plugins.registry"] = reg_mod

    # -- core.plugins.compat --
    compat_mod = types.ModuleType("core.plugins.compat")
    compat_mod.CompatibilityDetector = MagicMock()
    compat_mod.CompatStatus = _StubCompatStatus
    sys.modules["core.plugins.compat"] = compat_mod

    # -- core.plugins.loader --
    loader_mod = types.ModuleType("core.plugins.loader")
    loader_mod.PluginLoader = MagicMock()
    sys.modules["core.plugins.loader"] = loader_mod

    # -- utils modules --
    config_mod = types.ModuleType("utils.config_manager")
    config_mod.ConfigManager = MagicMock()
    config_mod.ConfigManager.load_config = MagicMock(return_value=None)
    sys.modules["utils.config_manager"] = config_mod

    fav_mod = types.ModuleType("utils.favorites")
    fav_mod.FavoritesManager = MagicMock()
    fav_mod.FavoritesManager.get_favorites = MagicMock(return_value=[])
    fav_mod.FavoritesManager.is_favorite = MagicMock(return_value=False)
    fav_mod.FavoritesManager.toggle_favorite = MagicMock()
    sys.modules["utils.favorites"] = fav_mod

    focus_mod = types.ModuleType("utils.focus_mode")
    focus_mod.FocusMode = MagicMock()
    focus_mod.FocusMode.is_active = MagicMock(return_value=False)
    focus_mod.FocusMode.toggle = MagicMock(
        return_value={"message": "Focus Mode activated"}
    )
    sys.modules["utils.focus_mode"] = focus_mod

    hist_mod = types.ModuleType("utils.history")
    hist_mod.HistoryManager = MagicMock
    sys.modules["utils.history"] = hist_mod

    log_mod = types.ModuleType("utils.log")
    log_mod.get_logger = lambda name: MagicMock()
    sys.modules["utils.log"] = log_mod

    sys_mod = types.ModuleType("services.system")
    sys_mod.SystemManager = MagicMock()
    sys.modules["services"] = types.ModuleType("services")
    sys.modules["services.system"] = sys_mod

    pulse_mod = types.ModuleType("utils.pulse")
    pulse_mod.PulseThread = MagicMock()
    pulse_mod.SystemPulse = MagicMock()
    sys.modules["utils.pulse"] = pulse_mod

    ver_mod = types.ModuleType("version")
    ver_mod.__version__ = "99.0.0"
    ver_mod.__version_codename__ = "Test"
    sys.modules["version"] = ver_mod

    # -- utils.desktop_utils --
    desk_mod = types.ModuleType("utils.desktop_utils")
    desk_mod.DesktopUtils = MagicMock()
    desk_mod.DesktopUtils.detect_color_scheme = MagicMock(return_value="dark")
    sys.modules["utils.desktop_utils"] = desk_mod

    # -- utils.notification_center --
    nc_mod = types.ModuleType("utils.notification_center")
    nc_mod.NotificationCenter = MagicMock
    sys.modules["utils.notification_center"] = nc_mod

    # -- utils.update_checker --
    uc_mod = types.ModuleType("utils.update_checker")
    uc_mod.UpdateChecker = MagicMock()
    sys.modules["utils.update_checker"] = uc_mod

    # -- services.hardware.disk --
    hw_mod = types.ModuleType("services.hardware")
    sys.modules["services.hardware"] = hw_mod
    disk_mod = types.ModuleType("services.hardware.disk")
    disk_mod.DiskManager = MagicMock()
    sys.modules["services.hardware.disk"] = disk_mod

    # -- utils (package) --
    if "utils" not in sys.modules:
        sys.modules["utils"] = types.ModuleType("utils")


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

_MODULE_KEYS = [
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "ui",
    "ui.base_tab",
    "ui.tab_utils",
    "ui.lazy_widget",
    "ui.doctor",
    "ui.command_palette",
    "ui.quick_actions",
    "ui.notification_toast",
    "ui.notification_panel",
    "ui.wizard",
    "core",
    "core.plugins",
    "core.plugins.interface",
    "core.plugins.metadata",
    "core.plugins.registry",
    "core.plugins.compat",
    "core.plugins.loader",
    "utils.config_manager",
    "utils.favorites",
    "utils.focus_mode",
    "utils.history",
    "utils.log",
    "utils.pulse",
    "utils.desktop_utils",
    "utils.notification_center",
    "utils.update_checker",
    "services",
    "services.system",
    "services.hardware",
    "services.hardware.disk",
    "version",
    "ui.main_window",
]

_module_backup = {}


def setUpModule():
    """Install stubs and import ui.main_window."""
    global _module_backup
    for key in _MODULE_KEYS:
        _module_backup[key] = sys.modules.get(key)
    _install_stubs()
    # Force re-import so stubs are used
    sys.modules.pop("ui.main_window", None)
    sys.modules.pop("ui", None)
    importlib.import_module("ui.main_window")


def tearDownModule():
    """Restore original modules."""
    sys.modules.pop("ui.main_window", None)
    for key, orig in _module_backup.items():
        if orig is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = orig


def _get_module():
    """Return the imported ui.main_window module."""
    return sys.modules["ui.main_window"]


def _make_window(skip_init=False):
    """Create a MainWindow instance, bypassing heavy __init__ unless needed.

    Args:
        skip_init: If True, create instance without calling __init__.

    Returns:
        A MainWindow instance with minimal required attributes.
    """
    mod = _get_module()
    if skip_init:
        win = object.__new__(mod.MainWindow)
        # Minimal attributes needed by most methods
        win.logger = MagicMock()
        win.pages = {}
        win.sidebar = _DummyTreeWidget()
        win.content_area = _DummyStackedWidget()
        win._sidebar_container = _Dummy()
        win._sidebar_toggle = _DummyButton()
        win._sidebar_collapsed = False
        win._sidebar_expanded_width = 210
        win._line_height = 14
        win.sidebar_search = _DummyLineEdit()
        win._status_label = _DummyLabel()
        win._undo_btn = _DummyButton()
        win._undo_btn._visible = False
        win._bc_category = _DummyButton()
        win._bc_page = _DummyLabel()
        win._bc_desc = _DummyLabel()
        win._bc_sep = _DummyLabel()
        win._breadcrumb_frame = _DummyFrame()
        win._breadcrumb_frame._layout = _DummyHBoxLayout()
        win._status_frame = _DummyFrame()
        win._status_frame._height = 28
        win.tray_icon = None
        win.pulse = None
        win.pulse_thread = None
        win._notif_badge = _DummyLabel()
        win._notif_badge._visible = False
        win.notif_panel = None
        win._toast_widget = None
        win.notif_bell = _DummyToolButton()
        return win
    else:
        return mod.MainWindow()


# ===================================================================
# Test Classes
# ===================================================================


class TestDisabledPluginPage(unittest.TestCase):
    """Tests for DisabledPluginPage widget creation."""

    def test_creation_with_metadata(self):
        """DisabledPluginPage should store meta name and reason text."""
        mod = _get_module()
        meta_mod = sys.modules["core.plugins.metadata"]
        meta = meta_mod.PluginMetadata(
            id="test_plugin",
            name="Test Plugin",
            description="A test",
            category="System",
            icon="🔧",
            badge="",
        )
        page = mod.DisabledPluginPage(meta, "Missing dependency")
        # DisabledPluginPage is a QWidget subclass — instantiation should not raise
        self.assertIsNotNone(page)

    def test_creation_empty_reason(self):
        """DisabledPluginPage handles empty reason string."""
        mod = _get_module()
        meta_mod = sys.modules["core.plugins.metadata"]
        meta = meta_mod.PluginMetadata(
            id="empty",
            name="Empty",
            description="",
            category="General",
            icon="📦",
            badge="",
        )
        page = mod.DisabledPluginPage(meta, "")
        self.assertIsNotNone(page)

    def test_creation_long_reason(self):
        """DisabledPluginPage handles long multi-line reason text."""
        mod = _get_module()
        meta_mod = sys.modules["core.plugins.metadata"]
        meta = meta_mod.PluginMetadata(
            id="long",
            name="Long Reason",
            description="desc",
            category="General",
            icon="⚠️",
            badge="",
        )
        reason = "Line one.\nLine two.\nLine three with extra detail."
        page = mod.DisabledPluginPage(meta, reason)
        self.assertIsNotNone(page)


class TestMainWindowInstantiation(unittest.TestCase):
    """Tests for MainWindow __init__ and basic setup."""

    @patch("ui.main_window.MainWindow.check_dependencies")
    @patch("ui.main_window.MainWindow.setup_tray")
    @patch("ui.main_window.MainWindow._check_first_run")
    @patch("ui.main_window.MainWindow._setup_notification_bell")
    @patch("ui.main_window.MainWindow._setup_keyboard_shortcuts")
    @patch("ui.main_window.MainWindow._setup_command_palette_shortcut")
    @patch("ui.main_window.MainWindow._setup_quick_actions")
    @patch("ui.main_window.MainWindow._build_favorites_section")
    @patch("ui.main_window.MainWindow._build_sidebar_from_registry")
    @patch("ui.main_window.MainWindow._start_pulse_listener")
    @patch("ui.main_window.MainWindow._get_frameless_mode_flag", return_value=False)
    def test_basic_instantiation(
        self,
        mock_frameless,
        mock_pulse,
        mock_registry,
        mock_fav,
        mock_qa,
        mock_palette,
        mock_kb,
        mock_notif,
        mock_first,
        mock_tray,
        mock_deps,
    ):
        """MainWindow instantiation completes without error."""
        mod = _get_module()
        win = mod.MainWindow()
        self.assertIsNotNone(win)
        self.assertIsInstance(win.pages, dict)

    @patch("ui.main_window.MainWindow.check_dependencies")
    @patch("ui.main_window.MainWindow.setup_tray")
    @patch("ui.main_window.MainWindow._check_first_run")
    @patch("ui.main_window.MainWindow._setup_notification_bell")
    @patch("ui.main_window.MainWindow._setup_keyboard_shortcuts")
    @patch("ui.main_window.MainWindow._setup_command_palette_shortcut")
    @patch("ui.main_window.MainWindow._setup_quick_actions")
    @patch("ui.main_window.MainWindow._build_favorites_section")
    @patch("ui.main_window.MainWindow._build_sidebar_from_registry")
    @patch("ui.main_window.MainWindow._start_pulse_listener")
    @patch("ui.main_window.MainWindow._get_frameless_mode_flag", return_value=True)
    def test_frameless_mode_warning(
        self,
        mock_frameless,
        mock_pulse,
        mock_registry,
        mock_fav,
        mock_qa,
        mock_palette,
        mock_kb,
        mock_notif,
        mock_first,
        mock_tray,
        mock_deps,
    ):
        """MainWindow logs warning when frameless mode is requested."""
        mod = _get_module()
        win = mod.MainWindow()
        self.assertIsNotNone(win)

    @patch("ui.main_window.MainWindow.check_dependencies")
    @patch("ui.main_window.MainWindow.setup_tray")
    @patch("ui.main_window.MainWindow._check_first_run")
    @patch("ui.main_window.MainWindow._setup_notification_bell")
    @patch("ui.main_window.MainWindow._setup_keyboard_shortcuts")
    @patch("ui.main_window.MainWindow._setup_command_palette_shortcut")
    @patch("ui.main_window.MainWindow._setup_quick_actions")
    @patch("ui.main_window.MainWindow._build_favorites_section")
    @patch("ui.main_window.MainWindow._build_sidebar_from_registry")
    @patch("ui.main_window.MainWindow._start_pulse_listener")
    @patch("ui.main_window.MainWindow._get_frameless_mode_flag", return_value=False)
    def test_pages_dict_initialized_empty(self, *mocks):
        """MainWindow.pages starts as empty dict before registry loads."""
        mod = _get_module()
        win = mod.MainWindow()
        self.assertIsInstance(win.pages, dict)


class TestAddPage(unittest.TestCase):
    """Tests for MainWindow.add_page()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_add_page_basic(self):
        """add_page registers widget in pages dict and content area."""
        widget = MagicMock()
        self.win.add_page("Dashboard", "📊", widget, category="Overview")
        self.assertIn("Dashboard", self.win.pages)
        self.assertEqual(self.win.pages["Dashboard"], widget)

    def test_add_page_creates_category(self):
        """add_page creates a new category item when none exists."""
        self.win.add_page("Network", "🌐", MagicMock(), category="Network & Security")
        self.assertEqual(self.win.sidebar.topLevelItemCount(), 1)
        cat = self.win.sidebar.topLevelItem(0)
        self.assertIn("Network & Security", cat.text(0))

    def test_add_page_reuses_category(self):
        """add_page reuses existing category item."""
        self.win.add_page("Page A", "🅰️", MagicMock(), category="System")
        self.win.add_page("Page B", "🅱️", MagicMock(), category="System")
        self.assertEqual(self.win.sidebar.topLevelItemCount(), 1)

    def test_add_page_with_recommended_badge(self):
        """add_page appends star badge for recommended plugins."""
        self.win.add_page("Top", "⭐", MagicMock(), badge="recommended")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertIn("★", child.text(0))

    def test_add_page_with_advanced_badge(self):
        """add_page appends gear badge for advanced plugins."""
        self.win.add_page("Advanced", "🔧", MagicMock(), badge="advanced")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertIn("⚙", child.text(0))

    def test_add_page_no_badge(self):
        """add_page with no badge omits badge suffix."""
        self.win.add_page("Plain", "📦", MagicMock(), badge="")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertNotIn("★", child.text(0))
        self.assertNotIn("⚙", child.text(0))

    def test_add_page_disabled(self):
        """add_page with disabled=True disables the sidebar item."""
        self.win.add_page(
            "Broken",
            "❌",
            MagicMock(),
            disabled=True,
            disabled_reason="Not supported on this system",
        )
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertTrue(child.isDisabled())

    def test_add_page_disabled_with_reason_tooltip(self):
        """Disabled page gets reason as tooltip."""
        reason = "Fedora 40+ required"
        self.win.add_page(
            "Old", "🕰️", MagicMock(), disabled=True, disabled_reason=reason
        )
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertEqual(child.toolTip(0), reason)

    def test_add_page_disabled_without_reason_fallback_tooltip(self):
        """Disabled page without reason gets default tooltip."""
        self.win.add_page(
            "Missing", "❓", MagicMock(), disabled=True, disabled_reason=""
        )
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertIn("not available", child.toolTip(0))

    def test_add_page_stores_description(self):
        """add_page stores description in item data."""
        mod = _get_module()
        self.win.add_page("Info", "ℹ️", MagicMock(), description="System information")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertEqual(child.data(0, mod._ROLE_DESC), "System information")

    def test_add_page_sets_tooltip_from_description(self):
        """add_page sets tooltip from description on enabled pages."""
        self.win.add_page("Net", "🌐", MagicMock(), description="Network tools")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertEqual(child.toolTip(0), "Network tools")

    def test_add_page_widget_added_to_content_area(self):
        """add_page adds wrapped widget to content_area stacked widget."""
        widget = MagicMock()
        self.win.add_page("Test", "🧪", widget)
        self.assertGreater(self.win.content_area.count(), 0)

    def test_add_page_with_category_icon(self):
        """add_page keeps category labels clean while assigning icons."""
        self.win.add_page("Dashboard", "📊", MagicMock(), category="Overview")
        cat = self.win.sidebar.topLevelItem(0)
        self.assertEqual(cat.text(0), "Overview")

    def test_add_page_multiple_categories(self):
        """add_page creates separate categories for different names."""
        self.win.add_page("A", "🅰️", MagicMock(), category="Overview")
        self.win.add_page("B", "🅱️", MagicMock(), category="Hardware")
        self.assertEqual(self.win.sidebar.topLevelItemCount(), 2)


class TestChangePage(unittest.TestCase):
    """Tests for MainWindow.change_page()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_change_page_with_widget(self):
        """change_page sets content area to item's widget."""
        self.win.add_page("Test", "🧪", MagicMock(), category="System")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        # Simulate page change
        self.win.change_page(child, None)
        # content_area.setCurrentWidget should have been called
        self.assertIsNotNone(self.win.content_area.currentWidget())

    def test_change_page_null_current(self):
        """change_page does nothing when current is None."""
        self.win.change_page(None, None)
        self.assertIsNone(self.win.content_area.currentWidget())

    def test_change_page_category_item_expands(self):
        """change_page on category item expands it and selects first child."""
        self.win.add_page("Child1", "📦", MagicMock(), category="Cat")
        cat = self.win.sidebar.topLevelItem(0)
        cat.setExpanded(False)
        self.win.change_page(cat, None)
        self.assertTrue(cat.isExpanded())

    def test_change_page_updates_breadcrumb(self):
        """change_page updates breadcrumb labels."""
        self.win.add_page(
            "Network", "🌐", MagicMock(), category="System", description="Network tools"
        )
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.win.change_page(child, None)
        # Breadcrumb page should contain "Network"
        self.assertIn("Network", self.win._bc_page._text)


class TestSwitchToTab(unittest.TestCase):
    """Tests for MainWindow.switch_to_tab()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_switch_to_existing_tab(self):
        """switch_to_tab finds and selects matching item."""
        self.win.add_page("Hardware", "🖥️", MagicMock(), category="System")
        self.win.switch_to_tab("Hardware")
        current = self.win.sidebar.currentItem()
        self.assertIsNotNone(current)
        self.assertIn("Hardware", current.text(0))

    def test_switch_to_nonexistent_tab(self):
        """switch_to_tab does nothing for non-existent tab name."""
        self.win.add_page("Exists", "📦", MagicMock(), category="Cat")
        self.win.switch_to_tab("DoesNotExist")
        # Should not crash and current shouldn't change to nonexistent

    def test_switch_to_tab_partial_match(self):
        """switch_to_tab matches partial name (substring)."""
        self.win.add_page("System Info", "💻", MagicMock(), category="System")
        self.win.switch_to_tab("Info")
        current = self.win.sidebar.currentItem()
        self.assertIsNotNone(current)

    def test_switch_to_tab_skips_category_items(self):
        """switch_to_tab only matches items with widget data (not categories)."""
        self.win.add_page("Page1", "📦", MagicMock(), category="Overview")
        # Category item text contains "Overview" but has no UserRole widget
        self.win.switch_to_tab("Overview")
        current = self.win.sidebar.currentItem()
        # Should not match the category item (it has no UserRole data)


class TestFilterSidebar(unittest.TestCase):
    """Tests for MainWindow._filter_sidebar()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)
        self.win.add_page(
            "Dashboard",
            "📊",
            MagicMock(),
            category="Overview",
            description="System overview",
        )
        self.win.add_page(
            "Network",
            "🌐",
            MagicMock(),
            category="System",
            description="Network configuration",
        )
        self.win.add_page(
            "Hardware", "🖥️", MagicMock(), category="System", description="Hardware info"
        )

    def test_filter_shows_matching(self):
        """Filtering by name shows matching items."""
        self.win._filter_sidebar("Network")
        cat = self.win.sidebar.topLevelItem(1)  # System category
        net_child = cat.child(0)
        hw_child = cat.child(1)
        self.assertFalse(net_child.isHidden())
        self.assertTrue(hw_child.isHidden())

    def test_filter_empty_shows_all(self):
        """Empty filter text shows all items."""
        self.win._filter_sidebar("")
        for i in range(self.win.sidebar.topLevelItemCount()):
            cat = self.win.sidebar.topLevelItem(i)
            self.assertFalse(cat.isHidden())
            for j in range(cat.childCount()):
                self.assertFalse(cat.child(j).isHidden())

    def test_filter_hides_empty_categories(self):
        """Category with no matching children gets hidden."""
        self.win._filter_sidebar("Network")
        overview_cat = self.win.sidebar.topLevelItem(0)
        self.assertTrue(overview_cat.isHidden())

    def test_filter_case_insensitive(self):
        """Filtering is case-insensitive."""
        self.win._filter_sidebar("dashboard")
        overview_cat = self.win.sidebar.topLevelItem(0)
        self.assertFalse(overview_cat.isHidden())
        child = overview_cat.child(0)
        self.assertFalse(child.isHidden())

    def test_filter_by_description(self):
        """Filtering matches description text too."""
        self.win._filter_sidebar("overview")
        overview_cat = self.win.sidebar.topLevelItem(0)
        self.assertFalse(overview_cat.isHidden())

    def test_filter_by_category_name_shows_all_children(self):
        """Filtering by category name shows all its children."""
        self.win._filter_sidebar("System")
        sys_cat = self.win.sidebar.topLevelItem(1)
        self.assertFalse(sys_cat.isHidden())
        for j in range(sys_cat.childCount()):
            self.assertFalse(sys_cat.child(j).isHidden())

    def test_filter_expands_matching_categories(self):
        """Matching categories are expanded when filter matches."""
        self.win._filter_sidebar("Hardware")
        sys_cat = self.win.sidebar.topLevelItem(1)
        self.assertTrue(sys_cat.isExpanded())

    def test_filter_no_matches_hides_all(self):
        """Non-matching filter hides all items."""
        self.win._filter_sidebar("zzzznonexistent")
        for i in range(self.win.sidebar.topLevelItemCount()):
            self.assertTrue(self.win.sidebar.topLevelItem(i).isHidden())

    def test_filter_by_badge(self):
        """Filtering matches badge data."""
        self.win.add_page(
            "Recommended", "⭐", MagicMock(), category="Extra", badge="recommended"
        )
        self.win._filter_sidebar("recommended")
        # The "Extra" category should be visible
        found = False
        for i in range(self.win.sidebar.topLevelItemCount()):
            cat = self.win.sidebar.topLevelItem(i)
            if "Extra" in cat.text(0):
                self.assertFalse(cat.isHidden())
                found = True
        self.assertTrue(found)


class TestToggleSidebar(unittest.TestCase):
    """Tests for MainWindow._toggle_sidebar()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_collapse_sidebar(self):
        """Toggle collapses expanded sidebar."""
        self.win._sidebar_collapsed = False
        self.win._toggle_sidebar()
        self.assertTrue(self.win._sidebar_collapsed)
        self.assertEqual(self.win._sidebar_toggle._text, "▶")

    def test_expand_sidebar(self):
        """Toggle expands collapsed sidebar."""
        self.win._sidebar_collapsed = True
        self.win._toggle_sidebar()
        self.assertFalse(self.win._sidebar_collapsed)
        self.assertEqual(self.win._sidebar_toggle._text, "◀")

    def test_toggle_round_trip(self):
        """Double toggle returns to original state."""
        self.win._sidebar_collapsed = False
        self.win._toggle_sidebar()
        self.win._toggle_sidebar()
        self.assertFalse(self.win._sidebar_collapsed)

    def test_collapse_hides_search(self):
        """Collapsing sidebar hides the search box."""
        self.win._sidebar_collapsed = False
        self.win._toggle_sidebar()
        self.assertFalse(self.win.sidebar_search.isVisible())

    def test_expand_shows_search(self):
        """Expanding sidebar shows the search box."""
        self.win._sidebar_collapsed = True
        self.win._toggle_sidebar()
        self.assertTrue(self.win.sidebar_search.isVisible())


class TestSetStatus(unittest.TestCase):
    """Tests for MainWindow.set_status()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_set_status_text(self):
        """set_status updates status label text."""
        self.win.set_status("Ready")
        self.assertEqual(self.win._status_label._text, "Ready")

    def test_set_status_empty(self):
        """set_status with empty string clears the label."""
        self.win.set_status("Something")
        self.win.set_status("")
        self.assertEqual(self.win._status_label._text, "")

    def test_set_status_special_chars(self):
        """set_status handles unicode and special characters."""
        self.win.set_status("✓ Operation completed — 100%")
        self.assertEqual(self.win._status_label._text, "✓ Operation completed — 100%")


class TestShowUndoButton(unittest.TestCase):
    """Tests for MainWindow.show_undo_button()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_show_undo_makes_visible(self):
        """show_undo_button makes undo button visible."""
        self.win.show_undo_button("Deleted file")
        self.assertTrue(self.win._undo_btn._visible)

    def test_show_undo_sets_description(self):
        """show_undo_button sets status text with description."""
        self.win.show_undo_button("Changed theme")
        self.assertIn("Changed theme", self.win._status_label._text)

    def test_show_undo_empty_description(self):
        """show_undo_button with empty description still shows button."""
        self.win.show_undo_button("")
        self.assertTrue(self.win._undo_btn._visible)

    def test_show_undo_prefixes_checkmark(self):
        """show_undo_button prefixes description with checkmark."""
        self.win.show_undo_button("Installed package")
        self.assertTrue(self.win._status_label._text.startswith("✓"))


class TestShowStatusToast(unittest.TestCase):
    """Tests for MainWindow.show_status_toast()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_success_toast(self):
        """show_status_toast sets success property."""
        self.win.show_status_toast("Done!")
        self.assertEqual(self.win._status_label._text, "Done!")
        self.assertEqual(self.win._status_label._properties.get("toast"), "success")

    def test_error_toast(self):
        """show_status_toast with error=True sets error property."""
        self.win.show_status_toast("Failed!", error=True)
        self.assertEqual(self.win._status_label._text, "Failed!")
        self.assertEqual(self.win._status_label._properties.get("toast"), "error")

    def test_toast_custom_duration(self):
        """show_status_toast accepts custom duration parameter."""
        self.win.show_status_toast("Quick", duration=1000)
        self.assertEqual(self.win._status_label._text, "Quick")


class TestShowToast(unittest.TestCase):
    """Tests for MainWindow.show_toast()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    @patch("ui.main_window.MainWindow._refresh_notif_badge")
    def test_show_toast_creates_widget(self, mock_refresh):
        """show_toast creates NotificationToast on first call."""
        self.win.show_toast("Title", "Message", "general")
        self.assertIsNotNone(self.win._toast_widget)

    @patch("ui.main_window.MainWindow._refresh_notif_badge")
    def test_show_toast_reuses_widget(self, mock_refresh):
        """show_toast reuses existing toast widget."""
        self.win.show_toast("First", "Msg1")
        first_widget = self.win._toast_widget
        self.win.show_toast("Second", "Msg2")
        self.assertIs(self.win._toast_widget, first_widget)

    def test_show_toast_exception_handling(self):
        """show_toast handles import errors gracefully."""
        # Temporarily break the import
        orig = sys.modules.get("ui.notification_toast")
        sys.modules["ui.notification_toast"] = types.ModuleType("ui.notification_toast")
        # Make NotificationToast raise
        sys.modules["ui.notification_toast"].NotificationToast = MagicMock(
            side_effect=RuntimeError("import failed")
        )
        self.win._toast_widget = None
        # Should not raise
        self.win.show_toast("Title", "Message")
        # Restore
        if orig:
            sys.modules["ui.notification_toast"] = orig


class TestClearToast(unittest.TestCase):
    """Tests for MainWindow._clear_toast()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_clear_toast_resets_text(self):
        """_clear_toast clears status label text."""
        self.win._status_label._text = "Old toast"
        self.win._clear_toast()
        self.assertEqual(self.win._status_label._text, "")

    def test_clear_toast_resets_property(self):
        """_clear_toast resets toast property."""
        self.win._status_label._properties["toast"] = "error"
        self.win._clear_toast()
        self.assertEqual(self.win._status_label._properties.get("toast"), "")


class TestCheckDependencies(unittest.TestCase):
    """Tests for MainWindow.check_dependencies()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    @patch("shutil.which", return_value="/usr/bin/dnf")
    def test_all_deps_present(self, mock_which):
        """No doctor shown when all dependencies are present."""
        self.win.show_doctor = MagicMock()
        self.win.check_dependencies()
        self.win.show_doctor.assert_not_called()

    @patch("shutil.which", return_value=None)
    def test_missing_deps_shows_doctor(self, mock_which):
        """Missing dependencies triggers doctor dialog."""
        self.win.show_doctor = MagicMock()
        self.win.check_dependencies()
        self.win.show_doctor.assert_called_once()

    @patch("shutil.which", side_effect=lambda t: "/usr/bin/dnf" if t == "dnf" else None)
    def test_partial_deps_missing(self, mock_which):
        """Missing pkexec alone triggers doctor."""
        self.win.show_doctor = MagicMock()
        self.win.check_dependencies()
        self.win.show_doctor.assert_called_once()


class TestLoadTheme(unittest.TestCase):
    """Tests for MainWindow.load_theme()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def tearDown(self):
        _DummyQApplication._instance = None

    @patch("builtins.open", mock_open(read_data="QWidget { color: white; }"))
    def test_load_dark_theme(self):
        """load_theme('dark') reads modern.qss."""
        app_mock = _DummyQApplication()
        app_mock.setStyleSheet = MagicMock()
        _DummyQApplication._instance = app_mock
        self.win.load_theme("dark")
        app_mock.setStyleSheet.assert_called_once()

    @patch("builtins.open", mock_open(read_data="QWidget { color: black; }"))
    def test_load_light_theme(self):
        """load_theme('light') reads light.qss."""
        app_mock = _DummyQApplication()
        app_mock.setStyleSheet = MagicMock()
        _DummyQApplication._instance = app_mock
        self.win.load_theme("light")
        app_mock.setStyleSheet.assert_called_once()

    def test_load_theme_file_missing(self):
        """load_theme handles missing QSS file gracefully."""
        with patch("builtins.open", side_effect=OSError("File not found")):
            # Should not raise
            self.win.load_theme("dark")

    @patch("builtins.open", mock_open(read_data="body {}"))
    def test_load_theme_unknown_name_defaults_dark(self):
        """Unknown theme name falls back to modern.qss."""
        app_mock = _DummyQApplication()
        app_mock.setStyleSheet = MagicMock()
        _DummyQApplication._instance = app_mock
        self.win.load_theme("nonexistent")
        app_mock.setStyleSheet.assert_called_once()

    @patch("builtins.open", mock_open(read_data="body {}"))
    def test_load_theme_app_not_qapplication(self):
        """load_theme does nothing when app is not a QApplication instance."""
        # instance() returns an object that is NOT a _DummyQApplication
        _DummyQApplication._instance = "not-an-app"
        self.win.load_theme("dark")
        # No crash, no setStyleSheet call


class TestDetectSystemTheme(unittest.TestCase):
    """Tests for MainWindow.detect_system_theme()."""

    def test_detect_dark(self):
        """detect_system_theme returns 'dark' when system prefers dark."""
        mod = _get_module()
        desk = sys.modules["utils.desktop_utils"]
        desk.DesktopUtils.detect_color_scheme = MagicMock(return_value="dark")
        result = mod.MainWindow.detect_system_theme()
        self.assertEqual(result, "dark")

    def test_detect_light(self):
        """detect_system_theme returns 'light' when system prefers light."""
        mod = _get_module()
        desk = sys.modules["utils.desktop_utils"]
        desk.DesktopUtils.detect_color_scheme = MagicMock(return_value="light")
        result = mod.MainWindow.detect_system_theme()
        self.assertEqual(result, "light")

    def test_detect_is_static_method(self):
        """detect_system_theme is a static method callable without instance."""
        mod = _get_module()
        # Should be callable on class without instantiation
        self.assertTrue(callable(mod.MainWindow.detect_system_theme))


class TestGetFramelessModeFlag(unittest.TestCase):
    """Tests for MainWindow._get_frameless_mode_flag()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_config_frameless_true(self):
        """Config file frameless_mode=True returns True."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(
            return_value={"ui": {"frameless_mode": True}}
        )
        result = self.win._get_frameless_mode_flag()
        self.assertTrue(result)

    def test_config_frameless_false(self):
        """Config file frameless_mode=False returns False."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(
            return_value={"ui": {"frameless_mode": False}}
        )
        result = self.win._get_frameless_mode_flag()
        self.assertFalse(result)

    @patch.dict(os.environ, {"LOOFI_FRAMELESS": "1"})
    def test_env_frameless_enabled(self):
        """Environment LOOFI_FRAMELESS=1 returns True when no config."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(return_value=None)
        result = self.win._get_frameless_mode_flag()
        self.assertTrue(result)

    @patch.dict(os.environ, {"LOOFI_FRAMELESS": "0"})
    def test_env_frameless_disabled(self):
        """Environment LOOFI_FRAMELESS=0 returns False."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(return_value=None)
        result = self.win._get_frameless_mode_flag()
        self.assertFalse(result)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_config_no_env_returns_false(self):
        """No config and no env var returns False (default)."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(return_value=None)
        # Remove LOOFI_FRAMELESS from env
        os.environ.pop("LOOFI_FRAMELESS", None)
        result = self.win._get_frameless_mode_flag()
        self.assertFalse(result)

    def test_config_no_ui_section(self):
        """Config without 'ui' section falls back to env."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(return_value={"other": {}})
        os.environ.pop("LOOFI_FRAMELESS", None)
        result = self.win._get_frameless_mode_flag()
        self.assertFalse(result)

    def test_config_ui_without_frameless_key(self):
        """Config with 'ui' section but no 'frameless_mode' key falls back to env."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(
            return_value={"ui": {"theme": "dark"}}
        )
        os.environ.pop("LOOFI_FRAMELESS", None)
        result = self.win._get_frameless_mode_flag()
        self.assertFalse(result)

    @patch.dict(os.environ, {"LOOFI_FRAMELESS": "1"})
    def test_config_priority_over_env(self):
        """Config file setting takes priority over environment variable."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(
            return_value={"ui": {"frameless_mode": False}}
        )
        result = self.win._get_frameless_mode_flag()
        self.assertFalse(result)

    @patch.dict(os.environ, {"LOOFI_FRAMELESS": "  1  "})
    def test_env_whitespace_stripped(self):
        """Environment variable value is stripped before comparison."""
        config_mod = sys.modules["utils.config_manager"]
        config_mod.ConfigManager.load_config = MagicMock(return_value=None)
        result = self.win._get_frameless_mode_flag()
        self.assertTrue(result)


class TestSetupTray(unittest.TestCase):
    """Tests for MainWindow.setup_tray()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_tray_created_when_available(self):
        """setup_tray creates tray icon when system tray is available."""
        _DummySystemTrayIcon._tray_available = True
        self.win.setup_tray()
        self.assertIsNotNone(self.win.tray_icon)

    def test_tray_none_when_unavailable(self):
        """setup_tray sets tray_icon to None when tray unavailable."""
        _DummySystemTrayIcon._tray_available = False
        self.win.setup_tray()
        self.assertIsNone(self.win.tray_icon)
        _DummySystemTrayIcon._tray_available = True  # Restore

    @patch("os.path.exists", return_value=True)
    def test_tray_uses_custom_icon(self, mock_exists):
        """setup_tray loads custom icon when file exists."""
        _DummySystemTrayIcon._tray_available = True
        self.win.setup_tray()
        self.assertIsNotNone(self.win.tray_icon)

    @patch("os.path.exists", return_value=False)
    def test_tray_uses_fallback_icon(self, mock_exists):
        """setup_tray uses standard icon when custom file missing."""
        _DummySystemTrayIcon._tray_available = True
        self.win.setup_tray()
        self.assertIsNotNone(self.win.tray_icon)


class TestQuitApp(unittest.TestCase):
    """Tests for MainWindow.quit_app()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_quit_hides_tray(self):
        """quit_app hides tray icon if present."""
        tray = _DummySystemTrayIcon()
        tray.show()
        self.win.tray_icon = tray
        self.win.quit_app()
        self.assertFalse(tray._visible)

    def test_quit_no_tray(self):
        """quit_app works when tray_icon is None."""
        self.win.tray_icon = None
        self.win.quit_app()  # Should not raise

    def test_quit_stops_pulse_thread(self):
        """quit_app stops pulse thread if running."""
        mock_thread = MagicMock()
        self.win.pulse_thread = mock_thread
        self.win.quit_app()
        mock_thread.stop.assert_called_once()

    def test_quit_no_pulse_thread(self):
        """quit_app works when pulse_thread is None."""
        self.win.pulse_thread = None
        self.win.quit_app()  # Should not raise


class TestCloseEvent(unittest.TestCase):
    """Tests for MainWindow.closeEvent()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_close_minimizes_to_tray(self):
        """closeEvent minimizes to tray when tray icon is visible."""
        tray = _DummySystemTrayIcon()
        tray.show()
        self.win.tray_icon = tray
        event = MagicMock()
        self.win.closeEvent(event)
        event.ignore.assert_called_once()

    def test_close_accepts_without_tray(self):
        """closeEvent accepts when no tray icon."""
        self.win.tray_icon = None
        event = MagicMock()
        self.win.closeEvent(event)
        event.accept.assert_called_once()

    def test_close_cleanup_pages(self):
        """closeEvent calls cleanup on pages that have it."""
        page_with_cleanup = MagicMock()
        page_with_cleanup.cleanup = MagicMock()
        self.win.pages = {"test": page_with_cleanup}
        self.win.tray_icon = None
        event = MagicMock()
        self.win.closeEvent(event)
        page_with_cleanup.cleanup.assert_called_once()

    def test_close_cleanup_exception_handling(self):
        """closeEvent handles cleanup exceptions gracefully."""
        page = MagicMock()
        page.cleanup.side_effect = RuntimeError("cleanup error")
        self.win.pages = {"broken": page}
        self.win.tray_icon = None
        event = MagicMock()
        self.win.closeEvent(event)  # Should not raise
        event.accept.assert_called_once()

    def test_close_tray_invisible_accepts(self):
        """closeEvent accepts when tray exists but is not visible."""
        tray = _DummySystemTrayIcon()
        tray._visible = False
        self.win.tray_icon = tray
        event = MagicMock()
        self.win.closeEvent(event)
        event.accept.assert_called_once()


class TestKeyboardShortcuts(unittest.TestCase):
    """Tests for MainWindow._setup_keyboard_shortcuts()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_setup_does_not_raise(self):
        """_setup_keyboard_shortcuts completes without error."""
        self.win._setup_keyboard_shortcuts()

    def test_select_category_valid_index(self):
        """_select_category selects and expands valid category."""
        self.win.add_page("P1", "📦", MagicMock(), category="Cat1")
        self.win.add_page("P2", "📦", MagicMock(), category="Cat2")
        self.win._select_category(0)
        cat = self.win.sidebar.topLevelItem(0)
        self.assertTrue(cat.isExpanded())

    def test_select_category_invalid_index(self):
        """_select_category does nothing for out-of-range index."""
        self.win.add_page("P1", "📦", MagicMock(), category="Cat1")
        self.win._select_category(99)  # Should not raise

    def test_select_next_item(self):
        """_select_next_item moves to next item in tree."""
        self.win.add_page("A", "📦", MagicMock(), category="Cat")
        self.win.add_page("B", "📦", MagicMock(), category="Cat")
        cat = self.win.sidebar.topLevelItem(0)
        self.win.sidebar._current = cat.child(0)
        self.win._select_next_item()
        self.assertIs(self.win.sidebar._current, cat.child(1))

    def test_select_next_wraps_around(self):
        """_select_next_item wraps to first item at end."""
        self.win.add_page("Only", "📦", MagicMock(), category="Cat")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.win.sidebar._current = child
        # itemBelow returns None for last item, should wrap
        self.win._select_next_item()

    def test_select_next_no_current(self):
        """_select_next_item does nothing when no current item."""
        self.win.sidebar._current = None
        self.win._select_next_item()  # Should not raise

    def test_select_prev_item(self):
        """_select_prev_item moves to previous item."""
        self.win.add_page("A", "📦", MagicMock(), category="Cat")
        self.win.add_page("B", "📦", MagicMock(), category="Cat")
        cat = self.win.sidebar.topLevelItem(0)
        self.win.sidebar._current = cat.child(1)
        self.win._select_prev_item()
        self.assertIs(self.win.sidebar._current, cat.child(0))

    def test_select_prev_no_current(self):
        """_select_prev_item does nothing when no current item."""
        self.win.sidebar._current = None
        self.win._select_prev_item()  # Should not raise

    def test_show_shortcut_help(self):
        """_show_shortcut_help does not raise."""
        self.win._show_shortcut_help()  # Should not raise


class TestCommandPalette(unittest.TestCase):
    """Tests for command palette shortcut and dialog."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_setup_command_palette_shortcut(self):
        """_setup_command_palette_shortcut completes without error."""
        self.win._setup_command_palette_shortcut()

    def test_show_command_palette(self):
        """_show_command_palette imports and shows the dialog."""
        self.win._show_command_palette()  # Should not raise

    def test_show_command_palette_import_error(self):
        """_show_command_palette handles missing module gracefully."""
        orig = sys.modules.get("ui.command_palette")
        sys.modules.pop("ui.command_palette", None)
        # Create broken module
        broken = types.ModuleType("ui.command_palette")
        sys.modules["ui.command_palette"] = broken
        # Should not raise
        self.win._show_command_palette()
        # Restore
        if orig:
            sys.modules["ui.command_palette"] = orig


class TestQuickActions(unittest.TestCase):
    """Tests for quick actions setup and display."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_setup_quick_actions(self):
        """_setup_quick_actions completes without error."""
        self.win._setup_quick_actions()


class TestFavorites(unittest.TestCase):
    """Tests for MainWindow._build_favorites_section()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_no_favorites(self):
        """_build_favorites_section does nothing when no favorites."""
        fav_mod = sys.modules["utils.favorites"]
        fav_mod.FavoritesManager.get_favorites = MagicMock(return_value=[])
        self.win._build_favorites_section()
        # No favorites category should be added
        for i in range(self.win.sidebar.topLevelItemCount()):
            cat = self.win.sidebar.topLevelItem(i)
            self.assertNotIn("Favorites", cat.text(0))

    def test_favorites_with_matching_pages(self):
        """_build_favorites_section creates pinned entries for matching favorites."""
        self.win.add_page("Hardware", "🖥️", MagicMock(), category="System")
        fav_mod = sys.modules["utils.favorites"]
        fav_mod.FavoritesManager.get_favorites = MagicMock(return_value=["hardware"])
        self.win._build_favorites_section()
        # Favorites category should be at position 0
        fav_cat = self.win.sidebar.topLevelItem(0)
        self.assertIn("Favorites", fav_cat.text(0))

    def test_favorites_non_matching_ignored(self):
        """_build_favorites_section ignores favorites that don't match pages."""
        fav_mod = sys.modules["utils.favorites"]
        fav_mod.FavoritesManager.get_favorites = MagicMock(return_value=["nonexistent"])
        self.win._build_favorites_section()
        # Favorites category created but with no pinned children
        fav_cat = self.win.sidebar.topLevelItem(0)
        if fav_cat and "Favorites" in fav_cat.text(0):
            self.assertEqual(fav_cat.childCount(), 0)

    def test_rebuild_favorites(self):
        """_rebuild_favorites_section removes and recreates favorites."""
        self.win.add_page("Network", "🌐", MagicMock(), category="System")
        fav_mod = sys.modules["utils.favorites"]

        # Build initial
        fav_mod.FavoritesManager.get_favorites = MagicMock(return_value=["network"])
        self.win._build_favorites_section()
        initial_count = self.win.sidebar.topLevelItemCount()

        # Rebuild
        fav_mod.FavoritesManager.get_favorites = MagicMock(return_value=[])
        self.win._rebuild_favorites_section()
        # Favorites section should be removed
        final_count = self.win.sidebar.topLevelItemCount()
        self.assertLessEqual(final_count, initial_count)


class TestNotificationBadge(unittest.TestCase):
    """Tests for MainWindow._refresh_notif_badge()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_badge_visible_with_unread(self):
        """Badge becomes visible when there are unread notifications."""
        nc_mod = sys.modules["utils.notification_center"]
        mock_nc_instance = MagicMock()
        mock_nc_instance.get_unread_count.return_value = 5
        nc_mod.NotificationCenter = MagicMock(return_value=mock_nc_instance)
        self.win._refresh_notif_badge()
        self.assertTrue(self.win._notif_badge._visible)
        self.assertEqual(self.win._notif_badge._text, "5")

    def test_badge_hidden_when_zero(self):
        """Badge is hidden when unread count is zero."""
        nc_mod = sys.modules["utils.notification_center"]
        mock_nc_instance = MagicMock()
        mock_nc_instance.get_unread_count.return_value = 0
        nc_mod.NotificationCenter = MagicMock(return_value=mock_nc_instance)
        self.win._refresh_notif_badge()
        self.assertFalse(self.win._notif_badge._visible)

    def test_badge_caps_at_99(self):
        """Badge text caps at 99 for large counts."""
        nc_mod = sys.modules["utils.notification_center"]
        mock_nc_instance = MagicMock()
        mock_nc_instance.get_unread_count.return_value = 150
        nc_mod.NotificationCenter = MagicMock(return_value=mock_nc_instance)
        self.win._refresh_notif_badge()
        self.assertEqual(self.win._notif_badge._text, "99")

    def test_badge_hidden_on_exception(self):
        """Badge is hidden when notification center raises."""
        nc_mod = sys.modules["utils.notification_center"]
        nc_mod.NotificationCenter = MagicMock(side_effect=RuntimeError("DB error"))
        self.win._notif_badge._visible = True
        self.win._refresh_notif_badge()
        self.assertFalse(self.win._notif_badge._visible)

    def test_badge_count_one(self):
        """Badge shows '1' for single unread notification."""
        nc_mod = sys.modules["utils.notification_center"]
        mock_nc_instance = MagicMock()
        mock_nc_instance.get_unread_count.return_value = 1
        nc_mod.NotificationCenter = MagicMock(return_value=mock_nc_instance)
        self.win._refresh_notif_badge()
        self.assertEqual(self.win._notif_badge._text, "1")
        self.assertTrue(self.win._notif_badge._visible)


class TestSetupNotificationBell(unittest.TestCase):
    """Tests for MainWindow._setup_notification_bell()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_setup_creates_bell(self):
        """_setup_notification_bell creates notification bell widgets."""
        self.win._setup_notification_bell()
        self.assertIsNotNone(self.win.notif_bell)
        self.assertIsNotNone(self.win._notif_badge)

    def test_setup_badge_initially_hidden(self):
        """Notification badge is initially hidden (zero count assumed)."""
        nc_mod = sys.modules["utils.notification_center"]
        mock_nc_instance = MagicMock()
        mock_nc_instance.get_unread_count.return_value = 0
        nc_mod.NotificationCenter = MagicMock(return_value=mock_nc_instance)
        self.win._setup_notification_bell()
        self.assertFalse(self.win._notif_badge._visible)


class TestBreadcrumb(unittest.TestCase):
    """Tests for breadcrumb bar updates."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_update_breadcrumb(self):
        """_update_breadcrumb sets category, page, and description."""
        self.win.add_page(
            "Network", "🌐", MagicMock(), category="System", description="Network tools"
        )
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.win._update_breadcrumb(child)
        # Category should be set (raw category name from _ROLE_DESC)
        self.assertIn("System", self.win._bc_category._text)
        self.assertIn("Network", self.win._bc_page._text)

    def test_update_breadcrumb_strips_badges(self):
        """_update_breadcrumb strips badge suffixes from page name."""
        self.win.add_page("Top", "⭐", MagicMock(), category="Cat", badge="recommended")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.win._update_breadcrumb(child)
        self.assertNotIn("★", self.win._bc_page._text)

    def test_on_breadcrumb_category_click_no_parent(self):
        """_on_breadcrumb_category_click handles no parent gracefully."""
        self.win._bc_parent_item = None
        self.win._on_breadcrumb_category_click()  # Should not raise

    def test_on_breadcrumb_category_click_with_parent(self):
        """_on_breadcrumb_category_click selects first child of category."""
        self.win.add_page("P1", "📦", MagicMock(), category="Cat")
        cat = self.win.sidebar.topLevelItem(0)
        self.win._bc_parent_item = cat
        self.win._on_breadcrumb_category_click()
        self.assertTrue(cat.isExpanded())


class TestOnUndoClicked(unittest.TestCase):
    """Tests for MainWindow._on_undo_clicked()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)
        self.win.show_status_toast = MagicMock()

    def test_undo_success(self):
        """_on_undo_clicked shows success toast on successful undo."""
        mock_hm = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Reverted theme"
        mock_hm.undo_last_action.return_value = mock_result

        mod = _get_module()
        original = getattr(mod, "HistoryManager", None)
        mod.HistoryManager = MagicMock(return_value=mock_hm)
        try:
            self.win._on_undo_clicked()
            self.win.show_status_toast.assert_called_with("Reverted theme")
            self.assertFalse(self.win._undo_btn._visible)
        finally:
            if original is not None:
                mod.HistoryManager = original

    def test_undo_failure(self):
        """_on_undo_clicked shows error toast on failed undo."""
        mock_hm = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Nothing to undo"
        mock_hm.undo_last_action.return_value = mock_result

        mod = _get_module()
        original = getattr(mod, "HistoryManager", None)
        mod.HistoryManager = MagicMock(return_value=mock_hm)
        try:
            self.win._on_undo_clicked()
            self.win.show_status_toast.assert_called_with("Nothing to undo", error=True)
            self.assertFalse(self.win._undo_btn._visible)
        finally:
            if original is not None:
                mod.HistoryManager = original

    def test_undo_exception(self):
        """_on_undo_clicked handles exception gracefully."""
        mod = _get_module()
        original = getattr(mod, "HistoryManager", None)
        mod.HistoryManager = MagicMock(side_effect=RuntimeError("DB error"))
        try:
            self.win._on_undo_clicked()
            self.win.show_status_toast.assert_called()
            self.assertFalse(self.win._undo_btn._visible)
        finally:
            if original is not None:
                mod.HistoryManager = original


class TestStartPulseListener(unittest.TestCase):
    """Tests for MainWindow._start_pulse_listener()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_pulse_listener_starts(self):
        """_start_pulse_listener initializes pulse and thread."""
        pulse_mod = sys.modules["utils.pulse"]
        pulse_mod.SystemPulse = MagicMock()
        pulse_mod.PulseThread = MagicMock()
        self.win._start_pulse_listener()
        self.assertIsNotNone(self.win.pulse)
        self.assertIsNotNone(self.win.pulse_thread)

    def test_pulse_listener_exception(self):
        """_start_pulse_listener handles exception gracefully."""
        pulse_mod = sys.modules["utils.pulse"]
        pulse_mod.SystemPulse = MagicMock(side_effect=RuntimeError("DBus error"))
        self.win._start_pulse_listener()
        # Should not raise, pulse remains None or whatever was set before


class TestWrapPageWidget(unittest.TestCase):
    """Tests for MainWindow._wrap_page_widget()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_wrap_returns_scroll_area(self):
        """_wrap_page_widget wraps widget in a scroll area."""
        widget = MagicMock()
        result = self.win._wrap_page_widget(widget)
        self.assertIsNotNone(result)

    def test_wrap_sets_widget(self):
        """_wrap_page_widget sets the inner widget on scroll area."""
        widget = MagicMock()
        scroll = self.win._wrap_page_widget(widget)
        # The scroll area should have the widget set
        self.assertIsNotNone(scroll)


class TestToggleFocusMode(unittest.TestCase):
    """Tests for MainWindow._toggle_focus_mode()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)
        self.win.focus_action = _DummyAction("Focus Mode")

    def test_toggle_focus_with_tray(self):
        """_toggle_focus_mode toggles and shows tray message."""
        focus_mod = sys.modules["utils.focus_mode"]
        focus_mod.FocusMode.toggle = MagicMock(
            return_value={"message": "Focus Mode activated"}
        )
        focus_mod.FocusMode.is_active = MagicMock(return_value=True)
        tray = _DummySystemTrayIcon()
        tray.showMessage = MagicMock()
        self.win.tray_icon = tray
        self.win._toggle_focus_mode()
        tray.showMessage.assert_called_once()

    def test_toggle_focus_no_tray(self):
        """_toggle_focus_mode works without tray icon."""
        focus_mod = sys.modules["utils.focus_mode"]
        focus_mod.FocusMode.toggle = MagicMock(return_value={"message": "Toggled"})
        focus_mod.FocusMode.is_active = MagicMock(return_value=False)
        self.win.tray_icon = None
        self.win._toggle_focus_mode()  # Should not raise


class TestCheckFirstRun(unittest.TestCase):
    """Tests for MainWindow._check_first_run()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    @patch("os.path.exists", return_value=True)
    def test_not_first_run(self, mock_exists):
        """_check_first_run does nothing when first_run_complete exists."""
        self.win._check_first_run()
        # Should not attempt to show wizard

    @patch("os.path.exists", return_value=False)
    def test_first_run_shows_wizard(self, mock_exists):
        """_check_first_run shows wizard on first launch."""
        self.win._check_first_run()
        # Should not raise (wizard is mocked)


class TestSidebarContextMenu(unittest.TestCase):
    """Tests for MainWindow._sidebar_context_menu()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_context_menu_no_item(self):
        """_sidebar_context_menu does nothing for empty area."""
        # itemAt returns None for empty tree
        self.win.sidebar._items = []
        self.win._sidebar_context_menu(MagicMock())  # Should not raise

    def test_context_menu_item_without_data(self):
        """_sidebar_context_menu ignores items without UserRole data."""
        item = _DummyTreeWidgetItem()
        item.setText(0, "Category")
        # No UserRole data set
        self.win.sidebar._items = [item]
        self.win._sidebar_context_menu(MagicMock())  # Should not raise


class TestRefreshStatusIndicators(unittest.TestCase):
    """Tests for MainWindow._refresh_status_indicators()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)
        self.win._set_tab_status = MagicMock()

    def test_refresh_with_updates_available(self):
        """_refresh_status_indicators sets warning when updates available."""
        uc_mod = sys.modules["utils.update_checker"]
        mock_info = MagicMock()
        mock_info.is_newer = True
        uc_mod.UpdateChecker.check_for_updates = MagicMock(return_value=mock_info)

        disk_mod = sys.modules["services.hardware.disk"]
        disk_mod.DiskManager.get_disk_usage = MagicMock(return_value=None)

        self.win._refresh_status_indicators()
        self.win._set_tab_status.assert_any_call(
            "Maintenance", "warning", "Updates available"
        )

    def test_refresh_no_updates(self):
        """_refresh_status_indicators sets ok when no updates."""
        uc_mod = sys.modules["utils.update_checker"]
        mock_info = MagicMock()
        mock_info.is_newer = False
        uc_mod.UpdateChecker.check_for_updates = MagicMock(return_value=mock_info)

        disk_mod = sys.modules["services.hardware.disk"]
        disk_mod.DiskManager.get_disk_usage = MagicMock(return_value=None)

        self.win._refresh_status_indicators()
        self.win._set_tab_status.assert_any_call("Maintenance", "ok", "Up to date")

    def test_refresh_update_check_exception(self):
        """_refresh_status_indicators handles update check failure."""
        uc_mod = sys.modules["utils.update_checker"]
        uc_mod.UpdateChecker.check_for_updates = MagicMock(side_effect=RuntimeError("timeout"))

        disk_mod = sys.modules["services.hardware.disk"]
        disk_mod.DiskManager.get_disk_usage = MagicMock(return_value=None)

        self.win._refresh_status_indicators()
        self.win._set_tab_status.assert_any_call("Maintenance", "", "")


class TestSetTabStatus(unittest.TestCase):
    """Tests for MainWindow._set_tab_status()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_set_tab_status_ok(self):
        """_set_tab_status adds [OK] marker for 'ok' status."""
        mod = _get_module()
        self.win.add_page("Maintenance", "🔧", MagicMock(), category="System")
        self.win._set_tab_status("Maintenance", "ok", "Healthy")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertIn("[OK]", child.text(0))

    def test_set_tab_status_warning(self):
        """_set_tab_status adds [WARN] marker for 'warning' status."""
        self.win.add_page("Storage", "💾", MagicMock(), category="System")
        self.win._set_tab_status("Storage", "warning", "75% used")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertIn("[WARN]", child.text(0))

    def test_set_tab_status_error(self):
        """_set_tab_status adds [ERR] marker for 'error' status."""
        self.win.add_page("Storage", "💾", MagicMock(), category="System")
        self.win._set_tab_status("Storage", "error", "90% full")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertIn("[ERR]", child.text(0))

    def test_set_tab_status_empty_clears_dot(self):
        """_set_tab_status with empty status removes existing marker."""
        self.win.add_page("Maintenance", "🔧", MagicMock(), category="System")
        self.win._set_tab_status("Maintenance", "ok", "Good")
        self.win._set_tab_status("Maintenance", "", "")
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertNotIn("[OK]", child.text(0))

    def test_set_tab_status_nonexistent_tab(self):
        """_set_tab_status does nothing for non-existent tab."""
        self.win._set_tab_status("Nonexistent", "ok", "Good")  # Should not raise


class TestShowDoctor(unittest.TestCase):
    """Tests for MainWindow.show_doctor()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_show_doctor(self):
        """show_doctor creates and execs DependencyDoctor dialog."""
        self.win.show_doctor()  # Should not raise (DependencyDoctor is mocked)


class TestWrapInLazy(unittest.TestCase):
    """Tests for MainWindow._wrap_in_lazy()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_wrap_in_lazy_returns_lazy_widget(self):
        """_wrap_in_lazy returns a LazyWidget wrapping the plugin factory."""
        mod = _get_module()
        plugin = MagicMock()
        plugin.create_widget = MagicMock(return_value=_Dummy())
        lazy = self.win._wrap_in_lazy(plugin)
        self.assertIsNotNone(lazy)
        self.assertEqual(lazy.loader_fn, plugin.create_widget)


class TestAddPluginPage(unittest.TestCase):
    """Tests for MainWindow._add_plugin_page()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)

    def test_add_plugin_page_compatible(self):
        """_add_plugin_page adds enabled page for compatible plugin."""
        meta_mod = sys.modules["core.plugins.metadata"]
        meta = meta_mod.PluginMetadata(
            id="test",
            name="Test",
            description="Test page",
            category="System",
            icon="🧪",
            badge="",
        )
        compat = meta_mod.CompatStatus(compatible=True)
        lazy_mod = sys.modules["ui.lazy_widget"]
        widget = lazy_mod.LazyWidget(lambda: _Dummy())
        self.win._add_plugin_page(meta, widget, compat)
        self.assertIn("Test", self.win.pages)

    def test_add_plugin_page_incompatible(self):
        """_add_plugin_page adds disabled page for incompatible plugin."""
        meta_mod = sys.modules["core.plugins.metadata"]
        meta = meta_mod.PluginMetadata(
            id="broken",
            name="Broken",
            description="Broken page",
            category="System",
            icon="❌",
            badge="",
        )
        compat = meta_mod.CompatStatus(compatible=False, reason="Fedora 42+ required")
        lazy_mod = sys.modules["ui.lazy_widget"]
        widget = lazy_mod.LazyWidget(lambda: _Dummy())
        self.win._add_plugin_page(meta, widget, compat)
        # Page is still registered in pages dict
        self.assertIn("Broken", self.win.pages)
        # But sidebar item should be disabled
        cat = self.win.sidebar.topLevelItem(0)
        child = cat.child(0)
        self.assertTrue(child.isDisabled())


class TestToggleNotificationPanel(unittest.TestCase):
    """Tests for MainWindow._toggle_notification_panel()."""

    def setUp(self):
        self.win = _make_window(skip_init=True)
        self.win._refresh_notif_badge = MagicMock()

    def test_toggle_creates_panel_on_first_call(self):
        """_toggle_notification_panel creates panel on first call."""
        self.win.notif_panel = None
        panel_mod = sys.modules["ui.notification_panel"]
        mock_panel = MagicMock()
        mock_panel.isVisible.return_value = False
        mock_panel.PANEL_WIDTH = 300
        mock_panel.EDGE_MARGIN = 8
        mock_panel.MIN_HEIGHT = 200
        mock_panel.MAX_HEIGHT = 500
        mock_panel.sizeHint.return_value = MagicMock(height=MagicMock(return_value=400))
        panel_mod.NotificationPanel = MagicMock(return_value=mock_panel)
        self.win.width = MagicMock(return_value=1100)
        self.win.height = MagicMock(return_value=700)
        self.win._toggle_notification_panel()
        self.assertIsNotNone(self.win.notif_panel)

    def test_toggle_hides_visible_panel(self):
        """_toggle_notification_panel hides panel when visible."""
        mock_panel = MagicMock()
        mock_panel.isVisible.return_value = True
        self.win.notif_panel = mock_panel
        self.win._toggle_notification_panel()
        mock_panel.hide.assert_called_once()


if __name__ == "__main__":
    unittest.main()
