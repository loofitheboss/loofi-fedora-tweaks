"""Tests for ui/monitor_tab.py — MonitorTab, MiniGraph, DualMiniGraph, _CoreBar,
_PerformanceSubTab, and _ProcessesSubTab.

Covers graph widgets, performance tick updates, process table refresh,
sorting, filtering, context menu actions (kill/renice), and the
PluginInterface metadata contract.
"""

import importlib
import os
import sys
import types
import unittest
from collections import deque
from dataclasses import dataclass
from typing import List
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


# ---------------------------------------------------------------------------
# Lightweight stubs for PyQt6 so the module can be imported without a display
# ---------------------------------------------------------------------------


class _StdBtn:
    """Enum-like button flag that supports bitwise OR (for QMessageBox.StandardButton)."""

    def __init__(self, name):
        self._name = name

    def __or__(self, other):
        return self

    def __ror__(self, other):
        return self

    def __eq__(self, other):
        return isinstance(other, _StdBtn) and self._name == other._name

    def __hash__(self):
        return hash(self._name)

    def __repr__(self):
        return f"StandardButton.{self._name}"


# Module-level button singletons for test assertions
STD_BTN_YES = _StdBtn("Yes")
STD_BTN_NO = _StdBtn("No")


class _Dummy:
    """Universal stub that absorbs any constructor / attribute access."""

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

    def __or__(self, other):
        return self


def _install_monitor_import_stubs():
    """Register lightweight PyQt6 stubs so ui.monitor_tab can be imported."""

    # -- PyQt6.QtWidgets --
    qt_widgets = types.ModuleType("PyQt6.QtWidgets")
    for name in (
        "QWidget",
        "QVBoxLayout",
        "QHBoxLayout",
        "QLabel",
        "QPushButton",
        "QComboBox",
        "QTreeWidget",
        "QTreeWidgetItem",
        "QMenu",
        "QMessageBox",
        "QInputDialog",
        "QFrame",
        "QHeaderView",
        "QGridLayout",
        "QGroupBox",
        "QTabWidget",
    ):
        setattr(qt_widgets, name, _Dummy)

    # QMessageBox needs StandardButton with enum-like attributes that support |
    _std_btn = types.SimpleNamespace(Yes=STD_BTN_YES, No=STD_BTN_NO)

    qt_widgets.QMessageBox = type(
        "QMessageBox",
        (_Dummy,),
        {
            "StandardButton": _std_btn,
            "question": staticmethod(lambda *a, **kw: _std_btn.No),
            "information": staticmethod(lambda *a, **kw: None),
            "warning": staticmethod(lambda *a, **kw: None),
        },
    )

    qt_widgets.QInputDialog = type(
        "QInputDialog",
        (_Dummy,),
        {
            "getInt": staticmethod(lambda *a, **kw: (0, False)),
        },
    )

    # -- PyQt6.QtCore --
    qt_core = types.ModuleType("PyQt6.QtCore")
    qt_core.Qt = types.SimpleNamespace(
        PenStyle=types.SimpleNamespace(NoPen=0),
        BrushStyle=types.SimpleNamespace(NoBrush=0),
        ContextMenuPolicy=types.SimpleNamespace(CustomContextMenu=0),
        AlignmentFlag=types.SimpleNamespace(
            AlignRight=0x0002,
            AlignVCenter=0x0080,
        ),
        ItemDataRole=types.SimpleNamespace(UserRole=0x0100),
    )
    qt_core.QTimer = _Dummy

    # -- PyQt6.QtGui --
    qt_gui = types.ModuleType("PyQt6.QtGui")
    for name in (
        "QPainter",
        "QColor",
        "QPen",
        "QPainterPath",
        "QLinearGradient",
        "QBrush",
    ):
        setattr(qt_gui, name, _Dummy)

    # -- PyQt6 package --
    pyqt = types.ModuleType("PyQt6")
    pyqt.QtWidgets = qt_widgets
    pyqt.QtCore = qt_core
    pyqt.QtGui = qt_gui

    # -- Dependency stubs --
    tab_utils_module = types.ModuleType("ui.tab_utils")
    tab_utils_module.configure_top_tabs = lambda *a, **kw: None

    interface_module = types.ModuleType("core.plugins.interface")
    interface_module.PluginInterface = type(
        "PluginInterface",
        (),
        {
            "metadata": lambda self: None,
            "create_widget": lambda self: None,
        },
    )

    metadata_module = types.ModuleType("core.plugins.metadata")

    class _PluginMetadata:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    metadata_module.PluginMetadata = _PluginMetadata

    perf_module = types.ModuleType("utils.performance")
    perf_module.PerformanceCollector = _Dummy

    proc_module = types.ModuleType("services.system")
    proc_module.ProcessManager = _Dummy

    log_module = types.ModuleType("utils.log")
    log_module.get_logger = lambda name: MagicMock()

    # Register all stubs
    sys.modules["PyQt6"] = pyqt
    sys.modules["PyQt6.QtWidgets"] = qt_widgets
    sys.modules["PyQt6.QtCore"] = qt_core
    sys.modules["PyQt6.QtGui"] = qt_gui
    sys.modules["ui.tab_utils"] = tab_utils_module
    sys.modules["core.plugins.interface"] = interface_module
    sys.modules["core.plugins.metadata"] = metadata_module
    sys.modules["utils.performance"] = perf_module
    sys.modules["services.system"] = proc_module
    sys.modules["utils.log"] = log_module


