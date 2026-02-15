"""Tests for utils.battery — deprecated backward compatibility shim."""

import os
import sys
import unittest
import warnings
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


class TestBatteryShim(unittest.TestCase):
    """Tests for the deprecated utils.battery shim module."""

    @patch.dict(sys.modules, {"services.hardware.battery": MagicMock()})
    def test_import_emits_deprecation_warning(self):
        """Importing utils.battery should emit a DeprecationWarning."""
        # Remove cached module to force re-import
        sys.modules.pop("utils.battery", None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import utils.battery  # noqa: F401

            sys.modules.pop("utils.battery", None)

        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        self.assertGreaterEqual(len(deprecation_warnings), 1)
        self.assertIn("deprecated", str(deprecation_warnings[0].message).lower())

    @patch.dict(sys.modules, {"services.hardware.battery": MagicMock()})
    def test_exports_battery_manager(self):
        """The shim should re-export BatteryManager."""
        sys.modules.pop("utils.battery", None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import utils.battery

            self.assertIn("BatteryManager", utils.battery.__all__)
            sys.modules.pop("utils.battery", None)


if __name__ == "__main__":
    unittest.main()
