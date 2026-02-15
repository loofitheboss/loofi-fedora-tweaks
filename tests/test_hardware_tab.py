"""Tests for ui/hardware_tab.py — headless PyQt6 stub testing."""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


# ── PyQt6 Stubs ──────────────────────────────────────────────────────────────


class _DummySignal:
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


class _DummyLabel:
    def __init__(self, text="", *a, **kw):
        self._text = text

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyComboBox:
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

    def currentIndex(self):
        return self._current

    def setCurrentIndex(self, i):
        self._current = i

    def setCurrentText(self, t):
        for i, (text, _) in enumerate(self._items):
            if text == t:
                self._current = i
                break

    def clear(self):
        self._items.clear()
        self._current = 0

    def count(self):
        return len(self._items)

    def blockSignals(self, b):
        pass

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummySlider:
    class TickPosition:
        NoTicks = 0
        TicksBelow = 2

    def __init__(self, *a, **kw):
        self._value = 0
        self.valueChanged = _DummySignal()

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = v

    def setRange(self, lo, hi):
        pass

    def setMinimum(self, v):
        pass

    def setMaximum(self, v):
        pass

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyButton(_Dummy):
    def __init__(self, text="", *a, **kw):
        self.clicked = _DummySignal()
        self._enabled = True

    def setEnabled(self, f):
        self._enabled = f

    def isEnabled(self):
        return self._enabled


class _DummyCursor:
    class MoveOperation:
        End = 0

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummyTextEdit:
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

    def textCursor(self):
        return _DummyCursor()

    def moveCursor(self, *a, **kw):
        pass

    def insertPlainText(self, t):
        self._text += t

    def __getattr__(self, n):
        return lambda *a, **kw: None


class _DummySpinBox:
    def __init__(self, *a, **kw):
        self._value = 0

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = v

    def setRange(self, lo, hi):
        pass

    def setSuffix(self, s):
        pass

    def __getattr__(self, n):
        return lambda *a, **kw: None


# ── Stub registration (installed/restored via setUpModule/tearDownModule) ────

_MODULE_KEYS = [
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "core",
    "core.plugins",
    "core.plugins.interface",
    "core.plugins.metadata",
    "services",
    "services.hardware",
    "ui.tooltips",
    "utils.command_runner",
    "utils.log",
    "ui.hardware_tab",
    "ui",
]
_module_backup = {}


class _StubPluginInterface:
    def metadata(self):
        raise NotImplementedError

    def create_widget(self):
        raise NotImplementedError


class _StubPluginMetadata:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _StubCommandRunner:
    def __init__(self, *a, **kw):
        self.output_received = _DummySignal()
        self.finished = _DummySignal()

    def run_command(self, cmd, args):
        pass


# Module-level references set by setUpModule
_hw_mod = None
_qtcore = None
_qtwidgets = None
HardwareManager = None
BluetoothManager = None


def _install_stubs():
    """Create and install all PyQt6/service stubs into sys.modules."""
    global _hw_mod, _qtcore, _qtwidgets, HardwareManager, BluetoothManager

    _qtwidgets = types.ModuleType("PyQt6.QtWidgets")
    _qtwidgets.QWidget = _Dummy
    _qtwidgets.QVBoxLayout = _Dummy
    _qtwidgets.QHBoxLayout = _Dummy
    _qtwidgets.QLabel = _DummyLabel
    _qtwidgets.QPushButton = _DummyButton
    _qtwidgets.QComboBox = _DummyComboBox
    _qtwidgets.QGroupBox = _Dummy
    _qtwidgets.QSlider = _DummySlider
    _qtwidgets.QMessageBox = MagicMock()
    _qtwidgets.QGridLayout = _Dummy
    _qtwidgets.QTextEdit = _DummyTextEdit
    _qtwidgets.QSpinBox = _DummySpinBox

    _qtcore = types.ModuleType("PyQt6.QtCore")
    _qtcore.Qt = _Dummy()
    _qtcore.QTimer = MagicMock()

    _qtgui = types.ModuleType("PyQt6.QtGui")
    _qtgui.QIcon = _Dummy

    _pyqt6 = types.ModuleType("PyQt6")

    sys.modules["PyQt6"] = _pyqt6
    sys.modules["PyQt6.QtWidgets"] = _qtwidgets
    sys.modules["PyQt6.QtCore"] = _qtcore
    sys.modules["PyQt6.QtGui"] = _qtgui

    # Plugin stubs
    _plugin_interface = types.ModuleType("core.plugins.interface")
    _plugin_interface.PluginInterface = _StubPluginInterface
    _plugin_metadata = types.ModuleType("core.plugins.metadata")
    _plugin_metadata.PluginMetadata = _StubPluginMetadata
    _core_plugins = types.ModuleType("core.plugins")
    _core = types.ModuleType("core")
    sys.modules["core"] = _core
    sys.modules["core.plugins"] = _core_plugins
    sys.modules["core.plugins.interface"] = _plugin_interface
    sys.modules["core.plugins.metadata"] = _plugin_metadata

    # Service / util stubs
    _hw_mod = types.ModuleType("services.hardware")
    _hw_mod.HardwareManager = MagicMock()
    _hw_mod.BluetoothManager = MagicMock()
    _services = types.ModuleType("services")
    sys.modules["services"] = _services
    sys.modules["services.hardware"] = _hw_mod

    _cmd_runner_mod = types.ModuleType("utils.command_runner")
    _cmd_runner_mod.CommandRunner = _StubCommandRunner
    _tooltips = types.ModuleType("ui.tooltips")
    _tooltips.HW_CPU_GOVERNOR = "CPU governor tooltip"
    _tooltips.HW_FAN_MODE = "Fan mode tooltip"
    _log_mod = types.ModuleType("utils.log")
    _log_mod.get_logger = MagicMock(return_value=MagicMock())
    sys.modules["ui.tooltips"] = _tooltips
    sys.modules["utils.command_runner"] = _cmd_runner_mod
    sys.modules["utils.log"] = _log_mod

    HardwareManager = _hw_mod.HardwareManager
    BluetoothManager = _hw_mod.BluetoothManager