# ---------------------------------------------------------------------------
# Data stubs mirroring the real dataclasses
# ---------------------------------------------------------------------------


@dataclass
class _CpuSample:
    timestamp: float = 0.0
    percent: float = 0.0
    per_core: List[float] = None

    def __post_init__(self):
        if self.per_core is None:
            self.per_core = []


@dataclass
class _MemorySample:
    timestamp: float = 0.0
    percent: float = 0.0
    used_bytes: int = 0
    total_bytes: int = 0


@dataclass
class _NetworkSample:
    timestamp: float = 0.0
    bytes_sent: int = 0
    bytes_recv: int = 0
    send_rate: float = 0.0
    recv_rate: float = 0.0


@dataclass
class _DiskIOSample:
    timestamp: float = 0.0
    read_bytes: int = 0
    write_bytes: int = 0
    read_rate: float = 0.0
    write_rate: float = 0.0


@dataclass
class _ProcessInfo:
    pid: int = 0
    name: str = ""
    user: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_bytes: int = 0
    state: str = "S"
    command: str = ""
    nice: int = 0


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

_MODULE_KEYS = [
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "ui.tab_utils",
    "core.plugins.interface",
    "core.plugins.metadata",
    "utils.performance",
    "services.system",
    "utils.log",
    "ui.monitor_tab",
]

_module_backup = {}


def setUpModule():
    """Install stubs and import ui.monitor_tab."""
    global _module_backup
    for key in _MODULE_KEYS:
        _module_backup[key] = sys.modules.get(key)
    _install_monitor_import_stubs()
    # Force re-import so stubs are used
    sys.modules.pop("ui.monitor_tab", None)
    importlib.import_module("ui.monitor_tab")


def tearDownModule():
    """Restore original modules."""
    sys.modules.pop("ui.monitor_tab", None)
    for key, orig in _module_backup.items():
        if orig is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = orig


def _get_module():
    """Return the imported ui.monitor_tab module."""
    return sys.modules["ui.monitor_tab"]


# ===================================================================
# Tests for MonitorTab (PluginInterface)
# ===================================================================


class TestMonitorTabMetadata(unittest.TestCase):
    """Tests for MonitorTab.metadata() and create_widget()."""

    def setUp(self):
        mod = _get_module()
        self.tab = mod.MonitorTab.__new__(mod.MonitorTab)
        # Manually assign _METADATA since __init__ is not called
        self.tab._METADATA = mod.MonitorTab._METADATA

    def test_metadata_returns_plugin_metadata(self):
        """metadata() should return a PluginMetadata instance."""
        meta = self.tab.metadata()
        self.assertIsNotNone(meta)

    def test_metadata_id_is_monitor(self):
        """metadata().id should be 'monitor'."""
        self.assertEqual(self.tab.metadata().id, "monitor")

    def test_metadata_name(self):
        """metadata().name should be 'System Monitor'."""
        self.assertEqual(self.tab.metadata().name, "System Monitor")

    def test_metadata_category(self):
        """metadata().category should be 'System'."""
        self.assertEqual(self.tab.metadata().category, "System")

    def test_metadata_icon(self):
        """metadata().icon should be the bar-chart emoji."""
        self.assertIn(self.tab.metadata().icon, "\U0001f4ca")

    def test_metadata_order(self):
        """metadata().order should be 30."""
        self.assertEqual(self.tab.metadata().order, 30)

    def test_create_widget_returns_self(self):
        """create_widget() should return self."""
        result = self.tab.create_widget()
        self.assertIs(result, self.tab)


# ===================================================================
# Tests for MiniGraph
# ===================================================================


