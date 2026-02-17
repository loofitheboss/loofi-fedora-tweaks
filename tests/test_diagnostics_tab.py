"""Tests for ui/diagnostics_tab.py — DiagnosticsTab, _WatchtowerSubTab, _BootSubTab.

Comprehensive behavioural tests covering service management, boot analysis,
journal diagnostics, kernel parameters, ZRAM, and Secure Boot.  All external
managers are mocked so no root privileges are required.  Lightweight PyQt6
stubs are used instead of a real QApplication so tests run headless.
"""

import importlib
import os
import sys
import types
import unittest
from enum import Enum
from unittest.mock import patch, MagicMock

# Add source path
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
        """QWidget.tr() stub — return the text unchanged."""
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
        self._text = text

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setObjectName(self, name):
        pass

    def setWordWrap(self, wrap):
        pass

    def setProperty(self, key, value):
        pass

    def tr(self, text):
        return text

    def __getattr__(self, name):
        """Absorb any unknown QWidget method calls."""
        return lambda *a, **kw: None


class _DummyTextEdit:
    """Minimal QTextEdit stand-in."""

    def __init__(self, *args, **kwargs):
        self._text = ""

    def setText(self, text):
        self._text = text

    def setPlainText(self, text):
        self._text = text

    def append(self, text):
        if self._text:
            self._text += "\n" + text
        else:
            self._text = text

    def toPlainText(self):
        return self._text

    def setReadOnly(self, flag):
        pass

    def setMinimumHeight(self, h):
        pass

    def setMaximumHeight(self, h):
        pass

    def clear(self):
        self._text = ""

    def __getattr__(self, name):
        """Absorb any unknown QWidget method calls."""
        return lambda *a, **kw: None


class _EchoMode:
    """Stub for QLineEdit.EchoMode."""

    Normal = 0
    Password = 2
    NoEcho = 1
    PasswordEchoOnEdit = 3


class _DummyLineEdit:
    """Minimal QLineEdit stand-in."""

    EchoMode = _EchoMode

    def __init__(self, *args, **kwargs):
        self._text = ""
        self.returnPressed = _DummySignal()

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def setAccessibleName(self, name):
        pass

    def setPlaceholderText(self, text):
        pass

    def clear(self):
        self._text = ""

    def __getattr__(self, name):
        """Absorb any unknown QWidget method calls."""
        return lambda *a, **kw: None


class _DummyComboBox:
    """Minimal QComboBox stand-in."""

    def __init__(self, *args, **kwargs):
        self._items = []
        self._current = 0
        self._blocked = False
        self.currentIndexChanged = _DummySignal()

    def addItem(self, text, data=None):
        self._items.append((text, data))

    def currentData(self):
        if self._items and 0 <= self._current < len(self._items):
            return self._items[self._current][1]
        return None

    def currentIndex(self):
        return self._current

    def setCurrentIndex(self, idx):
        self._current = idx

    def findData(self, data):
        for i, (_, d) in enumerate(self._items):
            if d == data:
                return i
        return -1

    def clear(self):
        self._items.clear()
        self._current = 0

    def setAccessibleName(self, name):
        pass

    def blockSignals(self, block):
        self._blocked = block

    def __getattr__(self, name):
        """Absorb any unknown QWidget method calls."""
        return lambda *a, **kw: None


class _DummyCheckBox:
    """Minimal QCheckBox stand-in."""

    def __init__(self, text="", *args, **kwargs):
        self._checked = False
        self._props = {}
        self.stateChanged = _DummySignal()

    def setChecked(self, state):
        self._checked = state

    def isChecked(self):
        return self._checked

    def setAccessibleName(self, name):
        pass

    def blockSignals(self, block):
        pass

    def setProperty(self, key, value):
        self._props[key] = value

    def property(self, key):
        return self._props.get(key)

    def __getattr__(self, name):
        """Absorb any unknown QWidget method calls."""
        return lambda *a, **kw: None


class _DummyButton(_Dummy):
    """Minimal QPushButton stand-in."""

    def __init__(self, text="", *args, **kwargs):
        self.clicked = _DummySignal()
        self._enabled = True

    def setEnabled(self, flag):
        self._enabled = flag

    def isEnabled(self):
        return self._enabled

    def setAccessibleName(self, name):
        pass


class _TickPosition:
    """Stub for QSlider.TickPosition."""

    NoTicks = 0
    TicksAbove = 1
    TicksBelow = 2
    TicksBothSides = 3


class _DummySlider:
    """Minimal QSlider stand-in."""

    TickPosition = _TickPosition

    def __init__(self, *args, **kwargs):
        self._value = 0
        self._min = 0
        self._max = 100
        self.valueChanged = _DummySignal()

    def value(self):
        return self._value

    def setValue(self, val):
        self._value = val

    def setMinimum(self, val):
        self._min = val

    def setMaximum(self, val):
        self._max = val

    def setRange(self, lo, hi):
        self._min = lo
        self._max = hi

    def setTickInterval(self, interval):
        pass

    def setTickPosition(self, pos):
        pass

    def setAccessibleName(self, name):
        pass

    def __getattr__(self, name):
        """Absorb any unknown QWidget method calls."""
        return lambda *a, **kw: None


class _DummyTreeWidgetItem:
    """Minimal QTreeWidgetItem stand-in."""

    def __init__(self, values=None, *args, **kwargs):
        self._values = values or []
        self._data = {}

    def text(self, col):
        if 0 <= col < len(self._values):
            return self._values[col]
        return ""

    def setData(self, col, role, value):
        self._data[(col, role)] = value

    def data(self, col, role):
        return self._data.get((col, role))


class _DummyTreeWidget:
    """Minimal QTreeWidget stand-in."""

    def __init__(self, *args, **kwargs):
        self._items = []
        self._columns = 0
        self._context_policy = None
        self.customContextMenuRequested = _DummySignal()

    def clear(self):
        self._items.clear()

    def addTopLevelItem(self, item):
        self._items.append(item)

    def topLevelItemCount(self):
        return len(self._items)

    def topLevelItem(self, idx):
        if 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    def setColumnCount(self, n):
        self._columns = n

    def setHeaderLabels(self, labels):
        pass

    def setContextMenuPolicy(self, policy):
        self._context_policy = policy

    def setAccessibleName(self, name):
        pass

    def currentItem(self):
        return self._items[0] if self._items else None

    def header(self):
        return _Dummy()

    def __getattr__(self, name):
        return lambda *a, **kw: None


