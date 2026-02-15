"""Tests for utils/vm_manager.py — VMManager lifecycle operations.

Covers Result/VMInfo dataclasses, VM_FLAVORS presets, name validation,
availability checks, list/info/create/start/stop/delete, storage-pool
fallback, and libvirt group membership.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.vm_manager import (
    Result,
    VMInfo,
    VMManager,
    VM_FLAVORS,
    _VM_NAME_RE,
)


# ── Realistic virsh output fixtures ──────────────────────────────────────

VIRSH_LIST_OUTPUT = (
    " Id   Name       State\n"
    "----------------------------\n"
    " 1    fedora41   running\n"
    " -    win11      shut off\n"
    " -    kali       paused\n"
)

VIRSH_LIST_EMPTY = " Id   Name   State\n--------------------\n"

VIRSH_DOMINFO_OUTPUT = (
    "Name:           fedora41\n"
    "UUID:           abc-123-def\n"
    "OS Type:        hvm\n"
    "State:          running\n"
    "CPU(s):         4\n"
    "Max memory:     4194304 KiB\n"
    "Used memory:    2097152 KiB\n"
)


# ── Dataclass tests ─────────────────────────────────────────────────────


class TestResultDataclass(unittest.TestCase):
    """Tests for the Result dataclass."""

    def test_success_result(self):
        """Result with success=True carries the message."""
        r = Result(success=True, message="ok")
        self.assertTrue(r.success)
        self.assertEqual(r.message, "ok")
        self.assertIsNone(r.data)

    def test_failure_result(self):
        """Result with success=False carries the error message."""
        r = Result(success=False, message="boom")
        self.assertFalse(r.success)
        self.assertEqual(r.message, "boom")

    def test_result_with_data(self):
        """Result.data stores arbitrary dict payload."""
        r = Result(True, "done", data={"disk": "/a.qcow2"})
        self.assertEqual(r.data["disk"], "/a.qcow2")


class TestVMInfoDataclass(unittest.TestCase):
    """Tests for the VMInfo dataclass."""

    def test_defaults(self):
        """VMInfo fills defaults for optional fields."""
        info = VMInfo(name="test-vm", state="running")
        self.assertEqual(info.name, "test-vm")
        self.assertEqual(info.state, "running")
        self.assertEqual(info.uuid, "")
        self.assertEqual(info.memory_mb, 0)
        self.assertEqual(info.vcpus, 0)
        self.assertEqual(info.disk_path, "")

    def test_all_fields(self):
        """VMInfo stores all supplied fields."""
        info = VMInfo("vm1", "shut off", "uid", 2048, 4, "/disk.qcow2")
        self.assertEqual(info.memory_mb, 2048)
        self.assertEqual(info.vcpus, 4)
        self.assertEqual(info.disk_path, "/disk.qcow2")


# ── Flavours & name regex ────────────────────────────────────────────────


class TestVMFlavors(unittest.TestCase):
    """Tests for VM_FLAVORS preset dictionary."""

    def test_expected_keys_present(self):
        """All five flavour keys exist."""
        expected = {"windows11", "fedora", "ubuntu", "kali", "arch"}
        self.assertEqual(set(VM_FLAVORS.keys()), expected)

    def test_each_flavor_has_required_fields(self):
        """Every flavour must supply ram_mb, vcpus, disk_gb, os_variant."""
        for key, flavor in VM_FLAVORS.items():
            for field in ("ram_mb", "vcpus", "disk_gb", "os_variant"):
                self.assertIn(field, flavor, f"{key} missing {field}")

    def test_windows11_needs_tpm(self):
        """Windows 11 preset requires TPM."""
        self.assertTrue(VM_FLAVORS["windows11"]["needs_tpm"])

    def test_linux_flavors_no_tpm(self):
        """Non-Windows flavours do not require TPM."""
        for key in ("fedora", "ubuntu", "kali", "arch"):
            self.assertFalse(VM_FLAVORS[key]["needs_tpm"])


class TestVMNameRegex(unittest.TestCase):
    """Tests for _VM_NAME_RE name validation pattern."""

    def test_valid_names(self):
        """Alphanumeric, dashes, and underscores are accepted."""
        for name in ("myvm", "my-vm", "my_vm", "VM01", "a-b_c-3"):
            self.assertIsNotNone(_VM_NAME_RE.match(name), f"'{name}' should match")

    def test_invalid_names(self):
        """Spaces, dots, slashes, and empty strings are rejected."""
        for name in ("my vm", "vm.1", "vm/bad", "", "vm@home", "has space"):
            self.assertIsNone(_VM_NAME_RE.match(name), f"'{name}' should NOT match")


# ── Availability ─────────────────────────────────────────────────────────


class TestIsAvailable(unittest.TestCase):
    """Tests for VMManager.is_available()."""

    @patch("utils.vm_manager.shutil.which")
    def test_both_tools_present(self, mock_which):
        """Returns True when both virsh and qemu-system-x86_64 are found."""
        mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}"
        self.assertTrue(VMManager.is_available())

    @patch("utils.vm_manager.shutil.which")
    def test_virsh_missing(self, mock_which):
        """Returns False when virsh is missing."""
        mock_which.side_effect = lambda cmd: (
            None if cmd == "virsh" else "/usr/bin/qemu-system-x86_64"
        )
        self.assertFalse(VMManager.is_available())

    @patch("utils.vm_manager.shutil.which")
    def test_qemu_missing(self, mock_which):
        """Returns False when qemu-system-x86_64 is missing."""
        mock_which.side_effect = lambda cmd: (
            "/usr/bin/virsh" if cmd == "virsh" else None
        )
        self.assertFalse(VMManager.is_available())

    @patch("utils.vm_manager.shutil.which")
    def test_both_missing(self, mock_which):
        """Returns False when neither tool is found."""
        mock_which.return_value = None
        self.assertFalse(VMManager.is_available())


# ── Flavour retrieval ────────────────────────────────────────────────────


class TestGetAvailableFlavors(unittest.TestCase):
    """Tests for VMManager.get_available_flavors()."""

    def test_returns_copy(self):
        """Returns a new dict, not the original module-level reference."""
        flavors = VMManager.get_available_flavors()
        self.assertEqual(set(flavors.keys()), set(VM_FLAVORS.keys()))
        self.assertIsNot(flavors, VM_FLAVORS)

    def test_mutation_does_not_affect_original(self):
        """Mutating the returned dict doesn't alter VM_FLAVORS."""
        flavors = VMManager.get_available_flavors()
        flavors["custom"] = {"label": "Custom"}
        self.assertNotIn("custom", VM_FLAVORS)


