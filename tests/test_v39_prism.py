"""Tests for v39.0 'Prism' — Deprecated Import Cleanup & QSS Migration."""
import os
import sys
import unittest
import glob
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC_DIR = os.path.join(PROJECT_ROOT, "loofi-fedora-tweaks")


class TestVersionAlignment(unittest.TestCase):
    """Verify version strings are consistent across all version sources."""

    def test_version_py_version(self):
        from version import __version__
        self.assertEqual(__version__, "39.0.0")

    def test_version_py_codename(self):
        from version import __version_codename__
        self.assertEqual(__version_codename__, "Prism")

    def test_pyproject_toml_version(self):
        toml_path = os.path.join(PROJECT_ROOT, "pyproject.toml")
        with open(toml_path, "r") as f:
            content = f.read()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        self.assertIsNotNone(match, "No version found in pyproject.toml")
        self.assertEqual(match.group(1), "39.0.0")

    def test_spec_file_version(self):
        spec_path = os.path.join(PROJECT_ROOT, "loofi-fedora-tweaks.spec")
        with open(spec_path, "r") as f:
            content = f.read()
        match = re.search(r'^Version:\s+(\S+)', content, re.MULTILINE)
        self.assertIsNotNone(match, "No Version: found in .spec")
        self.assertEqual(match.group(1), "39.0.0")


class TestShimRemoval(unittest.TestCase):
    """Verify deprecated shim modules have been removed."""

    DEPRECATED_FILES = [
        os.path.join(SRC_DIR, "utils", "system.py"),
        os.path.join(SRC_DIR, "utils", "hardware.py"),
        os.path.join(SRC_DIR, "utils", "bluetooth.py"),
        os.path.join(SRC_DIR, "utils", "disk.py"),
        os.path.join(SRC_DIR, "utils", "temperature.py"),
        os.path.join(SRC_DIR, "utils", "processes.py"),
        os.path.join(SRC_DIR, "utils", "services.py"),
        os.path.join(SRC_DIR, "utils", "hardware_profiles.py"),
        os.path.join(SRC_DIR, "services", "system", "process.py"),
    ]

    def test_deprecated_shim_files_removed(self):
        for filepath in self.DEPRECATED_FILES:
            self.assertFalse(
                os.path.exists(filepath),
                f"Deprecated shim still exists: {filepath}",
            )

    def test_no_production_imports_from_deprecated_modules(self):
        """Scan production code for imports from removed shim modules."""
        deprecated_patterns = [
            re.compile(r"from\s+utils\.system\s+import"),
            re.compile(r"from\s+utils\.hardware\s+import"),
            re.compile(r"from\s+utils\.bluetooth\s+import"),
            re.compile(r"from\s+utils\.disk\s+import"),
            re.compile(r"from\s+utils\.temperature\s+import"),
            re.compile(r"from\s+utils\.processes\s+import"),
            re.compile(r"from\s+utils\.services\s+import"),
            re.compile(r"from\s+utils\.hardware_profiles\s+import"),
        ]

        violations = []
        for root, dirs, files in os.walk(SRC_DIR):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        for pattern in deprecated_patterns:
                            if pattern.search(line):
                                rel = os.path.relpath(fpath, PROJECT_ROOT)
                                violations.append(f"{rel}:{lineno}: {line.strip()}")

        self.assertEqual(
            violations, [],
            "Production code still imports from deprecated modules:\n"
            + "\n".join(violations),
        )


class TestServicesLayerImports(unittest.TestCase):
    """Verify that canonical imports from the services layer work."""

    def test_import_system_manager(self):
        from services.system import SystemManager
        self.assertIsNotNone(SystemManager)

    def test_import_service_manager(self):
        from services.system import ServiceManager
        self.assertIsNotNone(ServiceManager)

    def test_import_process_manager(self):
        from services.system import ProcessManager
        self.assertIsNotNone(ProcessManager)

    def test_import_hardware_manager(self):
        from services.hardware import HardwareManager
        self.assertIsNotNone(HardwareManager)

    def test_import_bluetooth_manager(self):
        from services.hardware import BluetoothManager
        self.assertIsNotNone(BluetoothManager)

    def test_import_disk_manager(self):
        from services.hardware import DiskManager
        self.assertIsNotNone(DiskManager)

    def test_import_temperature_manager(self):
        from services.hardware import TemperatureManager
        self.assertIsNotNone(TemperatureManager)

    def test_import_detect_hardware_profile(self):
        from services.hardware.hardware_profiles import detect_hardware_profile
        self.assertTrue(callable(detect_hardware_profile))


class TestSetStyleSheetElimination(unittest.TestCase):
    """Verify inline setStyleSheet calls have been migrated to QSS."""

    def test_setstylesheet_only_in_main_window(self):
        """Only main_window.py should contain setStyleSheet (global theme loader)."""
        ui_dir = os.path.join(SRC_DIR, "ui")
        offenders = []

        for root, dirs, files in os.walk(ui_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if "setStyleSheet" in line:
                            rel = os.path.relpath(fpath, SRC_DIR)
                            offenders.append((rel, lineno, line.strip()))

        # Filter: only main_window.py should have setStyleSheet
        non_main = [
            f"{rel}:{lineno}: {line}"
            for rel, lineno, line in offenders
            if os.path.basename(rel) != "main_window.py"
        ]
        self.assertEqual(
            non_main, [],
            "setStyleSheet found outside main_window.py:\n" + "\n".join(non_main),
        )

    def test_setstylesheet_total_count(self):
        """Total setStyleSheet calls across all UI files should be <= 1."""
        ui_dir = os.path.join(SRC_DIR, "ui")
        count = 0

        for root, dirs, files in os.walk(ui_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", errors="ignore") as f:
                    for line in f:
                        if "setStyleSheet" in line:
                            count += 1

        self.assertLessEqual(
            count, 1,
            f"Expected at most 1 setStyleSheet call in ui/, found {count}",
        )


class TestQSSMigration(unittest.TestCase):
    """Verify QSS files contain v39.0 Prism sections."""

    def test_modern_qss_has_prism_sections(self):
        qss_path = os.path.join(SRC_DIR, "assets", "modern.qss")
        self.assertTrue(os.path.exists(qss_path), "modern.qss not found")
        with open(qss_path, "r") as f:
            content = f.read()
        self.assertIn("/* v39.0 Prism", content)

    def test_light_qss_has_prism_sections(self):
        qss_path = os.path.join(SRC_DIR, "assets", "light.qss")
        self.assertTrue(os.path.exists(qss_path), "light.qss not found")
        with open(qss_path, "r") as f:
            content = f.read()
        self.assertIn("/* v39.0 Prism", content)


if __name__ == "__main__":
    unittest.main()
