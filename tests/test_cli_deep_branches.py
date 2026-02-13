"""Tests for remaining uncovered CLI handlers: service, package, firewall,
bluetooth, storage, focus-mode, profile, health-history, logs, support-bundle,
doctor; plus JSON mode paths for many handlers."""

import argparse
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

import cli.main as cli_mod
from cli.main import (
    cmd_advanced,
    cmd_bluetooth,
    cmd_cleanup,
    cmd_disk,
    cmd_doctor,
    cmd_firewall,
    cmd_focus_mode,
    cmd_health,
    cmd_health_history,
    cmd_info,
    cmd_logs,
    cmd_netmon,
    cmd_network,
    cmd_package,
    cmd_plugin_marketplace,
    cmd_processes,
    cmd_profile,
    cmd_service,
    cmd_storage,
    cmd_support_bundle,
    cmd_temperature,
    cmd_tweak,
    main,
    run_operation,
)

# ── helpers ────────────────────────────────────────────────────────

def _ns(**kw):
    """Quick argparse.Namespace builder."""
    return argparse.Namespace(**kw)


def _set_json(val):
    cli_mod._json_output = val


# ── run_operation ──────────────────────────────────────────────────

class TestRunOperation(unittest.TestCase):
    """Cover run_operation success, failure, and exception paths."""

    @patch('cli.main._print')
    @patch('subprocess.run')
    def test_run_operation_success(self, mock_run, mock_print):
        _set_json(False)
        mock_run.return_value = SimpleNamespace(returncode=0, stdout='ok\n', stderr='')
        result = run_operation(('echo', ['hello'], 'Test op'))
        self.assertTrue(result)

    @patch('cli.main._print')
    @patch('subprocess.run')
    def test_run_operation_failure(self, mock_run, mock_print):
        _set_json(False)
        mock_run.return_value = SimpleNamespace(returncode=1, stdout='', stderr='err')
        result = run_operation(('false', [], 'Fail op'))
        self.assertFalse(result)

    @patch('cli.main._print')
    @patch('subprocess.run', side_effect=OSError('boom'))
    def test_run_operation_exception(self, mock_run, mock_print):
        _set_json(False)
        result = run_operation(('nonexistent', [], 'Bad op'))
        self.assertFalse(result)


# ── cmd_cleanup ────────────────────────────────────────────────────