# ── list_vms ─────────────────────────────────────────────────────────────


class TestListVMs(unittest.TestCase):
    """Tests for VMManager.list_vms()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_normal_output(self, mock_which, mock_run):
        """Parses three VMs with correct names and states."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_LIST_OUTPUT)

        vms = VMManager.list_vms()
        self.assertEqual(len(vms), 3)
        self.assertEqual(vms[0].name, "fedora41")
        self.assertEqual(vms[0].state, "running")
        self.assertEqual(vms[1].name, "win11")
        self.assertEqual(vms[1].state, "shut off")
        self.assertEqual(vms[2].name, "kali")
        self.assertEqual(vms[2].state, "paused")

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_empty_list(self, mock_which, mock_run):
        """Returns empty list when no VMs are defined."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_LIST_EMPTY)

        self.assertEqual(VMManager.list_vms(), [])

    @patch("utils.vm_manager.shutil.which")
    def test_virsh_not_installed(self, mock_which):
        """Returns empty list when virsh is not installed."""
        mock_which.return_value = None
        self.assertEqual(VMManager.list_vms(), [])

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_nonzero_returncode(self, mock_which, mock_run):
        """Returns empty list on non-zero exit code."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        self.assertEqual(VMManager.list_vms(), [])

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_timeout(self, mock_which, mock_run):
        """Returns empty list on subprocess timeout."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=15)

        self.assertEqual(VMManager.list_vms(), [])

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_generic_exception(self, mock_which, mock_run):
        """Returns empty list on unexpected exception."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = OSError("permission denied")

        self.assertEqual(VMManager.list_vms(), [])


# ── get_vm_info ──────────────────────────────────────────────────────────