class TestMiniGraph(unittest.TestCase):
    """Tests for MiniGraph data handling (no painting)."""

    def _make_graph(self):
        """Create a MiniGraph instance with stubbed super().__init__."""
        mod = _get_module()
        graph = mod.MiniGraph.__new__(mod.MiniGraph)
        # Manually initialise the fields that __init__ would set
        graph._color = _Dummy("#3dd68c")
        graph._values = deque(maxlen=mod.MiniGraph.MAX_POINTS)
        graph._max_value = 100.0
        return graph

    def test_max_points_constant(self):
        """MAX_POINTS should be 60."""
        mod = _get_module()
        self.assertEqual(mod.MiniGraph.MAX_POINTS, 60)

    def test_set_max_value_normal(self):
        """set_max_value should store the given value."""
        graph = self._make_graph()
        graph.set_max_value(200.0)
        self.assertEqual(graph._max_value, 200.0)

    def test_set_max_value_enforces_minimum(self):
        """set_max_value should clamp to at least 1.0."""
        graph = self._make_graph()
        graph.set_max_value(0.0)
        self.assertEqual(graph._max_value, 1.0)

    def test_set_max_value_negative(self):
        """set_max_value with negative value should clamp to 1.0."""
        graph = self._make_graph()
        graph.set_max_value(-50.0)
        self.assertEqual(graph._max_value, 1.0)

    def test_add_value_appends(self):
        """add_value should append a data point to _values."""
        graph = self._make_graph()
        graph.update = MagicMock()
        graph.add_value(42.5)
        self.assertEqual(len(graph._values), 1)
        self.assertEqual(graph._values[0], 42.5)

    def test_add_value_triggers_update(self):
        """add_value should call self.update() to trigger repaint."""
        graph = self._make_graph()
        graph.update = MagicMock()
        graph.add_value(10.0)
        graph.update.assert_called_once()

    def test_add_value_deque_overflow(self):
        """Deque should drop oldest values when MAX_POINTS is exceeded."""
        graph = self._make_graph()
        graph.update = MagicMock()
        for i in range(70):
            graph.add_value(float(i))
        self.assertEqual(len(graph._values), 60)
        # Oldest remaining should be 10 (items 0-9 were dropped)
        self.assertEqual(graph._values[0], 10.0)

    def test_initial_max_value(self):
        """Default _max_value should be 100.0."""
        graph = self._make_graph()
        self.assertEqual(graph._max_value, 100.0)


# ===================================================================
# Tests for DualMiniGraph
# ===================================================================


class TestDualMiniGraph(unittest.TestCase):
    """Tests for DualMiniGraph data handling and auto-scaling."""

    def _make_graph(self):
        """Create a DualMiniGraph instance with stubbed fields."""
        mod = _get_module()
        graph = mod.DualMiniGraph.__new__(mod.DualMiniGraph)
        graph._color_a = _Dummy("#b78eff")
        graph._color_b = _Dummy("#4dd9e3")
        graph._values_a = deque(maxlen=mod.DualMiniGraph.MAX_POINTS)
        graph._values_b = deque(maxlen=mod.DualMiniGraph.MAX_POINTS)
        graph._max_value = 1024.0
        graph.update = MagicMock()
        return graph

    def test_max_points_constant(self):
        """MAX_POINTS should be 60."""
        mod = _get_module()
        self.assertEqual(mod.DualMiniGraph.MAX_POINTS, 60)

    def test_add_values_appends_both_series(self):
        """add_values should append to both _values_a and _values_b."""
        graph = self._make_graph()
        graph.add_values(100.0, 200.0)
        self.assertEqual(len(graph._values_a), 1)
        self.assertEqual(len(graph._values_b), 1)
        self.assertEqual(graph._values_a[0], 100.0)
        self.assertEqual(graph._values_b[0], 200.0)

    def test_add_values_triggers_update(self):
        """add_values should call update() for repaint."""
        graph = self._make_graph()
        graph.add_values(10.0, 20.0)
        graph.update.assert_called_once()

    def test_auto_scale_increases_max(self):
        """_max_value should auto-scale to 1.2x peak when above floor."""
        graph = self._make_graph()
        # Add values that exceed the default 1024.0 floor
        graph.add_values(2000.0, 3000.0)
        # peak = 3000, expected max = 3000 * 1.2 = 3600.0
        self.assertAlmostEqual(graph._max_value, 3600.0)

    def test_auto_scale_enforces_floor(self):
        """_max_value should not drop below the 1024.0 floor."""
        graph = self._make_graph()
        graph.add_values(10.0, 20.0)
        # peak = 20, 20 * 1.2 = 24.0 < 1024.0 so floor applies
        self.assertEqual(graph._max_value, 1024.0)

    def test_auto_scale_with_mixed_values(self):
        """Auto-scale should consider all values across both series."""
        graph = self._make_graph()
        graph.add_values(500.0, 100.0)
        graph.add_values(100.0, 5000.0)
        # peak across all = 5000, expected = 5000 * 1.2 = 6000.0
        self.assertAlmostEqual(graph._max_value, 6000.0)

    def test_deque_overflow(self):
        """Both deques should cap at MAX_POINTS."""
        graph = self._make_graph()
        for i in range(70):
            graph.add_values(float(i), float(i * 2))
        self.assertEqual(len(graph._values_a), 60)
        self.assertEqual(len(graph._values_b), 60)