def _install_diagnostics_stubs():
    """Register lightweight PyQt6 stubs so ui.diagnostics_tab can be imported."""

    # -- PyQt6.QtWidgets --
    qt_widgets = types.ModuleType("PyQt6.QtWidgets")
    qt_widgets.QWidget = _Dummy
    qt_widgets.QVBoxLayout = _Dummy
    qt_widgets.QHBoxLayout = _Dummy
    qt_widgets.QGroupBox = _Dummy
    qt_widgets.QLabel = _DummyLabel
    qt_widgets.QPushButton = _DummyButton
    qt_widgets.QTextEdit = _DummyTextEdit
    qt_widgets.QScrollArea = _Dummy
    qt_widgets.QFrame = _Dummy
    qt_widgets.QTabWidget = _Dummy
    qt_widgets.QTreeWidget = _DummyTreeWidget
    qt_widgets.QTreeWidgetItem = _DummyTreeWidgetItem
    qt_widgets.QComboBox = _DummyComboBox
    qt_widgets.QMenu = _Dummy
    qt_widgets.QMessageBox = MagicMock()
    qt_widgets.QSlider = _DummySlider
    qt_widgets.QLineEdit = _DummyLineEdit
    qt_widgets.QCheckBox = _DummyCheckBox
    qt_widgets.QInputDialog = MagicMock()

    # -- PyQt6.QtCore --
    qt_core = types.ModuleType("PyQt6.QtCore")
    qt_core.Qt = types.SimpleNamespace(
        Orientation=types.SimpleNamespace(Horizontal=1, Vertical=2),
        ContextMenuPolicy=types.SimpleNamespace(CustomContextMenu=3),
        ItemDataRole=types.SimpleNamespace(UserRole=0x0100),
        CheckState=types.SimpleNamespace(
            Checked=types.SimpleNamespace(value=2),
            Unchecked=types.SimpleNamespace(value=0),
        ),
    )

    # -- PyQt6 package --
    pyqt = types.ModuleType("PyQt6")
    pyqt.QtWidgets = qt_widgets
    pyqt.QtCore = qt_core

    # -- ui.base_tab --
    base_tab_module = types.ModuleType("ui.base_tab")
    base_tab_module.BaseTab = type(
        "BaseTab",
        (_Dummy,),
        {
            "__init__": lambda self, *a, **kw: None,
            "tr": lambda self, text: text,
        },
    )

    # -- ui.tab_utils --
    tab_utils_module = types.ModuleType("ui.tab_utils")
    tab_utils_module.configure_top_tabs = lambda *a, **kw: None
    tab_utils_module.CONTENT_MARGINS = (0, 0, 0, 0)

    # -- core.plugins.interface --
    interface_module = types.ModuleType("core.plugins.interface")
    interface_module.PluginInterface = type(
        "PluginInterface",
        (),
        {
            "metadata": lambda self: None,
            "create_widget": lambda self: None,
        },
    )

    # -- core.plugins.metadata --
    metadata_module = types.ModuleType("core.plugins.metadata")

    class _StubPluginMetadata:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    metadata_module.PluginMetadata = _StubPluginMetadata

    # -- services.system --
    services_module = types.ModuleType("services.system")
    services_module.ServiceManager = MagicMock()
    services_module.UnitScope = MagicMock()
    services_module.UnitState = MagicMock()

    # -- utils modules --
    boot_analyzer_module = types.ModuleType("utils.boot_analyzer")
    boot_analyzer_module.BootAnalyzer = MagicMock()

    journal_module = types.ModuleType("utils.journal")
    journal_module.JournalManager = MagicMock()

    kernel_module = types.ModuleType("utils.kernel")
    kernel_module.KernelManager = MagicMock()

    zram_module = types.ModuleType("utils.zram")
    zram_module.ZramManager = MagicMock()

    secureboot_module = types.ModuleType("utils.secureboot")
    secureboot_module.SecureBootManager = MagicMock()

    log_module = types.ModuleType("utils.log")
    log_module.get_logger = lambda name: MagicMock()

    # Register stubs
    sys.modules["PyQt6"] = pyqt
    sys.modules["PyQt6.QtWidgets"] = qt_widgets
    sys.modules["PyQt6.QtCore"] = qt_core
    sys.modules["ui.base_tab"] = base_tab_module
    sys.modules["ui.tab_utils"] = tab_utils_module
    sys.modules["core.plugins.interface"] = interface_module
    sys.modules["core.plugins.metadata"] = metadata_module
    sys.modules["services.system"] = services_module
    sys.modules["utils.boot_analyzer"] = boot_analyzer_module
    sys.modules["utils.journal"] = journal_module
    sys.modules["utils.kernel"] = kernel_module
    sys.modules["utils.zram"] = zram_module
    sys.modules["utils.secureboot"] = secureboot_module
    sys.modules["utils.log"] = log_module


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

_MODULE_KEYS = [
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "ui",
    "ui.base_tab",
    "ui.tab_utils",
    "core.plugins.interface",
    "core.plugins.metadata",
    "services.system",
    "utils.boot_analyzer",
    "utils.journal",
    "utils.kernel",
    "utils.zram",
    "utils.secureboot",
    "utils.log",
    "ui.diagnostics_tab",
]

_module_backup = {}


def setUpModule():
    """Install stubs and import ui.diagnostics_tab."""
    global _module_backup
    for key in _MODULE_KEYS:
        _module_backup[key] = sys.modules.get(key)
    _install_diagnostics_stubs()
    # Force re-import so stubs are used
    sys.modules.pop("ui.diagnostics_tab", None)
    sys.modules.pop("ui", None)
    importlib.import_module("ui.diagnostics_tab")


def tearDownModule():
    """Restore original modules."""
    sys.modules.pop("ui.diagnostics_tab", None)
    for key, orig in _module_backup.items():
        if orig is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = orig


def _get_module():
    """Return the imported ui.diagnostics_tab module."""
    return sys.modules["ui.diagnostics_tab"]


# ---------------------------------------------------------------------------
# Module path for patching
# ---------------------------------------------------------------------------

_M = "ui.diagnostics_tab"


# ---------------------------------------------------------------------------
# Fake domain objects (lightweight stand-ins for dataclasses)
# ---------------------------------------------------------------------------


class FakeUnitState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    UNKNOWN = "unknown"


class FakeUnitScope(Enum):
    SYSTEM = "system"
    USER = "user"


class FakeServiceUnit:
    """Minimal ServiceUnit stand-in."""

    def __init__(
        self,
        name="svc",
        state=FakeUnitState.ACTIVE,
        scope=FakeUnitScope.USER,
        description="desc",
    ):
        self.name = name
        self.state = state
        self.scope = scope
        self.description = description


class FakeResult:
    def __init__(self, success=True, message="OK", data=None):
        self.success = success
        self.message = message
        self.data = data or {}


class FakeBootStats:
    def __init__(
        self, total=None, firmware=None, loader=None, kernel=None, userspace=None
    ):
        self.total_time = total
        self.firmware_time = firmware
        self.loader_time = loader
        self.kernel_time = kernel
        self.userspace_time = userspace


class FakeSlowService:
    def __init__(self, service="slow.service", time_seconds=7.5):
        self.service = service
        self.time_seconds = time_seconds


