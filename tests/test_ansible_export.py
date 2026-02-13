"""Tests for utils/ansible_export.py."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.ansible_export import AnsibleExporter


class TestAnsibleExporter(unittest.TestCase):
    """Coverage tests for Ansible playbook export module."""

    @patch('utils.ansible_export.subprocess.run')
    def test_get_installed_packages_filters_base_packages(self, mock_run):
        """Installed package list excludes base/system packages."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="kernel-core\nvim\nglibc-common\nhtop\n",
        )
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, ["vim", "htop"])

    @patch('utils.ansible_export.subprocess.run')
    @patch('utils.ansible_export.shutil.which', return_value='/usr/bin/flatpak')
    def test_get_flatpak_apps_success(self, mock_which, mock_run):
        """Flatpak app listing parses app IDs."""
        mock_run.return_value = MagicMock(returncode=0, stdout="org.foo.App\norg.bar.Tool\n")
        apps = AnsibleExporter._get_flatpak_apps()
        self.assertEqual(apps, ["org.foo.App", "org.bar.Tool"])
        mock_which.assert_called_once_with("flatpak")

    @patch('utils.ansible_export.shutil.which', return_value=None)
    def test_get_flatpak_apps_missing_binary(self, mock_which):
        """Flatpak listing is empty when tool is missing."""
        self.assertEqual(AnsibleExporter._get_flatpak_apps(), [])

    @patch('utils.ansible_export.subprocess.run')
    @patch('utils.ansible_export.shutil.which', return_value='/usr/bin/gsettings')
    def test_get_gnome_settings_collects_only_successful_keys(self, mock_which, mock_run):
        """GNOME settings parser keeps only successful lookups."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="'Adwaita-dark'\n"),
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=0, stdout="'Bibata'\n"),
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout=""),
        ]
        settings = AnsibleExporter._get_gnome_settings()
        self.assertIn("org.gnome.desktop.interface/gtk-theme", settings)
        self.assertIn("org.gnome.desktop.interface/cursor-theme", settings)
        self.assertNotIn("org.gnome.desktop.interface/icon-theme", settings)

    @patch('utils.ansible_export.subprocess.run')
    def test_get_enabled_repos_skips_fedora_defaults(self, mock_run):
        """Enabled repos include only non-default repositories."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="repo id repo name\nfedora Fedora\nupdates Updates\nrpmfusion-free RPM Fusion Free\n",
        )
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, ["rpmfusion-free"])

    @patch('utils.ansible_export.AnsibleExporter._get_gnome_settings', return_value={"org.gnome.desktop.interface/gtk-theme": "Adwaita-dark"})
    @patch('utils.ansible_export.AnsibleExporter._get_flatpak_apps', return_value=['org.foo.App'])
    @patch('utils.ansible_export.AnsibleExporter._get_installed_packages', return_value=['vim', 'htop'])
    def test_generate_playbook_includes_sections(self, mock_pkgs, mock_flatpaks, mock_settings):
        """Generated playbook includes package, flatpak, and setting tasks."""
        content = AnsibleExporter.generate_playbook()
        self.assertIn("Install user packages", content)
        self.assertIn("Install Flatpak apps", content)
        self.assertIn("Set gtk-theme", content)

    @patch('utils.ansible_export.AnsibleExporter.generate_playbook', return_value='---\n- name: demo\n')
    def test_save_playbook_success_creates_files(self, mock_generate):
        """Save playbook writes site.yml and README.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "bundle" / "site.yml"
            result = AnsibleExporter.save_playbook(path=out_path)
            self.assertTrue(result.success)
            self.assertTrue(out_path.exists())
            self.assertTrue((out_path.parent / "README.md").exists())

    @patch('utils.ansible_export.AnsibleExporter.generate_playbook', side_effect=Exception('boom'))
    def test_save_playbook_failure(self, mock_generate):
        """Save playbook returns failure object when generation fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "site.yml"
            result = AnsibleExporter.save_playbook(path=out_path)
            self.assertFalse(result.success)
            self.assertIn("failed", result.message.lower())

    @patch('utils.ansible_export.shutil.which', return_value=None)
    def test_validate_playbook_yaml_syntax_ok_without_ansible_lint(self, mock_which):
        """Without ansible-lint, YAML syntax validation or unavailable message is returned."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "site.yml"
            path.write_text("---\n- hosts: localhost\n", encoding='utf-8')
            result = AnsibleExporter.validate_playbook(path)
            self.assertTrue(result.success)
            msg = result.message.lower()
            self.assertTrue(
                "yaml syntax is valid" in msg or "unable to validate" in msg,
                f"Unexpected message: {result.message}"
            )

    @patch('utils.ansible_export.subprocess.run')
    @patch('utils.ansible_export.shutil.which', return_value='/usr/bin/ansible-lint')
    def test_validate_playbook_ansible_lint_failure(self, mock_which, mock_run):
        """ansible-lint non-zero return is reported as validation issues."""
        mock_run.return_value = MagicMock(returncode=2, stdout="line too long")
        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertFalse(result.success)
        self.assertIn("validation issues", result.message.lower())


if __name__ == '__main__':
    unittest.main()
