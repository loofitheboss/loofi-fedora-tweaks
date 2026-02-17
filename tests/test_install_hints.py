"""Tests for utils/install_hints.py."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.install_hints import build_install_hint


class TestInstallHints(unittest.TestCase):
    """Test package-manager-aware install hints."""

    @patch("utils.install_hints.SystemManager.get_package_manager", return_value="dnf")
    def test_build_install_hint_dnf(self, mock_pm):
        hint = build_install_hint("vim")
        self.assertEqual(hint, "Install with: pkexec dnf install vim")

    @patch("utils.install_hints.SystemManager.get_package_manager", return_value="rpm-ostree")
    def test_build_install_hint_rpm_ostree(self, mock_pm):
        hint = build_install_hint("vim")
        self.assertEqual(hint, "Install with: pkexec rpm-ostree install vim")