class FakeKernelResult:
    def __init__(self, success=True, message="OK", backup_path=None):
        self.success = success
        self.message = message
        self.backup_path = backup_path


class FakeZramConfig:
    def __init__(
        self,
        enabled=True,
        size_mb=4096,
        size_percent=100,
        algorithm="zstd",
        total_ram_mb=8192,
    ):
        self.enabled = enabled
        self.size_mb = size_mb
        self.size_percent = size_percent
        self.algorithm = algorithm
        self.total_ram_mb = total_ram_mb


class FakeSecureBootStatus:
    def __init__(self, enabled=True, mok=False, pending=False):
        self.secure_boot_enabled = enabled
        self.mok_enrolled = mok
        self.pending_mok = pending
        self.status_message = ""


class FakeSecureBootResult:
    def __init__(self, success=True, message="OK", requires_reboot=False):
        self.success = success
        self.message = message
        self.requires_reboot = requires_reboot


class FakeBackupPath:
    def __init__(self, name="grub-backup-2025"):
        self.name = name


# ---------------------------------------------------------------------------
# Shared decorator stacks
# ---------------------------------------------------------------------------

# All manager + enum patches needed when instantiating _WatchtowerSubTab.
_WATCHTOWER_PATCHES = [
    patch(f"{_M}.ServiceManager", new_callable=MagicMock),
    patch(f"{_M}.UnitState", new_callable=MagicMock),
    patch(f"{_M}.UnitScope", new_callable=MagicMock),
    patch(f"{_M}.BootAnalyzer", new_callable=MagicMock),
    patch(f"{_M}.JournalManager", new_callable=MagicMock),
]


def _setup_watchtower_mocks(mock_sm, mock_us, mock_usc, mock_ba, mock_jm):
    """Wire up default return values so __init__ succeeds."""
    mock_us.ACTIVE = FakeUnitState.ACTIVE
    mock_us.INACTIVE = FakeUnitState.INACTIVE
    mock_us.FAILED = FakeUnitState.FAILED
    mock_us.ACTIVATING = FakeUnitState.ACTIVATING
    mock_us.UNKNOWN = FakeUnitState.UNKNOWN
    mock_usc.SYSTEM = FakeUnitScope.SYSTEM
    mock_usc.USER = FakeUnitScope.USER

    mock_sm.list_units.return_value = []
    mock_ba.get_boot_stats.return_value = FakeBootStats()
    mock_ba.get_slow_services.return_value = []
    mock_ba.get_optimization_suggestions.return_value = []
    mock_jm.get_quick_diagnostic.return_value = {
        "error_count": 0,
        "failed_services": [],
    }
    mock_jm.get_boot_errors.return_value = ""


def _make_watchtower(mock_sm, mock_ba, mock_jm, mock_us, mock_usc):
    """Instantiate _WatchtowerSubTab with all managers pre-configured."""
    _setup_watchtower_mocks(mock_sm, mock_us, mock_usc, mock_ba, mock_jm)
    mod = _get_module()
    return mod._WatchtowerSubTab()


def _setup_boot_mocks(mock_km, mock_zm, mock_sb):
    """Wire up default return values so _BootSubTab.__init__ succeeds."""
    mock_km.get_current_params.return_value = ["quiet", "splash"]
    mock_km.has_param.return_value = False
    mock_zm.ALGORITHMS = {"zstd": "Zstandard", "lz4": "LZ4"}
    mock_zm.get_current_config.return_value = FakeZramConfig()
    mock_zm.get_current_usage.return_value = None
    mock_sb.get_status.return_value = FakeSecureBootStatus()
    mock_sb.has_keys.return_value = False


def _make_boot(mock_km, mock_zm, mock_sb):
    """Instantiate _BootSubTab with managers pre-configured."""
    _setup_boot_mocks(mock_km, mock_zm, mock_sb)
    mod = _get_module()
    return mod._BootSubTab()


# ===========================================================================
# _WatchtowerSubTab — _state_to_emoji
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.JournalManager", new_callable=MagicMock)
@patch(f"{_M}.BootAnalyzer", new_callable=MagicMock)
@patch(f"{_M}.UnitScope", new_callable=MagicMock)
@patch(f"{_M}.UnitState", new_callable=MagicMock)
@patch(f"{_M}.ServiceManager", new_callable=MagicMock)
class TestStateToEmoji(unittest.TestCase):
    """Tests for _WatchtowerSubTab._state_to_emoji."""

    def test_active(self, sm, us, usc, ba, jm):
        """Active state returns string containing 'active'."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        self.assertIn("active", tab._state_to_emoji(FakeUnitState.ACTIVE))

    def test_inactive(self, sm, us, usc, ba, jm):
        """Inactive state returns string containing 'inactive'."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        self.assertIn("inactive", tab._state_to_emoji(FakeUnitState.INACTIVE))

    def test_failed(self, sm, us, usc, ba, jm):
        """Failed state returns string containing 'failed'."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        self.assertIn("failed", tab._state_to_emoji(FakeUnitState.FAILED))

    def test_activating(self, sm, us, usc, ba, jm):
        """Activating state returns string containing 'starting'."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        self.assertIn("starting", tab._state_to_emoji(FakeUnitState.ACTIVATING))

    def test_unknown(self, sm, us, usc, ba, jm):
        """Unknown state returns string containing 'unknown'."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        self.assertIn("unknown", tab._state_to_emoji(FakeUnitState.UNKNOWN))

    def test_unmapped_returns_fallback(self, sm, us, usc, ba, jm):
        """Unmapped state returns question-mark fallback."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        self.assertEqual("\u2753", tab._state_to_emoji("totally_bogus"))


