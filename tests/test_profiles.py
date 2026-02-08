"""
Tests for utils/profiles.py — System Profiles Manager.
Covers: built-in profiles, custom CRUD, apply with mocked subprocess,
governor, services, swappiness, active profile tracking, capture.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add source path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.profiles import ProfileManager
from utils.containers import Result


# ---------------------------------------------------------------------------
# TestBuiltinProfiles — verify built-in profile definitions
# ---------------------------------------------------------------------------

class TestBuiltinProfiles(unittest.TestCase):
    """Tests for built-in profile definitions."""

    def test_five_builtin_profiles_exist(self):
        """All five expected built-in profiles are defined."""
        expected = {"gaming", "development", "battery_saver", "presentation", "server"}
        self.assertEqual(set(ProfileManager.BUILTIN_PROFILES.keys()), expected)

    def test_gaming_profile_has_required_fields(self):
        """Gaming profile has name, description, icon, and settings."""
        profile = ProfileManager.BUILTIN_PROFILES["gaming"]
        self.assertEqual(profile["name"], "Gaming")
        self.assertIn("description", profile)
        self.assertIn("icon", profile)
        self.assertIn("settings", profile)

    def test_gaming_profile_settings(self):
        """Gaming profile has the correct performance settings."""
        settings = ProfileManager.BUILTIN_PROFILES["gaming"]["settings"]
        self.assertEqual(settings["governor"], "performance")
        self.assertEqual(settings["compositor"], "disabled")
        self.assertEqual(settings["notifications"], "dnd")
        self.assertEqual(settings["swappiness"], 10)
        self.assertTrue(settings["gamemode"])

    def test_development_profile_settings(self):
        """Development profile enables docker and podman."""
        settings = ProfileManager.BUILTIN_PROFILES["development"]["settings"]
        self.assertEqual(settings["governor"], "schedutil")
        self.assertIn("docker", settings["services_enable"])
        self.assertIn("podman", settings["services_enable"])

    def test_battery_saver_profile_settings(self):
        """Battery saver uses powersave governor and high swappiness."""
        settings = ProfileManager.BUILTIN_PROFILES["battery_saver"]["settings"]
        self.assertEqual(settings["governor"], "powersave")
        self.assertEqual(settings["swappiness"], 60)
        self.assertIn("bluetooth", settings["services_disable"])

    def test_presentation_profile_settings(self):
        """Presentation profile disables screen timeout and DND."""
        settings = ProfileManager.BUILTIN_PROFILES["presentation"]["settings"]
        self.assertEqual(settings["governor"], "performance")
        self.assertEqual(settings["notifications"], "dnd")
        self.assertEqual(settings["screen_timeout"], 0)

    def test_server_profile_settings(self):
        """Server profile uses performance governor and disables compositor."""
        settings = ProfileManager.BUILTIN_PROFILES["server"]["settings"]
        self.assertEqual(settings["governor"], "performance")
        self.assertEqual(settings["compositor"], "disabled")
        self.assertEqual(settings["swappiness"], 10)

    def test_all_profiles_have_services_lists(self):
        """Every built-in profile has services_enable and services_disable keys."""
        for key, profile in ProfileManager.BUILTIN_PROFILES.items():
            settings = profile["settings"]
            self.assertIn("services_enable", settings, f"{key} missing services_enable")
            self.assertIn("services_disable", settings, f"{key} missing services_disable")


# ---------------------------------------------------------------------------
# TestListProfiles — listing built-in and custom profiles
# ---------------------------------------------------------------------------

class TestListProfiles(unittest.TestCase):
    """Tests for listing profiles."""

    def test_list_profiles_includes_builtins(self):
        """list_profiles returns at least the 5 built-in profiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                profiles = ProfileManager.list_profiles()
                names = [p["name"] for p in profiles]
                self.assertIn("Gaming", names)
                self.assertIn("Development", names)
                self.assertIn("Battery Saver", names)
                self.assertIn("Presentation", names)
                self.assertIn("Server", names)
            finally:
                ProfileManager.PROFILES_DIR = original

    def test_list_profiles_builtin_flag(self):
        """Built-in profiles are flagged as builtin=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                profiles = ProfileManager.list_profiles()
                builtins = [p for p in profiles if p.get("builtin")]
                self.assertEqual(len(builtins), 5)
            finally:
                ProfileManager.PROFILES_DIR = original

    def test_list_profiles_includes_custom(self):
        """Custom profiles on disk appear in the listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_data = {"name": "My Profile", "description": "Test", "icon": "T", "settings": {}}
            with open(os.path.join(tmpdir, "my_profile.json"), "w") as f:
                json.dump(custom_data, f)

            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                profiles = ProfileManager.list_profiles()
                custom = [p for p in profiles if not p.get("builtin")]
                self.assertEqual(len(custom), 1)
                self.assertEqual(custom[0]["name"], "My Profile")
            finally:
                ProfileManager.PROFILES_DIR = original

    def test_list_profiles_skips_invalid_json(self):
        """Invalid JSON files in profiles dir are silently skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "broken.json"), "w") as f:
                f.write("not valid json{{{")

            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                profiles = ProfileManager.list_profiles()
                custom = [p for p in profiles if not p.get("builtin")]
                self.assertEqual(len(custom), 0)
            finally:
                ProfileManager.PROFILES_DIR = original

    def test_list_profiles_nonexistent_dir(self):
        """Nonexistent profiles directory returns only built-ins."""
        original = ProfileManager.PROFILES_DIR
        try:
            ProfileManager.PROFILES_DIR = "/nonexistent/path/profiles"
            profiles = ProfileManager.list_profiles()
            self.assertEqual(len(profiles), 5)  # only builtins
        finally:
            ProfileManager.PROFILES_DIR = original


# ---------------------------------------------------------------------------
# TestGetProfile — fetching individual profiles
# ---------------------------------------------------------------------------

class TestGetProfile(unittest.TestCase):
    """Tests for getting a single profile by key."""

    def test_get_builtin_profile(self):
        """Built-in profiles are returned correctly."""
        profile = ProfileManager.get_profile("gaming")
        self.assertEqual(profile["name"], "Gaming")
        self.assertTrue(profile["builtin"])
        self.assertIn("governor", profile["settings"])

    def test_get_nonexistent_profile(self):
        """Missing profile returns empty dict."""
        profile = ProfileManager.get_profile("nonexistent_xyz")
        self.assertEqual(profile, {})

    def test_get_custom_profile(self):
        """Custom profiles on disk are returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_data = {"name": "Custom", "description": "D", "icon": "C", "settings": {"governor": "ondemand"}}
            with open(os.path.join(tmpdir, "custom.json"), "w") as f:
                json.dump(custom_data, f)

            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                profile = ProfileManager.get_profile("custom")
                self.assertEqual(profile["name"], "Custom")
                self.assertFalse(profile["builtin"])
                self.assertEqual(profile["settings"]["governor"], "ondemand")
            finally:
                ProfileManager.PROFILES_DIR = original


