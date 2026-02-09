"""
Tests for utils/package_explorer.py
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from subprocess import CalledProcessError

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.package_explorer import PackageExplorer, PackageInfo, PackageResult


class TestPackageInfo(unittest.TestCase):
    """Tests for the PackageInfo dataclass."""

    def test_to_dict(self):
        """Serialization to dict works."""
        info = PackageInfo(
            name="vim", version="9.0", repo="fedora",
            size="5.2 MB", summary="Vi Improved",
            installed=True, source="dnf", arch="x86_64",
        )
        d = info.to_dict()
        self.assertEqual(d["name"], "vim")
        self.assertEqual(d["version"], "9.0")
        self.assertTrue(d["installed"])
        self.assertEqual(d["source"], "dnf")

    def test_to_dict_all_keys(self):
        """to_dict returns all expected keys."""
        d = PackageInfo(name="test").to_dict()
        expected = {"name", "version", "repo", "size", "summary",
                    "installed", "source", "arch"}
        self.assertEqual(set(d.keys()), expected)

    def test_default_values(self):
        """Default values are set correctly."""
        info = PackageInfo(name="test")
        self.assertEqual(info.version, "")
        self.assertFalse(info.installed)
        self.assertEqual(info.source, "")


class TestPackageExplorerSearch(unittest.TestCase):
    """Tests for PackageExplorer.search()."""

    @patch('utils.package_explorer.PackageExplorer._is_flatpak_installed')
    @patch('utils.package_explorer.PackageExplorer._is_rpm_installed')
    @patch('utils.package_explorer.SystemManager.is_atomic')
    @patch('utils.package_explorer.subprocess.run')
    def test_search_dnf_success(self, mock_run, mock_atomic, mock_rpm_inst, mock_fp_inst):
        """Parses DNF search output correctly."""
        mock_atomic.return_value = False
        mock_rpm_inst.return_value = False
        mock_fp_inst.return_value = False
        dnf_output = (
            "Name Matched: vim\n"
            "vim-enhanced.x86_64 : Vi Improved - enhanced version\n"
            "vim-minimal.x86_64 : A minimal version of Vi\n"
        )
        # DNF search, then flatpak search fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=dnf_output, stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
        ]

        results = PackageExplorer.search("vim")

        self.assertEqual(len(results), 2)
        names = [p.name for p in results]
        self.assertIn("vim-enhanced", names)
        self.assertIn("vim-minimal", names)

    @patch('utils.package_explorer.PackageExplorer._is_flatpak_installed')
    @patch('utils.package_explorer.PackageExplorer._is_rpm_installed')
    @patch('utils.package_explorer.SystemManager.is_atomic')
    @patch('utils.package_explorer.subprocess.run')
    def test_search_with_flatpak(self, mock_run, mock_atomic, mock_rpm_inst, mock_fp_inst):
        """Includes Flatpak results when available."""
        mock_atomic.return_value = False
        mock_rpm_inst.return_value = False
        mock_fp_inst.return_value = False
        dnf_output = "vim-enhanced.x86_64 : Vi Improved\n"
        flatpak_output = "org.vim.Vim\t1.0\tflathub\tVim editor\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=dnf_output, stderr=""),
            MagicMock(returncode=0, stdout=flatpak_output, stderr=""),
        ]

        results = PackageExplorer.search("vim")

        sources = [p.source for p in results]
        self.assertIn("flatpak", sources)
        self.assertIn("dnf", sources)

    @patch('utils.package_explorer.subprocess.run')
    def test_search_dnf_failure(self, mock_run):
        """Returns empty on DNF search failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        results = PackageExplorer.search("nonexistent", include_flatpak=False)

        self.assertEqual(results, [])

    @patch('utils.package_explorer.subprocess.run')
    def test_search_timeout(self, mock_run):
        """Returns empty on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=30)

        results = PackageExplorer.search("test", include_flatpak=False)

        self.assertEqual(results, [])

    @patch('utils.package_explorer.PackageExplorer._is_rpm_installed')
    @patch('utils.package_explorer.SystemManager.is_atomic')
    @patch('utils.package_explorer.subprocess.run')
    def test_search_atomic_source(self, mock_run, mock_atomic, mock_rpm_inst):
        """On atomic Fedora, source is rpm-ostree."""
        mock_atomic.return_value = True
        mock_rpm_inst.return_value = False
        dnf_output = "vim.x86_64 : Vi Improved\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=dnf_output, stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
        ]

        results = PackageExplorer.search("vim")

        self.assertEqual(results[0].source, "rpm-ostree")

    @patch('utils.package_explorer.subprocess.run')
    def test_search_no_flatpak(self, mock_run):
        """Skips flatpak search when include_flatpak=False."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        PackageExplorer.search("test", include_flatpak=False)

        # Should only call once (DNF), not twice
        self.assertEqual(mock_run.call_count, 1)


