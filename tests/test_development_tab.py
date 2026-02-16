"""Tests for ui/development_tab.py — DevelopmentTab, InstallWorker.

Comprehensive behavioural tests covering container management, developer tool
installations, VS Code extension profiles, and background worker dispatch.
All external managers are mocked so no root privileges are required.
Lightweight PyQt6 stubs are used instead of a real QApplication so tests run
headless.
"""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


# ---------------------------------------------------------------------------
# Lightweight PyQt6 stubs (no display server required)
# ---------------------------------------------------------------------------


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


class _Dummy:
    """Universal stub that absorbs any constructor / attribute access."""

    class Shape:
        NoFrame = 0

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

    def start(self):
        """QThread.start() stub — does nothing."""
        pass


class _DummyLabel:
    """Minimal QLabel stand-in with text tracking."""

    def __init__(self, text="", *a, **kw):
        self._text = text

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyLineEdit:
    """Minimal QLineEdit stand-in."""

    def __init__(self, *a, **kw):
        self._text = ""
        self.returnPressed = _DummySignal()

    def text(self):
        return self._text

    def setText(self, t):
        self._text = t

    def clear(self):
        self._text = ""

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyComboBox:
    """Minimal QComboBox stand-in."""

    def __init__(self, *a, **kw):
        self._items = []
        self._current = 0
        self.currentIndexChanged = _DummySignal()
        self.currentTextChanged = _DummySignal()

    def addItem(self, text, data=None):
        self._items.append((text, data))

    def addItems(self, items):
        for i in items:
            self._items.append((i, None))

    def currentText(self):
        return self._items[self._current][0] if self._items else ""

    def currentData(self):
        if self._items and 0 <= self._current < len(self._items):
            return self._items[self._current][1]
        return None

    def currentIndex(self):
        return self._current

    def setCurrentIndex(self, i):
        self._current = i

    def clear(self):
        self._items.clear()
        self._current = 0

    def count(self):
        return len(self._items)

    def blockSignals(self, b):
        pass

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyButton(_Dummy):
    """Minimal QPushButton stand-in."""

    def __init__(self, text="", *a, **kw):
        self.clicked = _DummySignal()
        self._enabled = True
        self._text = text

    def setEnabled(self, f):
        self._enabled = f

    def isEnabled(self):
        return self._enabled

    def setText(self, t):
        self._text = t

    def text(self):
        return self._text


class _DummyTextEdit:
    """Minimal QTextEdit stand-in."""

    def __init__(self, *a, **kw):
        self._text = ""

    def setText(self, t):
        self._text = t

    def setPlainText(self, t):
        self._text = t

    def append(self, t):
        self._text += "\n" + t if self._text else t

    def toPlainText(self):
        return self._text

    def clear(self):
        self._text = ""

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyListWidget:
    """Minimal QListWidget stand-in."""

    def __init__(self, *a, **kw):
        self._items = []
        self._current = -1
        self.customContextMenuRequested = _DummySignal()
        self.itemDoubleClicked = _DummySignal()

    def addItem(self, item):
        self._items.append(item)

    def clear(self):
        self._items.clear()
        self._current = -1

    def count(self):
        return len(self._items)

    def currentItem(self):
        if 0 <= self._current < len(self._items):
            return self._items[self._current]
        return None

    def currentRow(self):
        return self._current

    def setCurrentRow(self, r):
        self._current = r

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyListWidgetItem:
    """Minimal QListWidgetItem stand-in."""

    def __init__(self, text="", *a, **kw):
        self._text = text
        self._data = {}
        self._flags = 0xFFFF  # all flags set

    def text(self):
        return self._text

    def setData(self, role, value):
        self._data[role] = value

    def data(self, role):
        return self._data.get(role)

    def flags(self):
        return self._flags

    def setFlags(self, flags):
        self._flags = flags


class _DummyProgressBar:
    """Minimal QProgressBar stand-in."""

    def __init__(self, *a, **kw):
        self._visible = True
        self._min = 0
        self._max = 100
        self._value = 0

    def setVisible(self, v):
        self._visible = v

    def isVisible(self):
        return self._visible

    def setRange(self, lo, hi):
        self._min = lo
        self._max = hi

    def setValue(self, v):
        self._value = v

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyAction:
    """Minimal QAction stand-in with triggered signal."""

    def __init__(self, *a, **kw):
        self.triggered = _DummySignal()

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyMenu:
    """Minimal QMenu stand-in."""

    def __init__(self, *a, **kw):
        self._actions = []

    def addAction(self, action):
        self._actions.append(action)

    def addSeparator(self):
        pass

    def exec(self, *a, **kw):
        pass

    def __getattr__(self, n):
        return lambda *a, **kw: None


# ---------------------------------------------------------------------------
# Stub installation
# ---------------------------------------------------------------------------


# Build ContainerStatus enum for stubs
class _StubContainerStatus:
    RUNNING = "running"
    STOPPED = "stopped"
    CREATED = "created"
    UNKNOWN = "unknown"


class _StubContainer:
    """Stub for Container dataclass."""

    def __init__(self, name, status, image, id=""):
        self.name = name
        self.status = status
        self.image = image
        self.id = id


class _StubResult:
    """Stub for Result dataclass."""

    def __init__(self, success, message, data=None):
        self.success = success
        self.message = message
        self.data = data