# ---------------------------------------------------------------------------
# TestApplyProfile — applying profiles (mocked system calls)
# ---------------------------------------------------------------------------

class TestApplyProfile(unittest.TestCase):
    """Tests for applying profiles with mocked subprocess calls."""

    @patch.object(ProfileManager, '_save_active_profile')
    @patch.object(ProfileManager, '_set_swappiness', return_value=True)
    @patch.object(ProfileManager, '_toggle_services')
    @patch.object(ProfileManager, '_set_governor', return_value=True)
    def test_apply_gaming_profile_success(self, mock_gov, mock_svc, mock_swap, mock_save):
        """Gaming profile applies governor, services, and swappiness."""
        result = ProfileManager.apply_profile("gaming")
        self.assertTrue(result.success)
        mock_gov.assert_called_once_with("performance")
        mock_swap.assert_called_once_with(10)
        mock_svc.assert_called_once()
        mock_save.assert_called_once_with("gaming")

    @patch.object(ProfileManager, '_save_active_profile')
    @patch.object(ProfileManager, '_set_swappiness', return_value=False)
    @patch.object(ProfileManager, '_toggle_services')
    @patch.object(ProfileManager, '_set_governor', return_value=True)
    def test_apply_profile_swappiness_failure(self, mock_gov, mock_svc, mock_swap, mock_save):
        """Profile apply reports swappiness failure."""
        result = ProfileManager.apply_profile("gaming")
        self.assertFalse(result.success)
        self.assertIn("swappiness", result.message)

    @patch.object(ProfileManager, '_save_active_profile')
    @patch.object(ProfileManager, '_toggle_services')
    @patch.object(ProfileManager, '_set_governor', return_value=False)
    def test_apply_profile_governor_failure(self, mock_gov, mock_svc, mock_save):
        """Profile apply reports governor failure."""
        result = ProfileManager.apply_profile("development")
        self.assertFalse(result.success)
        self.assertIn("governor", result.message)

    def test_apply_nonexistent_profile(self):
        """Applying a nonexistent profile returns failure."""
        result = ProfileManager.apply_profile("does_not_exist")
        self.assertFalse(result.success)
        self.assertIn("not found", result.message)

    @patch.object(ProfileManager, '_save_active_profile')
    @patch.object(ProfileManager, '_toggle_services')
    @patch.object(ProfileManager, '_set_governor', return_value=True)
    def test_apply_presentation_no_swappiness(self, mock_gov, mock_svc, mock_save):
        """Presentation profile does not set swappiness (not in settings)."""
        result = ProfileManager.apply_profile("presentation")
        self.assertTrue(result.success)
        mock_gov.assert_called_once_with("performance")