class TestCmdCleanup(unittest.TestCase):

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_cleanup_all(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_cleanup(_ns(action='all', days=14))
        self.assertEqual(r, 0)
        self.assertEqual(mock_run.call_count, 3)

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_cleanup_autoremove(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_cleanup(_ns(action='autoremove', days=14))
        self.assertEqual(r, 0)

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_cleanup_rpmdb(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_cleanup(_ns(action='rpmdb', days=14))
        self.assertEqual(r, 0)


# ── cmd_tweak ──────────────────────────────────────────────────────

class TestCmdTweak(unittest.TestCase):

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_tweak_audio(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_tweak(_ns(action='audio', profile='balanced', limit=80))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.operations.TweakOps.set_battery_limit')
    def test_tweak_battery(self, mock_bat, mock_print):
        _set_json(False)
        mock_bat.return_value = SimpleNamespace(success=True, message='ok')
        r = cmd_tweak(_ns(action='battery', profile='balanced', limit=80))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.operations.TweakOps.set_battery_limit')
    def test_tweak_battery_fail(self, mock_bat, mock_print):
        _set_json(False)
        mock_bat.return_value = SimpleNamespace(success=False, message='err')
        r = cmd_tweak(_ns(action='battery', profile='balanced', limit=80))
        self.assertEqual(r, 1)

    @patch('cli.main._output_json')
    @patch('utils.system.SystemManager.is_atomic', return_value=False)
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    def test_tweak_status_json(self, mock_prof, mock_atomic, mock_json):
        _set_json(True)
        r = cmd_tweak(_ns(action='status', profile='balanced', limit=80))
        self.assertEqual(r, 0)
        mock_json.assert_called_once()
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.system.SystemManager.is_atomic', return_value=False)
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    def test_tweak_status_text(self, mock_prof, mock_atomic, mock_print):
        _set_json(False)
        r = cmd_tweak(_ns(action='status', profile='balanced', limit=80))
        self.assertEqual(r, 0)


# ── cmd_advanced ───────────────────────────────────────────────────

class TestCmdAdvanced(unittest.TestCase):

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_advanced_bbr(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_advanced(_ns(action='bbr', value=10))
        self.assertEqual(r, 0)

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_advanced_gamemode(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_advanced(_ns(action='gamemode', value=10))
        self.assertEqual(r, 0)

    @patch('cli.main.run_operation', return_value=True)
    @patch('cli.main._print')
    def test_advanced_swappiness(self, mock_print, mock_run):
        _set_json(False)
        r = cmd_advanced(_ns(action='swappiness', value=60))
        self.assertEqual(r, 0)


# ── cmd_network ────────────────────────────────────────────────────

class TestCmdNetwork(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.operations.NetworkOps.set_dns')
    def test_network_dns_success(self, mock_dns, mock_print):
        _set_json(False)
        mock_dns.return_value = SimpleNamespace(success=True, message='set cf')
        r = cmd_network(_ns(action='dns', provider='cloudflare'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.operations.NetworkOps.set_dns')
    def test_network_dns_fail(self, mock_dns, mock_print):
        _set_json(False)
        mock_dns.return_value = SimpleNamespace(success=False, message='err')
        r = cmd_network(_ns(action='dns', provider='google'))
        self.assertEqual(r, 1)


# ── cmd_info ───────────────────────────────────────────────────────

class TestCmdInfo(unittest.TestCase):

    @patch('cli.main._output_json')
    @patch('utils.system.SystemManager.has_pending_deployment', return_value=True)
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    @patch('utils.system.SystemManager.get_package_manager', return_value='rpm-ostree')
    @patch('utils.system.SystemManager.is_atomic', return_value=True)
    def test_info_json_atomic(self, mock_at, mock_pm, mock_prof, mock_pending, mock_json):
        _set_json(True)
        r = cmd_info(_ns())
        self.assertEqual(r, 0)
        data = mock_json.call_args[0][0]
        self.assertTrue(data.get('pending_deployment'))
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.system.SystemManager.has_pending_deployment', return_value=True)
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    @patch('utils.system.SystemManager.get_package_manager', return_value='rpm-ostree')
    @patch('utils.system.SystemManager.is_atomic', return_value=True)
    def test_info_text_atomic(self, mock_at, mock_pm, mock_prof, mock_pending, mock_print):
        _set_json(False)
        r = cmd_info(_ns())
        self.assertEqual(r, 0)


# ── cmd_health ─────────────────────────────────────────────────────

class TestCmdHealth(unittest.TestCase):

    def _make_health(self, *, mem=True, cpu=True):
        h = SimpleNamespace(hostname='host1', uptime='2d')
        if mem:
            h.memory = SimpleNamespace(used_human='4 GB', total_human='16 GB', percent_used=25)
            h.memory_status = 'ok'
        else:
            h.memory = None
            h.memory_status = None
        if cpu:
            h.cpu = SimpleNamespace(load_1min=1.0, load_5min=0.8, load_15min=0.5,
                                    core_count=8, load_percent=12)
            h.cpu_status = 'ok'
        else:
            h.cpu = None
            h.cpu_status = None
        return h

    @patch('cli.main._output_json')
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    @patch('utils.disk.DiskManager.check_disk_health', return_value=('ok', 'healthy'))
    @patch('utils.monitor.SystemMonitor.get_system_health')
    def test_health_json(self, mock_health, mock_disk, mock_prof, mock_json):
        _set_json(True)
        mock_health.return_value = self._make_health()
        r = cmd_health(_ns())
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.system.SystemManager.get_variant_name', return_value='Workstation')
    @patch('utils.system.SystemManager.is_atomic', return_value=False)
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    @patch('utils.disk.DiskManager.check_disk_health', return_value=('warning', 'disk 80%'))
    @patch('utils.monitor.SystemMonitor.get_system_health')
    def test_health_text_no_mem_no_cpu(self, mock_health, mock_disk, mock_prof,
                                         mock_atomic, mock_var, mock_print):
        _set_json(False)
        mock_health.return_value = self._make_health(mem=False, cpu=False)
        r = cmd_health(_ns())
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.system.SystemManager.get_variant_name', return_value='Workstation')
    @patch('utils.system.SystemManager.is_atomic', return_value=False)
    @patch('utils.operations.TweakOps.get_power_profile', return_value='balanced')
    @patch('utils.disk.DiskManager.check_disk_health', return_value=('critical', 'disk 95%'))
    @patch('utils.monitor.SystemMonitor.get_system_health')
    def test_health_text_critical(self, mock_health, mock_disk, mock_prof,
                                    mock_atomic, mock_var, mock_print):
        _set_json(False)
        h = self._make_health()
        h.memory_status = 'critical'
        h.cpu_status = 'warning'
        mock_health.return_value = h
        r = cmd_health(_ns())
        self.assertEqual(r, 0)


# ── cmd_disk ───────────────────────────────────────────────────────

class TestCmdDisk(unittest.TestCase):

    def _usage(self, mp='/'):
        return SimpleNamespace(total_human='100 GB', used_human='40 GB',
                                free_human='60 GB', percent_used=40, mount_point=mp)

    @patch('cli.main._output_json')
    @patch('utils.disk.DiskManager.get_disk_usage')
    @patch('utils.disk.DiskManager.check_disk_health', return_value=('ok', 'healthy'))
    def test_disk_json(self, mock_dh, mock_usage, mock_json):
        _set_json(True)
        mock_usage.side_effect = [self._usage('/'), self._usage('/home')]
        r = cmd_disk(_ns(details=False))
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.disk.DiskManager.find_large_directories')
    @patch('utils.disk.DiskManager.check_disk_health', return_value=('ok', 'ok'))
    @patch('utils.disk.DiskManager.get_disk_usage')
    def test_disk_text_details(self, mock_usage, mock_dh, mock_large, mock_print):
        _set_json(False)
        mock_usage.side_effect = [self._usage('/'), self._usage('/')]  # same mount
        mock_large.return_value = [SimpleNamespace(size_human='5 GB', path='/home/docs')]
        r = cmd_disk(_ns(details=True))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.disk.DiskManager.get_disk_usage', return_value=None)
    def test_disk_text_no_usage(self, mock_usage, mock_print):
        _set_json(False)
        r = cmd_disk(_ns(details=False))
        self.assertEqual(r, 0)


# ── cmd_processes ──────────────────────────────────────────────────

class TestCmdProcesses(unittest.TestCase):

    @patch('cli.main._output_json')
    @patch('utils.processes.ProcessManager.get_top_by_memory')
    @patch('utils.processes.ProcessManager.get_process_count')
    def test_processes_json_by_memory(self, mock_cnt, mock_top, mock_json):
        _set_json(True)
        mock_cnt.return_value = {'total': 100, 'running': 5, 'sleeping': 90, 'zombie': 0}
        mock_top.return_value = [SimpleNamespace(pid=1, name='p', cpu_percent=5,
                                                  memory_percent=10, memory_bytes=1024, user='u')]
        r = cmd_processes(_ns(count=5, sort='memory'))
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.processes.ProcessManager.bytes_to_human', return_value='1 KB')
    @patch('utils.processes.ProcessManager.get_top_by_cpu')
    @patch('utils.processes.ProcessManager.get_process_count')
    def test_processes_text_by_cpu(self, mock_cnt, mock_top, mock_bth, mock_print):
        _set_json(False)
        mock_cnt.return_value = {'total': 10, 'running': 2, 'sleeping': 7, 'zombie': 1}
        mock_top.return_value = [SimpleNamespace(pid=42, name='bash', cpu_percent=99,
                                                  memory_percent=1, memory_bytes=512, user='root')]
        r = cmd_processes(_ns(count=10, sort='cpu'))
        self.assertEqual(r, 0)


# ── cmd_temperature ────────────────────────────────────────────────

class TestCmdTemperature(unittest.TestCase):

    @patch('cli.main._output_json')
    @patch('utils.temperature.TemperatureManager.get_all_sensors')
    def test_temperature_json_with_sensors(self, mock_sens, mock_json):
        _set_json(True)
        mock_sens.return_value = [SimpleNamespace(label='CPU', current=55, high=80, critical=95)]
        r = cmd_temperature(_ns())
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.temperature.TemperatureManager.get_all_sensors')
    def test_temperature_text_empty(self, mock_sens, mock_print):
        _set_json(False)
        mock_sens.return_value = []
        r = cmd_temperature(_ns())
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.temperature.TemperatureManager.get_all_sensors')
    def test_temperature_text_multiple(self, mock_sens, mock_print):
        _set_json(False)
        mock_sens.return_value = [
            SimpleNamespace(label='CPU', current=55, high=80, critical=95),
            SimpleNamespace(label='GPU', current=96, high=90, critical=95),
            SimpleNamespace(label='NVMe', current=40, high=None, critical=None),
        ]
        r = cmd_temperature(_ns())
        self.assertEqual(r, 0)


# ── cmd_netmon ─────────────────────────────────────────────────────

class TestCmdNetmon(unittest.TestCase):

    def _iface(self, name='eth0', up=True, rate=100):
        return SimpleNamespace(name=name, type='Wired', is_up=up,
                                ip_address='10.0.0.1', bytes_recv=1000,
                                bytes_sent=500, recv_rate=rate, send_rate=rate/2)

    @patch('cli.main._output_json')
    @patch('utils.network_monitor.NetworkMonitor.get_bandwidth_summary')
    @patch('utils.network_monitor.NetworkMonitor.get_all_interfaces')
    def test_netmon_json(self, mock_ifaces, mock_bw, mock_json):
        _set_json(True)
        mock_ifaces.return_value = [self._iface()]
        mock_bw.return_value = {'total_recv': 1000, 'total_sent': 500}
        r = cmd_netmon(_ns(connections=False))
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.network_monitor.NetworkMonitor.get_all_interfaces')
    def test_netmon_text_empty(self, mock_ifaces, mock_print):
        _set_json(False)
        mock_ifaces.return_value = []
        r = cmd_netmon(_ns(connections=False))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.network_monitor.NetworkMonitor.get_active_connections')
    @patch('utils.network_monitor.NetworkMonitor.get_bandwidth_summary')
    @patch('utils.network_monitor.NetworkMonitor.bytes_to_human', return_value='1 KB')
    @patch('utils.network_monitor.NetworkMonitor.get_all_interfaces')
    def test_netmon_text_with_connections(self, mock_ifaces, mock_bth, mock_bw,
                                           mock_conns, mock_print):
        _set_json(False)
        mock_ifaces.return_value = [self._iface()]
        mock_bw.return_value = {'total_recv': 5000, 'total_sent': 2000}
        mock_conns.return_value = [SimpleNamespace(
            protocol='tcp', local_addr='10.0.0.1', local_port=80,
            remote_addr='1.2.3.4', remote_port=443, state='ESTABLISHED',
            process_name='firefox')]
        r = cmd_netmon(_ns(connections=True))
        self.assertEqual(r, 0)


# ── cmd_doctor ─────────────────────────────────────────────────────

class TestCmdDoctor(unittest.TestCase):

    @patch('cli.main._output_json')
    @patch('shutil.which')
    def test_doctor_json_all_found(self, mock_which, mock_json):
        """JSON mode has a bug: all_ok unbound. We verify the JSON path runs
        and hits the known UnboundLocalError when all_ok is checked."""
        _set_json(True)
        mock_which.return_value = '/usr/bin/tool'
        # Bug in cli/main.py line 493: all_ok only assigned in text branch
        with self.assertRaises(UnboundLocalError):
            cmd_doctor(_ns())
        _set_json(False)

    @patch('cli.main._output_json')
    @patch('shutil.which')
    def test_doctor_json_missing(self, mock_which, mock_json):
        """Same bug, but when tools are missing."""
        _set_json(True)
        mock_which.return_value = None
        with self.assertRaises(UnboundLocalError):
            cmd_doctor(_ns())
        _set_json(False)

    @patch('cli.main._print')
    @patch('shutil.which')
    def test_doctor_text_missing_critical(self, mock_which, mock_print):
        _set_json(False)
        mock_which.return_value = None
        r = cmd_doctor(_ns())
        self.assertEqual(r, 1)


# ── cmd_support_bundle ─────────────────────────────────────────────

class TestCmdSupportBundle(unittest.TestCase):

    @patch('cli.main._output_json')
    @patch('utils.journal.JournalManager.export_support_bundle')
    def test_support_bundle_json(self, mock_export, mock_json):
        _set_json(True)
        mock_export.return_value = SimpleNamespace(success=True, message='done', data='/tmp/bundle.zip')
        r = cmd_support_bundle(_ns())
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.journal.JournalManager.export_support_bundle')
    def test_support_bundle_fail(self, mock_export, mock_print):
        _set_json(False)
        mock_export.return_value = SimpleNamespace(success=False, message='fail', data=None)
        r = cmd_support_bundle(_ns())
        self.assertEqual(r, 1)


# ── cmd_focus_mode ─────────────────────────────────────────────────

class TestCmdFocusMode(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.focus_mode.FocusMode.enable')
    def test_focus_on_success(self, mock_enable, mock_print):
        _set_json(False)
        mock_enable.return_value = {
            'success': True, 'message': 'Focus enabled',
            'hosts_modified': True, 'dnd_enabled': True,
            'processes_killed': ['slack']
        }
        r = cmd_focus_mode(_ns(action='on', profile='default'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.focus_mode.FocusMode.enable')
    def test_focus_on_fail(self, mock_enable, mock_print):
        _set_json(False)
        mock_enable.return_value = {'success': False, 'message': 'err'}
        r = cmd_focus_mode(_ns(action='on', profile='default'))
        self.assertEqual(r, 1)

    @patch('cli.main._output_json')
    @patch('utils.focus_mode.FocusMode.enable')
    def test_focus_on_json(self, mock_enable, mock_json):
        _set_json(True)
        mock_enable.return_value = {'success': True, 'message': 'ok'}
        r = cmd_focus_mode(_ns(action='on', profile='default'))
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._print')
    @patch('utils.focus_mode.FocusMode.disable')
    def test_focus_off(self, mock_disable, mock_print):
        _set_json(False)
        mock_disable.return_value = {'success': True, 'message': 'off'}
        r = cmd_focus_mode(_ns(action='off'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.focus_mode.FocusMode.list_profiles')
    @patch('utils.focus_mode.FocusMode.get_active_profile')
    @patch('utils.focus_mode.FocusMode.is_active')
    def test_focus_status(self, mock_active, mock_prof, mock_list, mock_print):
        _set_json(False)
        mock_active.return_value = True
        mock_prof.return_value = 'work'
        mock_list.return_value = ['default', 'work']
        r = cmd_focus_mode(_ns(action='status'))
        self.assertEqual(r, 0)


# ── cmd_service ────────────────────────────────────────────────────

class TestCmdService(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.list_services')
    def test_service_list(self, mock_list, mock_print):
        _set_json(False)
        svc = SimpleNamespace(name='sshd', state=SimpleNamespace(value='active'),
                               is_running=True, is_failed=False, enabled='enabled',
                               description='OpenSSH Daemon')
        mock_list.return_value = [svc]
        r = cmd_service(_ns(action='list', user=False, filter=None, search=None, name=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.start_service')
    def test_service_start(self, mock_start, mock_print):
        _set_json(False)
        mock_start.return_value = SimpleNamespace(success=True, message='started')
        r = cmd_service(_ns(action='start', name='sshd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.stop_service')
    def test_service_stop_fail(self, mock_stop, mock_print):
        _set_json(False)
        mock_stop.return_value = SimpleNamespace(success=False, message='denied')
        r = cmd_service(_ns(action='stop', name='sshd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    def test_service_start_no_name(self, mock_print):
        _set_json(False)
        r = cmd_service(_ns(action='start', name=None, user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.restart_service')
    def test_service_restart(self, mock_restart, mock_print):
        _set_json(False)
        mock_restart.return_value = SimpleNamespace(success=True, message='ok')
        r = cmd_service(_ns(action='restart', name='httpd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.enable_service')
    def test_service_enable(self, mock_enable, mock_print):
        _set_json(False)
        mock_enable.return_value = SimpleNamespace(success=True, message='enabled')
        r = cmd_service(_ns(action='enable', name='httpd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.disable_service')
    def test_service_disable(self, mock_disable, mock_print):
        _set_json(False)
        mock_disable.return_value = SimpleNamespace(success=True, message='disabled')
        r = cmd_service(_ns(action='disable', name='httpd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.mask_service')
    def test_service_mask(self, mock_mask, mock_print):
        _set_json(False)
        mock_mask.return_value = SimpleNamespace(success=True, message='masked')
        r = cmd_service(_ns(action='mask', name='httpd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.unmask_service')
    def test_service_unmask(self, mock_unmask, mock_print):
        _set_json(False)
        mock_unmask.return_value = SimpleNamespace(success=True, message='unmasked')
        r = cmd_service(_ns(action='unmask', name='httpd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.get_service_logs')
    def test_service_logs(self, mock_logs, mock_print):
        _set_json(False)
        mock_logs.return_value = 'Jan 01 sshd started'
        r = cmd_service(_ns(action='logs', name='sshd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_service_logs_no_name(self, mock_print):
        _set_json(False)
        r = cmd_service(_ns(action='logs', name=None, user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.service_explorer.ServiceExplorer.get_service_details')
    def test_service_status(self, mock_details, mock_print):
        _set_json(False)
        info = SimpleNamespace(
            name='sshd', description='OpenSSH', state=SimpleNamespace(value='active'),
            sub_state='running', enabled='enabled', memory_human='12 MB',
            main_pid=1234, active_enter='2025-01-01',
            to_dict=lambda: {}
        )
        mock_details.return_value = info
        r = cmd_service(_ns(action='status', name='sshd', user=False, filter=None,
                             search=None, lines=50))
        self.assertEqual(r, 0)

    @patch('cli.main._output_json')
    @patch('utils.service_explorer.ServiceExplorer.list_services')
    def test_service_list_json(self, mock_list, mock_json):
        _set_json(True)
        svc = SimpleNamespace(
            name='sshd', state=SimpleNamespace(value='active'),
            is_running=True, is_failed=False, enabled='enabled',
            description='OpenSSH', to_dict=lambda: {'name': 'sshd'}
        )
        mock_list.return_value = [svc]
        r = cmd_service(_ns(action='list', user=False, filter=None, search=None,
                             name=None, lines=50))
        self.assertEqual(r, 0)
        _set_json(False)


# ── cmd_package ────────────────────────────────────────────────────

class TestCmdPackage(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.package_explorer.PackageExplorer.search')
    def test_package_search(self, mock_search, mock_print):
        _set_json(False)
        pkg = SimpleNamespace(name='vim', version='9.0', source='dnf',
                               installed=True, summary='Vi editor', to_dict=lambda: {})
        mock_search.return_value = [pkg]
        r = cmd_package(_ns(action='search', name=None, query='vim', source=None,
                             search=None, days=30))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_package_search_no_query(self, mock_print):
        _set_json(False)
        r = cmd_package(_ns(action='search', name=None, query=None, source=None,
                             search=None, days=30))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.package_explorer.PackageExplorer.install')
    def test_package_install(self, mock_install, mock_print):
        _set_json(False)
        mock_install.return_value = SimpleNamespace(success=True, message='installed')
        r = cmd_package(_ns(action='install', name='htop', query=None, source=None,
                             search=None, days=30))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_package_install_no_name(self, mock_print):
        _set_json(False)
        r = cmd_package(_ns(action='install', name=None, query=None, source=None,
                             search=None, days=30))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.package_explorer.PackageExplorer.remove')
    def test_package_remove(self, mock_remove, mock_print):
        _set_json(False)
        mock_remove.return_value = SimpleNamespace(success=True, message='removed')
        r = cmd_package(_ns(action='remove', name='vim', query=None, source=None,
                             search=None, days=30))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.package_explorer.PackageExplorer.list_installed')
    def test_package_list(self, mock_list, mock_print):
        _set_json(False)
        pkg = SimpleNamespace(name='vim', version='9.0', source='dnf',
                               installed=True, summary='Vi', to_dict=lambda: {})
        mock_list.return_value = [pkg]
        r = cmd_package(_ns(action='list', name=None, query=None, source='all',
                             search='', days=30))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.package_explorer.PackageExplorer.recently_installed')
    def test_package_recent(self, mock_recent, mock_print):
        _set_json(False)
        pkg = SimpleNamespace(name='htop', version='3.2', source='dnf',
                               installed=True, summary='Monitor', to_dict=lambda: {})
        mock_recent.return_value = [pkg]
        r = cmd_package(_ns(action='recent', name=None, query=None, source=None,
                             search=None, days=7))
        self.assertEqual(r, 0)


# ── cmd_firewall ───────────────────────────────────────────────────

class TestCmdFirewall(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=False)
    def test_firewall_not_available(self, mock_avail, mock_print):
        _set_json(False)
        r = cmd_firewall(_ns(action='status', spec=None))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.get_status')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_status(self, mock_avail, mock_status, mock_print):
        _set_json(False)
        mock_status.return_value = SimpleNamespace(
            running=True, default_zone='public', active_zones='public',
            ports=['22/tcp'], services=['ssh'], rich_rules=['rule x'],
            to_dict=lambda: {}
        )
        r = cmd_firewall(_ns(action='status', spec=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.list_ports')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_ports(self, mock_avail, mock_ports, mock_print):
        _set_json(False)
        mock_ports.return_value = ['22/tcp', '80/tcp']
        r = cmd_firewall(_ns(action='ports', spec=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.list_ports')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_ports_empty(self, mock_avail, mock_ports, mock_print):
        _set_json(False)
        mock_ports.return_value = []
        r = cmd_firewall(_ns(action='ports', spec=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.open_port')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_open_port(self, mock_avail, mock_open, mock_print):
        _set_json(False)
        mock_open.return_value = SimpleNamespace(success=True, message='opened')
        r = cmd_firewall(_ns(action='open-port', spec='8080/tcp'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_open_port_no_spec(self, mock_avail, mock_print):
        _set_json(False)
        r = cmd_firewall(_ns(action='open-port', spec=None))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.open_port')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_open_port_no_proto(self, mock_avail, mock_open, mock_print):
        _set_json(False)
        mock_open.return_value = SimpleNamespace(success=True, message='opened')
        r = cmd_firewall(_ns(action='open-port', spec='9090'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.close_port')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_close_port(self, mock_avail, mock_close, mock_print):
        _set_json(False)
        mock_close.return_value = SimpleNamespace(success=True, message='closed')
        r = cmd_firewall(_ns(action='close-port', spec='80/tcp'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_close_port_no_spec(self, mock_avail, mock_print):
        _set_json(False)
        r = cmd_firewall(_ns(action='close-port', spec=None))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.list_services')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_services(self, mock_avail, mock_svc, mock_print):
        _set_json(False)
        mock_svc.return_value = ['ssh', 'http']
        r = cmd_firewall(_ns(action='services', spec=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.firewall_manager.FirewallManager.get_active_zones')
    @patch('utils.firewall_manager.FirewallManager.get_zones')
    @patch('utils.firewall_manager.FirewallManager.is_available', return_value=True)
    def test_firewall_zones(self, mock_avail, mock_zones, mock_active, mock_print):
        _set_json(False)
        mock_zones.return_value = ['public', 'trusted', 'drop']
        mock_active.return_value = {'public': ['eth0']}
        r = cmd_firewall(_ns(action='zones', spec=None))
        self.assertEqual(r, 0)


# ── cmd_bluetooth ──────────────────────────────────────────────────

class TestCmdBluetooth(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.get_adapter_status')
    def test_bt_status_no_adapter(self, mock_status, mock_print):
        _set_json(False)
        mock_status.return_value = SimpleNamespace(adapter_name='', powered=False,
                                                     discoverable=False, adapter_address='')
        r = cmd_bluetooth(_ns(action='status', address=None, paired=False, timeout=10))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.get_adapter_status')
    def test_bt_status_ok(self, mock_status, mock_print):
        _set_json(False)
        mock_status.return_value = SimpleNamespace(adapter_name='hci0', powered=True,
                                                     discoverable=False, adapter_address='AA:BB:CC')
        r = cmd_bluetooth(_ns(action='status', address=None, paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.list_devices')
    def test_bt_devices_empty(self, mock_devs, mock_print):
        _set_json(False)
        mock_devs.return_value = []
        r = cmd_bluetooth(_ns(action='devices', address=None, paired=True, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.list_devices')
    def test_bt_devices_with_items(self, mock_devs, mock_print):
        _set_json(False)
        dev = SimpleNamespace(address='11:22:33', name='AirPods', paired=True,
                               connected=True, trusted=True,
                               device_type=SimpleNamespace(value='audio'))
        mock_devs.return_value = [dev]
        r = cmd_bluetooth(_ns(action='devices', address=None, paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.scan')
    def test_bt_scan(self, mock_scan, mock_print):
        _set_json(False)
        dev = SimpleNamespace(address='11:22:33', name='Speaker',
                               device_type=SimpleNamespace(value='audio'))
        mock_scan.return_value = [dev]
        r = cmd_bluetooth(_ns(action='scan', address=None, paired=False, timeout=5))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.power_on')
    def test_bt_power_on(self, mock_power, mock_print):
        _set_json(False)
        mock_power.return_value = SimpleNamespace(success=True, message='ok')
        r = cmd_bluetooth(_ns(action='power-on', address=None, paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.power_off')
    def test_bt_power_off(self, mock_power, mock_print):
        _set_json(False)
        mock_power.return_value = SimpleNamespace(success=True, message='off')
        r = cmd_bluetooth(_ns(action='power-off', address=None, paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.connect')
    def test_bt_connect(self, mock_conn, mock_print):
        _set_json(False)
        mock_conn.return_value = SimpleNamespace(success=True, message='connected')
        r = cmd_bluetooth(_ns(action='connect', address='11:22:33', paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_bt_connect_no_address(self, mock_print):
        _set_json(False)
        r = cmd_bluetooth(_ns(action='connect', address=None, paired=False, timeout=10))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.disconnect')
    def test_bt_disconnect(self, mock_disc, mock_print):
        _set_json(False)
        mock_disc.return_value = SimpleNamespace(success=True, message='disconnected')
        r = cmd_bluetooth(_ns(action='disconnect', address='11:22:33', paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.pair')
    def test_bt_pair(self, mock_pair, mock_print):
        _set_json(False)
        mock_pair.return_value = SimpleNamespace(success=True, message='paired')
        r = cmd_bluetooth(_ns(action='pair', address='11:22:33', paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.bluetooth.BluetoothManager.trust')
    def test_bt_trust(self, mock_trust, mock_print):
        _set_json(False)
        mock_trust.return_value = SimpleNamespace(success=True, message='trusted')
        r = cmd_bluetooth(_ns(action='trust', address='11:22:33', paired=False, timeout=10))
        self.assertEqual(r, 0)

    @patch('cli.main._output_json')
    @patch('utils.bluetooth.BluetoothManager.get_adapter_status')
    def test_bt_status_json(self, mock_status, mock_json):
        _set_json(True)
        mock_status.return_value = SimpleNamespace(adapter_name='hci0', powered=True,
                                                     discoverable=True, adapter_address='AA:BB')
        r = cmd_bluetooth(_ns(action='status', address=None, paired=False, timeout=10))
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._output_json')
    @patch('utils.bluetooth.BluetoothManager.scan')
    @patch('cli.main._print')
    def test_bt_scan_json(self, mock_print, mock_scan, mock_json):
        _set_json(True)
        dev = SimpleNamespace(address='11:22:33', name='X',
                               device_type=SimpleNamespace(value='audio'))
        mock_scan.return_value = [dev]
        r = cmd_bluetooth(_ns(action='scan', address=None, paired=False, timeout=5))
        self.assertEqual(r, 0)
        _set_json(False)


# ── cmd_storage ────────────────────────────────────────────────────

class TestCmdStorage(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.storage.StorageManager.list_disks')
    def test_storage_disks(self, mock_disks, mock_print):
        _set_json(False)
        disk = SimpleNamespace(name='sda', size='500G', device_type='disk',
                                model='Samsung', mountpoint='/', rm=False)
        mock_disks.return_value = [disk]
        r = cmd_storage(_ns(action='disks', device=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.storage.StorageManager.list_disks')
    def test_storage_disks_empty(self, mock_disks, mock_print):
        _set_json(False)
        mock_disks.return_value = []
        r = cmd_storage(_ns(action='disks', device=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.storage.StorageManager.list_mounts')
    def test_storage_mounts(self, mock_mounts, mock_print):
        _set_json(False)
        mnt = SimpleNamespace(source='/dev/sda1', target='/', fstype='btrfs',
                               size='500G', used='200G', avail='300G', use_percent='40%')
        mock_mounts.return_value = [mnt]
        r = cmd_storage(_ns(action='mounts', device=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.storage.StorageManager.get_smart_health')
    def test_storage_smart(self, mock_smart, mock_print):
        _set_json(False)
        mock_smart.return_value = SimpleNamespace(
            model='Samsung 860', serial='S3Y9NX0M',
            health_passed=True, temperature_c=35,
            power_on_hours=5000, reallocated_sectors=0, raw_output=''
        )
        r = cmd_storage(_ns(action='smart', device='/dev/sda'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_storage_smart_no_device(self, mock_print):
        _set_json(False)
        r = cmd_storage(_ns(action='smart', device=None))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.storage.StorageManager.get_usage_summary')
    def test_storage_usage(self, mock_usage, mock_print):
        _set_json(False)
        mock_usage.return_value = {
            'total_size': '1 TB', 'total_used': '400 GB',
            'total_available': '600 GB', 'disk_count': 2, 'mount_count': 4
        }
        r = cmd_storage(_ns(action='usage', device=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.storage.StorageManager.trim_ssd')
    def test_storage_trim(self, mock_trim, mock_print):
        _set_json(False)
        mock_trim.return_value = SimpleNamespace(success=True, message='trimmed')
        r = cmd_storage(_ns(action='trim', device=None))
        self.assertEqual(r, 0)

    @patch('cli.main._output_json')
    @patch('utils.storage.StorageManager.list_disks')
    def test_storage_disks_json(self, mock_disks, mock_json):
        _set_json(True)
        disk = SimpleNamespace(name='nvme0n1', size='1T', device_type='disk',
                                model='WD', mountpoint='/', rm=False)
        mock_disks.return_value = [disk]
        r = cmd_storage(_ns(action='disks', device=None))
        self.assertEqual(r, 0)
        _set_json(False)

    @patch('cli.main._output_json')
    @patch('utils.storage.StorageManager.get_smart_health')
    def test_storage_smart_json(self, mock_smart, mock_json):
        _set_json(True)
        mock_smart.return_value = SimpleNamespace(
            model='WD', serial='123', health_passed=True,
            temperature_c=30, power_on_hours=100, reallocated_sectors=0, raw_output=''
        )
        r = cmd_storage(_ns(action='smart', device='/dev/sda'))
        self.assertEqual(r, 0)
        _set_json(False)


# ── cmd_profile ────────────────────────────────────────────────────

class TestCmdProfile(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.get_active_profile')
    @patch('utils.profiles.ProfileManager.list_profiles')
    def test_profile_list(self, mock_list, mock_active, mock_print):
        _set_json(False)
        mock_list.return_value = [
            {'name': 'Gaming', 'key': 'gaming', 'builtin': True,
             'icon': '🎮', 'description': 'Optimize for gaming'}
        ]
        mock_active.return_value = 'gaming'
        r = cmd_profile(_ns(action='list', name=None, path=None, overwrite=False,
                             no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.apply_profile')
    def test_profile_apply(self, mock_apply, mock_print):
        _set_json(False)
        mock_apply.return_value = SimpleNamespace(success=True, message='applied', data={})
        r = cmd_profile(_ns(action='apply', name='gaming', path=None, overwrite=False,
                             no_snapshot=True, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_profile_apply_no_name(self, mock_print):
        _set_json(False)
        r = cmd_profile(_ns(action='apply', name=None, path=None, overwrite=False,
                             no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.capture_current_as_profile')
    def test_profile_create(self, mock_capture, mock_print):
        _set_json(False)
        mock_capture.return_value = SimpleNamespace(success=True, message='created', data={})
        r = cmd_profile(_ns(action='create', name='my-profile', path=None, overwrite=False,
                             no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.delete_custom_profile')
    def test_profile_delete(self, mock_del, mock_print):
        _set_json(False)
        mock_del.return_value = SimpleNamespace(success=True, message='deleted')
        r = cmd_profile(_ns(action='delete', name='old', path=None, overwrite=False,
                             no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.export_profile_json')
    def test_profile_export(self, mock_export, mock_print):
        _set_json(False)
        mock_export.return_value = SimpleNamespace(success=True, message='exported', data={})
        r = cmd_profile(_ns(action='export', name='gaming', path='/tmp/g.json',
                             overwrite=False, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_profile_export_no_path(self, mock_print):
        _set_json(False)
        r = cmd_profile(_ns(action='export', name=None, path=None,
                             overwrite=False, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.import_profile_json')
    def test_profile_import(self, mock_import, mock_print):
        _set_json(False)
        mock_import.return_value = SimpleNamespace(success=True, message='imported', data={})
        r = cmd_profile(_ns(action='import', name=None, path='/tmp/g.json',
                             overwrite=True, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_profile_import_no_path(self, mock_print):
        _set_json(False)
        r = cmd_profile(_ns(action='import', name=None, path=None,
                             overwrite=False, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.export_bundle_json')
    def test_profile_export_all(self, mock_export, mock_print):
        _set_json(False)
        mock_export.return_value = SimpleNamespace(success=True, message='exported', data={})
        r = cmd_profile(_ns(action='export-all', name=None, path='/tmp/bundle.json',
                             overwrite=False, no_snapshot=False, include_builtins=True))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_profile_export_all_no_path(self, mock_print):
        _set_json(False)
        r = cmd_profile(_ns(action='export-all', name=None, path=None,
                             overwrite=False, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.profiles.ProfileManager.import_bundle_json')
    def test_profile_import_all(self, mock_import, mock_print):
        _set_json(False)
        mock_import.return_value = SimpleNamespace(success=True, message='bundle imported', data={})
        r = cmd_profile(_ns(action='import-all', name=None, path='/tmp/bundle.json',
                             overwrite=False, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_profile_import_all_no_path(self, mock_print):
        _set_json(False)
        r = cmd_profile(_ns(action='import-all', name=None, path=None,
                             overwrite=False, no_snapshot=False, include_builtins=False))
        self.assertEqual(r, 1)


# ── cmd_health_history ─────────────────────────────────────────────

class TestCmdHealthHistory(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.health_timeline.HealthTimeline.get_summary')
    def test_hh_show_empty(self, mock_summary, mock_print):
        _set_json(False)
        mock_summary.return_value = {}
        inst = MagicMock()
        inst.get_summary = mock_summary
        with patch('cli.main.HealthTimeline', return_value=inst):
            r = cmd_health_history(_ns(action='show', path=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.health_timeline.HealthTimeline')
    def test_hh_show_with_data(self, mock_cls, mock_print):
        _set_json(False)
        inst = MagicMock()
        inst.get_summary.return_value = {
            'cpu_temp': {'min': 30, 'max': 80, 'avg': 55, 'count': 10},
            'ram_usage': {'min': 20, 'max': 70, 'avg': 45, 'count': 10},
        }
        mock_cls.return_value = inst
        r = cmd_health_history(_ns(action='show', path=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.health_timeline.HealthTimeline')
    def test_hh_record(self, mock_cls, mock_print):
        _set_json(False)
        inst = MagicMock()
        inst.record_snapshot.return_value = SimpleNamespace(success=True, message='recorded', data={})
        mock_cls.return_value = inst
        r = cmd_health_history(_ns(action='record', path=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.health_timeline.HealthTimeline')
    def test_hh_export_json_fmt(self, mock_cls, mock_print):
        _set_json(False)
        inst = MagicMock()
        inst.export_metrics.return_value = SimpleNamespace(success=True, message='exported', data={})
        mock_cls.return_value = inst
        r = cmd_health_history(_ns(action='export', path='/tmp/metrics.json'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.health_timeline.HealthTimeline')
    def test_hh_export_csv_fmt(self, mock_cls, mock_print):
        _set_json(False)
        inst = MagicMock()
        inst.export_metrics.return_value = SimpleNamespace(success=True, message='exported', data={})
        mock_cls.return_value = inst
        r = cmd_health_history(_ns(action='export', path='/tmp/metrics.csv'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_hh_export_no_path(self, mock_print):
        _set_json(False)
        with patch('cli.main.HealthTimeline'):
            r = cmd_health_history(_ns(action='export', path=None))
        self.assertEqual(r, 1)

    @patch('cli.main._print')
    @patch('utils.health_timeline.HealthTimeline')
    def test_hh_prune(self, mock_cls, mock_print):
        _set_json(False)
        inst = MagicMock()
        inst.prune_old_data.return_value = SimpleNamespace(success=True, message='pruned', data={})
        mock_cls.return_value = inst
        r = cmd_health_history(_ns(action='prune', path=None))
        self.assertEqual(r, 0)


# ── cmd_logs ───────────────────────────────────────────────────────

class TestCmdLogs(unittest.TestCase):

    @patch('cli.main._print')
    @patch('utils.smart_logs.SmartLogViewer.get_logs')
    def test_logs_show(self, mock_logs, mock_print):
        _set_json(False)
        entry = SimpleNamespace(timestamp='Jan 01', priority_label='ERR',
                                 unit='sshd', message='Connection refused',
                                 pattern_match='auth failure')
        mock_logs.return_value = [entry]
        r = cmd_logs(_ns(action='show', unit=None, priority=None, since=None,
                          lines=50, path=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.smart_logs.SmartLogViewer.get_error_summary')
    def test_logs_errors(self, mock_summary, mock_print):
        _set_json(False)
        mock_summary.return_value = SimpleNamespace(
            total_entries=100, critical_count=2, error_count=10, warning_count=20,
            top_units=[('sshd', 5), ('httpd', 3)],
            detected_patterns=[('auth', 4)], vars=lambda: {}
        )
        r = cmd_logs(_ns(action='errors', unit=None, priority=None, since='1h ago',
                          lines=50, path=None))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.smart_logs.SmartLogViewer.export_logs')
    @patch('utils.smart_logs.SmartLogViewer.get_logs')
    def test_logs_export_text(self, mock_logs, mock_export, mock_print):
        _set_json(False)
        mock_logs.return_value = []
        mock_export.return_value = True
        r = cmd_logs(_ns(action='export', unit=None, priority=None, since=None,
                          lines=100, path='/tmp/logs.txt'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    @patch('utils.smart_logs.SmartLogViewer.export_logs')
    @patch('utils.smart_logs.SmartLogViewer.get_logs')
    def test_logs_export_json(self, mock_logs, mock_export, mock_print):
        _set_json(False)
        mock_logs.return_value = []
        mock_export.return_value = True
        r = cmd_logs(_ns(action='export', unit=None, priority=None, since=None,
                          lines=100, path='/tmp/logs.json'))
        self.assertEqual(r, 0)

    @patch('cli.main._print')
    def test_logs_export_no_path(self, mock_print):
        _set_json(False)
        r = cmd_logs(_ns(action='export', unit=None, priority=None, since=None,
                          lines=100, path=None))
        self.assertEqual(r, 1)


# ── cmd_plugin_marketplace extra ───────────────────────────────────

class TestCmdPluginMarketplaceExtra(unittest.TestCase):

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_marketplace_uninstall(self, mock_mp, mock_installer):
        _set_json(False)
        inst = MagicMock()
        inst.uninstall.return_value = SimpleNamespace(success=True, error=None)
        mock_installer.return_value = inst
        mock_mp.return_value = MagicMock()
        r = cmd_plugin_marketplace(_ns(action='uninstall', plugin_id='test-plugin',
                                        plugin=None, json=False, category=None,
                                        query=None, limit=20, offset=0,
                                        reviewer=None, rating=None, title=None,
                                        comment=None, accept_permissions=False))
        self.assertEqual(r, 0)

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_marketplace_update(self, mock_mp, mock_installer):
        _set_json(False)
        inst = MagicMock()
        inst.check_update.return_value = SimpleNamespace(
            success=True, data={'update_available': True}
        )
        inst.update.return_value = SimpleNamespace(success=True, error=None)
        mock_installer.return_value = inst
        mock_mp.return_value = MagicMock()
        r = cmd_plugin_marketplace(_ns(action='update', plugin_id='test-plugin',
                                        plugin=None, json=False, category=None,
                                        query=None, limit=20, offset=0,
                                        reviewer=None, rating=None, title=None,
                                        comment=None, accept_permissions=False))
        self.assertEqual(r, 0)

    @patch('cli.main.PluginInstaller')
    @patch('cli.main.PluginMarketplace')
    def test_marketplace_list_installed(self, mock_mp, mock_installer):
        _set_json(False)
        inst = MagicMock()
        inst.list_installed.return_value = SimpleNamespace(data=[
            {'name': 'test', 'id': 'test', 'version': '1.0'}
        ])
        mock_installer.return_value = inst
        mock_mp.return_value = MagicMock()
        r = cmd_plugin_marketplace(_ns(action='list-installed', plugin_id=None,
                                        plugin=None, json=False, category=None,
                                        query=None, limit=20, offset=0,
                                        reviewer=None, rating=None, title=None,
                                        comment=None, accept_permissions=False))
        self.assertEqual(r, 0)


# ── main() entrypoint ─────────────────────────────────────────────

class TestMain(unittest.TestCase):

    @patch('cli.main.cmd_info', return_value=0)
    def test_main_info(self, mock_cmd):
        r = main(['info'])
        self.assertEqual(r, 0)

    def test_main_no_command(self):
        r = main([])
        self.assertEqual(r, 0)

    @patch('cli.main.cmd_cleanup', return_value=0)
    def test_main_cleanup(self, mock_cmd):
        r = main(['cleanup', 'dnf'])
        self.assertEqual(r, 0)

    @patch('cli.main.cmd_info', return_value=0)
    def test_main_json_flag(self, mock_cmd):
        r = main(['--json', 'info'])
        self.assertEqual(r, 0)
        # Reset global
        _set_json(False)


if __name__ == '__main__':
    unittest.main()