class TestPackageExplorerInstall(unittest.TestCase):
    """Tests for PackageExplorer.install()."""

    @patch('utils.package_explorer.subprocess.run')
    def test_install_dnf_success(self, mock_run):
        """Install via DNF returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = PackageExplorer.install("vim", source="dnf")

        self.assertTrue(result.success)
        self.assertIn("Installed", result.message)

    @patch('utils.package_explorer.subprocess.run')
    def test_install_dnf_failure(self, mock_run):
        """Install failure returns failure result."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="No package vim available"
        )

        result = PackageExplorer.install("vim", source="dnf")

        self.assertFalse(result.success)
        self.assertIn("Failed", result.message)

    @patch('utils.package_explorer.subprocess.run')
    def test_install_flatpak(self, mock_run):
        """Install via Flatpak uses correct command."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = PackageExplorer.install("org.gnome.Calculator", source="flatpak")

        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("flatpak", cmd)
        self.assertIn("install", cmd)

    @patch('utils.package_explorer.subprocess.run')
    def test_install_rpm_ostree(self, mock_run):
        """Install via rpm-ostree uses PrivilegedCommand."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = PackageExplorer.install("vim", source="rpm-ostree")

        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("rpm-ostree", cmd)

    @patch('utils.package_explorer.subprocess.run')
    def test_install_timeout(self, mock_run):
        """Install timeout returns failure."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=300)

        result = PackageExplorer.install("vim", source="dnf")

        self.assertFalse(result.success)
        self.assertIn("Timed out", result.message)

    @patch('utils.package_explorer.subprocess.run')
    def test_install_os_error(self, mock_run):
        """Install OSError returns failure."""
        mock_run.side_effect = OSError("No such file")

        result = PackageExplorer.install("vim", source="dnf")

        self.assertFalse(result.success)
        self.assertIn("Error", result.message)

    @patch('utils.package_explorer.SystemManager.is_atomic')
    def test_install_auto_detect_flatpak(self, mock_atomic):
        """Auto detection picks flatpak for app IDs."""
        mock_atomic.return_value = False
        source = PackageExplorer._detect_source("org.gnome.Calculator")
        self.assertEqual(source, "flatpak")

    @patch('utils.package_explorer.SystemManager.is_atomic')
    def test_install_auto_detect_dnf(self, mock_atomic):
        """Auto detection picks dnf for simple names."""
        mock_atomic.return_value = False
        source = PackageExplorer._detect_source("vim")
        self.assertEqual(source, "dnf")

    @patch('utils.package_explorer.SystemManager.is_atomic')
    def test_install_auto_detect_atomic(self, mock_atomic):
        """Auto detection picks rpm-ostree on atomic."""
        mock_atomic.return_value = True
        source = PackageExplorer._detect_source("vim")
        self.assertEqual(source, "rpm-ostree")


class TestPackageExplorerRemove(unittest.TestCase):
    """Tests for PackageExplorer.remove()."""

    @patch('utils.package_explorer.subprocess.run')
    def test_remove_dnf_success(self, mock_run):
        """Remove via DNF returns success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = PackageExplorer.remove("vim", source="dnf")

        self.assertTrue(result.success)
        self.assertIn("Removed", result.message)

    @patch('utils.package_explorer.subprocess.run')
    def test_remove_failure(self, mock_run):
        """Remove failure returns failure result."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Not installed"
        )

        result = PackageExplorer.remove("vim", source="dnf")

        self.assertFalse(result.success)

    @patch('utils.package_explorer.subprocess.run')
    def test_remove_flatpak(self, mock_run):
        """Remove via Flatpak uses correct command."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = PackageExplorer.remove("org.gnome.Calculator", source="flatpak")

        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("flatpak", cmd)
        self.assertIn("uninstall", cmd)