# ---------------------------------------------------------------------------
# TestCreateCustomProfile — custom profile creation
# ---------------------------------------------------------------------------

class TestCreateCustomProfile(unittest.TestCase):
    """Tests for creating custom profiles."""

    def test_create_custom_profile_success(self):
        """Creating a custom profile writes JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                result = ProfileManager.create_custom_profile(
                    "My Gaming",
                    {"governor": "performance", "swappiness": 5},
                )
                self.assertTrue(result.success)

                filepath = os.path.join(tmpdir, "my_gaming.json")
                self.assertTrue(os.path.isfile(filepath))

                with open(filepath) as f:
                    data = json.load(f)
                self.assertEqual(data["name"], "My Gaming")
                self.assertEqual(data["settings"]["governor"], "performance")
            finally:
                ProfileManager.PROFILES_DIR = original

    def test_create_custom_profile_empty_name(self):
        """Empty name is rejected."""
        result = ProfileManager.create_custom_profile("", {"governor": "performance"})
        self.assertFalse(result.success)

    def test_create_custom_profile_whitespace_name(self):
        """Whitespace-only name is rejected."""
        result = ProfileManager.create_custom_profile("   ", {})
        self.assertFalse(result.success)

    def test_create_cannot_overwrite_builtin(self):
        """Creating a profile with a built-in name is rejected."""
        result = ProfileManager.create_custom_profile("gaming", {"governor": "powersave"})
        self.assertFalse(result.success)
        self.assertIn("built-in", result.message)

    def test_create_custom_profile_with_description(self):
        """Custom profiles can include a description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                result = ProfileManager.create_custom_profile(
                    "Test Profile",
                    {"description": "A test", "governor": "schedutil"},
                )
                self.assertTrue(result.success)

                filepath = os.path.join(tmpdir, "test_profile.json")
                with open(filepath) as f:
                    data = json.load(f)
                self.assertEqual(data["description"], "A test")
            finally:
                ProfileManager.PROFILES_DIR = original


# ---------------------------------------------------------------------------
# TestDeleteCustomProfile — deleting custom profiles
# ---------------------------------------------------------------------------

class TestDeleteCustomProfile(unittest.TestCase):
    """Tests for deleting custom profiles."""

    def test_delete_custom_profile_success(self):
        """Deleting an existing custom profile removes the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "deletable.json")
            with open(filepath, "w") as f:
                json.dump({"name": "Deletable"}, f)

            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                result = ProfileManager.delete_custom_profile("deletable")
                self.assertTrue(result.success)
                self.assertFalse(os.path.isfile(filepath))
            finally:
                ProfileManager.PROFILES_DIR = original

    def test_delete_builtin_rejected(self):
        """Cannot delete built-in profiles."""
        result = ProfileManager.delete_custom_profile("gaming")
        self.assertFalse(result.success)
        self.assertIn("built-in", result.message)

    def test_delete_nonexistent_profile(self):
        """Deleting a nonexistent custom profile returns failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original = ProfileManager.PROFILES_DIR
            try:
                ProfileManager.PROFILES_DIR = tmpdir
                result = ProfileManager.delete_custom_profile("ghost")
                self.assertFalse(result.success)
                self.assertIn("not found", result.message)
            finally:
                ProfileManager.PROFILES_DIR = original


