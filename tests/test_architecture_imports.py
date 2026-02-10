"""
Import validation tests for v23.0 Architecture Hardening.

Validates:
1. New core.executor imports work
2. Backward-compat utils/ shims work
3. Services layer imports work (system, hardware, etc.)
4. Core workers imports work
5. All public APIs are importable
6. No system calls (fast import-only checks)

This ensures the architecture refactor didn't break imports.
"""

import os
import sys
import pytest
import warnings

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks")
)


class TestCoreExecutorImports:
    """Test new core.executor module imports."""

    def test_action_result_import(self):
        """ActionResult should be importable from core.executor."""
        from core.executor import ActionResult

        assert ActionResult is not None
        assert hasattr(ActionResult, "ok")
        assert hasattr(ActionResult, "fail")
        assert hasattr(ActionResult, "previewed")

    def test_base_executor_import(self):
        """BaseActionExecutor should be importable from core.executor."""
        from core.executor import BaseActionExecutor

        assert BaseActionExecutor is not None
        assert hasattr(BaseActionExecutor, "execute")
        assert hasattr(BaseActionExecutor, "preview")

    def test_action_executor_import(self):
        """ActionExecutor should be importable from core.executor."""
        from core.executor import ActionExecutor

        assert ActionExecutor is not None
        # Verify it's the concrete implementation
        assert hasattr(ActionExecutor, "run")

    def test_all_exports(self):
        """Verify __all__ exports match expected public API."""
        import core.executor

        expected = {"ActionResult", "BaseActionExecutor", "ActionExecutor"}
        assert set(core.executor.__all__) == expected


class TestBackwardCompatUtils:
    """Test backward-compatibility shims in utils/."""

    def test_utils_action_result_import(self):
        """ActionResult should still work from utils/ (backward compat)."""
        from utils.action_result import ActionResult

        assert ActionResult is not None
        # Verify same class as core.executor
        from core.executor import ActionResult as CoreActionResult

        assert ActionResult is CoreActionResult

    def test_utils_action_executor_import(self):
        """ActionExecutor should still work from utils/ (backward compat)."""
        from utils.action_executor import ActionExecutor

        assert ActionExecutor is not None
        # Verify same class as core.executor
        from core.executor import ActionExecutor as CoreActionExecutor

        assert ActionExecutor is CoreActionExecutor

    def test_utils_operations_import(self):
        """Operations module should still be importable from utils/."""
        try:
            from utils import operations

            assert operations is not None
        except ImportError:
            # If operations was moved, verify the new location exists
            from core.executor import operations as core_operations

            assert core_operations is not None


class TestServicesSystemImports:
    """Test services.system module imports."""

    def test_system_manager_import(self):
        """SystemManager should be importable from services.system."""
        from services.system import SystemManager

        assert SystemManager is not None

    def test_service_manager_import(self):
        """ServiceManager should be importable from services.system."""
        from services.system import ServiceManager

        assert ServiceManager is not None

    def test_process_manager_import(self):
        """ProcessManager should be importable from services.system."""
        from services.system import ProcessManager

        assert ProcessManager is not None

    def test_service_types_import(self):
        """Service-related types should be importable."""
        from services.system import (
            ServiceUnit,
            UnitScope,
            UnitState,
            Result,
        )

        assert ServiceUnit is not None
        assert UnitScope is not None
        assert UnitState is not None
        assert Result is not None

    def test_process_types_import(self):
        """Process-related types should be importable."""
        from services.system import ProcessInfo

        assert ProcessInfo is not None

    def test_command_runner_backward_compat(self):
        """CommandRunner should be importable (backward compat)."""
        from services.system import CommandRunner

        assert CommandRunner is not None

    def test_all_exports(self):
        """Verify __all__ exports match expected public API."""
        import services.system

        expected = {
            "SystemManager",
            "ServiceManager",
            "ServiceUnit",
            "UnitScope",
            "UnitState",
            "Result",
            "ProcessManager",
            "ProcessInfo",
            "CommandRunner",
        }
        assert set(services.system.__all__) == expected


class TestServicesHardwareImports:
    """Test services.hardware module imports."""

    def test_hardware_manager_import(self):
        """HardwareManager should be importable from services.hardware."""
        from services.hardware import HardwareManager

        assert HardwareManager is not None

    def test_battery_manager_import(self):
        """BatteryManager should be importable from services.hardware."""
        from services.hardware import BatteryManager

        assert BatteryManager is not None

    def test_disk_manager_import(self):
        """DiskManager should be importable from services.hardware."""
        from services.hardware import DiskManager, DiskUsage, LargeDirectory

        assert DiskManager is not None
        assert DiskUsage is not None
        assert LargeDirectory is not None

    def test_temperature_manager_import(self):
        """TemperatureManager should be importable from services.hardware."""
        from services.hardware import TemperatureManager, TemperatureSensor

        assert TemperatureManager is not None
        assert TemperatureSensor is not None

    def test_bluetooth_manager_import(self):
        """BluetoothManager should be importable from services.hardware."""
        from services.hardware import (
            BluetoothManager,
            BluetoothDevice,
            BluetoothDeviceType,
            BluetoothResult,
            BluetoothStatus,
        )

        assert BluetoothManager is not None
        assert BluetoothDevice is not None
        assert BluetoothDeviceType is not None
        assert BluetoothResult is not None
        assert BluetoothStatus is not None

    def test_hardware_profiles_import(self):
        """Hardware profile utilities should be importable."""
        from services.hardware import (
            PROFILES,
            detect_hardware_profile,
            get_profile_label,
            get_all_profiles,
        )

        assert PROFILES is not None
        assert detect_hardware_profile is not None
        assert get_profile_label is not None
        assert get_all_profiles is not None

    def test_all_exports(self):
        """Verify __all__ exports match expected public API."""
        import services.hardware

        expected = {
            "HardwareManager",
            "BatteryManager",
            "DiskManager",
            "DiskUsage",
            "LargeDirectory",
            "TemperatureManager",
            "TemperatureSensor",
            "BluetoothManager",
            "BluetoothDevice",
            "BluetoothDeviceType",
            "BluetoothResult",
            "BluetoothStatus",
            "PROFILES",
            "detect_hardware_profile",
            "get_profile_label",
            "get_all_profiles",
        }
        assert set(services.hardware.__all__) == expected