def setUpModule():
    """Install stubs and import ui.hardware_tab."""
    global \
        _module_backup, \
        _hw_mod, \
        _qtcore, \
        _qtwidgets, \
        HardwareManager, \
        BluetoothManager
    for key in _MODULE_KEYS:
        _module_backup[key] = sys.modules.get(key)
    _install_stubs()
    # Force fresh import
    sys.modules.pop("ui.hardware_tab", None)
    sys.modules.pop("ui", None)
    importlib.import_module("ui.hardware_tab")


def tearDownModule():
    """Restore original sys.modules entries."""
    sys.modules.pop("ui.hardware_tab", None)
    for key, orig in _module_backup.items():
        if orig is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = orig


def _get_module():
    """Return the imported ui.hardware_tab module."""
    return sys.modules["ui.hardware_tab"]


def _make_tab():
    """Create a HardwareTab with standard mocks configured."""
    global HardwareManager, BluetoothManager
    HardwareManager = _hw_mod.HardwareManager
    BluetoothManager = _hw_mod.BluetoothManager
    HardwareManager.reset_mock()
    BluetoothManager.reset_mock()

    HardwareManager.get_cpu_frequency.return_value = {"current": 2400, "max": 4800}
    HardwareManager.get_available_governors.return_value = [
        "powersave",
        "performance",
        "schedutil",
    ]
    HardwareManager.get_current_governor.return_value = "schedutil"
    HardwareManager.is_power_profiles_available.return_value = True
    HardwareManager.get_power_profile.return_value = "balanced"
    HardwareManager.is_hybrid_gpu.return_value = True
    HardwareManager.get_available_gpu_tools.return_value = ["envycontrol"]
    HardwareManager.get_gpu_mode.return_value = "hybrid"
    HardwareManager.is_nbfc_available.return_value = True
    HardwareManager.get_fan_status.return_value = {"speed": 45.0, "temperature": 55.0}
    HardwareManager.set_governor.return_value = True
    HardwareManager.set_power_profile.return_value = True
    HardwareManager.set_fan_speed.return_value = True
    HardwareManager.set_gpu_mode.return_value = (True, "GPU mode set")

    BluetoothManager.get_adapter_status.return_value = MagicMock(
        adapter_name="hci0", powered=True
    )
    BluetoothManager.list_devices.return_value = []
    BluetoothManager.power_on.return_value = MagicMock(success=True, message="OK")
    BluetoothManager.power_off.return_value = MagicMock(success=True, message="OK")

    # Reset QTimer mock so singleShot doesn't break
    _qtcore.QTimer.reset_mock()

    mod = _get_module()
    tab = mod.HardwareTab()
    return tab


# ── Test Classes ─────────────────────────────────────────────────────────────


class TestHardwareTabInit(unittest.TestCase):
    """Tests for HardwareTab initialization and basic structure."""

    def setUp(self):
        self.tab = _make_tab()

    def test_tab_is_instance_of_hardware_tab(self):
        self.assertIsInstance(self.tab, _get_module().HardwareTab)

    def test_metadata_returns_plugin_metadata(self):
        md = self.tab.metadata()
        self.assertEqual(md.id, "hardware")
        self.assertEqual(md.name, "Hardware")

    def test_metadata_category(self):
        md = self.tab.metadata()
        self.assertEqual(md.category, "Hardware")

    def test_metadata_icon(self):
        md = self.tab.metadata()
        self.assertEqual(md.icon, "⚡")

    def test_metadata_badge(self):
        md = self.tab.metadata()
        self.assertEqual(md.badge, "recommended")

    def test_metadata_order(self):
        md = self.tab.metadata()
        self.assertEqual(md.order, 10)

    def test_create_widget_returns_self(self):
        self.assertIs(self.tab.create_widget(), self.tab)

    def test_hw_runner_created(self):
        self.assertIsNotNone(self.tab.hw_runner)

    def test_hw_output_area_created(self):
        self.assertTrue(hasattr(self.tab, "hw_output_area"))

    def test_cpu_freq_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_cpu_freq"))

    def test_governor_combo_created(self):
        self.assertTrue(hasattr(self.tab, "combo_governor"))

    def test_governor_combo_has_items(self):
        combo = self.tab.combo_governor
        self.assertEqual(combo.count(), 3)

    def test_governor_combo_current_is_schedutil(self):
        self.assertEqual(self.tab.combo_governor.currentText(), "schedutil")