# ===========================================================================
# _WatchtowerSubTab — _refresh_services
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.JournalManager", new_callable=MagicMock)
@patch(f"{_M}.BootAnalyzer", new_callable=MagicMock)
@patch(f"{_M}.UnitScope", new_callable=MagicMock)
@patch(f"{_M}.UnitState", new_callable=MagicMock)
@patch(f"{_M}.ServiceManager", new_callable=MagicMock)
class TestRefreshServices(unittest.TestCase):
    """Tests for _WatchtowerSubTab._refresh_services."""

    def test_loads_user_services(self, sm, us, usc, ba, jm):
        """Refresh loads user-scoped services and populates tree."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = FakeServiceUnit("test.service", FakeUnitState.ACTIVE)
        sm.list_units.return_value = [svc]
        # Set filter to 'all' (non-gaming)
        tab.service_filter.clear()
        tab.service_filter.addItem("All User Services", "all")

        tab._refresh_services()

        sm.list_units.assert_called_with(FakeUnitScope.USER, "all")
        self.assertEqual(tab.service_tree.topLevelItemCount(), 1)

    def test_gaming_filter_loads_both_scopes(self, sm, us, usc, ba, jm):
        """Gaming filter loads user AND system scoped services."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        user_svc = FakeServiceUnit(
            "gamemoded", FakeUnitState.ACTIVE, FakeUnitScope.USER
        )
        sys_svc = FakeServiceUnit(
            "nvidia-persist", FakeUnitState.ACTIVE, FakeUnitScope.SYSTEM
        )
        # Block signals to prevent clear/addItem from triggering _refresh_services
        tab.service_filter.blockSignals(True)
        tab.service_filter.clear()
        tab.service_filter.addItem("Gaming", "gaming")
        tab.service_filter.blockSignals(False)
        # Now configure and call explicitly
        sm.list_units.reset_mock()
        sm.list_units.side_effect = [[user_svc], [sys_svc]]

        tab._refresh_services()

        self.assertEqual(sm.list_units.call_count, 2)
        self.assertEqual(tab.service_tree.topLevelItemCount(), 2)

    def test_non_gaming_no_system_call(self, sm, us, usc, ba, jm):
        """Non-gaming filter does not call list_units for SYSTEM."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        # Block signals to prevent clear/addItem from triggering _refresh_services
        tab.service_filter.blockSignals(True)
        tab.service_filter.clear()
        tab.service_filter.addItem("Failed", "failed")
        tab.service_filter.blockSignals(False)
        # Reset mock AFTER combo manipulation, then call explicitly
        sm.list_units.reset_mock()
        sm.list_units.return_value = []

        tab._refresh_services()

        sm.list_units.assert_called_once_with(FakeUnitScope.USER, "failed")

    def test_clears_tree_before_loading(self, sm, us, usc, ba, jm):
        """Refresh clears existing tree items first."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        sm.list_units.return_value = []
        tab.service_filter.clear()
        tab.service_filter.addItem("All", "all")

        tab._refresh_services()

        self.assertEqual(tab.service_tree.topLevelItemCount(), 0)

    def test_logs_loaded_count(self, sm, us, usc, ba, jm):
        """Refresh appends loaded-count message to service log."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svcs = [FakeServiceUnit(f"s{i}") for i in range(3)]
        sm.list_units.return_value = svcs
        tab.service_filter.clear()
        tab.service_filter.addItem("All", "all")

        tab._refresh_services()

        self.assertIn("3", tab.service_log.toPlainText())


# ===========================================================================
# _WatchtowerSubTab — _service_action
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.JournalManager", new_callable=MagicMock)
@patch(f"{_M}.BootAnalyzer", new_callable=MagicMock)
@patch(f"{_M}.UnitScope", new_callable=MagicMock)
@patch(f"{_M}.UnitState", new_callable=MagicMock)
@patch(f"{_M}.ServiceManager", new_callable=MagicMock)
class TestServiceAction(unittest.TestCase):
    """Tests for _WatchtowerSubTab._service_action."""

    def _svc(self):
        return FakeServiceUnit("test.service", FakeUnitState.ACTIVE)

    def test_start(self, sm, us, usc, ba, jm):
        """Start calls ServiceManager.start_unit."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.start_unit.return_value = FakeResult(True, "Started")
        sm.list_units.return_value = []
        tab._service_action("start", svc)
        sm.start_unit.assert_called_once_with(svc.name, svc.scope)

    def test_stop(self, sm, us, usc, ba, jm):
        """Stop calls ServiceManager.stop_unit."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.stop_unit.return_value = FakeResult(True, "Stopped")
        sm.list_units.return_value = []
        tab._service_action("stop", svc)
        sm.stop_unit.assert_called_once_with(svc.name, svc.scope)

    def test_restart(self, sm, us, usc, ba, jm):
        """Restart calls ServiceManager.restart_unit."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.restart_unit.return_value = FakeResult(True, "Restarted")
        sm.list_units.return_value = []
        tab._service_action("restart", svc)
        sm.restart_unit.assert_called_once_with(svc.name, svc.scope)

    def test_mask(self, sm, us, usc, ba, jm):
        """Mask calls ServiceManager.mask_unit."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.mask_unit.return_value = FakeResult(True, "Masked")
        sm.list_units.return_value = []
        tab._service_action("mask", svc)
        sm.mask_unit.assert_called_once_with(svc.name, svc.scope)

    def test_unmask(self, sm, us, usc, ba, jm):
        """Unmask calls ServiceManager.unmask_unit."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.unmask_unit.return_value = FakeResult(True, "Unmasked")
        sm.list_units.return_value = []
        tab._service_action("unmask", svc)
        sm.unmask_unit.assert_called_once_with(svc.name, svc.scope)

    def test_success_refreshes(self, sm, us, usc, ba, jm):
        """Successful action triggers _refresh_services."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.start_unit.return_value = FakeResult(True, "OK")
        sm.list_units.return_value = []
        sm.list_units.reset_mock()
        tab.service_filter.clear()
        tab.service_filter.addItem("All", "all")
        tab._service_action("start", svc)
        self.assertTrue(sm.list_units.called)

    def test_failure_does_not_refresh(self, sm, us, usc, ba, jm):
        """Failed action does NOT trigger _refresh_services."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.start_unit.return_value = FakeResult(False, "Denied")
        sm.list_units.reset_mock()
        tab._service_action("start", svc)
        sm.list_units.assert_not_called()

    def test_logs_result_message(self, sm, us, usc, ba, jm):
        """Action appends result.message to service_log."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        sm.stop_unit.return_value = FakeResult(True, "Stopped OK")
        sm.list_units.return_value = []
        tab.service_filter.clear()
        tab.service_filter.addItem("All", "all")
        tab._service_action("stop", svc)
        self.assertIn("Stopped OK", tab.service_log.toPlainText())

    def test_invalid_action_noop(self, sm, us, usc, ba, jm):
        """Unknown action name is a no-op (no crash)."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        svc = self._svc()
        tab._service_action("nonexistent", svc)  # should not raise