def _install_stubs():
    """Register lightweight PyQt6 stubs for ui.development_tab import."""

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
    qt_widgets.QComboBox = _DummyComboBox
    qt_widgets.QLineEdit = _DummyLineEdit
    qt_widgets.QListWidget = _DummyListWidget
    qt_widgets.QListWidgetItem = _DummyListWidgetItem
    qt_widgets.QMenu = _DummyMenu
    qt_widgets.QMessageBox = MagicMock()
    qt_widgets.QProgressBar = _DummyProgressBar

    # -- PyQt6.QtCore --
    qt_core = types.ModuleType("PyQt6.QtCore")
    qt_core.Qt = types.SimpleNamespace(
        ContextMenuPolicy=types.SimpleNamespace(CustomContextMenu=3),
        ItemDataRole=types.SimpleNamespace(UserRole=0x0100),
        ItemFlag=types.SimpleNamespace(ItemIsSelectable=1),
    )
    qt_core.QThread = _Dummy
    qt_core.pyqtSignal = _DummySignal
    qt_core.QProcess = MagicMock()

    # -- PyQt6.QtGui --
    qt_gui = types.ModuleType("PyQt6.QtGui")
    qt_gui.QIcon = _Dummy
    qt_gui.QAction = _DummyAction
    qt_gui.QColor = _Dummy

    # -- PyQt6 package --
    pyqt = types.ModuleType("PyQt6")
    pyqt.QtWidgets = qt_widgets
    pyqt.QtCore = qt_core
    pyqt.QtGui = qt_gui

    # -- ui.base_tab --
    base_tab_module = types.ModuleType("ui.base_tab")

    class _BaseTab(_Dummy):
        def __init__(self, *a, **kw):
            self._output_lines = []
            self.output_area = _DummyTextEdit()
            self.runner = MagicMock()
            self.runner.output_received = _DummySignal()
            self.runner.finished = _DummySignal()
            self.runner.error_occurred = _DummySignal()
            self.runner.progress_update = _DummySignal()

        def tr(self, text):
            return text

        def run_command(self, cmd, args, description=""):
            pass

        def append_output(self, text):
            self._output_lines.append(text)

        def add_output_section(self, layout):
            pass

    base_tab_module.BaseTab = _BaseTab

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

    # -- utils.containers --
    containers_module = types.ModuleType("utils.containers")
    containers_module.ContainerManager = MagicMock()
    containers_module.ContainerStatus = _StubContainerStatus

    # -- utils.devtools --
    devtools_module = types.ModuleType("utils.devtools")
    devtools_module.DevToolsManager = MagicMock()

    # -- utils.vscode --
    vscode_module = types.ModuleType("utils.vscode")
    vscode_module.VSCodeManager = MagicMock()

    # -- utils.command_runner --
    command_runner_module = types.ModuleType("utils.command_runner")
    _runner_mock = MagicMock()
    _runner_mock.return_value.finished = _DummySignal()
    _runner_mock.return_value.output_received = _DummySignal()
    command_runner_module.CommandRunner = _runner_mock

    # -- utils.log --
    log_module = types.ModuleType("utils.log")
    log_module.get_logger = lambda name: MagicMock()

    # Register everything
    sys.modules["PyQt6"] = pyqt
    sys.modules["PyQt6.QtWidgets"] = qt_widgets
    sys.modules["PyQt6.QtCore"] = qt_core
    sys.modules["PyQt6.QtGui"] = qt_gui
    sys.modules["ui.base_tab"] = base_tab_module
    sys.modules["ui.tab_utils"] = tab_utils_module
    sys.modules["core.plugins.interface"] = interface_module
    sys.modules["core.plugins.metadata"] = metadata_module
    sys.modules["utils.containers"] = containers_module
    sys.modules["utils.devtools"] = devtools_module
    sys.modules["utils.vscode"] = vscode_module
    sys.modules["utils.command_runner"] = command_runner_module
    sys.modules["utils.log"] = log_module


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
    "core.plugins.interface",
    "core.plugins.metadata",
    "utils.containers",
    "utils.devtools",
    "utils.vscode",
    "utils.command_runner",
    "utils.log",
    "ui.development_tab",
]

_module_backup = {}


def setUpModule():
    """Install stubs and import ui.development_tab."""
    global _module_backup
    for key in _MODULE_KEYS:
        _module_backup[key] = sys.modules.get(key)
    _install_stubs()
    sys.modules.pop("ui.development_tab", None)
    sys.modules.pop("ui", None)
    importlib.import_module("ui.development_tab")


def tearDownModule():
    """Restore original modules."""
    sys.modules.pop("ui.development_tab", None)
    for key, orig in _module_backup.items():
        if orig is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = orig


def _get_module():
    """Return the imported ui.development_tab module."""
    return sys.modules["ui.development_tab"]


def _reset_mocks():
    """Reset shared mocks to avoid cross-test contamination."""
    cm = sys.modules["utils.containers"].ContainerManager
    cm.reset_mock()
    dtm = sys.modules["utils.devtools"].DevToolsManager
    dtm.reset_mock()
    vsm = sys.modules["utils.vscode"].VSCodeManager
    vsm.reset_mock()
    qt_widgets = sys.modules["PyQt6.QtWidgets"]
    qt_widgets.QMessageBox.reset_mock()


def _make_tab(distrobox_available=True, containers=None, vscode_available=True):
    """Create a DevelopmentTab with mocked managers.

    Args:
        distrobox_available: Whether distrobox is detected as installed.
        containers: List of container stubs to return from list_containers.
        vscode_available: Whether VS Code is detected as installed.

    Returns:
        Configured DevelopmentTab instance.
    """
    _reset_mocks()

    mod = _get_module()
    cm = sys.modules["utils.containers"].ContainerManager
    cm.is_available.return_value = distrobox_available
    cm.list_containers.return_value = containers or []
    cm.get_available_images.return_value = {
        "fedora": "registry.fedoraproject.org/fedora-toolbox:latest",
        "ubuntu": "docker.io/library/ubuntu:22.04",
    }

    dtm = sys.modules["utils.devtools"].DevToolsManager
    dtm.get_all_status.return_value = {
        "pyenv": (False, "Not installed"),
        "nvm": (False, "Not installed"),
        "rustup": (False, "Not installed"),
    }

    vsm = sys.modules["utils.vscode"].VSCodeManager
    vsm.is_available.return_value = vscode_available
    vsm.get_available_profiles.return_value = [
        {"name": "Python", "key": "python", "extension_count": 5},
        {"name": "Web", "key": "web", "extension_count": 8},
    ]

    tab = mod.DevelopmentTab()
    return tab


# ---------------------------------------------------------------------------
# Tests — InstallWorker
# ---------------------------------------------------------------------------


