"""Tests for utils/ansible_export.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.ansible_export import AnsibleExporter, Result


class TestResult(unittest.TestCase):
    """Tests for the Result dataclass."""

    def test_result_success_defaults(self):
        """Result with success=True has expected defaults."""
        r = Result(success=True, message="ok")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "ok")
        self.assertIsNone(r.data)

    def test_result_failure_with_data(self):
        """Result can carry arbitrary data dict."""
        r = Result(success=False, message="err", data={"key": "val"})
        self.assertFalse(r.success)
        self.assertEqual(r.data, {"key": "val"})

    def test_result_data_field_optional(self):
        """Result data field defaults to None when not provided."""
        r = Result(True, "msg")
        self.assertIsNone(r.data)


class TestAnsibleExporter(unittest.TestCase):
    """Coverage tests for Ansible playbook export module."""

    # ── _get_installed_packages ──────────────────────────────────────────

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_filters_base_packages(self, mock_run, mock_atomic):
        """Installed package list excludes base/system packages."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="kernel-core\nvim\nglibc-common\nhtop\n",
        )
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, ["vim", "htop"])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=True)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_atomic_path(self, mock_run, mock_atomic):
        """Atomic path parses rpm-ostree JSON and filters excluded prefixes."""
        data = {
            "deployments": [
                {
                    "requested-packages": [
                        "vim",
                        "htop",
                        "kernel-tools",
                        "dnf-plugins-core",
                        "fedora-release",
                        "systemd-container",
                        "rpm-build",
                        "glibc-langpack-en",
                        "neovim",
                    ]
                }
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(data),
        )
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, ["vim", "htop", "neovim"])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=True)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_atomic_empty_deployments(
        self, mock_run, mock_atomic
    ):
        """Atomic path with no deployments returns empty list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"deployments": []}),
        )
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=True)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_atomic_nonzero_returncode(
        self, mock_run, mock_atomic
    ):
        """Atomic path with non-zero return code returns empty list."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=True)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_atomic_exception(self, mock_run, mock_atomic):
        """Atomic path exception returns empty list."""
        mock_run.side_effect = subprocess.SubprocessError("timeout")
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_nonatomic_nonzero_returncode(
        self, mock_run, mock_atomic
    ):
        """Non-atomic path with non-zero return code returns empty list."""
        mock_run.return_value = MagicMock(returncode=1, stdout="error")
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_nonatomic_empty_stdout(self, mock_run, mock_atomic):
        """Non-atomic path with empty stdout returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_nonatomic_whitespace_only(
        self, mock_run, mock_atomic
    ):
        """Non-atomic path with whitespace-only stdout returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="  \n  \n  ")
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_nonatomic_exception(self, mock_run, mock_atomic):
        """Non-atomic path exception returns empty list."""
        mock_run.side_effect = OSError("No such file")
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_installed_packages_nonatomic_all_excluded(self, mock_run, mock_atomic):
        """Non-atomic path where all packages match excluded prefixes returns empty list."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="kernel-core\nglibc-common\nsystemd-libs\ndnf-data\nrpm-libs\nfedora-release\n",
        )
        packages = AnsibleExporter._get_installed_packages()
        self.assertEqual(packages, [])

    # ── _get_flatpak_apps ────────────────────────────────────────────────

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/flatpak")
    def test_get_flatpak_apps_success(self, mock_which, mock_run):
        """Flatpak app listing parses app IDs."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="org.foo.App\norg.bar.Tool\n"
        )
        apps = AnsibleExporter._get_flatpak_apps()
        self.assertEqual(apps, ["org.foo.App", "org.bar.Tool"])
        mock_which.assert_called_once_with("flatpak")

    @patch("utils.ansible_export.shutil.which", return_value=None)
    def test_get_flatpak_apps_missing_binary(self, mock_which):
        """Flatpak listing is empty when tool is missing."""
        self.assertEqual(AnsibleExporter._get_flatpak_apps(), [])

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/flatpak")
    def test_get_flatpak_apps_nonzero_returncode(self, mock_which, mock_run):
        """Flatpak listing returns empty list on non-zero return code."""
        mock_run.return_value = MagicMock(returncode=1, stdout="error output")
        apps = AnsibleExporter._get_flatpak_apps()
        self.assertEqual(apps, [])

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/flatpak")
    def test_get_flatpak_apps_subprocess_exception(self, mock_which, mock_run):
        """Flatpak listing returns empty list on subprocess exception."""
        mock_run.side_effect = subprocess.SubprocessError("flatpak crashed")
        apps = AnsibleExporter._get_flatpak_apps()
        self.assertEqual(apps, [])

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/flatpak")
    def test_get_flatpak_apps_empty_stdout(self, mock_which, mock_run):
        """Flatpak listing with empty stdout returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        apps = AnsibleExporter._get_flatpak_apps()
        self.assertEqual(apps, [])

    # ── _get_gnome_settings ──────────────────────────────────────────────

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/gsettings")
    def test_get_gnome_settings_collects_only_successful_keys(
        self, mock_which, mock_run
    ):
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

    @patch("utils.ansible_export.shutil.which", return_value=None)
    def test_get_gnome_settings_missing_binary(self, mock_which):
        """GNOME settings returns empty dict when gsettings not installed."""
        settings = AnsibleExporter._get_gnome_settings()
        self.assertEqual(settings, {})

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/gsettings")
    def test_get_gnome_settings_per_key_exception(self, mock_which, mock_run):
        """GNOME settings skips keys that raise exceptions and continues."""
        mock_run.side_effect = [
            subprocess.SubprocessError("gsettings timeout"),  # gtk-theme
            MagicMock(returncode=0, stdout="'Papirus'\n"),  # icon-theme
            OSError("broken"),  # cursor-theme
            MagicMock(returncode=0, stdout="'prefer-dark'\n"),  # color-scheme
            MagicMock(returncode=1, stdout=""),  # font-name
            MagicMock(returncode=1, stdout=""),  # monospace-font-name
            MagicMock(returncode=1, stdout=""),  # button-layout
        ]
        settings = AnsibleExporter._get_gnome_settings()
        self.assertNotIn("org.gnome.desktop.interface/gtk-theme", settings)
        self.assertIn("org.gnome.desktop.interface/icon-theme", settings)
        self.assertNotIn("org.gnome.desktop.interface/cursor-theme", settings)
        self.assertIn("org.gnome.desktop.interface/color-scheme", settings)
        self.assertEqual(len(settings), 2)

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/gsettings")
    def test_get_gnome_settings_all_keys_succeed(self, mock_which, mock_run):
        """GNOME settings collects all 7 keys when all succeed."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="'Adwaita'\n"),
            MagicMock(returncode=0, stdout="'Adwaita'\n"),
            MagicMock(returncode=0, stdout="'default'\n"),
            MagicMock(returncode=0, stdout="'default'\n"),
            MagicMock(returncode=0, stdout="'Cantarell 11'\n"),
            MagicMock(returncode=0, stdout="'Source Code Pro 10'\n"),
            MagicMock(returncode=0, stdout="'appmenu:close'\n"),
        ]
        settings = AnsibleExporter._get_gnome_settings()
        self.assertEqual(len(settings), 7)
        self.assertIn("org.gnome.desktop.wm.preferences/button-layout", settings)

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/gsettings")
    def test_get_gnome_settings_strips_quotes(self, mock_which, mock_run):
        """GNOME settings strips surrounding single quotes from values."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="'Adwaita-dark'\n"),
        ] + [MagicMock(returncode=1, stdout="")] * 6
        settings = AnsibleExporter._get_gnome_settings()
        self.assertEqual(
            settings["org.gnome.desktop.interface/gtk-theme"], "Adwaita-dark"
        )

    # ── _get_enabled_repos ───────────────────────────────────────────────

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_enabled_repos_skips_fedora_defaults(self, mock_run, mock_atomic):
        """Enabled repos include only non-default repositories."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="repo id repo name\nfedora Fedora\nupdates Updates\nrpmfusion-free RPM Fusion Free\n",
        )
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, ["rpmfusion-free"])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=True)
    def test_get_enabled_repos_atomic_returns_empty(self, mock_atomic):
        """Atomic systems return empty repo list."""
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_enabled_repos_nonzero_returncode(self, mock_run, mock_atomic):
        """Non-atomic path with non-zero return code returns empty list."""
        mock_run.return_value = MagicMock(returncode=1, stdout="error")
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_enabled_repos_exception(self, mock_run, mock_atomic):
        """Repos exception returns empty list."""
        mock_run.side_effect = OSError("dnf not found")
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_enabled_repos_all_defaults(self, mock_run, mock_atomic):
        """Repos list is empty when only default fedora/updates repos are present."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="repo id repo name\nfedora Fedora 43\nupdates Fedora Updates\nupdates-testing Testing\n",
        )
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, [])

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_enabled_repos_multiple_third_party(self, mock_run, mock_atomic):
        """Multiple non-default repos are all included."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="repo id repo name\nfedora Fedora\nrpmfusion-free Free\nrpmfusion-nonfree NonFree\ncopr-user-repo Custom\n",
        )
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(
            repos, ["rpmfusion-free", "rpmfusion-nonfree", "copr-user-repo"]
        )

    @patch("utils.ansible_export.SystemManager.is_atomic", return_value=False)
    @patch("utils.ansible_export.subprocess.run")
    def test_get_enabled_repos_empty_stdout(self, mock_run, mock_atomic):
        """Empty stdout from dnf repolist returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        repos = AnsibleExporter._get_enabled_repos()
        self.assertEqual(repos, [])

    # ── generate_playbook ────────────────────────────────────────────────

    @patch(
        "utils.ansible_export.AnsibleExporter._get_gnome_settings",
        return_value={"org.gnome.desktop.interface/gtk-theme": "Adwaita-dark"},
    )
    @patch(
        "utils.ansible_export.AnsibleExporter._get_flatpak_apps",
        return_value=["org.foo.App"],
    )
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages",
        return_value=["vim", "htop"],
    )
    def test_generate_playbook_includes_sections(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Generated playbook includes package, flatpak, and setting tasks."""
        content = AnsibleExporter.generate_playbook()
        self.assertIn("Install user packages", content)
        self.assertIn("Install Flatpak apps", content)
        self.assertIn("Set gtk-theme", content)

    @patch("utils.ansible_export.AnsibleExporter._get_enabled_repos", return_value=[])
    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages", return_value=[]
    )
    def test_generate_playbook_all_disabled(
        self, mock_pkgs, mock_flatpaks, mock_settings, mock_repos
    ):
        """Playbook with all include flags False produces no task content."""
        content = AnsibleExporter.generate_playbook(
            include_packages=False,
            include_flatpaks=False,
            include_settings=False,
            include_repos=False,
        )
        self.assertIn("GENERATED BY LOOFI", content)
        self.assertNotIn("Install user packages", content)
        self.assertNotIn("Install Flatpak apps", content)
        # Should not call any data-gathering methods when disabled
        mock_pkgs.assert_not_called()
        mock_flatpaks.assert_not_called()
        mock_settings.assert_not_called()

    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages", return_value=[]
    )
    def test_generate_playbook_empty_data_skips_sections(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Playbook with empty packages/flatpaks/settings skips those task sections."""
        content = AnsibleExporter.generate_playbook()
        self.assertNotIn("Install user packages", content)
        self.assertNotIn("Install Flatpak apps", content)
        self.assertNotIn("Enable Flathub", content)

    @patch(
        "utils.ansible_export.AnsibleExporter._get_enabled_repos",
        return_value=["rpmfusion-free"],
    )
    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages", return_value=[]
    )
    def test_generate_playbook_with_repos(
        self, mock_pkgs, mock_flatpaks, mock_settings, mock_repos
    ):
        """Playbook with include_repos=True does not crash (repos aren't in tasks but vars)."""
        content = AnsibleExporter.generate_playbook(include_repos=True)
        # Should not crash; repos section doesn't create tasks in current implementation
        self.assertIn("GENERATED BY LOOFI", content)

    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages",
        return_value=["vim"],
    )
    def test_generate_playbook_custom_name(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Playbook uses custom playbook_name in header and play name."""
        content = AnsibleExporter.generate_playbook(playbook_name="My Custom Setup")
        self.assertIn("My Custom Setup", content)

    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages",
        return_value=["vim"],
    )
    def test_generate_playbook_header_contains_warning(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Playbook header contains safety warning and usage instructions."""
        content = AnsibleExporter.generate_playbook()
        self.assertIn("WARNING", content)
        self.assertIn("ansible-playbook site.yml", content)
        self.assertIn("REVIEW", content)

    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch(
        "utils.ansible_export.AnsibleExporter._get_flatpak_apps",
        return_value=["org.foo.Bar"],
    )
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages",
        return_value=["vim", "htop"],
    )
    def test_generate_playbook_vars_section(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Generated playbook includes vars for packages and flatpaks."""
        content = AnsibleExporter.generate_playbook()
        self.assertIn("vim", content)
        self.assertIn("htop", content)
        self.assertIn("org.foo.Bar", content)

    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages",
        return_value=["vim"],
    )
    def test_generate_playbook_yaml_import_fallback(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Playbook falls back to JSON when yaml module is unavailable."""
        import importlib
        import utils.ansible_export as mod

        original_generate = AnsibleExporter.generate_playbook.__func__

        # Patch the yaml import inside generate_playbook by temporarily removing yaml
        real_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            content = AnsibleExporter.generate_playbook()

        # JSON fallback should produce valid JSON content after the header
        self.assertIn("GENERATED BY LOOFI", content)
        # The content should still have the playbook structure
        self.assertIn("vim", content)

    @patch("utils.ansible_export.AnsibleExporter._get_gnome_settings", return_value={})
    @patch(
        "utils.ansible_export.AnsibleExporter._get_flatpak_apps",
        return_value=["org.foo.App"],
    )
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages", return_value=[]
    )
    def test_generate_playbook_flatpak_enables_flathub(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Playbook with flatpaks includes Enable Flathub task."""
        content = AnsibleExporter.generate_playbook()
        self.assertIn("Enable Flathub", content)
        self.assertIn("flathub.org", content)

    @patch(
        "utils.ansible_export.AnsibleExporter._get_gnome_settings",
        return_value={
            "org.gnome.desktop.interface/gtk-theme": "Adwaita",
            "org.gnome.desktop.interface/icon-theme": "Papirus",
        },
    )
    @patch("utils.ansible_export.AnsibleExporter._get_flatpak_apps", return_value=[])
    @patch(
        "utils.ansible_export.AnsibleExporter._get_installed_packages", return_value=[]
    )
    def test_generate_playbook_settings_create_dconf_tasks(
        self, mock_pkgs, mock_flatpaks, mock_settings
    ):
        """Each GNOME setting creates a separate dconf task."""
        content = AnsibleExporter.generate_playbook()
        self.assertIn("Set gtk-theme", content)
        self.assertIn("Set icon-theme", content)

    # ── save_playbook ────────────────────────────────────────────────────

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        return_value="---\n- name: demo\n",
    )
    def test_save_playbook_success_creates_files(self, mock_generate):
        """Save playbook writes site.yml and README.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "bundle" / "site.yml"
            result = AnsibleExporter.save_playbook(path=out_path)
            self.assertTrue(result.success)
            self.assertTrue(out_path.exists())
            self.assertTrue((out_path.parent / "README.md").exists())

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        side_effect=Exception("boom"),
    )
    def test_save_playbook_failure(self, mock_generate):
        """Save playbook returns failure object when generation fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "site.yml"
            result = AnsibleExporter.save_playbook(path=out_path)
            self.assertFalse(result.success)
            self.assertIn("failed", result.message.lower())

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        return_value="---\n- name: test\n",
    )
    @patch("utils.ansible_export.Path.home")
    def test_save_playbook_default_path(self, mock_home, mock_generate):
        """Save playbook uses ~/loofi-playbook/site.yml when no path given."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)
            result = AnsibleExporter.save_playbook()
            self.assertTrue(result.success)
            expected_path = Path(temp_dir) / "loofi-playbook" / "site.yml"
            self.assertTrue(expected_path.exists())
            self.assertIn("loofi-playbook", result.data["path"])

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        return_value="---\n- name: test\n",
    )
    def test_save_playbook_result_data_fields(self, mock_generate):
        """Save playbook result includes path and readme in data dict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "site.yml"
            result = AnsibleExporter.save_playbook(path=out_path)
            self.assertTrue(result.success)
            self.assertIn("path", result.data)
            self.assertIn("readme", result.data)
            self.assertEqual(result.data["path"], str(out_path))

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        return_value="---\n- name: test\n",
    )
    def test_save_playbook_readme_content(self, mock_generate):
        """Save playbook creates README with usage instructions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "site.yml"
            AnsibleExporter.save_playbook(path=out_path)
            readme = (Path(temp_dir) / "README.md").read_text()
            self.assertIn("Loofi Fedora Configuration Playbook", readme)
            self.assertIn("ansible-playbook site.yml", readme)
            self.assertIn("community.general", readme)
            self.assertIn("Requirements", readme)

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        return_value="---\n- name: test\n",
    )
    def test_save_playbook_creates_parent_dirs(self, mock_generate):
        """Save playbook creates nested parent directories for custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "deep" / "nested" / "dir" / "site.yml"
            result = AnsibleExporter.save_playbook(path=out_path)
            self.assertTrue(result.success)
            self.assertTrue(out_path.exists())

    @patch(
        "utils.ansible_export.AnsibleExporter.generate_playbook",
        return_value="---\n- name: test\n",
    )
    def test_save_playbook_writes_content(self, mock_generate):
        """Save playbook writes the generated content to the file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "site.yml"
            AnsibleExporter.save_playbook(path=out_path)
            content = out_path.read_text()
            self.assertEqual(content, "---\n- name: test\n")

    # ── validate_playbook ────────────────────────────────────────────────

    @patch("utils.ansible_export.shutil.which", return_value=None)
    def test_validate_playbook_yaml_syntax_ok_without_ansible_lint(self, mock_which):
        """Without ansible-lint, YAML syntax validation or unavailable message is returned."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "site.yml"
            path.write_text("---\n- hosts: localhost\n", encoding="utf-8")
            result = AnsibleExporter.validate_playbook(path)
            self.assertTrue(result.success)
            msg = result.message.lower()
            self.assertTrue(
                "yaml syntax is valid" in msg or "unable to validate" in msg,
                f"Unexpected message: {result.message}",
            )

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/ansible-lint")
    def test_validate_playbook_ansible_lint_failure(self, mock_which, mock_run):
        """ansible-lint non-zero return is reported as validation issues."""
        mock_run.return_value = MagicMock(returncode=2, stdout="line too long")
        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertFalse(result.success)
        self.assertIn("validation issues", result.message.lower())

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/ansible-lint")
    def test_validate_playbook_ansible_lint_success(self, mock_which, mock_run):
        """ansible-lint success (returncode=0) reports passed validation."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertTrue(result.success)
        self.assertIn("passed", result.message.lower())

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/ansible-lint")
    def test_validate_playbook_ansible_lint_exception(self, mock_which, mock_run):
        """ansible-lint exception returns failure result."""
        mock_run.side_effect = subprocess.SubprocessError("lint crashed")
        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertFalse(result.success)
        self.assertIn("validation failed", result.message.lower())

    @patch("utils.ansible_export.shutil.which", return_value=None)
    def test_validate_playbook_invalid_yaml(self, mock_which):
        """Invalid YAML returns syntax error when yaml module is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "site.yml"
            path.write_text("---\n  bad:\n    - indentation: [\n", encoding="utf-8")
            result = AnsibleExporter.validate_playbook(path)
            # If yaml module is available, it should catch the error
            # If yaml module is not available, it returns "unable to validate"
            if "unable to validate" not in result.message.lower():
                self.assertFalse(result.success)
                self.assertIn("yaml syntax error", result.message.lower())

    @patch("builtins.__import__")
    @patch("utils.ansible_export.shutil.which", return_value=None)
    def test_validate_playbook_no_yaml_no_lint(self, mock_which, mock_import):
        """Without yaml AND ansible-lint, returns unable-to-validate message."""
        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("no yaml")
            return original_import(name, *args, **kwargs)

        mock_import.side_effect = fake_import

        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertTrue(result.success)
        self.assertIn("unable to validate", result.message.lower())

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/ansible-lint")
    def test_validate_playbook_ansible_lint_includes_stdout(self, mock_which, mock_run):
        """ansible-lint failure includes stdout in the message."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="WARNING: some lint warning\nERROR: bad task"
        )
        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertFalse(result.success)
        self.assertIn("bad task", result.message)

    @patch("utils.ansible_export.subprocess.run")
    @patch("utils.ansible_export.shutil.which", return_value="/usr/bin/ansible-lint")
    def test_validate_playbook_ansible_lint_timeout(self, mock_which, mock_run):
        """ansible-lint timeout exception returns failure."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ansible-lint", timeout=60)
        result = AnsibleExporter.validate_playbook(Path("/tmp/site.yml"))
        self.assertFalse(result.success)
        self.assertIn("validation failed", result.message.lower())


if __name__ == "__main__":
    unittest.main()