class TestCreateCpuCard(unittest.TestCase):
    """Tests for create_cpu_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_cpu_card_returns_group_box(self):
        card = self.tab.create_cpu_card()
        self.assertIsNotNone(card)

    def test_cpu_freq_label_shows_values(self):
        self.assertIn("2400", self.tab.lbl_cpu_freq._text)
        self.assertIn("4800", self.tab.lbl_cpu_freq._text)

    def test_governor_combo_populated(self):
        items = [t for t, _ in self.tab.combo_governor._items]
        self.assertIn("powersave", items)
        self.assertIn("performance", items)
        self.assertIn("schedutil", items)

    def test_cpu_freq_calls_hardware_manager(self):
        HardwareManager.get_cpu_frequency.assert_called()

    def test_available_governors_called(self):
        HardwareManager.get_available_governors.assert_called()

    def test_current_governor_called(self):
        HardwareManager.get_current_governor.assert_called()


class TestOnGovernorChanged(unittest.TestCase):
    """Tests for on_governor_changed."""

    def setUp(self):
        self.tab = _make_tab()

    def test_governor_change_success(self):
        HardwareManager.set_governor.return_value = True
        self.tab.on_governor_changed("performance")
        HardwareManager.set_governor.assert_called_with("performance")

    def test_governor_change_failure_reverts_combo(self):
        HardwareManager.set_governor.return_value = False
        HardwareManager.get_current_governor.return_value = "powersave"
        self.tab.on_governor_changed("performance")
        self.assertEqual(self.tab.combo_governor.currentText(), "powersave")

    def test_governor_change_failure_shows_warning(self):
        HardwareManager.set_governor.return_value = False
        HardwareManager.get_current_governor.return_value = "powersave"
        _qtwidgets.QMessageBox.warning.reset_mock()
        self.tab.on_governor_changed("performance")
        _qtwidgets.QMessageBox.warning.assert_called_once()

    def test_governor_change_success_calls_show_toast(self):
        HardwareManager.set_governor.return_value = True
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab.on_governor_changed("performance")
            mock_toast.assert_called_once()
            self.assertIn("performance", mock_toast.call_args[0][0])


class TestCreatePowerProfileCard(unittest.TestCase):
    """Tests for create_power_profile_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_power_profile_card_created(self):
        card = self.tab.create_power_profile_card()
        self.assertIsNotNone(card)

    def test_power_profile_label_shows_current(self):
        self.assertIn("Balanced", self.tab.lbl_power_profile._text)

    def test_power_profile_unavailable(self):
        HardwareManager.is_power_profiles_available.return_value = False
        tab = _make_tab()
        # Should still instantiate without error
        self.assertIsInstance(tab, _get_module().HardwareTab)

    def test_is_power_profiles_available_called(self):
        HardwareManager.is_power_profiles_available.assert_called()


class TestSetPowerProfile(unittest.TestCase):
    """Tests for set_power_profile."""

    def setUp(self):
        self.tab = _make_tab()

    def test_set_power_profile_success(self):
        HardwareManager.set_power_profile.return_value = True
        self.tab.set_power_profile("power-saver")
        HardwareManager.set_power_profile.assert_called_with("power-saver")

    def test_set_power_profile_updates_label(self):
        HardwareManager.set_power_profile.return_value = True
        self.tab.set_power_profile("performance")
        self.assertIn("Performance", self.tab.lbl_power_profile._text)

    def test_set_power_profile_failure_shows_warning(self):
        HardwareManager.set_power_profile.return_value = False
        _qtwidgets.QMessageBox.warning.reset_mock()
        self.tab.set_power_profile("performance")
        _qtwidgets.QMessageBox.warning.assert_called_once()

    def test_set_power_profile_success_shows_toast(self):
        HardwareManager.set_power_profile.return_value = True
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab.set_power_profile("balanced")
            mock_toast.assert_called_once()
            self.assertIn("balanced", mock_toast.call_args[0][0])

    def test_set_power_profile_failure_does_not_update_label(self):
        HardwareManager.set_power_profile.return_value = False
        original = self.tab.lbl_power_profile._text
        self.tab.set_power_profile("power-saver")
        # Label should not have been updated to power-saver
        self.assertEqual(self.tab.lbl_power_profile._text, original)