class TestGetVMInfo(unittest.TestCase):
    """Tests for VMManager.get_vm_info()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_parses_all_fields(self, mock_which, mock_run):
        """Parses state, UUID, memory, and vCPUs from dominfo output."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_DOMINFO_OUTPUT)

        info = VMManager.get_vm_info("fedora41")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "fedora41")
        self.assertEqual(info.state, "running")
        self.assertEqual(info.uuid, "abc-123-def")
        self.assertEqual(info.memory_mb, 4096)
        self.assertEqual(info.vcpus, 4)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_vm_not_found(self, mock_which, mock_run):
        """Returns None when virsh reports non-zero (VM not found)."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")

        self.assertIsNone(VMManager.get_vm_info("nonexistent"))

    @patch("utils.vm_manager.shutil.which")
    def test_virsh_not_installed(self, mock_which):
        """Returns None when virsh is not available."""
        mock_which.return_value = None
        self.assertIsNone(VMManager.get_vm_info("any"))

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_timeout(self, mock_which, mock_run):
        """Returns None on subprocess timeout."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=10)

        self.assertIsNone(VMManager.get_vm_info("test"))

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_malformed_memory_value(self, mock_which, mock_run):
        """Gracefully handles unparseable memory value."""
        mock_which.return_value = "/usr/bin/virsh"
        output = "State:          running\nMax memory:     notanumber KiB\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=output)

        info = VMManager.get_vm_info("vm1")
        self.assertIsNotNone(info)
        self.assertEqual(info.memory_mb, 0)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_malformed_vcpus_value(self, mock_which, mock_run):
        """Gracefully handles unparseable CPU(s) value."""
        mock_which.return_value = "/usr/bin/virsh"
        output = "State:          running\nCPU(s):         abc\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=output)

        info = VMManager.get_vm_info("vm1")
        self.assertIsNotNone(info)
        self.assertEqual(info.vcpus, 0)


# ── get_vm_state ─────────────────────────────────────────────────────────