class TestInstallWorker(unittest.TestCase):
    """Tests for the InstallWorker QThread class."""

    def _make_worker(self, tool, extra_args=None):
        mod = _get_module()
        w = mod.InstallWorker.__new__(mod.InstallWorker)
        w.tool = tool
        w.extra_args = extra_args or {}
        w.finished = _DummySignal()
        return w

    @patch("utils.devtools.DevToolsManager.install_pyenv")
    def test_run_pyenv_success(self, mock_install):
        """InstallWorker dispatches pyenv installation and emits finished."""
        mock_install.return_value = _StubResult(True, "pyenv installed")
        w = self._make_worker("pyenv", {"python_version": "3.11"})
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        mock_install.assert_called_once_with("3.11")
        self.assertEqual(results, [("pyenv", True, "pyenv installed")])

    @patch("utils.devtools.DevToolsManager.install_pyenv")
    def test_run_pyenv_default_version(self, mock_install):
        """Pyenv defaults to python 3.12 when no version specified."""
        mock_install.return_value = _StubResult(True, "ok")
        w = self._make_worker("pyenv")
        w.run()
        mock_install.assert_called_once_with("3.12")

    @patch("utils.devtools.DevToolsManager.install_nvm")
    def test_run_nvm_success(self, mock_install):
        """InstallWorker dispatches nvm installation."""
        mock_install.return_value = _StubResult(True, "nvm installed")
        w = self._make_worker("nvm", {"node_version": "18"})
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        mock_install.assert_called_once_with("18")
        self.assertEqual(results[0][1], True)

    @patch("utils.devtools.DevToolsManager.install_nvm")
    def test_run_nvm_default_version(self, mock_install):
        """NVM defaults to 'lts' when no version specified."""
        mock_install.return_value = _StubResult(True, "ok")
        w = self._make_worker("nvm")
        w.run()
        mock_install.assert_called_once_with("lts")

    @patch("utils.devtools.DevToolsManager.install_rustup")
    def test_run_rustup_success(self, mock_install):
        """InstallWorker dispatches rustup installation."""
        mock_install.return_value = _StubResult(True, "rustup installed")
        w = self._make_worker("rustup")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        mock_install.assert_called_once()
        self.assertTrue(results[0][1])

    @patch("utils.vscode.VSCodeManager.install_profile")
    def test_run_vscode_profile(self, mock_install):
        """InstallWorker dispatches VS Code profile installation."""
        mock_install.return_value = _StubResult(True, "profile installed")
        w = self._make_worker("vscode_python")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        mock_install.assert_called_once_with("python")
        self.assertEqual(results[0][0], "vscode_python")

    @patch("utils.vscode.VSCodeManager.install_profile")
    def test_run_vscode_web_profile(self, mock_install):
        """InstallWorker dispatches VS Code web profile correctly."""
        mock_install.return_value = _StubResult(True, "web installed")
        w = self._make_worker("vscode_web")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        mock_install.assert_called_once_with("web")
        self.assertEqual(results[0][0], "vscode_web")
        self.assertTrue(results[0][1])

    def test_run_unknown_tool(self):
        """Unknown tool results in failure emission."""
        w = self._make_worker("unknown_tool")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        self.assertFalse(results[0][1])
        self.assertIn("Unknown tool", results[0][2])

    @patch("utils.devtools.DevToolsManager.install_pyenv")
    def test_run_exception_handling(self, mock_install):
        """InstallWorker handles exceptions gracefully."""
        mock_install.side_effect = RuntimeError("network error")
        w = self._make_worker("pyenv")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        self.assertFalse(results[0][1])
        self.assertIn("network error", results[0][2])

    @patch("utils.devtools.DevToolsManager.install_pyenv")
    def test_run_pyenv_failure_result(self, mock_install):
        """InstallWorker emits failure when tool returns success=False."""
        mock_install.return_value = _StubResult(False, "deps missing")
        w = self._make_worker("pyenv")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        self.assertFalse(results[0][1])
        self.assertEqual(results[0][2], "deps missing")

    @patch("utils.devtools.DevToolsManager.install_nvm")
    def test_run_nvm_exception(self, mock_install):
        """NVM install exception is caught and emitted."""
        mock_install.side_effect = OSError("permission denied")
        w = self._make_worker("nvm")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        self.assertFalse(results[0][1])
        self.assertIn("permission denied", results[0][2])

    @patch("utils.devtools.DevToolsManager.install_rustup")
    def test_run_rustup_exception(self, mock_install):
        """Rustup install exception is caught and emitted."""
        mock_install.side_effect = Exception("curl failed")
        w = self._make_worker("rustup")
        results = []
        w.finished.connect(lambda t, s, m: results.append((t, s, m)))
        w.run()
        self.assertFalse(results[0][1])
        self.assertIn("curl failed", results[0][2])


# ---------------------------------------------------------------------------
# Tests — DevelopmentTab construction and metadata
# ---------------------------------------------------------------------------