class TestCreateGpuCard(unittest.TestCase):
    """Tests for create_gpu_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_gpu_card_created(self):
        card = self.tab.create_gpu_card()
        self.assertIsNotNone(card)

    def test_gpu_mode_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_gpu_mode"))

    def test_gpu_mode_label_shows_current(self):
        self.assertIn("Hybrid", self.tab.lbl_gpu_mode._text)

    def test_no_hybrid_gpu_detected(self):
        HardwareManager.is_hybrid_gpu.return_value = False
        tab = _make_tab()
        self.assertIsInstance(tab, _get_module().HardwareTab)

    def test_no_gpu_tools_available(self):
        HardwareManager.is_hybrid_gpu.return_value = True
        HardwareManager.get_available_gpu_tools.return_value = []
        tab = _make_tab()
        self.assertIsInstance(tab, _get_module().HardwareTab)


class TestSetGpuMode(unittest.TestCase):
    """Tests for set_gpu_mode."""

    def setUp(self):
        self.tab = _make_tab()

    def test_set_gpu_mode_confirmed_success(self):
        _qtwidgets.QMessageBox.question.return_value = (
            _qtwidgets.QMessageBox.StandardButton.Yes
        )
        HardwareManager.set_gpu_mode.return_value = (True, "GPU switched to integrated")
        self.tab.set_gpu_mode("integrated")
        HardwareManager.set_gpu_mode.assert_called_with("integrated")

    def test_set_gpu_mode_confirmed_updates_label(self):
        _qtwidgets.QMessageBox.question.return_value = (
            _qtwidgets.QMessageBox.StandardButton.Yes
        )
        HardwareManager.set_gpu_mode.return_value = (True, "OK")
        self.tab.set_gpu_mode("nvidia")
        self.assertIn("pending", self.tab.lbl_gpu_mode._text)

    def test_set_gpu_mode_confirmed_failure(self):
        _qtwidgets.QMessageBox.question.return_value = (
            _qtwidgets.QMessageBox.StandardButton.Yes
        )
        HardwareManager.set_gpu_mode.return_value = (False, "envycontrol error")
        _qtwidgets.QMessageBox.warning.reset_mock()
        self.tab.set_gpu_mode("nvidia")
        _qtwidgets.QMessageBox.warning.assert_called_once()

    def test_set_gpu_mode_declined_does_nothing(self):
        _qtwidgets.QMessageBox.question.return_value = (
            _qtwidgets.QMessageBox.StandardButton.No
        )
        HardwareManager.set_gpu_mode.reset_mock()
        self.tab.set_gpu_mode("nvidia")
        HardwareManager.set_gpu_mode.assert_not_called()

    def test_set_gpu_mode_success_shows_info_dialog(self):
        _qtwidgets.QMessageBox.question.return_value = (
            _qtwidgets.QMessageBox.StandardButton.Yes
        )
        HardwareManager.set_gpu_mode.return_value = (True, "Done")
        _qtwidgets.QMessageBox.information.reset_mock()
        self.tab.set_gpu_mode("hybrid")
        _qtwidgets.QMessageBox.information.assert_called_once()


class TestInstallEnvycontrol(unittest.TestCase):
    """Tests for install_envycontrol."""

    def setUp(self):
        self.tab = _make_tab()

    def test_install_envycontrol_shows_information(self):
        _qtwidgets.QMessageBox.information.reset_mock()
        self.tab.install_envycontrol()
        _qtwidgets.QMessageBox.information.assert_called_once()


class TestCreateFanCard(unittest.TestCase):
    """Tests for create_fan_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_fan_card_created(self):
        card = self.tab.create_fan_card()
        self.assertIsNotNone(card)

    def test_fan_status_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_fan_status"))

    def test_fan_status_shows_speed_and_temp(self):
        self.assertIn("45", self.tab.lbl_fan_status._text)
        self.assertIn("55", self.tab.lbl_fan_status._text)

    def test_fan_slider_created(self):
        self.assertTrue(hasattr(self.tab, "slider_fan"))

    def test_fan_percent_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_fan_percent"))

    def test_nbfc_not_available(self):
        HardwareManager.is_nbfc_available.return_value = False
        # Create a fresh tab with nbfc unavailable
        HardwareManager.get_cpu_frequency.return_value = {"current": 2400, "max": 4800}
        HardwareManager.get_available_governors.return_value = ["powersave"]
        HardwareManager.get_current_governor.return_value = "powersave"
        HardwareManager.is_power_profiles_available.return_value = True
        HardwareManager.get_power_profile.return_value = "balanced"
        HardwareManager.is_hybrid_gpu.return_value = True
        HardwareManager.get_available_gpu_tools.return_value = ["envycontrol"]
        HardwareManager.get_gpu_mode.return_value = "hybrid"
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="hci0", powered=True
        )
        BluetoothManager.list_devices.return_value = []
        _qtcore.QTimer.reset_mock()
        tab = _get_module().HardwareTab()
        # When nbfc is not available, slider_fan should not be in __dict__
        # (hasattr returns True on _Dummy due to __getattr__, so check __dict__)
        self.assertNotIn("slider_fan", tab.__dict__)

    def test_fan_slider_initial_value(self):
        self.assertEqual(self.tab.slider_fan._value, 50)


class TestSetFanSpeed(unittest.TestCase):
    """Tests for set_fan_speed."""

    def setUp(self):
        self.tab = _make_tab()

    def test_set_fan_speed_success(self):
        HardwareManager.set_fan_speed.return_value = True
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab.set_fan_speed(75)
            HardwareManager.set_fan_speed.assert_called_with(75)
            mock_toast.assert_called_once()

    def test_set_fan_speed_auto_mode(self):
        HardwareManager.set_fan_speed.return_value = True
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab.set_fan_speed(-1)
            HardwareManager.set_fan_speed.assert_called_with(-1)
            self.assertIn("Auto", mock_toast.call_args[0][0])

    def test_set_fan_speed_failure(self):
        HardwareManager.set_fan_speed.return_value = False
        _qtwidgets.QMessageBox.warning.reset_mock()
        self.tab.set_fan_speed(50)
        _qtwidgets.QMessageBox.warning.assert_called_once()

    def test_set_fan_speed_percentage_in_toast(self):
        HardwareManager.set_fan_speed.return_value = True
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab.set_fan_speed(80)
            self.assertIn("80%", mock_toast.call_args[0][0])


class TestShowNbfcHelp(unittest.TestCase):
    """Tests for show_nbfc_help."""

    def setUp(self):
        self.tab = _make_tab()

    def test_nbfc_help_shows_information(self):
        _qtwidgets.QMessageBox.information.reset_mock()
        self.tab.show_nbfc_help()
        _qtwidgets.QMessageBox.information.assert_called_once()


class TestCreateAudioCard(unittest.TestCase):
    """Tests for create_audio_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_audio_card_created(self):
        card = self.tab.create_audio_card()
        self.assertIsNotNone(card)


class TestCreateBatteryLimitCard(unittest.TestCase):
    """Tests for create_battery_limit_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_battery_card_created(self):
        card = self.tab.create_battery_limit_card()
        self.assertIsNotNone(card)