class TestGetVMState(unittest.TestCase):
    """Tests for VMManager.get_vm_state()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_returns_running(self, mock_which, mock_run):
        """Returns 'running' when VM is active."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout=VIRSH_DOMINFO_OUTPUT)

        self.assertEqual(VMManager.get_vm_state("fedora41"), "running")

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_returns_unknown_on_failure(self, mock_which, mock_run):
        """Returns 'unknown' when VM info cannot be retrieved."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        self.assertEqual(VMManager.get_vm_state("gone"), "unknown")


# ── create_vm ────────────────────────────────────────────────────────────


class TestCreateVM(unittest.TestCase):
    """Tests for VMManager.create_vm()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_create_success(self, mock_which, mock_isfile, mock_isdir, mock_run):
        """Successful VM creation returns Result with success=True and data."""
        mock_which.return_value = "/usr/bin/virt-install"
        mock_isfile.return_value = True
        mock_isdir.return_value = True  # storage pool exists
        mock_run.return_value = MagicMock(returncode=0, stdout="done")

        result = VMManager.create_vm("test-vm", "fedora", "/tmp/fedora.iso")
        self.assertTrue(result.success)
        self.assertIn("test-vm", result.message)
        self.assertEqual(result.data["name"], "test-vm")
        self.assertIn(".qcow2", result.data["disk"])

    @patch("utils.vm_manager.shutil.which")
    def test_invalid_name_spaces(self, mock_which):
        """Rejects names with spaces."""
        result = VMManager.create_vm("bad name", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("Invalid VM name", result.message)

    @patch("utils.vm_manager.shutil.which")
    def test_invalid_name_dots(self, mock_which):
        """Rejects names with dots."""
        result = VMManager.create_vm("my.vm", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)

    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_unknown_flavor(self, mock_which, mock_isfile):
        """Rejects unrecognised flavour keys."""
        result = VMManager.create_vm("test-vm", "haiku", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("Unknown flavour", result.message)

    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_missing_iso(self, mock_which, mock_isfile):
        """Rejects when ISO file does not exist."""
        mock_isfile.return_value = False
        result = VMManager.create_vm("test-vm", "fedora", "/tmp/nope.iso")
        self.assertFalse(result.success)
        self.assertIn("ISO file not found", result.message)

    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_empty_iso_path(self, mock_which, mock_isfile):
        """Rejects empty ISO path."""
        result = VMManager.create_vm("test-vm", "fedora", "")
        self.assertFalse(result.success)
        self.assertIn("ISO file not found", result.message)

    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_virt_install_missing(self, mock_which, mock_isfile):
        """Returns failure when virt-install is not installed."""
        mock_which.side_effect = lambda cmd: (
            None if cmd == "virt-install" else f"/usr/bin/{cmd}"
        )
        mock_isfile.return_value = True

        result = VMManager.create_vm("test-vm", "fedora", "/tmp/fedora.iso")
        self.assertFalse(result.success)
        self.assertIn("virt-install is not installed", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_overrides_applied(self, mock_which, mock_isfile, mock_isdir, mock_run):
        """Keyword overrides (ram_mb, vcpus, disk_gb) are applied to the command."""
        mock_which.return_value = "/usr/bin/virt-install"
        mock_isfile.return_value = True
        mock_isdir.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="ok")

        VMManager.create_vm(
            "vm1", "arch", "/tmp/arch.iso", ram_mb=8192, vcpus=8, disk_gb=100
        )
        cmd = mock_run.call_args[0][0]
        self.assertIn("8192", cmd)
        self.assertIn("8", cmd)
        self.assertIn("size=100", [a for a in cmd if "size=" in a][0])

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_windows11_with_swtpm(self, mock_which, mock_isfile, mock_isdir, mock_run):
        """Windows 11 VM includes --tpm flag when swtpm is available."""
        mock_which.return_value = "/usr/bin/swtpm"  # all which() calls return a path
        mock_isfile.return_value = True
        mock_isdir.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="ok")

        result = VMManager.create_vm("win", "windows11", "/tmp/win.iso")
        self.assertTrue(result.success)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--tpm", cmd)

    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_windows11_without_swtpm(self, mock_which, mock_isfile):
        """Windows 11 VM fails when swtpm is missing."""

        def which_side_effect(cmd):
            if cmd == "swtpm":
                return None
            return f"/usr/bin/{cmd}"

        mock_which.side_effect = which_side_effect
        mock_isfile.return_value = True

        result = VMManager.create_vm("win", "windows11", "/tmp/win.iso")
        self.assertFalse(result.success)
        self.assertIn("swtpm", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_virtio_drivers_attached(
        self, mock_which, mock_isfile, mock_isdir, mock_run
    ):
        """Windows 11 with virtio ISO attaches it as extra cdrom."""
        mock_which.return_value = "/usr/bin/swtpm"
        mock_isfile.return_value = True  # both ISO and virtio-win.iso exist
        mock_isdir.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="ok")

        VMManager.create_vm("win", "windows11", "/tmp/win.iso")
        cmd = mock_run.call_args[0][0]
        virtio_args = [a for a in cmd if "virtio-win" in a]
        self.assertTrue(len(virtio_args) > 0)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_create_failure_stderr(self, mock_which, mock_isfile, mock_isdir, mock_run):
        """Reports stderr content on virt-install failure."""
        mock_which.return_value = "/usr/bin/virt-install"
        mock_isfile.return_value = True
        mock_isdir.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="disk full")

        result = VMManager.create_vm("vm1", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("disk full", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_create_timeout(self, mock_which, mock_isfile, mock_isdir, mock_run):
        """Returns timeout message when virt-install exceeds 120s."""
        mock_which.return_value = "/usr/bin/virt-install"
        mock_isfile.return_value = True
        mock_isdir.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="virt-install", timeout=120
        )

        result = VMManager.create_vm("vm1", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.os.path.isdir")
    @patch("utils.vm_manager.os.path.isfile")
    @patch("utils.vm_manager.shutil.which")
    def test_create_generic_exception(
        self, mock_which, mock_isfile, mock_isdir, mock_run
    ):
        """Returns error message on unexpected exception."""
        mock_which.return_value = "/usr/bin/virt-install"
        mock_isfile.return_value = True
        mock_isdir.return_value = True
        mock_run.side_effect = OSError("permission denied")

        result = VMManager.create_vm("vm1", "fedora", "/tmp/f.iso")
        self.assertFalse(result.success)
        self.assertIn("Error creating VM", result.message)


# ── start_vm ─────────────────────────────────────────────────────────────


class TestStartVM(unittest.TestCase):
    """Tests for VMManager.start_vm()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_start_success(self, mock_which, mock_run):
        """Returns success when virsh start exits 0."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain started")

        result = VMManager.start_vm("fedora41")
        self.assertTrue(result.success)
        self.assertIn("started", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_start_failure(self, mock_which, mock_run):
        """Returns failure with stderr on non-zero exit."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="already running"
        )

        result = VMManager.start_vm("fedora41")
        self.assertFalse(result.success)
        self.assertIn("already running", result.message)

    @patch("utils.vm_manager.shutil.which")
    def test_start_virsh_missing(self, mock_which):
        """Returns failure when virsh is not installed."""
        mock_which.return_value = None
        result = VMManager.start_vm("any")
        self.assertFalse(result.success)
        self.assertIn("virsh is not installed", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_start_timeout(self, mock_which, mock_run):
        """Returns timeout message on subprocess timeout."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=30)

        result = VMManager.start_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)


# ── stop_vm ──────────────────────────────────────────────────────────────


class TestStopVM(unittest.TestCase):
    """Tests for VMManager.stop_vm()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_stop_success(self, mock_which, mock_run):
        """Returns success on graceful shutdown."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain shutdown")

        result = VMManager.stop_vm("vm1")
        self.assertTrue(result.success)
        self.assertIn("shutdown signal sent", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_stop_failure(self, mock_which, mock_run):
        """Returns failure on non-zero exit."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not running")

        result = VMManager.stop_vm("vm1")
        self.assertFalse(result.success)

    @patch("utils.vm_manager.shutil.which")
    def test_stop_virsh_missing(self, mock_which):
        """Returns failure when virsh is not installed."""
        mock_which.return_value = None
        result = VMManager.stop_vm("any")
        self.assertFalse(result.success)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_stop_timeout(self, mock_which, mock_run):
        """Returns timeout message on subprocess timeout."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=30)

        result = VMManager.stop_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_stop_generic_exception(self, mock_which, mock_run):
        """Returns error message on unexpected exception."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = RuntimeError("bus error")

        result = VMManager.stop_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("Error shutting down VM", result.message)


# ── force_stop_vm ────────────────────────────────────────────────────────


class TestForceStopVM(unittest.TestCase):
    """Tests for VMManager.force_stop_vm()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_force_stop_success(self, mock_which, mock_run):
        """Returns success on virsh destroy exit 0."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain destroyed")

        result = VMManager.force_stop_vm("vm1")
        self.assertTrue(result.success)
        self.assertIn("force-stopped", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_force_stop_failure(self, mock_which, mock_run):
        """Returns failure on non-zero exit."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not running")

        result = VMManager.force_stop_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("not running", result.message)

    @patch("utils.vm_manager.shutil.which")
    def test_force_stop_virsh_missing(self, mock_which):
        """Returns failure when virsh is not installed."""
        mock_which.return_value = None
        result = VMManager.force_stop_vm("any")
        self.assertFalse(result.success)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_force_stop_timeout(self, mock_which, mock_run):
        """Returns timeout message on subprocess timeout."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=30)

        result = VMManager.force_stop_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)


# ── delete_vm ────────────────────────────────────────────────────────────


class TestDeleteVM(unittest.TestCase):
    """Tests for VMManager.delete_vm()."""

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_delete_success(self, mock_which, mock_run):
        """Returns success on virsh undefine exit 0."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain undefined")

        result = VMManager.delete_vm("vm1")
        self.assertTrue(result.success)
        self.assertIn("deleted", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_delete_with_storage(self, mock_which, mock_run):
        """Passes --remove-all-storage when delete_storage=True."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain undefined")

        VMManager.delete_vm("vm1", delete_storage=True)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--remove-all-storage", cmd)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_delete_without_storage(self, mock_which, mock_run):
        """Does not pass --remove-all-storage when delete_storage=False."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(returncode=0, stdout="Domain undefined")

        VMManager.delete_vm("vm1", delete_storage=False)
        cmd = mock_run.call_args[0][0]
        self.assertNotIn("--remove-all-storage", cmd)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_delete_failure(self, mock_which, mock_run):
        """Returns failure with stderr on non-zero exit."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="domain not found"
        )

        result = VMManager.delete_vm("ghost")
        self.assertFalse(result.success)
        self.assertIn("domain not found", result.message)

    @patch("utils.vm_manager.shutil.which")
    def test_delete_virsh_missing(self, mock_which):
        """Returns failure when virsh is not installed."""
        mock_which.return_value = None
        result = VMManager.delete_vm("any")
        self.assertFalse(result.success)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_delete_timeout(self, mock_which, mock_run):
        """Returns timeout message on subprocess timeout."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="virsh", timeout=30)

        result = VMManager.delete_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.message)

    @patch("utils.vm_manager.subprocess.run")
    @patch("utils.vm_manager.shutil.which")
    def test_delete_generic_exception(self, mock_which, mock_run):
        """Returns error message on unexpected exception."""
        mock_which.return_value = "/usr/bin/virsh"
        mock_run.side_effect = PermissionError("access denied")

        result = VMManager.delete_vm("vm1")
        self.assertFalse(result.success)
        self.assertIn("Error deleting VM", result.message)