class TestDevelopmentTabInit(unittest.TestCase):
    """Tests for DevelopmentTab initialization and metadata."""

    def test_metadata_id(self):
        """Tab metadata has correct id."""
        tab = _make_tab()
        meta = tab.metadata()
        self.assertEqual(meta.id, "development")

    def test_metadata_name(self):
        """Tab metadata has correct name."""
        tab = _make_tab()
        meta = tab.metadata()
        self.assertEqual(meta.name, "Development")

    def test_metadata_category(self):
        """Tab metadata category is Developer."""
        tab = _make_tab()
        self.assertEqual(tab._METADATA.category, "Developer")

    def test_metadata_description(self):
        """Tab metadata has a description."""
        tab = _make_tab()
        self.assertIn("Container", tab._METADATA.description)

    def test_metadata_order(self):
        """Tab metadata order is set."""
        tab = _make_tab()
        self.assertEqual(tab._METADATA.order, 10)

    def test_create_widget_returns_self(self):
        """create_widget() returns the tab itself."""
        tab = _make_tab()
        self.assertIs(tab.create_widget(), tab)

    def test_workers_list_initialized(self):
        """Workers list is initialized as empty."""
        tab = _make_tab()
        self.assertIsInstance(tab.workers, list)

    def test_container_list_initialized_when_distrobox_available(self):
        """container_list is set when distrobox is available."""
        tab = _make_tab(distrobox_available=True)
        self.assertIsNotNone(tab.container_list)

    def test_container_list_none_when_distrobox_unavailable(self):
        """container_list stays None when distrobox is not available."""
        tab = _make_tab(distrobox_available=False)
        self.assertIsNone(tab.container_list)

    def test_init_calls_refresh_dev_status(self):
        """__init__ calls refresh_dev_status (get_all_status is called)."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.assert_called()

    def test_init_refreshes_containers_when_available(self):
        """__init__ calls refresh_containers when distrobox is available."""
        containers = [
            _StubContainer("test", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=containers)
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.assert_called()

    def test_init_skips_refresh_when_distrobox_unavailable(self):
        """__init__ does not call list_containers when distrobox unavailable."""
        tab = _make_tab(distrobox_available=False)
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — Container tab creation
# ---------------------------------------------------------------------------


class TestContainersTab(unittest.TestCase):
    """Tests for container tab UI creation."""

    def test_container_list_section_created(self):
        """Container list section is created when distrobox available."""
        tab = _make_tab(distrobox_available=True)
        self.assertIsNotNone(tab.container_list)

    def test_name_input_created(self):
        """Name input field is created when distrobox available."""
        tab = _make_tab(distrobox_available=True)
        self.assertIsInstance(tab.name_input, _DummyLineEdit)

    def test_image_combo_created(self):
        """Image combo is created with available images."""
        tab = _make_tab(distrobox_available=True)
        self.assertIsInstance(tab.image_combo, _DummyComboBox)
        self.assertGreater(tab.image_combo.count(), 0)

    def test_image_combo_items_capitalized(self):
        """Image combo items are capitalized."""
        tab = _make_tab(distrobox_available=True)
        if tab.image_combo.count() > 0:
            text = tab.image_combo._items[0][0]
            self.assertTrue(text[0].isupper())

    def test_container_status_label_created(self):
        """Container status label is created."""
        tab = _make_tab(distrobox_available=True)
        self.assertIsNotNone(tab.container_status_label)

    def test_install_section_when_no_distrobox(self):
        """Install section is shown when distrobox is not available."""
        tab = _make_tab(distrobox_available=False)
        self.assertIsNone(tab.container_list)

    def test_image_combo_data_stores_key(self):
        """Image combo stores lowercase key as data."""
        tab = _make_tab(distrobox_available=True)
        if tab.image_combo.count() > 0:
            data = tab.image_combo._items[0][1]
            self.assertIn(data, ["fedora", "ubuntu"])


# ---------------------------------------------------------------------------
# Tests — refresh_containers
# ---------------------------------------------------------------------------


class TestRefreshContainers(unittest.TestCase):
    """Tests for refresh_containers method."""

    def test_refresh_no_containers(self):
        """Empty container list shows 'no containers' message."""
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = []

        tab.refresh_containers()

        self.assertEqual(tab.container_status_label.text(), "0 containers")

    def test_refresh_with_running_container(self):
        """Running container is listed with Running status."""
        containers = [
            _StubContainer(
                "dev-box", _StubContainerStatus.RUNNING, "registry/fedora:latest"
            ),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers

        tab.refresh_containers()

        self.assertEqual(tab.container_list.count(), 1)
        item = tab.container_list._items[0]
        self.assertIsInstance(item, _DummyListWidgetItem)
        self.assertIn("Running", item.text())
        self.assertIn("dev-box", item.text())

    def test_refresh_with_stopped_container(self):
        """Stopped container is listed with Stopped status."""
        containers = [
            _StubContainer("old-box", _StubContainerStatus.STOPPED, "ubuntu:22.04"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers

        tab.refresh_containers()

        item = tab.container_list._items[0]
        self.assertIn("Stopped", item.text())

    def test_refresh_with_unknown_status(self):
        """Unknown status container shows Unknown."""
        containers = [
            _StubContainer("weird", _StubContainerStatus.UNKNOWN, "alpine:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers

        tab.refresh_containers()

        item = tab.container_list._items[0]
        self.assertIn("Unknown", item.text())

    def test_refresh_multiple_containers(self):
        """Multiple containers are all listed."""
        containers = [
            _StubContainer("c1", _StubContainerStatus.RUNNING, "fedora:latest"),
            _StubContainer("c2", _StubContainerStatus.STOPPED, "ubuntu:22.04"),
            _StubContainer("c3", _StubContainerStatus.RUNNING, "arch:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers

        tab.refresh_containers()

        self.assertEqual(tab.container_list.count(), 3)
        self.assertIn("3 containers", tab.container_status_label.text())

    def test_refresh_clears_old_items(self):
        """Refresh clears the list before repopulating."""
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager

        cm.list_containers.return_value = [
            _StubContainer("a", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab.refresh_containers()
        self.assertEqual(tab.container_list.count(), 1)

        cm.list_containers.return_value = [
            _StubContainer("b", _StubContainerStatus.RUNNING, "fedora:latest"),
            _StubContainer("c", _StubContainerStatus.STOPPED, "ubuntu:22.04"),
        ]
        tab.refresh_containers()
        self.assertEqual(tab.container_list.count(), 2)

    def test_refresh_noop_when_container_list_none(self):
        """refresh_containers returns early when container_list is None."""
        tab = _make_tab(distrobox_available=False)
        self.assertIsNone(tab.container_list)
        # Should not raise
        tab.refresh_containers()

    def test_refresh_container_image_shortname(self):
        """Container display shows only last part of image path."""
        containers = [
            _StubContainer(
                "dev",
                _StubContainerStatus.RUNNING,
                "registry.fedoraproject.org/fedora-toolbox:latest",
            ),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers

        tab.refresh_containers()

        item = tab.container_list._items[0]
        self.assertIn("fedora-toolbox:latest", item.text())

    def test_refresh_sets_user_role_data(self):
        """Each item has container name stored in UserRole."""
        containers = [
            _StubContainer("mybox", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        qt_core = sys.modules["PyQt6.QtCore"]

        tab.refresh_containers()

        item = tab.container_list._items[0]
        self.assertEqual(item.data(qt_core.Qt.ItemDataRole.UserRole), "mybox")


# ---------------------------------------------------------------------------
# Tests — _get_selected_container
# ---------------------------------------------------------------------------


class TestGetSelectedContainer(unittest.TestCase):
    """Tests for _get_selected_container."""

    def test_no_selection_returns_none(self):
        """Returns None when nothing is selected."""
        tab = _make_tab(distrobox_available=True)
        result = tab._get_selected_container()
        self.assertIsNone(result)

    def test_selected_item_returns_name(self):
        """Returns container name from selected item."""
        containers = [
            _StubContainer("mybox", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()

        tab.container_list.setCurrentRow(0)
        result = tab._get_selected_container()
        self.assertEqual(result, "mybox")

    def test_selected_item_no_data_returns_none(self):
        """Returns None if item has no UserRole data."""
        tab = _make_tab(distrobox_available=True)
        item = _DummyListWidgetItem("No containers found")
        tab.container_list.addItem(item)
        tab.container_list.setCurrentRow(0)
        result = tab._get_selected_container()
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Tests — Container actions
# ---------------------------------------------------------------------------


class TestEnterContainer(unittest.TestCase):
    """Tests for _enter_container."""

    def test_enter_no_selection(self):
        """Outputs message when no container selected."""
        tab = _make_tab(distrobox_available=True)
        tab._enter_container()
        output = "".join(tab._output_lines)
        self.assertIn("No container selected", output)

    @patch("ui.development_tab.shutil.which", return_value=None)
    def test_enter_no_terminal_fallback(self, mock_which):
        """Falls back to showing command when no terminal emulator found."""
        containers = [
            _StubContainer("dev", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        cm.get_enter_command.return_value = "distrobox enter dev"
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        tab._enter_container()
        output = "".join(tab._output_lines)
        self.assertIn("No terminal emulator found", output)
        self.assertIn("distrobox enter dev", output)


class TestOpenTerminal(unittest.TestCase):
    """Tests for _open_terminal."""

    @patch("ui.development_tab.shutil.which", return_value="/usr/bin/gnome-terminal")
    def test_open_terminal_gnome(self, mock_which):
        """Opens gnome-terminal when available."""
        tab = _make_tab(distrobox_available=True)
        cm = sys.modules["utils.containers"].ContainerManager
        cm.get_enter_command.return_value = "distrobox enter dev"

        qt_core = sys.modules["PyQt6.QtCore"]
        qt_core.QProcess = MagicMock()

        tab._open_terminal("dev")
        output = "".join(tab._output_lines)
        self.assertIn("Opened terminal", output)
        self.assertIn("dev", output)

    @patch("ui.development_tab.shutil.which", return_value=None)
    def test_open_terminal_no_emulator(self, mock_which):
        """Shows fallback command when no terminal found."""
        tab = _make_tab(distrobox_available=True)
        cm = sys.modules["utils.containers"].ContainerManager
        cm.get_enter_command.return_value = "distrobox enter test-box"

        tab._open_terminal("test-box")
        output = "".join(tab._output_lines)
        self.assertIn("No terminal emulator found", output)
        self.assertIn("distrobox enter test-box", output)

    @patch("ui.development_tab.shutil.which", return_value="/usr/bin/gnome-terminal")
    def test_open_terminal_includes_container_name(self, mock_which):
        """Success message includes container name."""
        tab = _make_tab(distrobox_available=True)
        cm = sys.modules["utils.containers"].ContainerManager
        cm.get_enter_command.return_value = "distrobox enter mybox"

        qt_core = sys.modules["PyQt6.QtCore"]
        qt_core.QProcess = MagicMock()

        tab._open_terminal("mybox")
        output = "".join(tab._output_lines)
        self.assertIn("mybox", output)


class TestStopContainer(unittest.TestCase):
    """Tests for _stop_container."""

    def test_stop_no_selection(self):
        """Outputs message when no container selected."""
        tab = _make_tab(distrobox_available=True)
        tab._stop_container()
        output = "".join(tab._output_lines)
        self.assertIn("No container selected", output)

    def test_stop_success(self):
        """Successful stop outputs message and refreshes."""
        containers = [
            _StubContainer("dev", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        cm.stop_container.return_value = _StubResult(True, "Container 'dev' stopped.")
        cm.list_containers.return_value = []

        tab._stop_container()
        output = "".join(tab._output_lines)
        self.assertIn("stopped", output)

    def test_stop_failure(self):
        """Failed stop outputs error message."""
        containers = [
            _StubContainer("dev", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        cm.stop_container.return_value = _StubResult(False, "Failed to stop")

        tab._stop_container()
        output = "".join(tab._output_lines)
        self.assertIn("Failed to stop", output)

    def test_stop_success_triggers_refresh(self):
        """Successful stop calls refresh_containers."""
        containers = [
            _StubContainer("dev", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        cm.stop_container.return_value = _StubResult(True, "Stopped.")
        cm.list_containers.reset_mock()
        cm.list_containers.return_value = []

        tab._stop_container()
        cm.list_containers.assert_called()

    def test_stop_failure_does_not_refresh(self):
        """Failed stop does not refresh the list."""
        containers = [
            _StubContainer("dev", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        cm.stop_container.return_value = _StubResult(False, "Cannot stop")
        cm.list_containers.reset_mock()

        tab._stop_container()
        cm.list_containers.assert_not_called()


class TestDeleteContainer(unittest.TestCase):
    """Tests for _delete_container."""

    def test_delete_no_selection(self):
        """Outputs message when no container selected."""
        tab = _make_tab(distrobox_available=True)
        tab._delete_container()
        output = "".join(tab._output_lines)
        self.assertIn("No container selected", output)

    def test_delete_confirmed(self):
        """Confirmed delete calls ContainerManager.delete_container with force."""
        containers = [
            _StubContainer("old", _StubContainerStatus.STOPPED, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.question.return_value = (
            qt_widgets.QMessageBox.StandardButton.Yes
        )
        cm.delete_container.return_value = _StubResult(True, "Container 'old' deleted.")
        cm.list_containers.return_value = []

        tab._delete_container()
        cm.delete_container.assert_called_with("old", force=True)
        output = "".join(tab._output_lines)
        self.assertIn("deleted", output)

    def test_delete_cancelled(self):
        """Cancelled delete does not call delete_container."""
        containers = [
            _StubContainer("keep", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.question.return_value = (
            qt_widgets.QMessageBox.StandardButton.No
        )

        tab._delete_container()
        cm.delete_container.assert_not_called()

    def test_delete_failure(self):
        """Failed delete outputs error message."""
        containers = [
            _StubContainer("old", _StubContainerStatus.STOPPED, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.question.return_value = (
            qt_widgets.QMessageBox.StandardButton.Yes
        )
        cm.delete_container.return_value = _StubResult(False, "Permission denied")

        tab._delete_container()
        output = "".join(tab._output_lines)
        self.assertIn("Permission denied", output)

    def test_delete_failure_does_not_refresh(self):
        """Failed delete does not refresh container list."""
        containers = [
            _StubContainer("old", _StubContainerStatus.STOPPED, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.question.return_value = (
            qt_widgets.QMessageBox.StandardButton.Yes
        )
        cm.delete_container.return_value = _StubResult(False, "Error")
        cm.list_containers.reset_mock()

        tab._delete_container()
        cm.list_containers.assert_not_called()


class TestCreateContainer(unittest.TestCase):
    """Tests for _create_container."""

    def test_create_empty_name(self):
        """Empty name outputs error message."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("")
        tab._create_container()
        output = "".join(tab._output_lines)
        self.assertIn("Please enter a container name", output)

    def test_create_whitespace_name(self):
        """Whitespace-only name outputs error message."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("   ")
        tab._create_container()
        output = "".join(tab._output_lines)
        self.assertIn("Please enter a container name", output)

    def test_create_success(self):
        """Successful creation outputs message, clears input, refreshes."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("new-box")

        cm = sys.modules["utils.containers"].ContainerManager
        cm.create_container.return_value = _StubResult(
            True, "Container 'new-box' created."
        )
        cm.list_containers.return_value = []

        tab._create_container()
        output = "".join(tab._output_lines)
        self.assertIn("Creating container", output)
        self.assertIn("new-box", output)
        self.assertIn("created", output)
        self.assertEqual(tab.name_input.text(), "")

    def test_create_failure(self):
        """Failed creation does not clear input."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("bad-name")

        cm = sys.modules["utils.containers"].ContainerManager
        cm.create_container.return_value = _StubResult(False, "Invalid name")

        tab._create_container()
        output = "".join(tab._output_lines)
        self.assertIn("Invalid name", output)
        self.assertEqual(tab.name_input.text(), "bad-name")

    def test_create_uses_selected_image(self):
        """Create uses the image from the combo box."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("my-ubuntu")
        if tab.image_combo.count() > 1:
            tab.image_combo.setCurrentIndex(1)

        cm = sys.modules["utils.containers"].ContainerManager
        cm.create_container.return_value = _StubResult(True, "Created!")
        cm.list_containers.return_value = []

        tab._create_container()
        # Verify the call was made with the name and image data
        last_call = cm.create_container.call_args
        self.assertEqual(last_call[0][0], "my-ubuntu")

    def test_create_success_refreshes_containers(self):
        """Successful creation calls refresh_containers."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("fresh")

        cm = sys.modules["utils.containers"].ContainerManager
        cm.create_container.return_value = _StubResult(True, "Done")
        cm.list_containers.reset_mock()
        cm.list_containers.return_value = []

        tab._create_container()
        cm.list_containers.assert_called()

    def test_create_passes_image_data_to_manager(self):
        """Create container passes combo data (not display text) as image."""
        tab = _make_tab(distrobox_available=True)
        tab.name_input.setText("testbox")
        tab.image_combo.setCurrentIndex(0)

        cm = sys.modules["utils.containers"].ContainerManager
        cm.create_container.return_value = _StubResult(True, "OK")
        cm.list_containers.return_value = []

        tab._create_container()
        last_call = cm.create_container.call_args
        # Second arg is the image data from combo
        self.assertEqual(last_call[0][1], tab.image_combo._items[0][1])


# ---------------------------------------------------------------------------
# Tests — Distrobox installation
# ---------------------------------------------------------------------------


class TestInstallDistrobox(unittest.TestCase):
    """Tests for _install_distrobox and _on_distrobox_install_finished."""

    def test_install_distrobox_creates_runner(self):
        """Install creates a CommandRunner and starts it."""
        tab = _make_tab(distrobox_available=False)
        tab._install_distrobox()
        self.assertIsNotNone(tab._distrobox_runner)
        output = "".join(tab._output_lines)
        self.assertIn("Installing Distrobox", output)

    def test_distrobox_install_finished_success(self):
        """Successful installation shows success message."""
        tab = _make_tab(distrobox_available=False)
        qt_widgets = sys.modules["PyQt6.QtWidgets"]

        tab._on_distrobox_install_finished(0)
        output = "".join(tab._output_lines)
        self.assertIn("installed successfully", output)
        qt_widgets.QMessageBox.information.assert_called()

    def test_distrobox_install_finished_failure(self):
        """Failed installation shows error with exit code."""
        tab = _make_tab(distrobox_available=False)
        tab._on_distrobox_install_finished(1)
        output = "".join(tab._output_lines)
        self.assertIn("Installation failed", output)
        self.assertIn("1", output)

    def test_distrobox_install_finished_nonzero_code(self):
        """Non-zero exit code with value 127 is reported."""
        tab = _make_tab(distrobox_available=False)
        tab._on_distrobox_install_finished(127)
        output = "".join(tab._output_lines)
        self.assertIn("127", output)


# ---------------------------------------------------------------------------
# Tests — Developer Tools sub-tab
# ---------------------------------------------------------------------------


class TestDeveloperToolsTab(unittest.TestCase):
    """Tests for developer tools UI elements."""

    def test_pyenv_status_label_created(self):
        """PyEnv status label is created."""
        tab = _make_tab()
        self.assertIsNotNone(tab.pyenv_status)

    def test_nvm_status_label_created(self):
        """NVM status label is created."""
        tab = _make_tab()
        self.assertIsNotNone(tab.nvm_status)

    def test_rust_status_label_created(self):
        """Rust status label is created."""
        tab = _make_tab()
        self.assertIsNotNone(tab.rust_status)

    def test_pyenv_button_created(self):
        """PyEnv install button is created."""
        tab = _make_tab()
        self.assertIsNotNone(tab.pyenv_btn)

    def test_nvm_button_created(self):
        """NVM install button is created."""
        tab = _make_tab()
        self.assertIsNotNone(tab.nvm_btn)

    def test_rust_button_created(self):
        """Rustup install button is created."""
        tab = _make_tab()
        self.assertIsNotNone(tab.rust_btn)


# ---------------------------------------------------------------------------
# Tests — refresh_dev_status
# ---------------------------------------------------------------------------


class TestRefreshDevStatus(unittest.TestCase):
    """Tests for refresh_dev_status."""

    def test_all_not_installed(self):
        """Status labels show 'Not installed' when tools are missing."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (False, "Not installed"),
            "nvm": (False, "Not installed"),
            "rustup": (False, "Not installed"),
        }

        tab.refresh_dev_status()

        self.assertIn("Not installed", tab.pyenv_status.text())
        self.assertIn("Not installed", tab.nvm_status.text())
        self.assertIn("Not installed", tab.rust_status.text())

    def test_pyenv_installed(self):
        """PyEnv status shows version and button changes to Reinstall."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (True, "2.3.35"),
            "nvm": (False, "Not installed"),
            "rustup": (False, "Not installed"),
        }

        tab.refresh_dev_status()

        self.assertIn("2.3.35", tab.pyenv_status.text())
        self.assertEqual(tab.pyenv_btn._text, "Reinstall")

    def test_nvm_installed(self):
        """NVM status shows version and button changes to Reinstall."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (False, "Not installed"),
            "nvm": (True, "0.39.7"),
            "rustup": (False, "Not installed"),
        }

        tab.refresh_dev_status()

        self.assertIn("0.39.7", tab.nvm_status.text())
        self.assertEqual(tab.nvm_btn._text, "Reinstall")

    def test_rustup_installed(self):
        """Rustup status shows version and button changes to Reinstall."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (False, "Not installed"),
            "nvm": (False, "Not installed"),
            "rustup": (True, "1.27.0"),
        }

        tab.refresh_dev_status()

        self.assertIn("1.27.0", tab.rust_status.text())
        self.assertEqual(tab.rust_btn._text, "Reinstall")

    def test_all_installed(self):
        """All three tools installed updates all labels and buttons."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (True, "2.3.35"),
            "nvm": (True, "0.39.7"),
            "rustup": (True, "1.27.0"),
        }

        tab.refresh_dev_status()

        self.assertIn("2.3.35", tab.pyenv_status.text())
        self.assertIn("0.39.7", tab.nvm_status.text())
        self.assertIn("1.27.0", tab.rust_status.text())
        self.assertEqual(tab.pyenv_btn._text, "Reinstall")
        self.assertEqual(tab.nvm_btn._text, "Reinstall")
        self.assertEqual(tab.rust_btn._text, "Reinstall")