class TestSetBatteryLimit(unittest.TestCase):
    """Tests for _set_battery_limit."""

    def setUp(self):
        self.tab = _make_tab()

    def test_set_battery_limit_with_cmd(self):
        mock_manager = MagicMock()
        mock_manager.set_limit.return_value = ("pkexec", ["bash", "/tmp/battery.sh"])
        batt_mod = types.ModuleType("utils.battery")
        batt_mod.BatteryManager = MagicMock(return_value=mock_manager)
        with patch.dict(sys.modules, {"utils.battery": batt_mod}):
            with patch.object(self.tab, "_run_hw_command") as mock_run:
                self.tab._set_battery_limit(80)
                mock_manager.set_limit.assert_called_with(80)
                mock_run.assert_called_once()

    def test_set_battery_limit_echo_cmd(self):
        mock_manager = MagicMock()
        mock_manager.set_limit.return_value = ("echo", ["Battery limit set to 80%"])
        batt_mod = types.ModuleType("utils.battery")
        batt_mod.BatteryManager = MagicMock(return_value=mock_manager)
        with patch.dict(sys.modules, {"utils.battery": batt_mod}):
            self.tab._set_battery_limit(80)
        self.assertIn("80%", self.tab.hw_output_area._text)

    def test_set_battery_limit_none_cmd(self):
        mock_manager = MagicMock()
        mock_manager.set_limit.return_value = (None, None)
        batt_mod = types.ModuleType("utils.battery")
        batt_mod.BatteryManager = MagicMock(return_value=mock_manager)
        with patch.dict(sys.modules, {"utils.battery": batt_mod}):
            self.tab._set_battery_limit(80)
        self.assertIn("Failed", self.tab.hw_output_area._text)

    def test_set_battery_limit_100(self):
        mock_manager = MagicMock()
        mock_manager.set_limit.return_value = ("echo", ["Battery limit set to 100%"])
        batt_mod = types.ModuleType("utils.battery")
        batt_mod.BatteryManager = MagicMock(return_value=mock_manager)
        with patch.dict(sys.modules, {"utils.battery": batt_mod}):
            self.tab._set_battery_limit(100)
        mock_manager.set_limit.assert_called_with(100)


class TestCreateFingerprintCard(unittest.TestCase):
    """Tests for create_fingerprint_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_fingerprint_card_created(self):
        card = self.tab.create_fingerprint_card()
        self.assertIsNotNone(card)


class TestEnrollFingerprint(unittest.TestCase):
    """Tests for _enroll_fingerprint."""

    def setUp(self):
        self.tab = _make_tab()

    def test_enroll_fingerprint_opens_dialog(self):
        mock_dialog_cls = MagicMock()
        mock_dialog_inst = MagicMock()
        mock_dialog_cls.return_value = mock_dialog_inst
        fp_mod = types.ModuleType("ui.fingerprint_dialog")
        fp_mod.FingerprintDialog = mock_dialog_cls
        with patch.dict(sys.modules, {"ui.fingerprint_dialog": fp_mod}):
            self.tab._enroll_fingerprint()
        mock_dialog_cls.assert_called_once_with(self.tab)
        mock_dialog_inst.exec.assert_called_once()


class TestCreateBluetoothCard(unittest.TestCase):
    """Tests for create_bluetooth_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_bluetooth_card_created(self):
        card = self.tab.create_bluetooth_card()
        self.assertIsNotNone(card)

    def test_bt_status_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_bt_status"))

    def test_bt_devices_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_bt_devices"))


class TestBtRefreshStatus(unittest.TestCase):
    """Tests for _bt_refresh_status."""

    def setUp(self):
        self.tab = _make_tab()
        # Ensure no stale side_effect from previous tests
        BluetoothManager.get_adapter_status.side_effect = None
        BluetoothManager.list_devices.side_effect = None

    def test_bt_refresh_with_adapter_powered_on(self):
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="hci0", powered=True
        )
        BluetoothManager.list_devices.return_value = []
        self.tab._bt_refresh_status()
        self.assertIn("On", self.tab.lbl_bt_status._text)
        self.assertIn("hci0", self.tab.lbl_bt_status._text)

    def test_bt_refresh_with_adapter_powered_off(self):
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="hci0", powered=False
        )
        BluetoothManager.list_devices.return_value = []
        self.tab._bt_refresh_status()
        self.assertIn("Off", self.tab.lbl_bt_status._text)

    def test_bt_refresh_no_adapter(self):
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="", powered=False
        )
        self.tab._bt_refresh_status()
        self.assertIn("No adapter", self.tab.lbl_bt_status._text)

    def test_bt_refresh_with_paired_devices(self):
        dev1 = MagicMock(name="AirPods", connected=True)
        dev1.name = "AirPods"
        dev2 = MagicMock(name="KB", connected=False)
        dev2.name = "KB"
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="hci0", powered=True
        )
        BluetoothManager.list_devices.return_value = [dev1, dev2]
        self.tab._bt_refresh_status()
        self.assertIn("AirPods", self.tab.lbl_bt_devices._text)
        self.assertIn("connected", self.tab.lbl_bt_devices._text)
        self.assertIn("KB", self.tab.lbl_bt_devices._text)
        self.assertIn("paired", self.tab.lbl_bt_devices._text)

    def test_bt_refresh_no_paired_devices(self):
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="hci0", powered=True
        )
        BluetoothManager.list_devices.return_value = []
        self.tab._bt_refresh_status()
        self.assertIn("none", self.tab.lbl_bt_devices._text)

    def test_bt_refresh_exception_handled(self):
        BluetoothManager.get_adapter_status.side_effect = RuntimeError("fail")
        self.tab._bt_refresh_status()
        self.assertIn("not available", self.tab.lbl_bt_status._text)

    def test_bt_refresh_max_five_devices_shown(self):
        devices = []
        for i in range(7):
            d = MagicMock()
            d.name = f"Dev{i}"
            d.connected = False
            devices.append(d)
        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="hci0", powered=True
        )
        BluetoothManager.list_devices.return_value = devices
        self.tab._bt_refresh_status()
        # Should only show first 5
        self.assertIn("Dev4", self.tab.lbl_bt_devices._text)
        self.assertNotIn("Dev5", self.tab.lbl_bt_devices._text)