# ===================================================================
# Tests for _CoreBar
# ===================================================================


class TestCoreBar(unittest.TestCase):
    """Tests for _CoreBar value clamping."""

    def _make_bar(self):
        """Create a _CoreBar with stubbed fields."""
        mod = _get_module()
        bar = mod._CoreBar.__new__(mod._CoreBar)
        bar._value = 0.0
        bar.update = MagicMock()
        return bar

    def test_set_value_normal(self):
        """set_value with a normal percentage should store it."""
        bar = self._make_bar()
        bar.set_value(65.0)
        self.assertEqual(bar._value, 65.0)

    def test_set_value_clamps_high(self):
        """set_value above 100 should clamp to 100."""
        bar = self._make_bar()
        bar.set_value(150.0)
        self.assertEqual(bar._value, 100.0)

    def test_set_value_clamps_low(self):
        """set_value below 0 should clamp to 0."""
        bar = self._make_bar()
        bar.set_value(-10.0)
        self.assertEqual(bar._value, 0.0)

    def test_set_value_zero(self):
        """set_value(0) should store 0.0."""
        bar = self._make_bar()
        bar.set_value(0.0)
        self.assertEqual(bar._value, 0.0)

    def test_set_value_hundred(self):
        """set_value(100) should store 100.0."""
        bar = self._make_bar()
        bar.set_value(100.0)
        self.assertEqual(bar._value, 100.0)

    def test_set_value_triggers_update(self):
        """set_value should call update() for repaint."""
        bar = self._make_bar()
        bar.set_value(50.0)
        bar.update.assert_called_once()


# ===================================================================
# Tests for _PerformanceSubTab
# ===================================================================