# ── get_default_storage_pool ─────────────────────────────────────────────


class TestGetDefaultStoragePool(unittest.TestCase):
    """Tests for VMManager.get_default_storage_pool()."""

    @patch("utils.vm_manager.os.path.isdir")
    def test_system_pool_exists(self, mock_isdir):
        """Returns /var/lib/libvirt/images when the directory exists."""
        mock_isdir.return_value = True
        result = VMManager.get_default_storage_pool()
        self.assertEqual(result, "/var/lib/libvirt/images")

    @patch("utils.vm_manager.os.makedirs")
    @patch("utils.vm_manager.os.path.expanduser")
    @patch("utils.vm_manager.os.path.isdir")
    def test_fallback_pool(self, mock_isdir, mock_expanduser, mock_makedirs):
        """Falls back to ~/.local/share/loofi-vms when system path is absent."""
        mock_isdir.return_value = False
        mock_expanduser.return_value = "/home/user/.local/share/loofi-vms"

        result = VMManager.get_default_storage_pool()
        self.assertEqual(result, "/home/user/.local/share/loofi-vms")
        mock_makedirs.assert_called_once_with(
            "/home/user/.local/share/loofi-vms",
            exist_ok=True,
        )


# ── check_user_in_libvirt_group ──────────────────────────────────────────