# ===========================================================================
# _WatchtowerSubTab — _refresh_boot_analysis
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.JournalManager", new_callable=MagicMock)
@patch(f"{_M}.BootAnalyzer", new_callable=MagicMock)
@patch(f"{_M}.UnitScope", new_callable=MagicMock)
@patch(f"{_M}.UnitState", new_callable=MagicMock)
@patch(f"{_M}.ServiceManager", new_callable=MagicMock)
class TestBootAnalysis(unittest.TestCase):
    """Tests for _WatchtowerSubTab._refresh_boot_analysis."""

    def test_with_full_stats(self, sm, us, usc, ba, jm):
        """Full boot stats show total, firmware, kernel in label."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        ba.get_boot_stats.return_value = FakeBootStats(
            total=22.0, firmware=2.5, loader=1.2, kernel=3.1, userspace=15.2
        )
        ba.get_slow_services.return_value = []
        ba.get_optimization_suggestions.return_value = []
        tab._refresh_boot_analysis()
        text = tab.boot_stats_label.text()
        self.assertIn("22.0", text)
        self.assertIn("Firmware", text)
        self.assertIn("Kernel", text)

    def test_without_stats(self, sm, us, usc, ba, jm):
        """No boot stats shows 'Unable to analyze' message."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        ba.get_boot_stats.return_value = FakeBootStats()
        ba.get_slow_services.return_value = []
        ba.get_optimization_suggestions.return_value = []
        tab._refresh_boot_analysis()
        self.assertIn("Unable", tab.boot_stats_label.text())

    def test_partial_stats(self, sm, us, usc, ba, jm):
        """Partial stats (only total+kernel) renders correctly."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        ba.get_boot_stats.return_value = FakeBootStats(total=10.0, kernel=5.0)
        ba.get_slow_services.return_value = []
        ba.get_optimization_suggestions.return_value = []
        tab._refresh_boot_analysis()
        text = tab.boot_stats_label.text()
        self.assertIn("10.0", text)
        self.assertIn("Kernel", text)
        self.assertNotIn("Firmware", text)

    def test_slow_services_listed(self, sm, us, usc, ba, jm):
        """Slow services appear in the text area."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        ba.get_boot_stats.return_value = FakeBootStats()
        ba.get_slow_services.return_value = [
            FakeSlowService("NetworkManager.service", 8.3)
        ]
        ba.get_optimization_suggestions.return_value = []
        tab._refresh_boot_analysis()
        text = tab.slow_services_list.toPlainText()
        self.assertIn("NetworkManager", text)
        self.assertIn("8.3", text)

    def test_no_slow_services(self, sm, us, usc, ba, jm):
        """Empty slow list shows 'No services' message."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        ba.get_boot_stats.return_value = FakeBootStats()
        ba.get_slow_services.return_value = []
        ba.get_optimization_suggestions.return_value = []
        tab._refresh_boot_analysis()
        self.assertIn("No services", tab.slow_services_list.toPlainText())

    def test_suggestions_displayed(self, sm, us, usc, ba, jm):
        """Suggestions are joined and shown in label."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        ba.get_boot_stats.return_value = FakeBootStats()
        ba.get_slow_services.return_value = []
        ba.get_optimization_suggestions.return_value = [
            "Disable unneeded services",
            "Enable readahead",
        ]
        tab._refresh_boot_analysis()
        text = tab.suggestions_label.text()
        self.assertIn("Disable unneeded", text)
        self.assertIn("readahead", text)


# ===========================================================================
# _WatchtowerSubTab — _refresh_journal
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.JournalManager", new_callable=MagicMock)
@patch(f"{_M}.BootAnalyzer", new_callable=MagicMock)
@patch(f"{_M}.UnitScope", new_callable=MagicMock)
@patch(f"{_M}.UnitState", new_callable=MagicMock)
@patch(f"{_M}.ServiceManager", new_callable=MagicMock)
class TestJournal(unittest.TestCase):
    """Tests for _WatchtowerSubTab._refresh_journal."""

    def test_sets_error_count(self, sm, us, usc, ba, jm):
        """Error count label shows diagnostic error count."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.get_quick_diagnostic.return_value = {
            "error_count": 42,
            "failed_services": ["a", "b"],
        }
        jm.get_boot_errors.return_value = "some errors"
        tab._refresh_journal()
        self.assertIn("42", tab.error_count_label.text())

    def test_sets_failed_count(self, sm, us, usc, ba, jm):
        """Failed services count label shows length of list."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.get_quick_diagnostic.return_value = {
            "error_count": 5,
            "failed_services": ["x", "y", "z"],
        }
        jm.get_boot_errors.return_value = ""
        tab._refresh_journal()
        self.assertIn("3", tab.failed_count_label.text())

    def test_shows_boot_errors(self, sm, us, usc, ba, jm):
        """Boot errors text is set in journal output."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.get_quick_diagnostic.return_value = {
            "error_count": 1,
            "failed_services": [],
        }
        jm.get_boot_errors.return_value = "kernel BUG at mm/page_alloc"
        tab._refresh_journal()
        self.assertIn("kernel BUG", tab.journal_output.toPlainText())

    def test_no_errors_message(self, sm, us, usc, ba, jm):
        """Empty errors shows 'No errors' text."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.get_quick_diagnostic.return_value = {
            "error_count": 0,
            "failed_services": [],
        }
        jm.get_boot_errors.return_value = ""
        tab._refresh_journal()
        self.assertIn("No errors", tab.journal_output.toPlainText())