class TestBtPowerOn(unittest.TestCase):
    """Tests for _bt_power_on."""

    def setUp(self):
        self.tab = _make_tab()

    def test_bt_power_on_success(self):
        BluetoothManager.power_on.return_value = MagicMock(success=True, message="OK")
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab._bt_power_on()
            mock_toast.assert_called_once()
            self.assertIn("powered on", mock_toast.call_args[0][0])

    def test_bt_power_on_failure(self):
        BluetoothManager.power_on.return_value = MagicMock(
            success=False, message="No adapter"
        )
        _qtwidgets.QMessageBox.warning.reset_mock()
        self.tab._bt_power_on()
        _qtwidgets.QMessageBox.warning.assert_called_once()


class TestBtPowerOff(unittest.TestCase):
    """Tests for _bt_power_off."""

    def setUp(self):
        self.tab = _make_tab()

    def test_bt_power_off_success(self):
        BluetoothManager.power_off.return_value = MagicMock(success=True, message="OK")
        with patch.object(self.tab, "show_toast") as mock_toast:
            self.tab._bt_power_off()
            mock_toast.assert_called_once()
            self.assertIn("powered off", mock_toast.call_args[0][0])

    def test_bt_power_off_failure(self):
        BluetoothManager.power_off.return_value = MagicMock(
            success=False, message="Error"
        )
        _qtwidgets.QMessageBox.warning.reset_mock()
        self.tab._bt_power_off()
        _qtwidgets.QMessageBox.warning.assert_called_once()


class TestBtScan(unittest.TestCase):
    """Tests for _bt_scan."""

    def setUp(self):
        self.tab = _make_tab()

    def test_bt_scan_runs_command(self):
        with patch.object(self.tab, "_run_hw_command") as mock_run:
            self.tab._bt_scan()
            mock_run.assert_called_once_with(
                "bluetoothctl",
                ["--timeout", "10", "scan", "on"],
                "Scanning for Bluetooth devices...",
            )


class TestCreateBootConfigCard(unittest.TestCase):
    """Tests for create_boot_config_card."""

    def setUp(self):
        self.tab = _make_tab()

    def test_boot_card_created(self):
        card = self.tab.create_boot_config_card()
        self.assertIsNotNone(card)

    def test_boot_info_label_created(self):
        self.assertTrue(hasattr(self.tab, "lbl_boot_info"))

    def test_boot_timeout_spin_created(self):
        self.assertTrue(hasattr(self.tab, "boot_timeout_spin"))