# ---------------------------------------------------------------------------
# TestActiveProfile — active profile tracking
# ---------------------------------------------------------------------------

class TestActiveProfile(unittest.TestCase):
    """Tests for active profile state tracking."""

    def test_get_active_profile_when_none(self):
        """Returns empty string when no state file exists."""
        original = ProfileManager.STATE_FILE
        try:
            ProfileManager.STATE_FILE = "/nonexistent/path/active.json"
            result = ProfileManager.get_active_profile()
            self.assertEqual(result, "")
        finally:
            ProfileManager.STATE_FILE = original

    def test_get_active_profile_reads_state(self):
        """Reads active profile from state file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"active_profile": "gaming"}, f)
            tmppath = f.name

        original = ProfileManager.STATE_FILE
        try:
            ProfileManager.STATE_FILE = tmppath
            result = ProfileManager.get_active_profile()
            self.assertEqual(result, "gaming")
        finally:
            ProfileManager.STATE_FILE = original
            os.unlink(tmppath)

    def test_save_active_profile(self):
        """_save_active_profile writes the state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "active.json")
            original = ProfileManager.STATE_FILE
            try:
                ProfileManager.STATE_FILE = state_path
                ProfileManager._save_active_profile("development")

                with open(state_path) as f:
                    data = json.load(f)
                self.assertEqual(data["active_profile"], "development")
            finally:
                ProfileManager.STATE_FILE = original

    def test_get_active_profile_corrupt_json(self):
        """Returns empty string when state file contains invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json{{{")
            tmppath = f.name

        original = ProfileManager.STATE_FILE
        try:
            ProfileManager.STATE_FILE = tmppath
            result = ProfileManager.get_active_profile()
            self.assertEqual(result, "")
        finally:
            ProfileManager.STATE_FILE = original
            os.unlink(tmppath)


# ---------------------------------------------------------------------------
# TestSetGovernor — CPU governor mocked subprocess
# ---------------------------------------------------------------------------

class TestSetGovernor(unittest.TestCase):
    """Tests for _set_governor with mocked system calls."""

    @patch('utils.profiles.subprocess.run')
    @patch('utils.profiles.shutil.which', return_value='/usr/bin/cpupower')
    def test_set_governor_success(self, mock_which, mock_run):
        """Governor is set when cpupower succeeds."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(ProfileManager._set_governor("performance"))
        mock_run.assert_called_once()

    @patch('utils.profiles.shutil.which', return_value=None)
    def test_set_governor_no_cpupower(self, mock_which):
        """Returns False when cpupower is not installed."""
        self.assertFalse(ProfileManager._set_governor("performance"))

    @patch('utils.profiles.subprocess.run')
    @patch('utils.profiles.shutil.which', return_value='/usr/bin/cpupower')
    def test_set_governor_failure(self, mock_which, mock_run):
        """Returns False when cpupower returns non-zero."""
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(ProfileManager._set_governor("invalid"))

    @patch('utils.profiles.subprocess.run', side_effect=OSError("exec failed"))
    @patch('utils.profiles.shutil.which', return_value='/usr/bin/cpupower')
    def test_set_governor_oserror(self, mock_which, mock_run):
        """Returns False on OSError."""
        self.assertFalse(ProfileManager._set_governor("performance"))


# ---------------------------------------------------------------------------
# TestToggleServices — service toggling
# ---------------------------------------------------------------------------

class TestToggleServices(unittest.TestCase):
    """Tests for _toggle_services with mocked systemctl."""

    @patch('utils.profiles.subprocess.run')
    def test_enable_services(self, mock_run):
        """Start is called for each enabled service."""
        mock_run.return_value = MagicMock(returncode=0)
        ProfileManager._toggle_services(["docker", "podman"], [])
        self.assertEqual(mock_run.call_count, 2)

    @patch('utils.profiles.subprocess.run')
    def test_disable_services(self, mock_run):
        """Stop is called for each disabled service."""
        mock_run.return_value = MagicMock(returncode=0)
        ProfileManager._toggle_services([], ["bluetooth", "tracker-miner-fs-3"])
        self.assertEqual(mock_run.call_count, 2)

    @patch('utils.profiles.subprocess.run')
    def test_toggle_both(self, mock_run):
        """Both enable and disable are processed."""
        mock_run.return_value = MagicMock(returncode=0)
        ProfileManager._toggle_services(["docker"], ["bluetooth"])
        self.assertEqual(mock_run.call_count, 2)

    @patch('utils.profiles.subprocess.run', side_effect=OSError("fail"))
    def test_toggle_services_error_handled(self, mock_run):
        """OSError during service toggle is caught gracefully."""
        ProfileManager._toggle_services(["docker"], ["bluetooth"])