# ===========================================================================
# _WatchtowerSubTab — export methods
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.QMessageBox")
@patch(f"{_M}.JournalManager", new_callable=MagicMock)
@patch(f"{_M}.BootAnalyzer", new_callable=MagicMock)
@patch(f"{_M}.UnitScope", new_callable=MagicMock)
@patch(f"{_M}.UnitState", new_callable=MagicMock)
@patch(f"{_M}.ServiceManager", new_callable=MagicMock)
class TestExports(unittest.TestCase):
    """Tests for panic log and support bundle export."""

    def test_panic_log_success(self, sm, us, usc, ba, jm, msgbox):
        """Successful panic export shows information dialog."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.export_panic_log.return_value = FakeResult(
            True, "OK", {"path": "/tmp/panic.log"}
        )
        tab._export_panic_log()
        msgbox.information.assert_called_once()

    def test_panic_log_failure(self, sm, us, usc, ba, jm, msgbox):
        """Failed panic export shows warning dialog."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.export_panic_log.return_value = FakeResult(False, "No access")
        tab._export_panic_log()
        msgbox.warning.assert_called_once()

    def test_bundle_success(self, sm, us, usc, ba, jm, msgbox):
        """Successful bundle export shows information dialog."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.export_support_bundle.return_value = FakeResult(
            True, "OK", {"path": "/tmp/bundle.zip"}
        )
        tab._export_support_bundle()
        msgbox.information.assert_called_once()

    def test_bundle_failure(self, sm, us, usc, ba, jm, msgbox):
        """Failed bundle export shows warning dialog."""
        tab = _make_watchtower(sm, ba, jm, us, usc)
        jm.export_support_bundle.return_value = FakeResult(False, "Disk full")
        tab._export_support_bundle()
        msgbox.warning.assert_called_once()


# ===========================================================================
# _BootSubTab — refresh_kernel
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestRefreshKernel(unittest.TestCase):
    """Tests for _BootSubTab.refresh_kernel."""

    def test_displays_params(self, km, zm, sb):
        """Current params label shows kernel parameters."""
        tab = _make_boot(km, zm, sb)
        km.get_current_params.return_value = ["quiet", "splash", "ro"]
        km.has_param.return_value = False
        tab.refresh_kernel()
        text = tab.current_params_label.text()
        self.assertIn("quiet", text)
        self.assertIn("splash", text)

    def test_truncates_long_params(self, km, zm, sb):
        """More than 10 params adds ellipsis."""
        tab = _make_boot(km, zm, sb)
        km.get_current_params.return_value = [f"p{i}" for i in range(15)]
        km.has_param.return_value = False
        tab.refresh_kernel()
        self.assertIn("...", tab.current_params_label.text())

    def test_updates_checkboxes(self, km, zm, sb):
        """Checkboxes reflect KernelManager.has_param results."""
        tab = _make_boot(km, zm, sb)
        km.get_current_params.return_value = []
        km.has_param.side_effect = lambda p: p == "nowatchdog"
        tab.refresh_kernel()
        for param, cb in tab.param_checkboxes.items():
            if param == "nowatchdog":
                self.assertTrue(cb.isChecked())
            else:
                self.assertFalse(cb.isChecked())


# ===========================================================================
# _BootSubTab — refresh_zram
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestRefreshZram(unittest.TestCase):
    """Tests for _BootSubTab.refresh_zram."""

    def test_active_zram(self, km, zm, sb):
        """Active ZRAM shows 'Active' in status label."""
        tab = _make_boot(km, zm, sb)
        zm.get_current_config.return_value = FakeZramConfig(enabled=True)
        zm.get_current_usage.return_value = None
        tab.refresh_zram()
        self.assertIn("Active", tab.zram_status_label.text())

    def test_inactive_zram(self, km, zm, sb):
        """Inactive ZRAM shows 'Inactive' in status label."""
        tab = _make_boot(km, zm, sb)
        zm.get_current_config.return_value = FakeZramConfig(enabled=False)
        zm.get_current_usage.return_value = None
        tab.refresh_zram()
        self.assertIn("Inactive", tab.zram_status_label.text())

    def test_active_with_usage(self, km, zm, sb):
        """Active ZRAM with usage shows MB values."""
        tab = _make_boot(km, zm, sb)
        zm.get_current_config.return_value = FakeZramConfig(enabled=True)
        zm.get_current_usage.return_value = (512, 4096)
        tab.refresh_zram()
        text = tab.zram_status_label.text()
        self.assertIn("512", text)
        self.assertIn("4096", text)

    def test_slider_set_to_config(self, km, zm, sb):
        """Slider value and label reflect config size_percent."""
        tab = _make_boot(km, zm, sb)
        zm.get_current_config.return_value = FakeZramConfig(size_percent=75)
        zm.get_current_usage.return_value = None
        tab.refresh_zram()
        self.assertEqual(tab.zram_slider.value(), 75)
        self.assertIn("75%", tab.zram_size_label.text())


# ===========================================================================
# _BootSubTab — refresh_secureboot
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestRefreshSecureBoot(unittest.TestCase):
    """Tests for _BootSubTab.refresh_secureboot."""

    def test_enabled(self, km, zm, sb):
        """Secure Boot enabled shows 'Enabled'."""
        tab = _make_boot(km, zm, sb)
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True)
        sb.has_keys.return_value = False
        tab.refresh_secureboot()
        self.assertIn("Enabled", tab.sb_status_label.text())

    def test_disabled(self, km, zm, sb):
        """Secure Boot disabled shows 'Disabled'."""
        tab = _make_boot(km, zm, sb)
        sb.get_status.return_value = FakeSecureBootStatus(enabled=False)
        sb.has_keys.return_value = False
        tab.refresh_secureboot()
        self.assertIn("Disabled", tab.sb_status_label.text())

    def test_has_keys(self, km, zm, sb):
        """Generated MOK key shows 'Generated'."""
        tab = _make_boot(km, zm, sb)
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True)
        sb.has_keys.return_value = True
        tab.refresh_secureboot()
        self.assertIn("Generated", tab.mok_status_label.text())

    def test_no_keys(self, km, zm, sb):
        """No MOK key shows 'Not generated'."""
        tab = _make_boot(km, zm, sb)
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True)
        sb.has_keys.return_value = False
        tab.refresh_secureboot()
        self.assertIn("Not generated", tab.mok_status_label.text())

    def test_pending_enrollment(self, km, zm, sb):
        """Pending MOK appends 'Pending enrollment' to label."""
        tab = _make_boot(km, zm, sb)
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True, pending=True)
        sb.has_keys.return_value = True
        tab.refresh_secureboot()
        self.assertIn("Pending enrollment", tab.mok_status_label.text())


# ===========================================================================
# _BootSubTab — on_param_toggled
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestParamToggle(unittest.TestCase):
    """Tests for _BootSubTab.on_param_toggled."""

    def test_checked_adds(self, km, zm, sb):
        """Checking calls add_param."""
        tab = _make_boot(km, zm, sb)
        km.add_param.return_value = FakeKernelResult(True, "Added")
        from PyQt6.QtCore import Qt

        tab.on_param_toggled("nowatchdog", Qt.CheckState.Checked.value)
        km.add_param.assert_called_once_with("nowatchdog")

    def test_unchecked_removes(self, km, zm, sb):
        """Unchecking calls remove_param."""
        tab = _make_boot(km, zm, sb)
        km.remove_param.return_value = FakeKernelResult(True, "Removed")
        from PyQt6.QtCore import Qt

        tab.on_param_toggled("nowatchdog", Qt.CheckState.Unchecked.value)
        km.remove_param.assert_called_once_with("nowatchdog")

    def test_failure_refreshes_kernel(self, km, zm, sb):
        """Failed toggle calls refresh_kernel to revert checkbox."""
        tab = _make_boot(km, zm, sb)
        km.add_param.return_value = FakeKernelResult(False, "Denied")
        km.get_current_params.reset_mock()
        from PyQt6.QtCore import Qt

        tab.on_param_toggled("test", Qt.CheckState.Checked.value)
        self.assertTrue(km.get_current_params.called)

    def test_logs_message(self, km, zm, sb):
        """Toggle logs the result message."""
        tab = _make_boot(km, zm, sb)
        km.add_param.return_value = FakeKernelResult(True, "Param added")
        from PyQt6.QtCore import Qt

        tab.on_param_toggled("test", Qt.CheckState.Checked.value)
        self.assertIn("Param added", tab.output_text.toPlainText())


# ===========================================================================
# _BootSubTab — add_custom_param / remove_custom_param
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestCustomParam(unittest.TestCase):
    """Tests for add_custom_param and remove_custom_param."""

    def test_add(self, km, zm, sb):
        """Adding custom param calls KernelManager.add_param and clears input."""
        tab = _make_boot(km, zm, sb)
        tab.custom_param_input.setText("mem=4G")
        km.add_param.return_value = FakeKernelResult(True, "Added")
        tab.add_custom_param()
        km.add_param.assert_called_with("mem=4G")
        self.assertEqual(tab.custom_param_input.text(), "")

    def test_add_empty_noop(self, km, zm, sb):
        """Adding empty string does nothing."""
        tab = _make_boot(km, zm, sb)
        tab.custom_param_input.setText("   ")
        km.add_param.reset_mock()
        tab.add_custom_param()
        km.add_param.assert_not_called()

    def test_remove(self, km, zm, sb):
        """Removing custom param calls KernelManager.remove_param."""
        tab = _make_boot(km, zm, sb)
        tab.custom_param_input.setText("mem=4G")
        km.remove_param.return_value = FakeKernelResult(True, "Removed")
        tab.remove_custom_param()
        km.remove_param.assert_called_with("mem=4G")
        self.assertEqual(tab.custom_param_input.text(), "")

    def test_remove_empty_noop(self, km, zm, sb):
        """Removing empty string does nothing."""
        tab = _make_boot(km, zm, sb)
        tab.custom_param_input.setText("")
        km.remove_param.reset_mock()
        tab.remove_custom_param()
        km.remove_param.assert_not_called()


# ===========================================================================
# _BootSubTab — backup_grub / restore_grub
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.QInputDialog")
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestGrubBackupRestore(unittest.TestCase):
    """Tests for backup_grub and restore_grub."""

    def test_backup_with_path(self, km, zm, sb, dlg):
        """Backup with backup_path logs the path."""
        tab = _make_boot(km, zm, sb)
        km.backup_grub.return_value = FakeKernelResult(
            True, "Backup created", backup_path="/tmp/grub.bak"
        )
        tab.backup_grub()
        text = tab.output_text.toPlainText()
        self.assertIn("Backup created", text)
        self.assertIn("/tmp/grub.bak", text)

    def test_backup_without_path(self, km, zm, sb, dlg):
        """Backup without backup_path only logs message."""
        tab = _make_boot(km, zm, sb)
        km.backup_grub.return_value = FakeKernelResult(True, "Backup created")
        tab.backup_grub()
        text = tab.output_text.toPlainText()
        self.assertIn("Backup created", text)

    def test_restore_no_backups(self, km, zm, sb, dlg):
        """No backups logs 'No backups available'."""
        tab = _make_boot(km, zm, sb)
        km.get_backups.return_value = []
        tab.restore_grub()
        self.assertIn("No backups", tab.output_text.toPlainText())

    def test_restore_selects_backup(self, km, zm, sb, dlg):
        """Selecting a backup calls restore_backup."""
        tab = _make_boot(km, zm, sb)
        backups = [FakeBackupPath("backup-2025-01-01")]
        km.get_backups.return_value = backups
        km.BACKUP_DIR = MagicMock()
        km.BACKUP_DIR.__truediv__ = MagicMock(return_value="/backups/backup-2025-01-01")
        km.restore_backup.return_value = FakeKernelResult(True, "Restored")
        dlg.getItem.return_value = ("backup-2025-01-01", True)
        tab.restore_grub()
        km.restore_backup.assert_called_once()
        self.assertIn("Restored", tab.output_text.toPlainText())

    def test_restore_user_cancels(self, km, zm, sb, dlg):
        """User cancelling dialog does not restore."""
        tab = _make_boot(km, zm, sb)
        km.get_backups.return_value = [FakeBackupPath("bk")]
        dlg.getItem.return_value = ("", False)
        tab.restore_grub()
        km.restore_backup.assert_not_called()


# ===========================================================================
# _BootSubTab — ZRAM slider / apply
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestZramActions(unittest.TestCase):
    """Tests for ZRAM slider and apply."""

    def test_slider_updates_label(self, km, zm, sb):
        """Slider value change updates size label."""
        tab = _make_boot(km, zm, sb)
        tab.on_zram_slider_changed(75)
        self.assertEqual(tab.zram_size_label.text(), "75%")

    def test_slider_max_value(self, km, zm, sb):
        """Slider at 150% updates label."""
        tab = _make_boot(km, zm, sb)
        tab.on_zram_slider_changed(150)
        self.assertEqual(tab.zram_size_label.text(), "150%")

    def test_apply_zram(self, km, zm, sb):
        """Apply calls set_config and refreshes."""
        tab = _make_boot(km, zm, sb)
        tab.zram_slider.setValue(75)
        # Set algorithm combo to zstd
        idx = tab.zram_algo_combo.findData("zstd")
        if idx >= 0:
            tab.zram_algo_combo.setCurrentIndex(idx)
        zm.set_config.return_value = MagicMock(message="ZRAM configured")
        zm.get_current_config.return_value = FakeZramConfig(size_percent=75)
        zm.get_current_usage.return_value = None
        tab.apply_zram()
        zm.set_config.assert_called_once_with(75, "zstd")


# ===========================================================================
# _BootSubTab — generate_mok_key
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.QMessageBox")
@patch(f"{_M}.QInputDialog")
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestGenerateMokKey(unittest.TestCase):
    """Tests for _BootSubTab.generate_mok_key."""

    def test_short_password(self, km, zm, sb, dlg, msgbox):
        """Password <8 chars logs error, does not call generate_key."""
        tab = _make_boot(km, zm, sb)
        dlg.getText.return_value = ("short", True)
        tab.generate_mok_key()
        self.assertIn("too short", tab.output_text.toPlainText())
        sb.generate_key.assert_not_called()

    def test_success(self, km, zm, sb, dlg, msgbox):
        """Valid password generates key and refreshes."""
        tab = _make_boot(km, zm, sb)
        dlg.getText.return_value = ("longpassword", True)
        sb.generate_key.return_value = FakeSecureBootResult(True, "Key gen")
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True)
        sb.has_keys.return_value = True
        tab.generate_mok_key()
        sb.generate_key.assert_called_once_with("longpassword")

    def test_cancel_dialog(self, km, zm, sb, dlg, msgbox):
        """Cancelling dialog does not generate key."""
        tab = _make_boot(km, zm, sb)
        dlg.getText.return_value = ("", False)
        tab.generate_mok_key()
        sb.generate_key.assert_not_called()


# ===========================================================================
# _BootSubTab — enroll_mok_key
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.QMessageBox")
@patch(f"{_M}.QInputDialog")
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestEnrollMokKey(unittest.TestCase):
    """Tests for _BootSubTab.enroll_mok_key."""

    def test_no_keys(self, km, zm, sb, dlg, msgbox):
        """No keys logs 'Generate one first'."""
        tab = _make_boot(km, zm, sb)
        sb.has_keys.return_value = False
        tab.enroll_mok_key()
        self.assertIn("No MOK key", tab.output_text.toPlainText())
        sb.import_key.assert_not_called()

    def test_success_with_reboot(self, km, zm, sb, dlg, msgbox):
        """Enrollment requiring reboot shows info dialog."""
        tab = _make_boot(km, zm, sb)
        sb.has_keys.return_value = True
        dlg.getText.return_value = ("password123", True)
        sb.import_key.return_value = FakeSecureBootResult(
            True, "Enrolled", requires_reboot=True
        )
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True)
        tab.enroll_mok_key()
        sb.import_key.assert_called_once_with("password123")
        msgbox.information.assert_called_once()

    def test_success_without_reboot(self, km, zm, sb, dlg, msgbox):
        """Enrollment not requiring reboot does not show dialog."""
        tab = _make_boot(km, zm, sb)
        sb.has_keys.return_value = True
        dlg.getText.return_value = ("password123", True)
        sb.import_key.return_value = FakeSecureBootResult(
            True, "Enrolled", requires_reboot=False
        )
        sb.get_status.return_value = FakeSecureBootStatus(enabled=True)
        tab.enroll_mok_key()
        sb.import_key.assert_called_once()
        msgbox.information.assert_not_called()

    def test_cancel_dialog(self, km, zm, sb, dlg, msgbox):
        """Cancelling password dialog does not enroll."""
        tab = _make_boot(km, zm, sb)
        sb.has_keys.return_value = True
        dlg.getText.return_value = ("", False)
        tab.enroll_mok_key()
        sb.import_key.assert_not_called()


# ===========================================================================
# _BootSubTab — log helper
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestLog(unittest.TestCase):
    """Tests for _BootSubTab.log."""

    def test_appends_message(self, km, zm, sb):
        """log() appends message to output."""
        tab = _make_boot(km, zm, sb)
        tab.log("Test message")
        self.assertIn("Test message", tab.output_text.toPlainText())

    def test_multiple_messages(self, km, zm, sb):
        """Multiple log() calls accumulate."""
        tab = _make_boot(km, zm, sb)
        tab.log("First")
        tab.log("Second")
        text = tab.output_text.toPlainText()
        self.assertIn("First", text)
        self.assertIn("Second", text)


# ===========================================================================
# _BootSubTab — refresh_all
# ===========================================================================


@patch(f"{_M}.configure_top_tabs", MagicMock())
@patch(f"{_M}.SecureBootManager", new_callable=MagicMock)
@patch(f"{_M}.ZramManager", new_callable=MagicMock)
@patch(f"{_M}.KernelManager", new_callable=MagicMock)
class TestRefreshAll(unittest.TestCase):
    """Tests for _BootSubTab.refresh_all."""

    def test_calls_all_refreshers(self, km, zm, sb):
        """refresh_all calls kernel, zram, and secureboot refresh."""
        tab = _make_boot(km, zm, sb)
        km.get_current_params.reset_mock()
        zm.get_current_config.reset_mock()
        sb.get_status.reset_mock()
        tab.refresh_all()
        km.get_current_params.assert_called_once()
        zm.get_current_config.assert_called_once()
        sb.get_status.assert_called_once()


# ===========================================================================
# DiagnosticsTab — metadata and source-level checks
# ===========================================================================


class TestDiagnosticsTabMetadata(unittest.TestCase):
    """Tests for DiagnosticsTab._METADATA and metadata()."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "loofi-fedora-tweaks",
            "ui",
            "diagnostics_tab.py",
        )
        with open(path, "r", encoding="utf-8") as fh:
            cls.source = fh.read()

    def test_metadata_id(self):
        """Metadata ID is 'diagnostics'."""
        self.assertIn('id="diagnostics"', self.source)

    def test_metadata_name(self):
        """Metadata name is 'Diagnostics'."""
        self.assertIn('name="Diagnostics"', self.source)

    def test_metadata_category(self):
        """Metadata category is 'Maintenance'."""
        self.assertIn('category="Maintenance"', self.source)

    def test_create_widget_returns_self(self):
        """create_widget returns self."""
        self.assertIn("return self", self.source)

    def test_inherits_base_tab(self):
        """DiagnosticsTab inherits BaseTab."""
        self.assertIn("class DiagnosticsTab(BaseTab)", self.source)


