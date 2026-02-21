"""Tests for core.plugins.compat — CompatibilityDetector.

All system I/O is mocked at the private method level:
  - _read_fedora_version  (file read)
  - _read_desktop_env     (env var read)
  - _check_package        (subprocess rpm -q)

No real filesystem, subprocess, or environment access occurs.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from core.plugins.compat import CompatibilityDetector
from core.plugins.metadata import CompatStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detector(fedora_ver: int = 40, de: str = "gnome", is_wayland: bool = False):
    """Return a CompatibilityDetector with all private I/O pre-mocked."""
    det = CompatibilityDetector()
    det._read_fedora_version = MagicMock(return_value=fedora_ver)
    det._read_desktop_env = MagicMock(return_value=de)
    det._check_package = MagicMock(return_value=True)
    # Populate cache so public methods return mocked values without calling I/O
    det._cache["fedora_version"] = fedora_ver
    det._cache["desktop_env"] = de
    det._cache["is_wayland"] = is_wayland
    return det


# ---------------------------------------------------------------------------
# Public API surface tests (no system calls)
# ---------------------------------------------------------------------------

class TestCompatibilityDetectorPublicAPI:
    """Verify public accessor methods read from cache and never re-call I/O."""

    def test_fedora_version_returns_cached_value(self):
        """fedora_version() returns the value stored in _cache without I/O."""
        det = CompatibilityDetector()
        det._cache["fedora_version"] = 42
        assert det.fedora_version() == 42

    def test_fedora_version_calls_private_on_cache_miss(self):
        """fedora_version() calls _read_fedora_version when cache is empty."""
        det = CompatibilityDetector()
        det._read_fedora_version = MagicMock(return_value=39)
        result = det.fedora_version()
        assert result == 39
        det._read_fedora_version.assert_called_once()

    def test_fedora_version_does_not_call_private_on_cache_hit(self):
        """fedora_version() must not call _read_fedora_version if already cached."""
        det = CompatibilityDetector()
        det._cache["fedora_version"] = 41
        det._read_fedora_version = MagicMock(return_value=99)
        _ = det.fedora_version()
        det._read_fedora_version.assert_not_called()

    def test_desktop_environment_returns_cached_value(self):
        """desktop_environment() returns the value stored in _cache."""
        det = CompatibilityDetector()
        det._cache["desktop_env"] = "kde"
        assert det.desktop_environment() == "kde"

    def test_is_wayland_returns_cached_bool(self):
        """is_wayland() returns the bool stored in _cache."""
        det = CompatibilityDetector()
        det._cache["is_wayland"] = True
        assert det.is_wayland() is True

    def test_is_wayland_reads_env_var_on_cache_miss(self):
        """is_wayland() inspects WAYLAND_DISPLAY when cache is empty."""
        det = CompatibilityDetector()
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}):
            result = det.is_wayland()
        assert result is True

    def test_is_wayland_false_when_env_absent(self):
        """is_wayland() returns False when WAYLAND_DISPLAY is not set."""
        det = CompatibilityDetector()
        env_copy = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"}
        with patch.dict(os.environ, env_copy, clear=True):
            result = det.is_wayland()
        assert result is False

    def test_has_package_calls_check_package_on_cache_miss(self):
        """has_package() calls _check_package on first call for each package."""
        det = CompatibilityDetector()
        det._check_package = MagicMock(return_value=True)
        result = det.has_package("vim")
        assert result is True
        det._check_package.assert_called_once_with("vim")

    def test_has_package_caches_result(self):
        """has_package() does not call _check_package a second time."""
        det = CompatibilityDetector()
        det._check_package = MagicMock(return_value=False)
        det.has_package("vim")
        det.has_package("vim")
        det._check_package.assert_called_once_with("vim")


# ---------------------------------------------------------------------------
# _read_fedora_version private method
# ---------------------------------------------------------------------------

class TestReadFedoraVersion:
    """Tests for CompatibilityDetector._read_fedora_version()."""

    def test_parses_version_from_fedora_release_file(self):
        """Parses integer version from '/etc/fedora-release' content."""
        det = CompatibilityDetector()
        fake_content = "Fedora release 41 (Forty One)\n"
        with patch("builtins.open", MagicMock(
            return_value=MagicMock(
                __enter__=lambda s: s,
                __exit__=MagicMock(return_value=False),
                read=lambda: fake_content,
            )
        )):
            result = det._read_fedora_version()
        assert result == 41

    def test_returns_zero_when_file_missing(self):
        """Returns 0 when /etc/fedora-release raises OSError."""
        det = CompatibilityDetector()
        with patch("builtins.open", side_effect=OSError("no file")):
            result = det._read_fedora_version()
        assert result == 0

    def test_returns_zero_when_content_has_no_version(self):
        """Returns 0 when file content does not contain 'release <N>'."""
        det = CompatibilityDetector()
        fake_content = "Not a Fedora file\n"
        with patch("builtins.open", MagicMock(
            return_value=MagicMock(
                __enter__=lambda s: s,
                __exit__=MagicMock(return_value=False),
                read=lambda: fake_content,
            )
        )):
            result = det._read_fedora_version()
        assert result == 0


# ---------------------------------------------------------------------------
# _read_desktop_env private method
# ---------------------------------------------------------------------------

class TestReadDesktopEnv:
    """Tests for CompatibilityDetector._read_desktop_env()."""

    def test_gnome_detected_from_xdg(self):
        """XDG_CURRENT_DESKTOP=GNOME maps to 'gnome'."""
        det = CompatibilityDetector()
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}):
            assert det._read_desktop_env() == "gnome"

    def test_kde_detected_from_plasma(self):
        """XDG_CURRENT_DESKTOP=KDE:Plasma maps to 'kde'."""
        det = CompatibilityDetector()
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE:Plasma"}):
            assert det._read_desktop_env() == "kde"

    def test_xfce_detected(self):
        """XDG_CURRENT_DESKTOP=XFCE maps to 'xfce'."""
        det = CompatibilityDetector()
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "XFCE"}):
            assert det._read_desktop_env() == "xfce"

    def test_other_for_unrecognised_de(self):
        """Unrecognised but present XDG_CURRENT_DESKTOP maps to 'other'."""
        det = CompatibilityDetector()
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "sway"}):
            assert det._read_desktop_env() == "other"

    def test_unknown_when_env_absent(self):
        """Absent XDG_CURRENT_DESKTOP maps to 'unknown'."""
        det = CompatibilityDetector()
        env_copy = {k: v for k, v in os.environ.items() if k != "XDG_CURRENT_DESKTOP"}
        with patch.dict(os.environ, env_copy, clear=True):
            assert det._read_desktop_env() == "unknown"


# ---------------------------------------------------------------------------
# _check_package private method
# ---------------------------------------------------------------------------

class TestCheckPackage:
    """Tests for CompatibilityDetector._check_package()."""

    def test_returns_true_when_rpm_exits_zero(self):
        """Returns True when rpm -q exits with code 0."""
        det = CompatibilityDetector()
        mock_result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = det._check_package("vim-enhanced")
        assert result is True
        mock_run.assert_called_once_with(
            ["rpm", "-q", "vim-enhanced"],
            capture_output=True, timeout=5
        )

    def test_returns_false_when_rpm_exits_nonzero(self):
        """Returns False when rpm -q exits with non-zero code."""
        det = CompatibilityDetector()
        mock_result = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            result = det._check_package("nonexistent-package")
        assert result is False

    def test_returns_false_on_os_error(self):
        """Returns False when subprocess.run raises OSError."""
        det = CompatibilityDetector()
        with patch("subprocess.run", side_effect=OSError("rpm not found")):
            result = det._check_package("vim")
        assert result is False

    def test_returns_false_on_timeout(self):
        """Returns False when subprocess.run raises TimeoutExpired."""
        import subprocess
        det = CompatibilityDetector()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["rpm"], 5)):
            result = det._check_package("slow-package")
        assert result is False


# ---------------------------------------------------------------------------
# check_plugin_compat — the main public integration method
# ---------------------------------------------------------------------------

class TestCheckPluginCompat:
    """Tests for CompatibilityDetector.check_plugin_compat()."""

    def test_empty_spec_always_compatible(self):
        """An empty compat spec produces a compatible CompatStatus."""
        det = _detector(fedora_ver=40, de="gnome", is_wayland=False)
        status = det.check_plugin_compat({})
        assert status.compatible is True
        assert status.reason == ""

    # --- min_fedora ---

    def test_min_fedora_passes_when_version_meets_requirement(self):
        """min_fedora=38 passes when running Fedora 40."""
        det = _detector(fedora_ver=40)
        status = det.check_plugin_compat({"min_fedora": 38})
        assert status.compatible is True

    def test_min_fedora_passes_when_version_exactly_matches(self):
        """min_fedora=40 passes when running Fedora 40."""
        det = _detector(fedora_ver=40)
        status = det.check_plugin_compat({"min_fedora": 40})
        assert status.compatible is True

    def test_min_fedora_fails_when_version_too_low(self):
        """min_fedora=42 fails when running Fedora 40."""
        det = _detector(fedora_ver=40)
        status = det.check_plugin_compat({"min_fedora": 42})
        assert status.compatible is False
        assert "42" in status.reason
        assert "40" in status.reason

    def test_min_fedora_zero_does_not_gate(self):
        """min_fedora=0 (default) never blocks compatibility."""
        det = _detector(fedora_ver=0)
        status = det.check_plugin_compat({"min_fedora": 0})
        assert status.compatible is True

    # --- de filter ---

    def test_de_filter_passes_for_matching_de(self):
        """de=['gnome','kde'] passes when running GNOME."""
        det = _detector(de="gnome")
        status = det.check_plugin_compat({"de": ["gnome", "kde"]})
        assert status.compatible is True

    def test_de_filter_fails_for_non_matching_de(self):
        """de=['gnome'] fails when running KDE."""
        det = _detector(de="kde")
        status = det.check_plugin_compat({"de": ["gnome"]})
        assert status.compatible is False
        assert "gnome" in status.reason

    def test_de_empty_list_allows_all_des(self):
        """de=[] does not gate on desktop environment."""
        det = _detector(de="xfce")
        status = det.check_plugin_compat({"de": []})
        assert status.compatible is True

    # --- wayland_only ---

    def test_wayland_only_passes_on_wayland(self):
        """wayland_only=True passes when is_wayland is True."""
        det = _detector(is_wayland=True)
        status = det.check_plugin_compat({"wayland_only": True})
        assert status.compatible is True

    def test_wayland_only_fails_on_x11(self):
        """wayland_only=True fails when is_wayland is False."""
        det = _detector(is_wayland=False)
        status = det.check_plugin_compat({"wayland_only": True})
        assert status.compatible is False
        assert "Wayland" in status.reason

    # --- x11_only ---

    def test_x11_only_passes_on_x11(self):
        """x11_only=True passes when is_wayland is False."""
        det = _detector(is_wayland=False)
        status = det.check_plugin_compat({"x11_only": True})
        assert status.compatible is True

    def test_x11_only_fails_on_wayland(self):
        """x11_only=True fails when is_wayland is True."""
        det = _detector(is_wayland=True)
        status = det.check_plugin_compat({"x11_only": True})
        assert status.compatible is False
        assert "X11" in status.reason

    # --- requires_packages ---

    def test_requires_packages_all_present_no_warnings(self):
        """requires_packages with all installed packages yields no warnings."""
        det = _detector()
        det._check_package = MagicMock(return_value=True)
        # Rebuild cache keys for packages
        det._cache["pkg:vim"] = True
        det._cache["pkg:git"] = True

        status = det.check_plugin_compat({"requires_packages": ["vim", "git"]})
        assert status.compatible is True
        assert status.warnings == []

    def test_requires_packages_missing_package_adds_warning(self):
        """Missing package adds warning but does not mark incompatible."""
        det = _detector()
        det._cache["pkg:missing-pkg"] = False

        status = det.check_plugin_compat({"requires_packages": ["missing-pkg"]})
        assert status.compatible is True
        assert len(status.warnings) == 1
        assert "missing-pkg" in status.warnings[0]

    def test_requires_packages_multiple_missing_all_warned(self):
        """Each missing package produces its own warning entry."""
        det = _detector()
        det._cache["pkg:pkg-a"] = False
        det._cache["pkg:pkg-b"] = False

        status = det.check_plugin_compat({"requires_packages": ["pkg-a", "pkg-b"]})
        assert status.compatible is True
        assert len(status.warnings) == 2

    # --- precedence / short-circuit ---

    def test_min_fedora_checked_before_de(self):
        """min_fedora failure returns before checking DE."""
        det = _detector(fedora_ver=38, de="gnome")
        status = det.check_plugin_compat({"min_fedora": 42, "de": ["kde"]})
        # Should fail on fedora version, not DE
        assert status.compatible is False
        assert "42" in status.reason

    def test_compat_status_type_is_compat_status(self):
        """check_plugin_compat always returns a CompatStatus instance."""
        det = _detector()
        result = det.check_plugin_compat({})
        assert isinstance(result, CompatStatus)