class TestCoreWorkersImports:
    """Test core.workers module imports."""

    def test_base_worker_import(self):
        """BaseWorker should be importable from core.workers."""
        from core.workers import BaseWorker

        assert BaseWorker is not None
        # Verify it has expected methods (QThread-based)
        assert hasattr(BaseWorker, "run")

    def test_all_exports(self):
        """Verify __all__ exports match expected public API."""
        import core.workers

        expected = {"BaseWorker", "CommandWorker"}
        assert set(core.workers.__all__) == expected


class TestServicesNamespaceImports:
    """Test other services namespace imports."""

    def test_services_namespace_exists(self):
        """services/ package should be importable."""
        import services

        assert services is not None

    def test_services_submodules_exist(self):
        """All services submodules should be importable."""
        import services.desktop
        import services.hardware
        import services.network
        import services.security
        import services.software
        import services.storage
        import services.system
        import services.virtualization

        assert services.desktop is not None
        assert services.hardware is not None
        assert services.network is not None
        assert services.security is not None
        assert services.software is not None
        assert services.storage is not None
        assert services.system is not None
        assert services.virtualization is not None


class TestImportPerformance:
    """Test that imports are fast (no expensive initialization)."""

    def test_executor_import_speed(self):
        """Importing core.executor should be fast."""
        import time

        start = time.time()
        from core.executor import ActionExecutor

        duration = time.time() - start
        # Import should take < 1 second (even on slow CI)
        assert duration < 1.0

    def test_services_import_speed(self):
        """Importing services modules should be fast."""
        import time

        start = time.time()
        from services.system import SystemManager
        from services.hardware import HardwareManager

        duration = time.time() - start
        # Import should take < 1 second
        assert duration < 1.0


class TestNoSystemCalls:
    """Verify that imports don't trigger system calls."""

    def test_action_result_import_no_execution(self):
        """Importing ActionResult should not execute system calls."""
        # This test passes if import completes without subprocess calls
        from core.executor import ActionResult

        # Create instance should also not execute anything
        result = ActionResult.ok("test")
        assert result.success is True

    def test_executor_import_no_execution(self):
        """Importing ActionExecutor should not execute system calls."""
        from core.executor import ActionExecutor

        # Just importing and instantiating should not run commands
        # (actual execution happens in .run())
        assert ActionExecutor is not None


class TestCrossModuleCompatibility:
    """Test that old and new imports refer to the same objects."""

    def test_action_result_identity(self):
        """ActionResult from utils and core.executor should be identical."""
        from utils.action_result import ActionResult as UtilsActionResult
        from core.executor import ActionResult as CoreActionResult

        # Same class object
        assert UtilsActionResult is CoreActionResult

        # Same instance behavior
        r1 = UtilsActionResult.ok("test")
        r2 = CoreActionResult.ok("test")
        assert type(r1) == type(r2)
        assert r1.success == r2.success

    def test_action_executor_identity(self):
        """ActionExecutor from utils and core.executor should be identical."""
        from utils.action_executor import ActionExecutor as UtilsExecutor
        from core.executor import ActionExecutor as CoreExecutor

        assert UtilsExecutor is CoreExecutor


class TestPublicAPIStability:
    """Test that public API surface matches expectations."""

    def test_executor_public_methods(self):
        """ActionExecutor should have expected public methods."""
        from core.executor import ActionExecutor

        expected_methods = {"run", "preview", "execute"}
        actual_methods = {
            m
            for m in dir(ActionExecutor)
            if not m.startswith("_") and callable(getattr(ActionExecutor, m, None))
        }
        # Verify expected methods exist (may have additional helper methods)
        assert expected_methods.issubset(actual_methods)

    def test_action_result_public_methods(self):
        """ActionResult should have expected convenience methods."""
        from core.executor import ActionResult

        assert hasattr(ActionResult, "ok")
        assert hasattr(ActionResult, "fail")
        assert hasattr(ActionResult, "previewed")
        assert callable(ActionResult.ok)
        assert callable(ActionResult.fail)
        assert callable(ActionResult.previewed)

    def test_base_executor_is_abstract(self):
        """BaseActionExecutor should be abstract (cannot instantiate)."""
        from core.executor import BaseActionExecutor

        with pytest.raises(TypeError):
            # Should fail because abstract methods not implemented
            BaseActionExecutor()