# ---------------------------------------------------------------------------
# Tests — _install_tool
# ---------------------------------------------------------------------------


class TestInstallTool(unittest.TestCase):
    """Tests for _install_tool method."""

    def test_install_pyenv_disables_button(self):
        """Installing pyenv disables pyenv button."""
        tab = _make_tab()
        tab._install_tool("pyenv")
        self.assertFalse(tab.pyenv_btn.isEnabled())

    def test_install_nvm_disables_button(self):
        """Installing nvm disables nvm button."""
        tab = _make_tab()
        tab._install_tool("nvm")
        self.assertFalse(tab.nvm_btn.isEnabled())

    def test_install_rustup_disables_button(self):
        """Installing rustup disables rustup button."""
        tab = _make_tab()
        tab._install_tool("rustup")
        self.assertFalse(tab.rust_btn.isEnabled())

    def test_install_tool_outputs_message(self):
        """Install tool shows installing message."""
        tab = _make_tab()
        tab._install_tool("pyenv")
        output = "".join(tab._output_lines)
        self.assertIn("Installing pyenv", output)

    def test_install_tool_creates_worker(self):
        """Install tool creates and tracks worker."""
        tab = _make_tab()
        tab._install_tool("rustup")
        self.assertEqual(len(tab.workers), 1)

    def test_install_multiple_tools(self):
        """Installing multiple tools tracks all workers."""
        tab = _make_tab()
        tab._install_tool("pyenv")
        tab._install_tool("nvm")
        self.assertEqual(len(tab.workers), 2)