class TestLoadBootInfo(unittest.TestCase):
    """Tests for _load_boot_info."""

    def setUp(self):
        self.tab = _make_tab()

    def test_load_boot_info_success(self):
        mock_bcm = MagicMock()
        mock_bcm.get_current_cmdline.return_value = (
            "BOOT_IMAGE=/vmlinuz-6.8.0 root=UUID=abcdef"
        )
        boot_mod = types.ModuleType("utils.boot_config")
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._load_boot_info()
        self.assertIn("BOOT_IMAGE", self.tab.lbl_boot_info._text)

    def test_load_boot_info_exception(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.get_current_cmdline.side_effect = OSError("file not found")
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._load_boot_info()
        self.assertIn("detection failed", self.tab.lbl_boot_info._text)

    def test_load_boot_info_empty_cmdline(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.get_current_cmdline.return_value = ""
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._load_boot_info()
        self.assertIn("unknown", self.tab.lbl_boot_info._text)

    def test_load_boot_info_truncates_long_cmdline(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.get_current_cmdline.return_value = "A" * 200
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._load_boot_info()
        # Should truncate to 80 chars plus the "Current: " prefix
        label_text = self.tab.lbl_boot_info._text
        # The actual content portion is [:80]
        self.assertTrue(len(label_text) < 200)


class TestListBootKernels(unittest.TestCase):
    """Tests for _list_boot_kernels."""

    def setUp(self):
        self.tab = _make_tab()

    def test_list_kernels_success(self):
        k1 = MagicMock(title="Fedora 41", version="6.8.0", is_default=True)
        k2 = MagicMock(title="Fedora 41 (old)", version="6.7.0", is_default=False)
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.list_kernels.return_value = [k1, k2]
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._list_boot_kernels()
        output = self.tab.hw_output_area._text
        self.assertIn("Fedora 41", output)
        self.assertIn("6.8.0", output)
        self.assertIn("→", output)  # default marker

    def test_list_kernels_empty(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.list_kernels.return_value = []
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._list_boot_kernels()
        self.assertIn("No kernels found", self.tab.hw_output_area._text)

    def test_list_kernels_exception(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.list_kernels.side_effect = RuntimeError("grubby error")
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._list_boot_kernels()
        self.assertIn("ERROR", self.tab.hw_output_area._text)


class TestShowGrubConfig(unittest.TestCase):
    """Tests for _show_grub_config."""

    def setUp(self):
        self.tab = _make_tab()

    def test_show_grub_config_success(self):
        config = MagicMock(
            default_entry="Fedora",
            timeout=5,
            theme="/boot/grub2/themes/fedora",
            cmdline_linux="quiet splash",
        )
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.get_grub_config.return_value = config
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._show_grub_config()
        output = self.tab.hw_output_area._text
        self.assertIn("Default: Fedora", output)
        self.assertIn("Timeout: 5s", output)
        self.assertIn("quiet splash", output)

    def test_show_grub_config_no_theme(self):
        config = MagicMock(
            default_entry="saved",
            timeout=0,
            theme=None,
            cmdline_linux="",
        )
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.get_grub_config.return_value = config
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._show_grub_config()
        self.assertIn("none", self.tab.hw_output_area._text)

    def test_show_grub_config_exception(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.get_grub_config.side_effect = FileNotFoundError("no grub.cfg")
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._show_grub_config()
        self.assertIn("ERROR", self.tab.hw_output_area._text)


class TestSetBootTimeout(unittest.TestCase):
    """Tests for _set_boot_timeout."""

    def setUp(self):
        self.tab = _make_tab()

    def test_set_boot_timeout_success(self):
        self.tab.boot_timeout_spin._value = 10
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.set_timeout.return_value = (
            "pkexec",
            ["sed", "-i", "..."],
            "Setting timeout",
        )
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            with patch.object(self.tab, "_run_hw_command") as mock_run:
                self.tab._set_boot_timeout()
                mock_bcm.set_timeout.assert_called_with(10)
                mock_run.assert_called_once()

    def test_set_boot_timeout_exception(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.set_timeout.side_effect = ValueError("invalid")
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._set_boot_timeout()
        self.assertIn("ERROR", self.tab.hw_output_area._text)


class TestApplyGrub(unittest.TestCase):
    """Tests for _apply_grub."""

    def setUp(self):
        self.tab = _make_tab()

    def test_apply_grub_success(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.apply_grub_changes.return_value = (
            "pkexec",
            ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"],
            "Rebuilding GRUB",
        )
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            with patch.object(self.tab, "_run_hw_command") as mock_run:
                self.tab._apply_grub()
                mock_run.assert_called_once_with(
                    "pkexec",
                    ["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"],
                    "Rebuilding GRUB",
                )

    def test_apply_grub_exception(self):
        boot_mod = types.ModuleType("utils.boot_config")
        mock_bcm = MagicMock()
        mock_bcm.apply_grub_changes.side_effect = OSError("permission denied")
        boot_mod.BootConfigManager = mock_bcm
        with patch.dict(sys.modules, {"utils.boot_config": boot_mod}):
            self.tab._apply_grub()
        self.assertIn("ERROR", self.tab.hw_output_area._text)


class TestRefreshStatus(unittest.TestCase):
    """Tests for refresh_status."""

    def setUp(self):
        self.tab = _make_tab()

    def test_refresh_updates_cpu_freq(self):
        HardwareManager.get_cpu_frequency.return_value = {"current": 3200, "max": 5000}
        self.tab.refresh_status()
        self.assertIn("3200", self.tab.lbl_cpu_freq._text)
        self.assertIn("5000", self.tab.lbl_cpu_freq._text)

    def test_refresh_updates_fan_status(self):
        HardwareManager.is_nbfc_available.return_value = True
        HardwareManager.get_fan_status.return_value = {
            "speed": 80.0,
            "temperature": 72.0,
        }
        self.tab.refresh_status()
        self.assertIn("80", self.tab.lbl_fan_status._text)
        self.assertIn("72", self.tab.lbl_fan_status._text)

    def test_refresh_skips_fan_when_nbfc_unavailable(self):
        HardwareManager.is_nbfc_available.return_value = False
        HardwareManager.get_fan_status.reset_mock()
        self.tab.refresh_status()
        HardwareManager.get_fan_status.assert_not_called()

    def test_refresh_handles_exception(self):
        HardwareManager.get_cpu_frequency.side_effect = RuntimeError("hw error")
        # Should not raise
        self.tab.refresh_status()
        HardwareManager.get_cpu_frequency.side_effect = None


class TestShowToast(unittest.TestCase):
    """Tests for show_toast."""

    def setUp(self):
        self.tab = _make_tab()

    def test_show_toast_with_parent_window(self):
        mock_parent = MagicMock()
        mock_parent.windowTitle.return_value = "Loofi"
        self.tab.window = MagicMock(return_value=mock_parent)
        self.tab.show_toast("Test message")
        mock_parent.setWindowTitle.assert_called()
        title_arg = mock_parent.setWindowTitle.call_args[0][0]
        self.assertIn("Test message", title_arg)

    def test_show_toast_no_parent_window(self):
        self.tab.window = MagicMock(return_value=None)
        # Should not raise
        self.tab.show_toast("Test message")


class TestRunHwCommand(unittest.TestCase):
    """Tests for _run_hw_command."""

    def setUp(self):
        self.tab = _make_tab()

    def test_run_hw_command_clears_output(self):
        self.tab.hw_output_area._text = "old output"
        self.tab._run_hw_command("ls", ["-la"], "Listing files")
        # After clear + setPlainText, text should be description
        self.assertIn("Listing files", self.tab.hw_output_area._text)

    def test_run_hw_command_no_description(self):
        self.tab.hw_output_area._text = "old"
        self.tab._run_hw_command("ls", ["-la"])
        # Output should have been cleared but no description set

    def test_run_hw_command_calls_runner(self):
        with patch.object(self.tab.hw_runner, "run_command") as mock_run:
            self.tab._run_hw_command("echo", ["hello"], "Test")
            mock_run.assert_called_once_with("echo", ["hello"])


class TestOnHwOutput(unittest.TestCase):
    """Tests for _on_hw_output."""

    def setUp(self):
        self.tab = _make_tab()

    def test_on_hw_output_appends_text(self):
        # _on_hw_output uses insertPlainText which is a no-op on our stub
        # but should not raise
        self.tab._on_hw_output("some output")


class TestOnHwCommandFinished(unittest.TestCase):
    """Tests for _on_hw_command_finished."""

    def setUp(self):
        self.tab = _make_tab()

    def test_on_hw_command_finished_no_crash(self):
        # insertPlainText is a no-op on our stub but should not raise
        self.tab._on_hw_command_finished(0)

    def test_on_hw_command_finished_nonzero_exit(self):
        self.tab._on_hw_command_finished(1)


class TestCreateCard(unittest.TestCase):
    """Tests for create_card helper."""

    def setUp(self):
        self.tab = _make_tab()

    def test_create_card_returns_group_box(self):
        card = self.tab.create_card("Test", "🧪")
        self.assertIsNotNone(card)

    def test_create_card_title_format(self):
        # The title should contain the icon and name
        # GroupBox is a _Dummy so we can't check title directly, but no crash
        card = self.tab.create_card("My Card", "🔥")
        self.assertIsNotNone(card)


class TestSetupCommandRunner(unittest.TestCase):
    """Tests for _setup_command_runner."""

    def setUp(self):
        self.tab = _make_tab()

    def test_hw_runner_has_output_signal(self):
        self.assertIsNotNone(self.tab.hw_runner.output_received)

    def test_hw_runner_has_finished_signal(self):
        self.assertIsNotNone(self.tab.hw_runner.finished)

    def test_hw_runner_signals_connected(self):
        # output_received should have at least one slot connected
        self.assertTrue(len(self.tab.hw_runner.output_received._slots) >= 1)
        self.assertTrue(len(self.tab.hw_runner.finished._slots) >= 1)


class TestEdgeCases(unittest.TestCase):
    """Edge case and integration tests."""

    def test_tab_creation_with_no_hybrid_gpu_no_nbfc_no_power_profiles(self):
        HardwareManager.reset_mock()
        BluetoothManager.reset_mock()

        HardwareManager.get_cpu_frequency.return_value = {"current": 0, "max": 0}
        HardwareManager.get_available_governors.return_value = []
        HardwareManager.get_current_governor.return_value = ""
        HardwareManager.is_power_profiles_available.return_value = False
        HardwareManager.is_hybrid_gpu.return_value = False
        HardwareManager.get_available_gpu_tools.return_value = []
        HardwareManager.is_nbfc_available.return_value = False

        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="", powered=False
        )
        BluetoothManager.list_devices.return_value = []

        _qtcore.QTimer.reset_mock()

        tab = _get_module().HardwareTab()
        self.assertIsNotNone(tab)

    def test_tab_with_zero_cpu_freq(self):
        HardwareManager.reset_mock()
        BluetoothManager.reset_mock()

        HardwareManager.get_cpu_frequency.return_value = {"current": 0, "max": 0}
        HardwareManager.get_available_governors.return_value = ["powersave"]
        HardwareManager.get_current_governor.return_value = "powersave"
        HardwareManager.is_power_profiles_available.return_value = True
        HardwareManager.get_power_profile.return_value = "balanced"
        HardwareManager.is_hybrid_gpu.return_value = False
        HardwareManager.is_nbfc_available.return_value = False

        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="", powered=False
        )
        BluetoothManager.list_devices.return_value = []

        _qtcore.QTimer.reset_mock()

        tab = _get_module().HardwareTab()
        self.assertIn("0", tab.lbl_cpu_freq._text)

    def test_governor_combo_empty_governors_list(self):
        HardwareManager.reset_mock()
        BluetoothManager.reset_mock()

        HardwareManager.get_cpu_frequency.return_value = {"current": 100, "max": 100}
        HardwareManager.get_available_governors.return_value = []
        HardwareManager.get_current_governor.return_value = ""
        HardwareManager.is_power_profiles_available.return_value = False
        HardwareManager.is_hybrid_gpu.return_value = False
        HardwareManager.is_nbfc_available.return_value = False

        BluetoothManager.get_adapter_status.return_value = MagicMock(
            adapter_name="", powered=False
        )
        BluetoothManager.list_devices.return_value = []

        _qtcore.QTimer.reset_mock()

        tab = _get_module().HardwareTab()
        self.assertEqual(tab.combo_governor.count(), 0)

    def test_fan_slider_value_change_updates_label(self):
        tab = _make_tab()
        # Simulate valueChanged signal
        tab.slider_fan.valueChanged.emit(75)
        self.assertEqual(tab.lbl_fan_percent._text, "75%")

    def test_multiple_refresh_calls(self):
        tab = _make_tab()
        HardwareManager.get_cpu_frequency.return_value = {"current": 1000, "max": 2000}
        HardwareManager.is_nbfc_available.return_value = True
        HardwareManager.get_fan_status.return_value = {
            "speed": 30.0,
            "temperature": 40.0,
        }
        tab.refresh_status()
        self.assertIn("1000", tab.lbl_cpu_freq._text)
        HardwareManager.get_cpu_frequency.return_value = {"current": 2000, "max": 3000}
        tab.refresh_status()
        self.assertIn("2000", tab.lbl_cpu_freq._text)


if __name__ == "__main__":
    unittest.main()
