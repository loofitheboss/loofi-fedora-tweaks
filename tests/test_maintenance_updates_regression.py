"""Regression tests for Maintenance update actions."""
import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


def _install_maintenance_import_stubs():
    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    qt_widgets = types.ModuleType("PyQt6.QtWidgets")
    qt_widgets.QWidget = _Dummy
    qt_widgets.QVBoxLayout = _Dummy
    qt_widgets.QHBoxLayout = _Dummy
    qt_widgets.QLabel = _Dummy
    qt_widgets.QPushButton = _Dummy
    qt_widgets.QTextEdit = _Dummy
    qt_widgets.QGroupBox = _Dummy
    qt_widgets.QProgressBar = _Dummy
    qt_widgets.QTabWidget = _Dummy
    qt_widgets.QListWidget = _Dummy
    qt_widgets.QListWidgetItem = _Dummy
    qt_widgets.QFrame = _Dummy
    qt_widgets.QMessageBox = _Dummy

    qt_core = types.ModuleType("PyQt6.QtCore")
    qt_core.Qt = types.SimpleNamespace(GlobalColor=types.SimpleNamespace(darkGray=0))

    pyqt = types.ModuleType("PyQt6")
    pyqt.QtWidgets = qt_widgets
    pyqt.QtCore = qt_core

    base_tab_module = types.ModuleType("ui.base_tab")
    base_tab_module.BaseTab = _Dummy

    tab_utils_module = types.ModuleType("ui.tab_utils")
    tab_utils_module.configure_top_tabs = lambda *args, **kwargs: None

    command_runner_module = types.ModuleType("utils.command_runner")
    command_runner_module.CommandRunner = _Dummy

    services_system_module = types.ModuleType("services.system")
    services_system_module.SystemManager = type(
        "SystemManager",
        (),
        {
            "get_package_manager": staticmethod(lambda: "dnf"),
            "is_atomic": staticmethod(lambda: False),
            "get_variant_name": staticmethod(lambda: "Test"),
            "get_layered_packages": staticmethod(lambda: []),
            "has_pending_deployment": staticmethod(lambda: False),
        },
    )

    metadata_module = types.ModuleType("core.plugins.metadata")

    class PluginMetadata:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    metadata_module.PluginMetadata = PluginMetadata

    sys.modules["PyQt6"] = pyqt
    sys.modules["PyQt6.QtWidgets"] = qt_widgets
    sys.modules["PyQt6.QtCore"] = qt_core
    sys.modules["ui.base_tab"] = base_tab_module
    sys.modules["ui.tab_utils"] = tab_utils_module
    sys.modules["utils.command_runner"] = command_runner_module
    sys.modules["services.system"] = services_system_module
    sys.modules["core.plugins.metadata"] = metadata_module


class TestMaintenanceUpdatesRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._module_backup = {}
        for module_name in (
            "PyQt6",
            "PyQt6.QtWidgets",
            "PyQt6.QtCore",
            "ui.base_tab",
            "ui.tab_utils",
            "utils.command_runner",
            "services.system",
            "core.plugins.metadata",
        ):
            cls._module_backup[module_name] = sys.modules.get(module_name)

        _install_maintenance_import_stubs()
        sys.modules.pop("ui.maintenance_tab", None)
        cls.maintenance_module = importlib.import_module("ui.maintenance_tab")
        cls.updates_tab_cls = cls.maintenance_module._UpdatesSubTab

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("ui.maintenance_tab", None)
        for module_name, module_value in cls._module_backup.items():
            if module_value is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = module_value

    def test_system_update_step_dnf(self):
        cmd, args, desc = self.updates_tab_cls._system_update_step("dnf")
        self.assertEqual(cmd, "pkexec")
        self.assertEqual(args, ["dnf", "update", "-y"])
        self.assertEqual(desc, "Starting System Update...")

    def test_system_update_step_rpm_ostree(self):
        cmd, args, desc = self.updates_tab_cls._system_update_step("rpm-ostree")
        self.assertEqual(cmd, "pkexec")
        self.assertEqual(args, ["rpm-ostree", "upgrade"])
        self.assertEqual(desc, "Starting System Upgrade...")

    @patch("utils.safety.SafetyManager.confirm_action", return_value=True)
    @patch("utils.safety.SafetyManager.check_dnf_lock", return_value=False)
    def test_run_update_all_starts_with_system_step(self, _mock_lock, _mock_confirm):
        fake_self = types.SimpleNamespace(
            package_manager="dnf",
            update_queue=[],
            current_update_index=0,
            runner=types.SimpleNamespace(run_command=MagicMock()),
            start_process=MagicMock(),
            append_output=MagicMock(),
            tr=lambda x: x,
            _system_update_step=self.updates_tab_cls._system_update_step,
        )

        self.updates_tab_cls.run_update_all(fake_self)

        fake_self.start_process.assert_called_once()
        fake_self.runner.run_command.assert_called_once_with(
            "pkexec",
            ["dnf", "update", "-y"],
        )
        self.assertEqual(len(fake_self.update_queue), 3)


if __name__ == "__main__":
    unittest.main()
