"""Deep tests for utils/focus_mode.py — profiles, domain blocking, DND, process control."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.focus_mode import FocusMode, FocusModeProfile


class TestFocusModeProfile(unittest.TestCase):
    def test_defaults(self):
        p = FocusModeProfile(name="x", blocked_domains=[], kill_processes=[])
        self.assertTrue(p.enable_dnd)
        self.assertEqual(p.custom_hosts_backup, "")

    def test_custom(self):
        p = FocusModeProfile(name="w", blocked_domains=["a.com"], kill_processes=["bad"], enable_dnd=False)
        self.assertFalse(p.enable_dnd)
        self.assertEqual(p.blocked_domains, ["a.com"])


class TestEnsureConfig(unittest.TestCase):
    def test_creates_default_config(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td) / "cfg"
            cfg_file = cfg_dir / "focus_mode.json"
            with patch.object(FocusMode, 'CONFIG_DIR', cfg_dir):
                with patch.object(FocusMode, 'CONFIG_FILE', cfg_file):
                    FocusMode.ensure_config()
                    self.assertTrue(cfg_file.exists())
                    data = json.loads(cfg_file.read_text())
                    self.assertFalse(data["active"])
                    self.assertIn("default", data["profiles"])

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td)
            cfg_file = cfg_dir / "focus_mode.json"
            cfg_file.write_text('{"custom": true}')
            with patch.object(FocusMode, 'CONFIG_DIR', cfg_dir):
                with patch.object(FocusMode, 'CONFIG_FILE', cfg_file):
                    FocusMode.ensure_config()
                    data = json.loads(cfg_file.read_text())
                    self.assertTrue(data.get("custom"))


class TestLoadConfig(unittest.TestCase):
    def test_valid(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td)
            cfg_file = cfg_dir / "focus_mode.json"
            cfg_file.write_text('{"active": false, "profiles": {"x": {}}}')
            with patch.object(FocusMode, 'CONFIG_DIR', cfg_dir):
                with patch.object(FocusMode, 'CONFIG_FILE', cfg_file):
                    config = FocusMode.load_config()
                    self.assertIn("profiles", config)

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td)
            cfg_file = cfg_dir / "focus_mode.json"
            cfg_file.write_text('not json')
            with patch.object(FocusMode, 'CONFIG_DIR', cfg_dir):
                with patch.object(FocusMode, 'CONFIG_FILE', cfg_file):
                    config = FocusMode.load_config()
                    self.assertFalse(config.get("active"))


class TestSaveConfig(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td)
            cfg_file = cfg_dir / "focus_mode.json"
            with patch.object(FocusMode, 'CONFIG_DIR', cfg_dir):
                with patch.object(FocusMode, 'CONFIG_FILE', cfg_file):
                    FocusMode.save_config({"active": True, "profiles": {}})
                    data = json.loads(cfg_file.read_text())
                    self.assertTrue(data["active"])


class TestListProfiles(unittest.TestCase):
    @patch.object(FocusMode, 'load_config', return_value={"profiles": {"work": {}, "rest": {}}})
    def test_returns_names(self, _):
        names = FocusMode.list_profiles()
        self.assertIn("work", names)
        self.assertIn("rest", names)

    @patch.object(FocusMode, 'load_config', return_value={})
    def test_empty(self, _):
        self.assertEqual(FocusMode.list_profiles(), [])


class TestGetProfile(unittest.TestCase):
    @patch.object(FocusMode, 'load_config', return_value={"profiles": {"w": {"blocked_domains": []}}})
    def test_found(self, _):
        p = FocusMode.get_profile("w")
        self.assertIsNotNone(p)

    @patch.object(FocusMode, 'load_config', return_value={"profiles": {}})
    def test_not_found(self, _):
        self.assertIsNone(FocusMode.get_profile("nope"))


class TestSaveProfile(unittest.TestCase):
    @patch.object(FocusMode, 'save_config')
    @patch.object(FocusMode, 'load_config', return_value={"profiles": {}})
    def test_success(self, _, mock_save):
        result = FocusMode.save_profile("new", {"blocked_domains": []})
        self.assertTrue(result)

    @patch.object(FocusMode, 'load_config', side_effect=Exception("write fail"))
    def test_failure(self, _):
        result = FocusMode.save_profile("bad", {})
        self.assertFalse(result)


class TestDeleteProfile(unittest.TestCase):
    @patch.object(FocusMode, 'save_config')
    @patch.object(FocusMode, 'load_config', return_value={"profiles": {"old": {}}})
    def test_success(self, _, __):
        self.assertTrue(FocusMode.delete_profile("old"))

    @patch.object(FocusMode, 'load_config', return_value={"profiles": {}})
    def test_not_found(self, _):
        self.assertFalse(FocusMode.delete_profile("nope"))


class TestIsActive(unittest.TestCase):
    @patch.object(FocusMode, 'load_config', return_value={"active": True})
    def test_active(self, _):
        self.assertTrue(FocusMode.is_active())

    @patch.object(FocusMode, 'load_config', return_value={"active": False})
    def test_inactive(self, _):
        self.assertFalse(FocusMode.is_active())


class TestGetActiveProfile(unittest.TestCase):
    @patch.object(FocusMode, 'load_config', return_value={"active": True, "active_profile": "work"})
    def test_active(self, _):
        self.assertEqual(FocusMode.get_active_profile(), "work")

    @patch.object(FocusMode, 'load_config', return_value={"active": False})
    def test_inactive(self, _):
        self.assertIsNone(FocusMode.get_active_profile())


class TestRemoveFocusEntries(unittest.TestCase):
    def test_removes_block(self):
        hosts = "127.0.0.1 localhost\n# LOOFI-FOCUS-MODE-START\n127.0.0.1 reddit.com\n# LOOFI-FOCUS-MODE-END\n"
        cleaned = FocusMode._remove_focus_entries(hosts)
        self.assertNotIn("reddit.com", cleaned)
        self.assertIn("localhost", cleaned)

    def test_no_block(self):
        hosts = "127.0.0.1 localhost\n"
        cleaned = FocusMode._remove_focus_entries(hosts)
        self.assertEqual(cleaned.strip(), "127.0.0.1 localhost")


class TestBlockDomains(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    @patch("builtins.open", mock_open(read_data="127.0.0.1 localhost\n"))
    def test_success(self, mock_run):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(FocusMode, 'CONFIG_DIR', Path(td)):
                with patch.object(FocusMode, 'HOSTS_BACKUP', Path(td) / "hosts.bak"):
                    result = FocusMode._block_domains(["reddit.com"])
                    self.assertTrue(result["success"])

    @patch("subprocess.run", return_value=MagicMock(returncode=1))
    @patch("builtins.open", mock_open(read_data="127.0.0.1 localhost\n"))
    def test_pkexec_denied(self, mock_run):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(FocusMode, 'CONFIG_DIR', Path(td)):
                with patch.object(FocusMode, 'HOSTS_BACKUP', Path(td) / "hosts.bak"):
                    result = FocusMode._block_domains(["reddit.com"])
                    self.assertFalse(result["success"])

    @patch("builtins.open", side_effect=PermissionError("no"))
    def test_permission_error(self, _):
        result = FocusMode._block_domains(["reddit.com"])
        self.assertFalse(result["success"])


class TestRestoreHosts(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    @patch("builtins.open", mock_open(read_data="127.0.0.1 localhost\n"))
    def test_success(self, mock_run):
        result = FocusMode._restore_hosts()
        self.assertTrue(result["success"])

    @patch("builtins.open", side_effect=Exception("fail"))
    def test_failure(self, _):
        result = FocusMode._restore_hosts()
        self.assertFalse(result["success"])


class TestKdeDnd(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_enable_success(self, _):
        r = FocusMode._kde_dnd(True)
        self.assertTrue(r["success"])

    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_disable_success(self, _):
        r = FocusMode._kde_dnd(False)
        self.assertTrue(r["success"])

    @patch("subprocess.run", return_value=MagicMock(returncode=1))
    def test_failure(self, _):
        r = FocusMode._kde_dnd(True)
        self.assertFalse(r["success"])

    @patch("subprocess.run", side_effect=FileNotFoundError("no dbus"))
    def test_exception(self, _):
        r = FocusMode._kde_dnd(True)
        self.assertFalse(r["success"])


class TestGnomeDnd(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_enable(self, _):
        r = FocusMode._gnome_dnd(True)
        self.assertTrue(r["success"])

    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_disable(self, _):
        r = FocusMode._gnome_dnd(False)
        self.assertTrue(r["success"])

    @patch("subprocess.run", return_value=MagicMock(returncode=1))
    def test_failure(self, _):
        r = FocusMode._gnome_dnd(False)
        self.assertFalse(r["success"])


class TestEnableDnd(unittest.TestCase):
    @patch.object(FocusMode, '_kde_dnd', return_value={"success": True, "message": "ok"})
    def test_kde_first(self, _):
        r = FocusMode._enable_dnd()
        self.assertTrue(r["success"])

    @patch.object(FocusMode, '_gnome_dnd', return_value={"success": True, "message": "ok"})
    @patch.object(FocusMode, '_kde_dnd', return_value={"success": False, "message": "no"})
    def test_gnome_fallback(self, _, __):
        r = FocusMode._enable_dnd()
        self.assertTrue(r["success"])

    @patch.object(FocusMode, '_gnome_dnd', return_value={"success": False, "message": "no"})
    @patch.object(FocusMode, '_kde_dnd', return_value={"success": False, "message": "no"})
    def test_unsupported(self, _, __):
        r = FocusMode._enable_dnd()
        self.assertFalse(r["success"])


class TestDisableDnd(unittest.TestCase):
    @patch.object(FocusMode, '_kde_dnd', return_value={"success": True, "message": "ok"})
    def test_success(self, _):
        r = FocusMode._disable_dnd()
        self.assertTrue(r["success"])


class TestKillProcesses(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(returncode=0))
    def test_kills(self, _):
        killed = FocusMode._kill_processes(["steam", "discord"])
        self.assertEqual(len(killed), 2)

    @patch("subprocess.run", return_value=MagicMock(returncode=1))
    def test_not_running(self, _):
        killed = FocusMode._kill_processes(["nonexistent"])
        self.assertEqual(killed, [])

    @patch("subprocess.run", side_effect=Exception("err"))
    def test_exception(self, _):
        killed = FocusMode._kill_processes(["bad"])
        self.assertEqual(killed, [])


class TestGetRunningDistractions(unittest.TestCase):
    @patch("subprocess.run", return_value=MagicMock(stdout="bash\nsteam\nfirefox\n"))
    def test_found(self, _):
        running = FocusMode.get_running_distractions(["steam", "discord"])
        self.assertIn("steam", running)
        self.assertNotIn("discord", running)

    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_exception(self, _):
        self.assertEqual(FocusMode.get_running_distractions(), [])


class TestEnable(unittest.TestCase):
    @patch.object(FocusMode, 'save_config')
    @patch.object(FocusMode, 'load_config', return_value={"active": False, "profiles": {}})
    @patch.object(FocusMode, '_kill_processes', return_value=["steam"])
    @patch.object(FocusMode, '_enable_dnd', return_value={"success": True})
    @patch.object(FocusMode, '_block_domains', return_value={"success": True, "message": "ok"})
    @patch.object(FocusMode, 'get_profile', return_value={
        "blocked_domains": ["reddit.com"], "enable_dnd": True, "kill_processes": ["steam"]
    })
    def test_success(self, *_):
        r = FocusMode.enable("default")
        self.assertTrue(r["success"])

    @patch.object(FocusMode, 'get_profile', return_value=None)
    def test_no_profile(self, _):
        r = FocusMode.enable("nonexistent")
        self.assertFalse(r["success"])

    @patch.object(FocusMode, '_block_domains', return_value={"success": False, "message": "denied"})
    @patch.object(FocusMode, 'get_profile', return_value={"blocked_domains": ["x.com"]})
    def test_block_fail(self, _, __):
        r = FocusMode.enable("default")
        self.assertFalse(r["success"])


class TestDisable(unittest.TestCase):
    @patch.object(FocusMode, 'save_config')
    @patch.object(FocusMode, 'load_config', return_value={"active": True})
    @patch.object(FocusMode, '_disable_dnd', return_value={"success": True})
    @patch.object(FocusMode, '_restore_hosts', return_value={"success": True, "message": "ok"})
    def test_success(self, *_):
        r = FocusMode.disable()
        self.assertTrue(r["success"])


class TestToggle(unittest.TestCase):
    @patch.object(FocusMode, 'enable', return_value={"success": True})
    @patch.object(FocusMode, 'is_active', return_value=False)
    def test_enable_when_inactive(self, _, __):
        r = FocusMode.toggle()
        self.assertTrue(r["success"])

    @patch.object(FocusMode, 'disable', return_value={"success": True})
    @patch.object(FocusMode, 'is_active', return_value=True)
    def test_disable_when_active(self, _, __):
        r = FocusMode.toggle()
        self.assertTrue(r["success"])


if __name__ == "__main__":
    unittest.main()