class TestCheckUserInLibvirtGroup(unittest.TestCase):
    """Tests for VMManager.check_user_in_libvirt_group()."""

    @patch("utils.vm_manager.subprocess.run")
    def test_user_in_group(self, mock_run):
        """Returns True when 'libvirt' appears in user's groups."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="wheel docker libvirt users",
        )
        self.assertTrue(VMManager.check_user_in_libvirt_group())

    @patch("utils.vm_manager.subprocess.run")
    def test_user_not_in_group(self, mock_run):
        """Returns False when 'libvirt' is absent from user's groups."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="wheel docker users",
        )
        self.assertFalse(VMManager.check_user_in_libvirt_group())

    @patch("utils.vm_manager.subprocess.run")
    def test_partial_match_rejected(self, mock_run):
        """Does not match 'libvirtd' as 'libvirt' (word-level split)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="wheel libvirtd users",
        )
        self.assertFalse(VMManager.check_user_in_libvirt_group())

    @patch("utils.vm_manager.subprocess.run")
    def test_id_command_fails(self, mock_run):
        """Returns False when id command exits non-zero."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertFalse(VMManager.check_user_in_libvirt_group())

    @patch("utils.vm_manager.subprocess.run")
    def test_timeout(self, mock_run):
        """Returns False on subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="id", timeout=5)
        self.assertFalse(VMManager.check_user_in_libvirt_group())

    @patch("utils.vm_manager.subprocess.run")
    def test_generic_exception(self, mock_run):
        """Returns False on unexpected exception."""
        mock_run.side_effect = OSError("no such command")
        self.assertFalse(VMManager.check_user_in_libvirt_group())


if __name__ == "__main__":
    unittest.main()
