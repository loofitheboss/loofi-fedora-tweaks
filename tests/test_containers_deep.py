"""
Tests for utils/containers.py — Distrobox container manager.

Covers:
- ContainerManager.is_available
- list_containers (parsing, statuses, errors)
- create_container (validation, success, failure, timeout)
- enter_container
- get_enter_command
- delete_container (normal, force)
- stop_container
- get_available_images
- export_app_from_container
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.containers import ContainerManager, ContainerStatus


class TestIsAvailable(unittest.TestCase):

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_available(self, mock_which):
        self.assertTrue(ContainerManager.is_available())

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        self.assertFalse(ContainerManager.is_available())


class TestListContainers(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        self.assertEqual(ContainerManager.list_containers(), [])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_parse_output(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ID | NAME | STATUS | IMAGE\nabc123 | fedora-dev | Up 2 hours | fedora-toolbox:latest\ndef456 | ubuntu-test | Exited | ubuntu:22.04\n"
        )
        containers = ContainerManager.list_containers()
        self.assertEqual(len(containers), 2)
        self.assertEqual(containers[0].name, "fedora-dev")
        self.assertEqual(containers[0].status, ContainerStatus.RUNNING)
        self.assertEqual(containers[1].status, ContainerStatus.STOPPED)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_created_status(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ID | NAME | STATUS | IMAGE\nabc | test | Created | fedora:latest\n"
        )
        containers = ContainerManager.list_containers()
        self.assertEqual(containers[0].status, ContainerStatus.CREATED)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_unknown_status(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ID | NAME | STATUS | IMAGE\nabc | test | paused | fedora:latest\n"
        )
        containers = ContainerManager.list_containers()
        self.assertEqual(containers[0].status, ContainerStatus.UNKNOWN)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_parse_running_up(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ID | NAME | STATUS | IMAGE\nabc | test | running | fedora:latest\n"
        )
        containers = ContainerManager.list_containers()
        self.assertEqual(containers[0].status, ContainerStatus.RUNNING)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_command_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        self.assertEqual(ContainerManager.list_containers(), [])

    @patch("subprocess.run", side_effect=OSError("fail"))
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_exception(self, mock_which, mock_run):
        self.assertEqual(ContainerManager.list_containers(), [])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_empty_output(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ID | NAME | STATUS | IMAGE\n")
        self.assertEqual(ContainerManager.list_containers(), [])

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("distrobox", 30))
    def test_timeout(self, mock_run, mock_which):
        self.assertEqual(ContainerManager.list_containers(), [])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_short_line_skipped(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ID | NAME | STATUS | IMAGE\nshort line\n"
        )
        self.assertEqual(ContainerManager.list_containers(), [])


class TestCreateContainer(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        r = ContainerManager.create_container("test")
        self.assertFalse(r.success)
        self.assertIn("not installed", r.message)
        self.assertIn("pkexec", r.message)
        self.assertNotIn("sudo ", r.message)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_invalid_name(self, mock_which):
        r = ContainerManager.create_container("bad name!")
        self.assertFalse(r.success)
        self.assertIn("Invalid", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success_default_image(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.create_container("mybox")
        self.assertTrue(r.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("fedora", " ".join(cmd))

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success_custom_image(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.create_container("mybox", image="ubuntu")
        self.assertTrue(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success_no_home_sharing(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.create_container("mybox", home_sharing=False)
        self.assertTrue(r.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--no-entry", cmd)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_with_additional_packages(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.create_container("mybox", additional_packages=["vim", "git"])
        self.assertTrue(r.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--additional-packages", cmd)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="image not found", stdout="")
        r = ContainerManager.create_container("mybox")
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("distrobox", 300))
    def test_timeout(self, mock_run, mock_which):
        r = ContainerManager.create_container("mybox")
        self.assertFalse(r.success)
        self.assertIn("timed out", r.message)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=OSError("oops"))
    def test_exception(self, mock_run, mock_which):
        r = ContainerManager.create_container("mybox")
        self.assertFalse(r.success)


class TestEnterContainer(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        result = ContainerManager.enter_container("test")
        self.assertIsNone(result)

    @patch("subprocess.Popen")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success(self, mock_which, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        result = ContainerManager.enter_container("test")
        self.assertEqual(result, mock_proc)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.Popen", side_effect=OSError("fail"))
    def test_exception(self, mock_popen, mock_which):
        result = ContainerManager.enter_container("test")
        self.assertIsNone(result)


class TestGetEnterCommand(unittest.TestCase):

    def test_returns_string(self):
        cmd = ContainerManager.get_enter_command("mybox")
        self.assertEqual(cmd, "distrobox enter mybox")


class TestDeleteContainer(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        r = ContainerManager.delete_container("test")
        self.assertFalse(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.delete_container("test")
        self.assertTrue(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_force_delete(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.delete_container("test", force=True)
        self.assertTrue(r.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--force", cmd)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="busy", stdout="")
        r = ContainerManager.delete_container("test")
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("distrobox", 60))
    def test_timeout(self, mock_run, mock_which):
        r = ContainerManager.delete_container("test")
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_which):
        r = ContainerManager.delete_container("test")
        self.assertFalse(r.success)


class TestStopContainer(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        r = ContainerManager.stop_container("test")
        self.assertFalse(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.stop_container("test")
        self.assertTrue(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="err", stdout="")
        r = ContainerManager.stop_container("test")
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_which):
        r = ContainerManager.stop_container("test")
        self.assertFalse(r.success)


class TestGetAvailableImages(unittest.TestCase):

    def test_returns_copy(self):
        imgs = ContainerManager.get_available_images()
        self.assertIsInstance(imgs, dict)
        self.assertIn("fedora", imgs)
        # Verify it's a copy
        imgs["test"] = "test"
        self.assertNotIn("test", ContainerManager.AVAILABLE_IMAGES)


class TestExportApp(unittest.TestCase):

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        r = ContainerManager.export_app_from_container("test", "firefox")
        self.assertFalse(r.success)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        r = ContainerManager.export_app_from_container("mybox", "firefox")
        self.assertTrue(r.success)
        self.assertIn("firefox", r.message)

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/distrobox")
    def test_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="not found", stdout="")
        r = ContainerManager.export_app_from_container("mybox", "firefox")
        self.assertFalse(r.success)

    @patch("shutil.which", return_value="/usr/bin/distrobox")
    @patch("subprocess.run", side_effect=OSError("fail"))
    def test_exception(self, mock_run, mock_which):
        r = ContainerManager.export_app_from_container("mybox", "firefox")
        self.assertFalse(r.success)


if __name__ == '__main__':
    unittest.main()
