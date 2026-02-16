"""Tests for utils/wizard_health.py."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.wizard_health import WizardHealth


class TestWizardHealth(unittest.TestCase):
    """WizardHealth checks."""

    @patch('utils.wizard_health.subprocess.run')
    @patch('utils.wizard_health.shutil.which')
    @patch('utils.wizard_health.SystemManager.get_package_manager', return_value='dnf')
    @patch('utils.wizard_health.os.statvfs')
    def test_run_health_checks_dnf_healthy(self, mock_statvfs, _mock_pm, mock_which, mock_run):
        """DNF path should mark package state healthy when duplicates check succeeds."""
        mock_statvfs.return_value = MagicMock(
            f_bavail=30 * 1024**3,
            f_frsize=1,
            f_blocks=100 * 1024**3,
        )

        def which_side_effect(name):
            if name in {'dnf', 'firewall-cmd', 'timeshift'}:
                return f'/usr/bin/{name}'
            return None

        mock_which.side_effect = which_side_effect
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=''),
            MagicMock(returncode=0, stdout='running\n'),
            MagicMock(returncode=0, stdout='Enforcing\n'),
        ]

        checks, results = WizardHealth.run_health_checks()

        self.assertTrue(results.get('pkg_healthy'))
        self.assertTrue(results.get('firewall_running'))
        self.assertEqual(results.get('backup_tool'), 'timeshift')
        self.assertEqual(results.get('selinux'), 'Enforcing')
        self.assertTrue(any('Package state healthy' in c[1] for c in checks))

    @patch('utils.wizard_health.subprocess.run')
    @patch('utils.wizard_health.shutil.which', return_value=None)
    @patch('utils.wizard_health.SystemManager.get_package_manager', return_value='dnf')
    @patch('utils.wizard_health.os.statvfs')
    def test_run_health_checks_dnf_missing(self, mock_statvfs, _mock_pm, _mock_which, mock_run):
        """Missing dnf should produce info status instead of failure."""
        mock_statvfs.return_value = MagicMock(
            f_bavail=20 * 1024**3,
            f_frsize=1,
            f_blocks=100 * 1024**3,
        )
        mock_run.return_value = MagicMock(returncode=0, stdout='Permissive\n')

        checks, results = WizardHealth.run_health_checks()

        self.assertTrue(any('DNF not found' in c[1] for c in checks))
        self.assertNotIn('pkg_healthy', results)

    @patch('utils.wizard_health.subprocess.run')
    @patch('utils.wizard_health.shutil.which', return_value=None)
    @patch('utils.wizard_health.SystemManager.get_package_manager', return_value='rpm-ostree')
    @patch('utils.wizard_health.os.statvfs')
    def test_run_health_checks_ostree(self, mock_statvfs, _mock_pm, _mock_which, mock_run):
        """rpm-ostree path should use status check and set pkg_healthy."""
        mock_statvfs.return_value = MagicMock(
            f_bavail=20 * 1024**3,
            f_frsize=1,
            f_blocks=100 * 1024**3,
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout='State: idle\n'),
            MagicMock(returncode=0, stdout='Enforcing\n'),
        ]

        checks, results = WizardHealth.run_health_checks()

        self.assertTrue(results.get('pkg_healthy'))
        self.assertTrue(any('rpm-ostree status' in c[1] for c in checks))

    @patch('utils.wizard_health.subprocess.run', side_effect=FileNotFoundError('getenforce'))
    @patch('utils.wizard_health.shutil.which', return_value=None)
    @patch('utils.wizard_health.SystemManager.get_package_manager', return_value='dnf')
    @patch('utils.wizard_health.os.statvfs', side_effect=OSError('bad stat'))
    def test_run_health_checks_handles_disk_and_selinux_errors(
        self,
        _mock_statvfs,
        _mock_pm,
        _mock_which,
        _mock_run,
    ):
        """Errors should map to unknown statuses, not exceptions."""
        checks, _results = WizardHealth.run_health_checks()
        texts = [c[1] for c in checks]

        self.assertIn('Could not check disk space', texts)
        self.assertIn('Could not check SELinux', texts)


if __name__ == '__main__':
    unittest.main()