# ---------------------------------------------------------------------------
# Tests — _on_install_finished
# ---------------------------------------------------------------------------


class TestOnInstallFinished(unittest.TestCase):
    """Tests for _on_install_finished callback."""

    def test_pyenv_success_reenables_button(self):
        """Successful pyenv install re-enables button."""
        tab = _make_tab()
        tab.pyenv_btn.setEnabled(False)

        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (True, "2.3.35"),
            "nvm": (False, ""),
            "rustup": (False, ""),
        }

        tab._on_install_finished("pyenv", True, "pyenv installed")
        self.assertTrue(tab.pyenv_btn.isEnabled())

    def test_nvm_success_reenables_button(self):
        """Successful nvm install re-enables button."""
        tab = _make_tab()
        tab.nvm_btn.setEnabled(False)

        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (False, ""),
            "nvm": (True, "0.39.7"),
            "rustup": (False, ""),
        }

        tab._on_install_finished("nvm", True, "nvm installed")
        self.assertTrue(tab.nvm_btn.isEnabled())

    def test_rustup_success_reenables_button(self):
        """Successful rustup install re-enables button."""
        tab = _make_tab()
        tab.rust_btn.setEnabled(False)

        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (False, ""),
            "nvm": (False, ""),
            "rustup": (True, "1.27.0"),
        }

        tab._on_install_finished("rustup", True, "rustup installed")
        self.assertTrue(tab.rust_btn.isEnabled())

    def test_success_shows_messagebox(self):
        """Successful tool install shows information dialog."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (True, "2.3.35"),
            "nvm": (False, ""),
            "rustup": (False, ""),
        }
        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.information.reset_mock()

        tab._on_install_finished("pyenv", True, "Done!")
        qt_widgets.QMessageBox.information.assert_called()

    def test_success_refreshes_dev_status(self):
        """Successful install refreshes dev status."""
        tab = _make_tab()
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.reset_mock()
        dtm.get_all_status.return_value = {
            "pyenv": (True, "2.3.35"),
            "nvm": (False, ""),
            "rustup": (False, ""),
        }

        tab._on_install_finished("pyenv", True, "Installed")
        dtm.get_all_status.assert_called()

    def test_failure_outputs_message(self):
        """Failed install outputs error message."""
        tab = _make_tab()
        tab._on_install_finished("pyenv", False, "dependency error")
        output = "".join(tab._output_lines)
        self.assertIn("dependency error", output)

    def test_failure_reenables_button(self):
        """Failed install still re-enables the button."""
        tab = _make_tab()
        tab.pyenv_btn.setEnabled(False)
        tab._on_install_finished("pyenv", False, "fail")
        self.assertTrue(tab.pyenv_btn.isEnabled())

    def test_failure_no_messagebox(self):
        """Failed install does not show success dialog."""
        tab = _make_tab()
        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.information.reset_mock()

        tab._on_install_finished("pyenv", False, "error")
        qt_widgets.QMessageBox.information.assert_not_called()

    def test_vscode_finished_hides_progress(self):
        """VS Code profile finished hides progress bar."""
        tab = _make_tab(vscode_available=True)
        if hasattr(tab, "vscode_progress") and isinstance(
            tab.vscode_progress, _DummyProgressBar
        ):
            tab.vscode_progress.setVisible(True)
            tab._on_install_finished("vscode_python", True, "Done")
            self.assertFalse(tab.vscode_progress.isVisible())

    def test_vscode_success_no_terminal_restart_dialog(self):
        """VS Code install success does not show 'restart terminal' dialog."""
        tab = _make_tab(vscode_available=True)
        dtm = sys.modules["utils.devtools"].DevToolsManager
        dtm.get_all_status.return_value = {
            "pyenv": (False, ""),
            "nvm": (False, ""),
            "rustup": (False, ""),
        }
        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.information.reset_mock()

        tab._on_install_finished("vscode_python", True, "Extensions installed")
        qt_widgets.QMessageBox.information.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — VS Code section
# ---------------------------------------------------------------------------


class TestVSCodeSection(unittest.TestCase):
    """Tests for VS Code extension management."""

    def test_vscode_section_when_available(self):
        """VS Code section has profile combo when VS Code is available."""
        tab = _make_tab(vscode_available=True)
        self.assertIsInstance(tab.profile_combo, _DummyComboBox)

    def test_vscode_section_when_unavailable(self):
        """VS Code section does not create a usable profile combo when unavailable."""
        tab = _make_tab(vscode_available=False)
        # When VS Code is unavailable, profile_combo is never assigned
        # as a _DummyComboBox (it may be a _Dummy from __getattr__)
        self.assertNotIsInstance(getattr(tab, "profile_combo", None), _DummyComboBox)

    def test_profile_combo_populated(self):
        """Profile combo has items from VSCodeManager."""
        tab = _make_tab(vscode_available=True)
        self.assertGreater(tab.profile_combo.count(), 0)

    def test_profile_combo_first_item(self):
        """First profile combo item has correct text."""
        tab = _make_tab(vscode_available=True)
        text = tab.profile_combo._items[0][0]
        self.assertIn("Python", text)
        self.assertIn("5 extensions", text)

    def test_profile_combo_data_keys(self):
        """Profile combo stores key as data."""
        tab = _make_tab(vscode_available=True)
        self.assertEqual(tab.profile_combo._items[0][1], "python")
        self.assertEqual(tab.profile_combo._items[1][1], "web")

    def test_vscode_progress_bar_created(self):
        """Progress bar is created and initially hidden."""
        tab = _make_tab(vscode_available=True)
        self.assertIsInstance(tab.vscode_progress, _DummyProgressBar)
        self.assertFalse(tab.vscode_progress.isVisible())


class TestInstallVSCodeProfile(unittest.TestCase):
    """Tests for _install_vscode_profile."""

    def test_install_profile_outputs_message(self):
        """Install profile outputs installing message."""
        tab = _make_tab(vscode_available=True)
        tab._install_vscode_profile()
        output = "".join(tab._output_lines)
        self.assertIn("Installing VS Code", output)
        self.assertIn("python", output)

    def test_install_profile_shows_progress(self):
        """Install profile makes progress bar visible."""
        tab = _make_tab(vscode_available=True)
        tab._install_vscode_profile()
        self.assertTrue(tab.vscode_progress.isVisible())

    def test_install_profile_sets_indeterminate(self):
        """Install profile sets progress to indeterminate (0,0)."""
        tab = _make_tab(vscode_available=True)
        tab._install_vscode_profile()
        self.assertEqual(tab.vscode_progress._min, 0)
        self.assertEqual(tab.vscode_progress._max, 0)

    def test_install_profile_creates_worker(self):
        """Install profile creates worker with vscode_ prefix."""
        tab = _make_tab(vscode_available=True)
        tab._install_vscode_profile()
        self.assertEqual(len(tab.workers), 1)
        self.assertEqual(tab.workers[0].tool, "vscode_python")

    def test_install_second_profile(self):
        """Installing second profile uses correct key."""
        tab = _make_tab(vscode_available=True)
        tab.profile_combo.setCurrentIndex(1)
        tab._install_vscode_profile()
        self.assertEqual(tab.workers[0].tool, "vscode_web")


class TestApplyVSCodeSettings(unittest.TestCase):
    """Tests for _apply_vscode_settings."""

    def test_apply_settings_success(self):
        """Successful settings application shows dialog."""
        tab = _make_tab(vscode_available=True)
        vsm = sys.modules["utils.vscode"].VSCodeManager
        vsm.inject_settings.return_value = _StubResult(True, "Settings applied")
        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.information.reset_mock()

        tab._apply_vscode_settings()
        output = "".join(tab._output_lines)
        self.assertIn("Settings applied", output)
        qt_widgets.QMessageBox.information.assert_called()

    def test_apply_settings_failure(self):
        """Failed settings application outputs error."""
        tab = _make_tab(vscode_available=True)
        vsm = sys.modules["utils.vscode"].VSCodeManager
        vsm.inject_settings.return_value = _StubResult(False, "File not found")
        qt_widgets = sys.modules["PyQt6.QtWidgets"]
        qt_widgets.QMessageBox.information.reset_mock()

        tab._apply_vscode_settings()
        output = "".join(tab._output_lines)
        self.assertIn("File not found", output)
        qt_widgets.QMessageBox.information.assert_not_called()

    def test_apply_settings_uses_selected_profile(self):
        """Apply settings uses the selected profile from combo."""
        tab = _make_tab(vscode_available=True)
        tab.profile_combo.setCurrentIndex(1)
        vsm = sys.modules["utils.vscode"].VSCodeManager
        vsm.inject_settings.reset_mock()
        vsm.inject_settings.return_value = _StubResult(True, "OK")

        tab._apply_vscode_settings()
        vsm.inject_settings.assert_called_once_with("web")


# ---------------------------------------------------------------------------
# Tests — Context menu
# ---------------------------------------------------------------------------


class TestShowContextMenu(unittest.TestCase):
    """Tests for _show_context_menu."""

    def test_context_menu_no_selection(self):
        """Context menu does nothing without a selection."""
        tab = _make_tab(distrobox_available=True)
        # Should not raise
        tab._show_context_menu(MagicMock())

    def test_context_menu_with_selection(self):
        """Context menu creates menu when container is selected."""
        containers = [
            _StubContainer("dev", _StubContainerStatus.RUNNING, "fedora:latest"),
        ]
        tab = _make_tab(distrobox_available=True, containers=[])
        cm = sys.modules["utils.containers"].ContainerManager
        cm.list_containers.return_value = containers
        tab.refresh_containers()
        tab.container_list.setCurrentRow(0)

        # Should not raise — QMenu and QAction are properly stubbed
        tab._show_context_menu(MagicMock())


if __name__ == "__main__":
    unittest.main()