class TestDiagnosticsTabStructure(unittest.TestCase):
    """Source-level checks for DiagnosticsTab structure."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "loofi-fedora-tweaks",
            "ui",
            "diagnostics_tab.py",
        )
        with open(path, "r", encoding="utf-8") as fh:
            cls.source = fh.read()

    def test_has_watchtower_sub_tab(self):
        """Source contains _WatchtowerSubTab class."""
        self.assertIn("class _WatchtowerSubTab", self.source)

    def test_has_boot_sub_tab(self):
        """Source contains _BootSubTab class."""
        self.assertIn("class _BootSubTab", self.source)

    def test_has_service_action_method(self):
        """Source contains _service_action method."""
        self.assertIn("def _service_action", self.source)

    def test_has_refresh_boot_analysis(self):
        """Source contains _refresh_boot_analysis method."""
        self.assertIn("def _refresh_boot_analysis", self.source)

    def test_has_refresh_journal(self):
        """Source contains _refresh_journal method."""
        self.assertIn("def _refresh_journal", self.source)

    def test_has_export_panic_log(self):
        """Source contains _export_panic_log method."""
        self.assertIn("def _export_panic_log", self.source)

    def test_has_export_support_bundle(self):
        """Source contains _export_support_bundle method."""
        self.assertIn("def _export_support_bundle", self.source)

    def test_has_refresh_kernel(self):
        """Source contains refresh_kernel method."""
        self.assertIn("def refresh_kernel", self.source)

    def test_has_refresh_zram(self):
        """Source contains refresh_zram method."""
        self.assertIn("def refresh_zram", self.source)

    def test_has_refresh_secureboot(self):
        """Source contains refresh_secureboot method."""
        self.assertIn("def refresh_secureboot", self.source)

    def test_has_generate_mok_key(self):
        """Source contains generate_mok_key method."""
        self.assertIn("def generate_mok_key", self.source)

    def test_has_enroll_mok_key(self):
        """Source contains enroll_mok_key method."""
        self.assertIn("def enroll_mok_key", self.source)

    def test_has_backup_grub(self):
        """Source contains backup_grub method."""
        self.assertIn("def backup_grub", self.source)

    def test_has_restore_grub(self):
        """Source contains restore_grub method."""
        self.assertIn("def restore_grub", self.source)

    def test_uses_service_manager(self):
        """Source imports ServiceManager."""
        self.assertIn("ServiceManager", self.source)

    def test_uses_kernel_manager(self):
        """Source imports KernelManager."""
        self.assertIn("KernelManager", self.source)

    def test_uses_zram_manager(self):
        """Source imports ZramManager."""
        self.assertIn("ZramManager", self.source)

    def test_uses_secureboot_manager(self):
        """Source imports SecureBootManager."""
        self.assertIn("SecureBootManager", self.source)

    def test_uses_boot_analyzer(self):
        """Source imports BootAnalyzer."""
        self.assertIn("BootAnalyzer", self.source)

    def test_uses_journal_manager(self):
        """Source imports JournalManager."""
        self.assertIn("JournalManager", self.source)

    def test_tabs_watchtower_and_boot(self):
        """Main tab adds Watchtower and Boot sub-tabs."""
        self.assertIn("Watchtower", self.source)
        self.assertIn("Boot", self.source)


if __name__ == "__main__":
    unittest.main()
