"""
Tests for utils/tiling.py — TilingManager and DotfileManager.
Coverage-oriented: compositor detection, config paths, keybindings,
add keybinding, reload, workspace templates, move window, dotfile ops.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.tiling import TilingManager, DotfileManager


class TestCompositorDetection(unittest.TestCase):
    """Test is_hyprland, is_sway, get_compositor."""

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "Hyprland"})
    def test_is_hyprland_from_env(self):
        self.assertTrue(TilingManager.is_hyprland())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": ""})
    @patch("utils.tiling.shutil.which", return_value="/usr/bin/hyprctl")
    def test_is_hyprland_from_which(self, mock_which):
        self.assertTrue(TilingManager.is_hyprland())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "sway"})
    def test_is_sway_from_env(self):
        self.assertTrue(TilingManager.is_sway())

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": ""})
    @patch("utils.tiling.shutil.which", return_value=None)
    def test_neither_compositor(self, mock_which):
        self.assertFalse(TilingManager.is_hyprland())
        self.assertFalse(TilingManager.is_sway())

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_get_compositor_unknown(self, mock_sway, mock_hypr):
        self.assertEqual(TilingManager.get_compositor(), "unknown")

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    def test_get_compositor_hyprland(self, mock_hypr):
        self.assertEqual(TilingManager.get_compositor(), "hyprland")

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    def test_get_compositor_sway(self, mock_sway, mock_hypr):
        self.assertEqual(TilingManager.get_compositor(), "sway")


class TestConfigPath(unittest.TestCase):
    """Test get_config_path."""

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    def test_hyprland_config_path(self, mock_hypr):
        path = TilingManager.get_config_path()
        self.assertIn("hyprland.conf", str(path))

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    def test_sway_config_path(self, mock_sway, mock_hypr):
        path = TilingManager.get_config_path()
        self.assertIn("sway", str(path))

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_fallback_config_path(self, mock_sway, mock_hypr):
        path = TilingManager.get_config_path()
        self.assertEqual(path, Path.home() / ".config")


class TestGetKeybindings(unittest.TestCase):
    """Test get_keybindings parsing."""

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_hyprland_binds(self, mock_sway, mock_hypr):
        config_content = "bind = SUPER, Q, killactive,\nbind = SUPER, T, exec, kitty\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(config_content)
            f.flush()
            with patch.object(TilingManager, "get_config_path", return_value=Path(f.name)):
                bindings = TilingManager.get_keybindings()
                self.assertEqual(len(bindings), 2)
                self.assertEqual(bindings[0]["key"], "Q")
                self.assertEqual(bindings[1]["action"], "exec")
        os.unlink(f.name)

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    def test_sway_binds(self, mock_sway, mock_hypr):
        config_content = "bindsym $mod+Return exec alacritty\nbindsym $mod+d exec dmenu_run\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(config_content)
            f.flush()
            with patch.object(TilingManager, "get_config_path", return_value=Path(f.name)):
                bindings = TilingManager.get_keybindings()
                self.assertEqual(len(bindings), 2)
                self.assertEqual(bindings[0]["key"], "$mod+Return")
        os.unlink(f.name)

    @patch.object(TilingManager, "get_config_path", return_value=Path("/nonexistent/config"))
    def test_no_config_returns_empty(self, mock_path):
        self.assertEqual(TilingManager.get_keybindings(), [])


class TestAddKeybinding(unittest.TestCase):
    """Test add_keybinding."""

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_hyprland_append(self, mock_sway, mock_hypr):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write("# existing config\n")
            f.flush()
            with patch.object(TilingManager, "get_config_path", return_value=Path(f.name)):
                result = TilingManager.add_keybinding("SUPER", "Return", "exec", "kitty")
                self.assertTrue(result.success)
                content = Path(f.name).read_text()
                self.assertIn("bind = SUPER, Return, exec, kitty", content)
        os.unlink(f.name)

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    def test_sway_append(self, mock_sway, mock_hypr):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write("# sway\n")
            f.flush()
            with patch.object(TilingManager, "get_config_path", return_value=Path(f.name)):
                result = TilingManager.add_keybinding("$mod", "Return", "exec", "alacritty")
                self.assertTrue(result.success)
                content = Path(f.name).read_text()
                self.assertIn("bindsym $mod+Return exec alacritty", content)
        os.unlink(f.name)

    @patch.object(TilingManager, "get_config_path", return_value=Path("/no/such/config"))
    def test_missing_config_fails(self, mock_path):
        result = TilingManager.add_keybinding("SUPER", "Q", "killactive")
        self.assertFalse(result.success)


class TestReloadConfig(unittest.TestCase):
    """Test reload_config."""

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    @patch("utils.tiling.subprocess.run")
    def test_hyprland_reload(self, mock_run, mock_hypr):
        mock_run.return_value = MagicMock(returncode=0)
        result = TilingManager.reload_config()
        self.assertTrue(result.success)
        mock_run.assert_called_once()

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    @patch("utils.tiling.subprocess.run")
    def test_sway_reload(self, mock_run, mock_sway, mock_hypr):
        mock_run.return_value = MagicMock(returncode=0)
        result = TilingManager.reload_config()
        self.assertTrue(result.success)

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_unknown_compositor_fails(self, mock_sway, mock_hypr):
        result = TilingManager.reload_config()
        self.assertFalse(result.success)

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    @patch("utils.tiling.subprocess.run", side_effect=OSError("err"))
    def test_reload_exception(self, mock_run, mock_hypr):
        result = TilingManager.reload_config()
        self.assertFalse(result.success)


class TestWorkspaceTemplates(unittest.TestCase):
    """Test generate_workspace_template."""

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_hyprland_template(self, mock_sway, mock_hypr):
        result = TilingManager.generate_workspace_template("development")
        self.assertTrue(result.success)
        self.assertIn("windowrulev2", result.data["config"])

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    def test_sway_template(self, mock_sway, mock_hypr):
        result = TilingManager.generate_workspace_template("gaming")
        self.assertTrue(result.success)
        self.assertIn("assign", result.data["config"])

    def test_unknown_template_fails(self):
        result = TilingManager.generate_workspace_template("nonexistent")
        self.assertFalse(result.success)


class TestMoveWindow(unittest.TestCase):
    """Test move_window_to_workspace."""

    @patch.object(TilingManager, "is_hyprland", return_value=True)
    @patch("utils.tiling.subprocess.run")
    def test_hyprland_move(self, mock_run, mock_hypr):
        mock_run.return_value = MagicMock(returncode=0)
        result = TilingManager.move_window_to_workspace(3)
        self.assertTrue(result.success)

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=True)
    @patch("utils.tiling.subprocess.run")
    def test_sway_move(self, mock_run, mock_sway, mock_hypr):
        mock_run.return_value = MagicMock(returncode=0)
        result = TilingManager.move_window_to_workspace(2)
        self.assertTrue(result.success)

    @patch.object(TilingManager, "is_hyprland", return_value=False)
    @patch.object(TilingManager, "is_sway", return_value=False)
    def test_unknown_compositor(self, mock_sway, mock_hypr):
        result = TilingManager.move_window_to_workspace(1)
        self.assertFalse(result.success)


class TestDotfileManager(unittest.TestCase):
    """Test DotfileManager operations."""

    def test_create_dotfile_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "dotfiles"
            with patch("utils.tiling.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = DotfileManager.create_dotfile_repo(repo)
                self.assertTrue(result.success)
                self.assertTrue((repo / "config").is_dir())
                self.assertTrue((repo / "scripts").is_dir())
                self.assertTrue((repo / "install.sh").exists())
                self.assertTrue((repo / "README.md").exists())

    def test_sync_dotfile_unknown_name(self):
        result = DotfileManager.sync_dotfile("unknown", Path("/tmp"))
        self.assertFalse(result.success)

    def test_sync_dotfile_missing_source(self):
        with patch.object(Path, "exists", return_value=False):
            result = DotfileManager.sync_dotfile("zsh", Path("/tmp/repo"))
            self.assertFalse(result.success)

    def test_list_managed_dotfiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "nvim").mkdir()
            (config_dir / "kitty").mkdir()
            files = DotfileManager.list_managed_dotfiles(Path(tmpdir))
            self.assertEqual(len(files), 2)
            self.assertIn("nvim", files)

    def test_list_managed_dotfiles_missing_dir(self):
        files = DotfileManager.list_managed_dotfiles(Path("/nonexistent/repo"))
        self.assertEqual(files, [])


class TestLayouts(unittest.TestCase):
    """Test LAYOUTS and WORKSPACE_TEMPLATES data."""

    def test_layouts_has_required_keys(self):
        for key, layout in TilingManager.LAYOUTS.items():
            self.assertIn("name", layout)
            self.assertIn("hyprland", layout)
            self.assertIn("sway", layout)

    def test_workspace_templates_has_required_keys(self):
        for key, tmpl in TilingManager.WORKSPACE_TEMPLATES.items():
            self.assertIn("name", tmpl)
            self.assertIn("workspaces", tmpl)
            for ws_num, ws in tmpl["workspaces"].items():
                self.assertIn("name", ws)
                self.assertIn("apps", ws)


if __name__ == "__main__":
    unittest.main()