# ---------------------------------------------------------------------------
# TestSetSwappiness — swappiness setting
# ---------------------------------------------------------------------------

class TestSetSwappiness(unittest.TestCase):
    """Tests for _set_swappiness with mocked sysctl."""

    @patch('utils.profiles.subprocess.run')
    def test_set_swappiness_success(self, mock_run):
        """Swappiness is set when sysctl succeeds."""
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(ProfileManager._set_swappiness(10))

    @patch('utils.profiles.subprocess.run')
    def test_set_swappiness_failure(self, mock_run):
        """Returns False when sysctl fails."""
        mock_run.return_value = MagicMock(returncode=1)
        self.assertFalse(ProfileManager._set_swappiness(60))

    def test_set_swappiness_out_of_range_high(self):
        """Rejects values above 100."""
        self.assertFalse(ProfileManager._set_swappiness(150))

    def test_set_swappiness_out_of_range_negative(self):
        """Rejects negative values."""
        self.assertFalse(ProfileManager._set_swappiness(-1))

    @patch('utils.profiles.subprocess.run', side_effect=OSError("fail"))
    def test_set_swappiness_oserror(self, mock_run):
        """Returns False on OSError."""
        self.assertFalse(ProfileManager._set_swappiness(10))


# ---------------------------------------------------------------------------
# TestSanitizeName — name sanitization
# ---------------------------------------------------------------------------

class TestSanitizeName(unittest.TestCase):
    """Tests for _sanitize_name helper."""

    def test_simple_name(self):
        """Simple names are lowercased with spaces replaced."""
        self.assertEqual(ProfileManager._sanitize_name("My Profile"), "my_profile")

    def test_path_traversal_stripped(self):
        """Path traversal characters are removed."""
        result = ProfileManager._sanitize_name("../../etc/passwd")
        self.assertNotIn("/", result)
        self.assertNotIn("..", result)

    def test_empty_name_fallback(self):
        """Empty string falls back to unnamed_profile."""
        self.assertEqual(ProfileManager._sanitize_name(""), "unnamed_profile")

    def test_backslash_stripped(self):
        """Backslashes are removed."""
        result = ProfileManager._sanitize_name("foo\\bar")
        self.assertNotIn("\\", result)


# ---------------------------------------------------------------------------
# TestCaptureCurrentAsProfile — current state capture
# ---------------------------------------------------------------------------

class TestCaptureCurrentAsProfile(unittest.TestCase):
    """Tests for capturing the current system state as a profile."""

    @patch.object(ProfileManager, 'create_custom_profile')
    @patch('builtins.open', mock_open(read_data="60\n"))
    @patch('utils.profiles.subprocess.run')
    def test_capture_success(self, mock_run, mock_create):
        """Capture reads governor and swappiness, then creates profile."""
        mock_run.return_value = MagicMock(returncode=0, stdout="schedutil\n")
        mock_create.return_value = Result(True, "Saved")

        result = ProfileManager.capture_current_as_profile("Captured")
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        settings = call_args[0][1]
        self.assertEqual(settings["governor"], "schedutil")
        self.assertEqual(settings["swappiness"], 60)

    def test_capture_empty_name(self):
        """Capture with empty name is rejected."""
        result = ProfileManager.capture_current_as_profile("")
        self.assertFalse(result.success)

    @patch.object(ProfileManager, 'create_custom_profile')
    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('utils.profiles.subprocess.run', side_effect=OSError("fail"))
    def test_capture_with_no_system_data(self, mock_run, mock_open_fn, mock_create):
        """Capture proceeds even if system reads fail."""
        mock_create.return_value = Result(True, "Saved")
        result = ProfileManager.capture_current_as_profile("Bare")
        mock_create.assert_called_once()


if __name__ == '__main__':
    unittest.main()