class TestPerformanceSubTab(unittest.TestCase):
    """Tests for _PerformanceSubTab timer callbacks and core bars."""

    def _make_subtab(self):
        """Create a _PerformanceSubTab with mocked dependencies."""
        mod = _get_module()
        subtab = mod._PerformanceSubTab.__new__(mod._PerformanceSubTab)
        # Mock the collector
        subtab.collector = MagicMock()
        # Mock the UI widgets that _on_tick writes to
        subtab.cpu_graph = MagicMock()
        subtab.mem_graph = MagicMock()
        subtab.net_graph = MagicMock()
        subtab.disk_graph = MagicMock()
        subtab.lbl_cpu = MagicMock()
        subtab.lbl_mem = MagicMock()
        subtab.lbl_net = MagicMock()
        subtab.lbl_disk = MagicMock()
        subtab.cpu_core_bars = []
        subtab.cpu_core_layout = MagicMock()
        subtab.refresh_timer = MagicMock()
        # tr() passthrough
        subtab.tr = lambda s: s
        return subtab

    def test_ensure_core_bars_creates_bars(self):
        """_ensure_core_bars should create the requested number of bars."""
        subtab = self._make_subtab()
        _get_module()
        subtab._ensure_core_bars(4)
        self.assertEqual(len(subtab.cpu_core_bars), 4)

    def test_ensure_core_bars_noop_when_same_count(self):
        """_ensure_core_bars should do nothing if count matches."""
        subtab = self._make_subtab()
        subtab._ensure_core_bars(4)
        bars_before = list(subtab.cpu_core_bars)
        subtab._ensure_core_bars(4)
        # Should be the same bar objects (not recreated)
        self.assertEqual(subtab.cpu_core_bars, bars_before)

    def test_ensure_core_bars_recreates_on_count_change(self):
        """_ensure_core_bars should recreate bars when count changes."""
        subtab = self._make_subtab()
        subtab._ensure_core_bars(2)
        self.assertEqual(len(subtab.cpu_core_bars), 2)
        subtab._ensure_core_bars(4)
        self.assertEqual(len(subtab.cpu_core_bars), 4)

    @patch("ui.monitor_tab.PerformanceCollector")
    def test_on_tick_cpu(self, mock_collector_cls):
        """_on_tick should update CPU graph and labels when cpu sample is present."""
        subtab = self._make_subtab()
        cpu_sample = _CpuSample(percent=45.0, per_core=[40.0, 50.0])
        subtab.collector.collect_all.return_value = {
            "cpu": cpu_sample,
            "memory": None,
            "network": None,
            "disk_io": None,
        }

        subtab._on_tick()

        subtab.cpu_graph.add_value.assert_called_once_with(45.0)
        subtab.lbl_cpu.setText.assert_called_once()
        label_text = subtab.lbl_cpu.setText.call_args[0][0]
        self.assertIn("45.0", label_text)
        self.assertIn("2", label_text)

    @patch("ui.monitor_tab.PerformanceCollector")
    def test_on_tick_memory(self, mock_collector_cls):
        """_on_tick should update memory graph and labels."""
        subtab = self._make_subtab()
        mem_sample = _MemorySample(
            percent=60.0,
            used_bytes=4 * 1024**3,
            total_bytes=8 * 1024**3,
        )
        subtab.collector.collect_all.return_value = {
            "cpu": None,
            "memory": mem_sample,
            "network": None,
            "disk_io": None,
        }

        # Mock the class-level bytes_to_human
        mock_collector_cls.bytes_to_human = lambda x: f"{x} B"

        subtab._on_tick()

        subtab.mem_graph.add_value.assert_called_once_with(60.0)
        subtab.lbl_mem.setText.assert_called_once()

    @patch("ui.monitor_tab.PerformanceCollector")
    def test_on_tick_network(self, mock_collector_cls):
        """_on_tick should update network graph and labels."""
        subtab = self._make_subtab()
        net_sample = _NetworkSample(recv_rate=1024.0, send_rate=512.0)
        subtab.collector.collect_all.return_value = {
            "cpu": None,
            "memory": None,
            "network": net_sample,
            "disk_io": None,
        }
        mock_collector_cls.bytes_to_human = lambda x: f"{x} B"

        subtab._on_tick()

        subtab.net_graph.add_values.assert_called_once_with(1024.0, 512.0)
        subtab.lbl_net.setText.assert_called_once()

    @patch("ui.monitor_tab.PerformanceCollector")
    def test_on_tick_disk(self, mock_collector_cls):
        """_on_tick should update disk graph and labels."""
        subtab = self._make_subtab()
        disk_sample = _DiskIOSample(read_rate=2048.0, write_rate=1024.0)
        subtab.collector.collect_all.return_value = {
            "cpu": None,
            "memory": None,
            "network": None,
            "disk_io": disk_sample,
        }
        mock_collector_cls.bytes_to_human = lambda x: f"{x} B"

        subtab._on_tick()

        subtab.disk_graph.add_values.assert_called_once_with(2048.0, 1024.0)
        subtab.lbl_disk.setText.assert_called_once()

    @patch("ui.monitor_tab.PerformanceCollector")
    def test_on_tick_no_data(self, mock_collector_cls):
        """_on_tick should not crash when all samples are None."""
        subtab = self._make_subtab()
        subtab.collector.collect_all.return_value = {
            "cpu": None,
            "memory": None,
            "network": None,
            "disk_io": None,
        }

        subtab._on_tick()  # should not raise

        subtab.cpu_graph.add_value.assert_not_called()
        subtab.mem_graph.add_value.assert_not_called()
        subtab.net_graph.add_values.assert_not_called()
        subtab.disk_graph.add_values.assert_not_called()

    @patch("ui.monitor_tab.PerformanceCollector")
    def test_on_tick_cpu_updates_core_bars(self, mock_collector_cls):
        """_on_tick should update individual core bar values."""
        subtab = self._make_subtab()
        # Pre-populate with mock bars so set_value is trackable
        mock_bars = [MagicMock() for _ in range(4)]
        subtab.cpu_core_bars = mock_bars
        cpu_sample = _CpuSample(percent=55.0, per_core=[30.0, 60.0, 80.0, 90.0])
        subtab.collector.collect_all.return_value = {
            "cpu": cpu_sample,
            "memory": None,
            "network": None,
            "disk_io": None,
        }

        subtab._on_tick()

        for i, bar in enumerate(mock_bars):
            bar.set_value.assert_called_once_with(cpu_sample.per_core[i])


# ===================================================================
# Tests for _ProcessesSubTab
# ===================================================================


class TestProcessesSubTabGetUsername(unittest.TestCase):
    """Tests for _ProcessesSubTab._get_current_username()."""

    @patch("ui.monitor_tab.os.getlogin", return_value="testuser")
    def test_get_current_username_success(self, mock_login):
        """Should return os.getlogin() value on success."""
        mod = _get_module()
        result = mod._ProcessesSubTab._get_current_username()
        self.assertEqual(result, "testuser")

    @patch("ui.monitor_tab.os.getlogin", side_effect=OSError("No tty"))
    @patch("ui.monitor_tab.os.getuid", return_value=1000)
    def test_get_current_username_fallback(self, mock_uid, mock_login):
        """Should fall back to pwd.getpwuid when getlogin raises OSError."""
        mod = _get_module()
        with patch.dict("sys.modules", {"pwd": MagicMock()}):
            import pwd

            pwd.getpwuid.return_value = MagicMock(pw_name="fallbackuser")
            result = mod._ProcessesSubTab._get_current_username()
            self.assertEqual(result, "fallbackuser")