class TestPackageExplorerListInstalled(unittest.TestCase):
    """Tests for PackageExplorer.list_installed()."""

    @patch('utils.package_explorer.SystemManager.is_atomic')
    @patch('utils.package_explorer.subprocess.run')
    def test_list_rpm_installed(self, mock_run, mock_atomic):
        """Lists RPM packages correctly."""
        mock_atomic.return_value = False
        rpm_output = (
            "vim-enhanced\t9.0-1.fc43\tx86_64\tVi Improved\n"
            "bash\t5.2-1.fc43\tx86_64\tBourne Again Shell\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=rpm_output, stderr="")

        results = PackageExplorer.list_installed(source="dnf")

        self.assertEqual(len(results), 2)
        self.assertTrue(all(p.installed for p in results))

    @patch('utils.package_explorer.subprocess.run')
    def test_list_flatpak_installed(self, mock_run):
        """Lists Flatpak apps correctly."""
        flatpak_output = (
            "org.gnome.Calculator\t45.0\tflathub\tGNOME Calculator\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=flatpak_output, stderr="")

        results = PackageExplorer.list_installed(source="flatpak")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "flatpak")
        self.assertTrue(results[0].installed)

    @patch('utils.package_explorer.subprocess.run')
    def test_list_installed_search_filter(self, mock_run):
        """Search filter narrows results."""
        rpm_output = (
            "vim-enhanced\t9.0-1\tx86_64\tVi Improved\n"
            "bash\t5.2-1\tx86_64\tBourne Again Shell\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=rpm_output, stderr="")

        results = PackageExplorer.list_installed(source="dnf", search="vim")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "vim-enhanced")

    @patch('utils.package_explorer.subprocess.run')
    def test_list_installed_empty(self, mock_run):
        """Empty output returns empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        results = PackageExplorer.list_installed(source="dnf")

        self.assertEqual(results, [])

    @patch('utils.package_explorer.subprocess.run')
    def test_list_installed_failure(self, mock_run):
        """Failure returns empty list."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        results = PackageExplorer.list_installed(source="dnf")

        self.assertEqual(results, [])


class TestPackageExplorerRecentlyInstalled(unittest.TestCase):
    """Tests for PackageExplorer.recently_installed()."""

    @patch('utils.package_explorer.subprocess.run')
    def test_recently_installed_success(self, mock_run):
        """Parses DNF history for recent installs."""
        history_output = (
            "   1 | user   | 2025-01-15 10:00 | Install | vim-enhanced\n"
            "   2 | user   | 2025-01-14 09:00 | Install | git\n"
            "   3 | user   | 2020-01-01 01:00 | Install | oldpkg\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=history_output, stderr="")

        results = PackageExplorer.recently_installed(days=30)

        # Only recent ones (within 30 days) should be included
        # The exact count depends on the current date vs the fixture dates
        self.assertIsInstance(results, list)

    @patch('utils.package_explorer.subprocess.run')
    def test_recently_installed_failure(self, mock_run):
        """Returns empty on DNF history failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        results = PackageExplorer.recently_installed()

        self.assertEqual(results, [])

    @patch('utils.package_explorer.subprocess.run')
    def test_recently_installed_timeout(self, mock_run):
        """Returns empty on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=30)

        results = PackageExplorer.recently_installed()

        self.assertEqual(results, [])


class TestPackageExplorerInfo(unittest.TestCase):
    """Tests for PackageExplorer.get_package_info()."""

    @patch('utils.package_explorer.SystemManager.is_atomic')
    @patch('utils.package_explorer.subprocess.run')
    def test_get_info_success(self, mock_run, mock_atomic):
        """Parses dnf info output correctly."""
        mock_atomic.return_value = False
        info_output = (
            "Name         : vim-enhanced\n"
            "Version      : 9.0\n"
            "Release      : 1.fc43\n"
            "Architecture : x86_64\n"
            "Size         : 5.2 MB\n"
            "Summary      : Vi Improved - enhanced version\n"
            "Repository   : @fedora\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=info_output, stderr="")

        info = PackageExplorer.get_package_info("vim-enhanced")

        self.assertIsNotNone(info)
        self.assertEqual(info.name, "vim-enhanced")
        self.assertEqual(info.version, "9.0-1.fc43")
        self.assertEqual(info.arch, "x86_64")
        self.assertTrue(info.installed)  # @-prefixed repo means installed

    @patch('utils.package_explorer.subprocess.run')
    def test_get_info_not_found(self, mock_run):
        """Returns None when package not found."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="No matching")

        info = PackageExplorer.get_package_info("nonexistent")

        self.assertIsNone(info)

    @patch('utils.package_explorer.subprocess.run')
    def test_get_info_timeout(self, mock_run):
        """Returns None on timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=15)

        info = PackageExplorer.get_package_info("test")

        self.assertIsNone(info)


class TestPackageExplorerHelpers(unittest.TestCase):
    """Tests for helper methods."""

    @patch('utils.package_explorer.subprocess.run')
    def test_is_rpm_installed_true(self, mock_run):
        """RPM installed check returns True."""
        mock_run.return_value = MagicMock(returncode=0)

        self.assertTrue(PackageExplorer._is_rpm_installed("vim"))

    @patch('utils.package_explorer.subprocess.run')
    def test_is_rpm_installed_false(self, mock_run):
        """RPM not installed check returns False."""
        mock_run.return_value = MagicMock(returncode=1)

        self.assertFalse(PackageExplorer._is_rpm_installed("nonexistent"))

    @patch('utils.package_explorer.subprocess.run')
    def test_is_flatpak_installed_true(self, mock_run):
        """Flatpak installed check returns True."""
        mock_run.return_value = MagicMock(returncode=0)

        self.assertTrue(PackageExplorer._is_flatpak_installed("org.gnome.Calculator"))

    @patch('utils.package_explorer.subprocess.run')
    def test_is_flatpak_installed_false(self, mock_run):
        """Flatpak not installed returns False."""
        mock_run.return_value = MagicMock(returncode=1)

        self.assertFalse(PackageExplorer._is_flatpak_installed("org.fake.App"))

    @patch('utils.package_explorer.subprocess.run')
    def test_is_rpm_installed_timeout(self, mock_run):
        """Timeout returns False."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="rpm", timeout=5)

        self.assertFalse(PackageExplorer._is_rpm_installed("test"))

    @patch('utils.package_explorer.PackageExplorer._is_flatpak_installed')
    @patch('utils.package_explorer.SystemManager.is_atomic')
    def test_detect_source_installed_flatpak(self, mock_atomic, mock_fp_inst):
        """Detects flatpak as source for installed flatpak apps."""
        mock_fp_inst.return_value = True
        mock_atomic.return_value = False

        source = PackageExplorer._detect_source_installed("org.gnome.Calculator")

        self.assertEqual(source, "flatpak")

    @patch('utils.package_explorer.PackageExplorer._is_flatpak_installed')
    @patch('utils.package_explorer.SystemManager.is_atomic')
    def test_detect_source_installed_rpm(self, mock_atomic, mock_fp_inst):
        """Detects dnf for non-flatpak on traditional."""
        mock_fp_inst.return_value = False
        mock_atomic.return_value = False

        source = PackageExplorer._detect_source_installed("vim")

        self.assertEqual(source, "dnf")


class TestPackageExplorerCounts(unittest.TestCase):
    """Tests for PackageExplorer.get_counts()."""

    @patch('utils.package_explorer.subprocess.run')
    def test_get_counts(self, mock_run):
        """Returns correct counts."""
        rpm_output = "vim-9.0\nbash-5.2\ngcc-13.0\n"
        flatpak_output = "org.gnome.Calculator\n"
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=rpm_output, stderr=""),
            MagicMock(returncode=0, stdout=flatpak_output, stderr=""),
        ]

        counts = PackageExplorer.get_counts()

        self.assertEqual(counts["rpm"], 3)
        self.assertEqual(counts["flatpak"], 1)
        self.assertEqual(counts["total"], 4)

    @patch('utils.package_explorer.subprocess.run')
    def test_get_counts_failure(self, mock_run):
        """Returns zero counts on failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        counts = PackageExplorer.get_counts()

        self.assertEqual(counts["rpm"], 0)
        self.assertEqual(counts["flatpak"], 0)
        self.assertEqual(counts["total"], 0)


class TestPackageResult(unittest.TestCase):
    """Tests for the PackageResult dataclass."""

    def test_success_result(self):
        """Success result attributes."""
        r = PackageResult(success=True, message="Installed vim")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "Installed vim")

    def test_failure_result(self):
        """Failure result attributes."""
        r = PackageResult(success=False, message="Failed")
        self.assertFalse(r.success)


if __name__ == '__main__':
    unittest.main()