class TestProcessesSubTab(unittest.TestCase):
    """Tests for _ProcessesSubTab process list, sorting, filtering, and actions."""

    def _make_subtab(self):
        """Create a _ProcessesSubTab with mocked widgets."""
        mod = _get_module()
        subtab = mod._ProcessesSubTab.__new__(mod._ProcessesSubTab)
        subtab._show_all = True
        subtab._current_sort = "cpu"
        subtab._current_user = "testuser"
        subtab.refresh_timer = MagicMock()

        # Mock UI widgets
        subtab.lbl_summary = MagicMock()
        subtab.sort_combo = MagicMock()
        subtab.btn_toggle_filter = MagicMock()
        subtab.process_tree = MagicMock()
        subtab.process_tree.verticalScrollBar.return_value = MagicMock(
            value=MagicMock(return_value=0)
        )
        subtab.process_tree.currentItem.return_value = None
        subtab.process_tree.columnCount.return_value = 8

        # tr() passthrough
        subtab.tr = lambda s: s
        return subtab

    def _make_processes(self):
        """Create a list of test ProcessInfo objects."""
        return [
            _ProcessInfo(
                pid=100,
                name="firefox",
                user="testuser",
                cpu_percent=25.0,
                memory_percent=5.0,
                memory_bytes=500_000_000,
                state="S",
                nice=0,
            ),
            _ProcessInfo(
                pid=200,
                name="chrome",
                user="testuser",
                cpu_percent=60.0,
                memory_percent=10.0,
                memory_bytes=1_000_000_000,
                state="R",
                nice=0,
            ),
            _ProcessInfo(
                pid=300,
                name="systemd",
                user="root",
                cpu_percent=1.0,
                memory_percent=0.5,
                memory_bytes=50_000_000,
                state="S",
                nice=-20,
            ),
            _ProcessInfo(
                pid=400,
                name="zombie_proc",
                user="testuser",
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_bytes=0,
                state="Z",
                nice=0,
            ),
        ]

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_updates_summary(self, mock_pm):
        """refresh_processes should update the summary label."""
        subtab = self._make_subtab()
        mock_pm.get_process_count.return_value = {
            "total": 150,
            "running": 5,
            "sleeping": 140,
            "zombie": 1,
        }
        mock_pm.get_all_processes.return_value = []
        mock_pm.bytes_to_human = lambda x: f"{x} B"

        subtab.refresh_processes()

        subtab.lbl_summary.setText.assert_called_once()
        text = subtab.lbl_summary.setText.call_args[0][0]
        self.assertIn("150", text)
        self.assertIn("5", text)
        self.assertIn("140", text)
        self.assertIn("1", text)

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_sort_by_cpu(self, mock_pm):
        """Processes should be sorted by CPU descending when sort=cpu."""
        subtab = self._make_subtab()
        subtab._current_sort = "cpu"
        procs = self._make_processes()
        mock_pm.get_process_count.return_value = {
            "total": 4,
            "running": 1,
            "sleeping": 2,
            "zombie": 1,
        }
        mock_pm.get_all_processes.return_value = procs
        mock_pm.bytes_to_human = lambda x: f"{x} B"

        subtab.refresh_processes()

        # Verify addTopLevelItem was called 4 times
        self.assertEqual(subtab.process_tree.addTopLevelItem.call_count, 4)

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_sort_by_memory(self, mock_pm):
        """Processes should be sorted by memory descending when sort=memory."""
        subtab = self._make_subtab()
        subtab._current_sort = "memory"
        procs = self._make_processes()
        mock_pm.get_process_count.return_value = {
            "total": 4,
            "running": 1,
            "sleeping": 2,
            "zombie": 1,
        }
        mock_pm.get_all_processes.return_value = procs
        mock_pm.bytes_to_human = lambda x: f"{x} B"

        subtab.refresh_processes()

        self.assertEqual(subtab.process_tree.addTopLevelItem.call_count, 4)

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_sort_by_name(self, mock_pm):
        """Processes should be sorted by name ascending when sort=name."""
        subtab = self._make_subtab()
        subtab._current_sort = "name"
        procs = self._make_processes()
        mock_pm.get_process_count.return_value = {
            "total": 4,
            "running": 1,
            "sleeping": 2,
            "zombie": 1,
        }
        mock_pm.get_all_processes.return_value = procs
        mock_pm.bytes_to_human = lambda x: f"{x} B"

        subtab.refresh_processes()

        self.assertEqual(subtab.process_tree.addTopLevelItem.call_count, 4)

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_sort_by_pid(self, mock_pm):
        """Processes should be sorted by PID ascending when sort=pid."""
        subtab = self._make_subtab()
        subtab._current_sort = "pid"
        procs = self._make_processes()
        mock_pm.get_process_count.return_value = {
            "total": 4,
            "running": 1,
            "sleeping": 2,
            "zombie": 1,
        }
        mock_pm.get_all_processes.return_value = procs
        mock_pm.bytes_to_human = lambda x: f"{x} B"

        subtab.refresh_processes()

        self.assertEqual(subtab.process_tree.addTopLevelItem.call_count, 4)

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_filter_my_processes(self, mock_pm):
        """When _show_all is False, only current user's processes should show."""
        subtab = self._make_subtab()
        subtab._show_all = False
        subtab._current_user = "testuser"
        procs = self._make_processes()
        mock_pm.get_process_count.return_value = {
            "total": 4,
            "running": 1,
            "sleeping": 2,
            "zombie": 1,
        }
        mock_pm.get_all_processes.return_value = procs
        mock_pm.bytes_to_human = lambda x: f"{x} B"

        subtab.refresh_processes()

        # Should filter out 'root' processes (systemd), leaving 3
        self.assertEqual(subtab.process_tree.addTopLevelItem.call_count, 3)

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_clears_tree(self, mock_pm):
        """refresh_processes should clear the tree before populating."""
        subtab = self._make_subtab()
        mock_pm.get_process_count.return_value = {
            "total": 0,
            "running": 0,
            "sleeping": 0,
            "zombie": 0,
        }
        mock_pm.get_all_processes.return_value = []

        subtab.refresh_processes()

        subtab.process_tree.clear.assert_called_once()

    def test_on_sort_changed_updates_sort(self):
        """_on_sort_changed should update _current_sort from combo data."""
        subtab = self._make_subtab()
        subtab.sort_combo.currentData.return_value = "memory"
        subtab.refresh_processes = MagicMock()

        subtab._on_sort_changed(1)

        self.assertEqual(subtab._current_sort, "memory")
        subtab.refresh_processes.assert_called_once()

    def test_on_filter_toggled_true(self):
        """_on_filter_toggled(True) should set _show_all to False."""
        subtab = self._make_subtab()
        subtab.refresh_processes = MagicMock()

        subtab._on_filter_toggled(True)

        self.assertFalse(subtab._show_all)
        subtab.refresh_processes.assert_called_once()

    def test_on_filter_toggled_false(self):
        """_on_filter_toggled(False) should set _show_all to True."""
        subtab = self._make_subtab()
        subtab.refresh_processes = MagicMock()

        subtab._on_filter_toggled(False)

        self.assertTrue(subtab._show_all)
        subtab.refresh_processes.assert_called_once()

    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_kill_process_sigterm_confirmed_success(self, mock_pm, mock_msgbox):
        """Kill with SIGTERM after confirmation should call ProcessManager.kill_process."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_YES
        mock_pm.kill_process.return_value = (True, "Killed")
        subtab.refresh_processes = MagicMock()

        subtab._kill_process(123, "test_proc", 15)

        mock_pm.kill_process.assert_called_once_with(123, 15)
        mock_msgbox.information.assert_called_once()
        subtab.refresh_processes.assert_called_once()

    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_kill_process_sigkill_confirmed_success(self, mock_pm, mock_msgbox):
        """Kill with SIGKILL after confirmation should use signal 9."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_YES
        mock_pm.kill_process.return_value = (True, "Force killed")
        subtab.refresh_processes = MagicMock()

        subtab._kill_process(456, "bad_proc", 9)

        mock_pm.kill_process.assert_called_once_with(456, 9)

    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_kill_process_declined(self, mock_pm, mock_msgbox):
        """Declining the confirmation dialog should not call kill_process."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_NO

        subtab._kill_process(123, "test_proc", 15)

        mock_pm.kill_process.assert_not_called()

    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_kill_process_confirmed_failure(self, mock_pm, mock_msgbox):
        """Failed kill should show a warning dialog, not information."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_YES
        mock_pm.kill_process.return_value = (False, "Permission denied")
        subtab.refresh_processes = MagicMock()

        subtab._kill_process(123, "root_proc", 15)

        mock_msgbox.warning.assert_called_once()
        mock_msgbox.information.assert_not_called()
        subtab.refresh_processes.assert_not_called()

    @patch("ui.monitor_tab.QInputDialog")
    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_renice_process_confirmed_success(self, mock_pm, mock_msgbox, mock_input):
        """Renice with confirmed dialog and valid input should succeed."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_YES
        mock_input.getInt.return_value = (10, True)
        mock_pm.renice_process.return_value = (True, "Reniced")
        subtab.refresh_processes = MagicMock()

        subtab._renice_process(123, "test_proc")

        mock_pm.renice_process.assert_called_once_with(123, 10)
        mock_msgbox.information.assert_called_once()
        subtab.refresh_processes.assert_called_once()

    @patch("ui.monitor_tab.QInputDialog")
    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_renice_process_confirm_declined(self, mock_pm, mock_msgbox, mock_input):
        """Declining the confirm dialog should not show input dialog."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_NO

        subtab._renice_process(123, "test_proc")

        mock_input.getInt.assert_not_called()
        mock_pm.renice_process.assert_not_called()

    @patch("ui.monitor_tab.QInputDialog")
    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_renice_process_input_cancelled(self, mock_pm, mock_msgbox, mock_input):
        """Cancelling the input dialog should not call renice_process."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_YES
        mock_input.getInt.return_value = (5, False)  # ok=False means cancelled

        subtab._renice_process(123, "test_proc")

        mock_pm.renice_process.assert_not_called()

    @patch("ui.monitor_tab.QInputDialog")
    @patch("ui.monitor_tab.QMessageBox")
    @patch("ui.monitor_tab.ProcessManager")
    def test_renice_process_failure(self, mock_pm, mock_msgbox, mock_input):
        """Failed renice should show a warning, not information."""
        subtab = self._make_subtab()
        mock_msgbox.StandardButton = types.SimpleNamespace(
            Yes=STD_BTN_YES, No=STD_BTN_NO
        )
        mock_msgbox.question.return_value = STD_BTN_YES
        mock_input.getInt.return_value = (-5, True)
        mock_pm.renice_process.return_value = (False, "Permission denied")
        subtab.refresh_processes = MagicMock()

        subtab._renice_process(123, "test_proc")

        mock_pm.renice_process.assert_called_once_with(123, -5)
        mock_msgbox.warning.assert_called_once()
        mock_msgbox.information.assert_not_called()
        subtab.refresh_processes.assert_not_called()

    @patch("ui.monitor_tab.ProcessManager")
    def test_refresh_processes_empty_list(self, mock_pm):
        """refresh_processes with no processes should result in no tree items."""
        subtab = self._make_subtab()
        mock_pm.get_process_count.return_value = {
            "total": 0,
            "running": 0,
            "sleeping": 0,
            "zombie": 0,
        }
        mock_pm.get_all_processes.return_value = []

        subtab.refresh_processes()

        subtab.process_tree.addTopLevelItem.assert_not_called()


# ===================================================================
# Tests for _ProcessesSubTab context menu
# ===================================================================


class TestProcessesSubTabContextMenu(unittest.TestCase):
    """Tests for _show_context_menu."""

    def _make_subtab(self):
        """Create a _ProcessesSubTab with mocked widgets for context menu."""
        mod = _get_module()
        subtab = mod._ProcessesSubTab.__new__(mod._ProcessesSubTab)
        subtab.process_tree = MagicMock()
        subtab.tr = lambda s: s
        return subtab

    def test_show_context_menu_no_item(self):
        """_show_context_menu should return early when no item at position."""
        subtab = self._make_subtab()
        subtab.process_tree.itemAt.return_value = None
        mock_position = MagicMock()

        # Should not raise
        subtab._show_context_menu(mock_position)

    def test_show_context_menu_no_pid(self):
        """_show_context_menu should return early when item has no PID data."""
        subtab = self._make_subtab()
        mock_item = MagicMock()
        mock_item.data.return_value = None
        subtab.process_tree.itemAt.return_value = mock_item
        mock_position = MagicMock()

        # Should not raise
        subtab._show_context_menu(mock_position)


# ===================================================================
# Tests for colour constants
# ===================================================================


class TestProcessesSubTabConstants(unittest.TestCase):
    """Tests for Catppuccin Mocha colour constants on _ProcessesSubTab."""

    def test_colour_constants_exist(self):
        """All expected colour constants should be defined."""
        mod = _get_module()
        cls = mod._ProcessesSubTab
        expected = [
            "COLOR_BASE",
            "COLOR_SURFACE0",
            "COLOR_SURFACE1",
            "COLOR_SUBTEXT0",
            "COLOR_TEXT",
            "COLOR_BLUE",
            "COLOR_GREEN",
            "COLOR_RED",
            "COLOR_YELLOW",
            "COLOR_MAUVE",
            "COLOR_PEACH",
        ]
        for name in expected:
            self.assertTrue(
                hasattr(cls, name),
                f"Missing colour constant: {name}",
            )

    def test_colour_constants_are_hex(self):
        """All colour constants should be valid hex colour strings."""
        mod = _get_module()
        cls = mod._ProcessesSubTab
        for name in dir(cls):
            if name.startswith("COLOR_"):
                value = getattr(cls, name)
                self.assertIsInstance(value, str)
                self.assertTrue(
                    value.startswith("#") and len(value) == 7,
                    f"{name} = {value!r} is not a valid hex colour",
                )


if __name__ == "__main__":
    unittest.main()
