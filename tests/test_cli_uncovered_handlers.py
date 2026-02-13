"""Tests for uncovered CLI handlers in cli/main.py."""

import argparse
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from cli.main import (
    cmd_agent,
    cmd_ai_models,
    cmd_mesh,
    cmd_security_audit,
    cmd_teleport,
    cmd_vfio,
    cmd_vm,
)


class TestVMHandlers(unittest.TestCase):
    """Tests for VM-related CLI handlers."""

    @patch('cli.main._print')
    @patch('utils.vm_manager.VMManager.list_vms')
    def test_vm_list_empty(self, mock_list, mock_print):
        mock_list.return_value = []
        result = cmd_vm(argparse.Namespace(action='list', name=None))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.vm_manager.VMManager.get_vm_info')
    def test_vm_status_not_found(self, mock_info, mock_print):
        mock_info.return_value = None
        result = cmd_vm(argparse.Namespace(action='status', name='missing-vm'))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.vm_manager.VMManager.start_vm')
    def test_vm_start_failure(self, mock_start, mock_print):
        mock_start.return_value = SimpleNamespace(success=False, message='boom')
        result = cmd_vm(argparse.Namespace(action='start', name='vm1'))
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('utils.vm_manager.VMManager.stop_vm')
    def test_vm_stop_success(self, mock_stop, mock_print):
        mock_stop.return_value = SimpleNamespace(success=True, message='ok')
        result = cmd_vm(argparse.Namespace(action='stop', name='vm1'))
        self.assertEqual(result, 0)


class TestVfioMeshAiHandlers(unittest.TestCase):
    """Tests for VFIO, mesh and AI model CLI handlers."""

    @patch('cli.main._print')
    @patch('utils.vfio.VFIOAssistant.check_prerequisites')
    def test_vfio_check(self, mock_check, mock_print):
        mock_check.return_value = {'iommu': True, 'virt': False}
        result = cmd_vfio(argparse.Namespace(action='check'))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.vfio.VFIOAssistant.get_passthrough_candidates')
    def test_vfio_gpus_empty(self, mock_candidates, mock_print):
        mock_candidates.return_value = []
        result = cmd_vfio(argparse.Namespace(action='gpus'))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.vfio.VFIOAssistant.get_step_by_step_plan')
    def test_vfio_plan(self, mock_plan, mock_print):
        mock_plan.return_value = ['Enable IOMMU', 'Bind GPU']
        result = cmd_vfio(argparse.Namespace(action='plan'))
        self.assertEqual(result, 0)

    @patch('utils.mesh_discovery.MeshDiscovery.discover_peers')
    @patch('cli.main._print')
    def test_mesh_discover_empty(self, mock_print, mock_discover):
        mock_discover.return_value = []
        result = cmd_mesh(argparse.Namespace(action='discover'))
        self.assertEqual(result, 0)

    @patch('utils.mesh_discovery.MeshDiscovery.get_local_ips')
    @patch('utils.mesh_discovery.MeshDiscovery.get_device_id')
    @patch('cli.main._print')
    def test_mesh_status(self, mock_print, mock_device, mock_ips):
        mock_device.return_value = 'abc-123'
        mock_ips.return_value = ['192.168.1.20']
        result = cmd_mesh(argparse.Namespace(action='status'))
        self.assertEqual(result, 0)

    @patch('utils.ai_models.AIModelManager.get_installed_models')
    @patch.object(__import__('utils.ai_models', fromlist=['AIModelManager']).AIModelManager, 'RECOMMENDED_MODELS', {'llama3.2:3b': {'description': 'test'}}, create=True)
    @patch('cli.main._print')
    def test_ai_models_list(self, mock_print, mock_installed):
        mock_installed.return_value = ['llama3.2:3b']
        result = cmd_ai_models(argparse.Namespace(action='list'))
        self.assertEqual(result, 0)

    @patch('utils.ai_models.AIModelManager.get_recommended_model')
    @patch('cli.main._print')
    def test_ai_models_recommend_none(self, mock_print, mock_recommend):
        mock_recommend.return_value = None
        result = cmd_ai_models(argparse.Namespace(action='recommend'))
        self.assertEqual(result, 0)


class TestTeleportAndSecurityHandlers(unittest.TestCase):
    """Tests for teleport and security audit command handlers."""

    @patch('cli.main._print')
    @patch('utils.state_teleport.StateTeleportManager.save_package_to_file')
    @patch('utils.state_teleport.StateTeleportManager.get_package_dir')
    @patch('utils.state_teleport.StateTeleportManager.create_teleport_package')
    @patch('utils.state_teleport.StateTeleportManager.capture_full_state')
    def test_teleport_capture_success(
        self,
        mock_capture,
        mock_create,
        mock_pkg_dir,
        mock_save,
        mock_print,
    ):
        mock_capture.return_value = {'state': 1}
        mock_create.return_value = SimpleNamespace(package_id='pkg123', size_bytes=321)
        mock_pkg_dir.return_value = '/tmp'
        mock_save.return_value = SimpleNamespace(success=True, message='saved')
        args = argparse.Namespace(action='capture', path='/tmp/ws', target='laptop')
        result = cmd_teleport(args)
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.state_teleport.StateTeleportManager.list_saved_packages')
    def test_teleport_list_empty(self, mock_list, mock_print):
        mock_list.return_value = []
        result = cmd_teleport(argparse.Namespace(action='list', package_id=None))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    def test_teleport_restore_requires_id(self, mock_print):
        result = cmd_teleport(argparse.Namespace(action='restore', package_id=None))
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('os.listdir')
    @patch('utils.state_teleport.StateTeleportManager.get_package_dir')
    def test_teleport_restore_not_found(self, mock_pkg_dir, mock_listdir, mock_print):
        mock_pkg_dir.return_value = '/tmp/pkgs'
        mock_listdir.return_value = ['other-package.json']
        result = cmd_teleport(argparse.Namespace(action='restore', package_id='wanted'))
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('utils.ports.PortAuditor.is_firewalld_running')
    @patch('utils.ports.PortAuditor.get_security_score')
    def test_security_audit_success(self, mock_score, mock_fw, mock_print):
        mock_fw.return_value = True
        mock_score.return_value = {
            'score': 88,
            'rating': 'Good',
            'open_ports': 3,
            'risky_ports': 0,
            'recommendations': ['Keep firewall enabled'],
        }
        result = cmd_security_audit(argparse.Namespace())
        self.assertEqual(result, 0)


class TestAgentHandlers(unittest.TestCase):
    """Tests for sentinel agent command handler."""

    @patch('cli.main._print')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_status(self, mock_instance, mock_print):
        registry = MagicMock()
        registry.get_agent_summary.return_value = {
            'total_agents': 2,
            'enabled': 1,
            'running': 0,
            'errors': 0,
            'total_runs': 10,
        }
        mock_instance.return_value = registry
        result = cmd_agent(argparse.Namespace(action='status', agent_id=None, goal=None, webhook=None, min_severity=None))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_enable_missing_id(self, mock_instance, mock_print):
        mock_instance.return_value = MagicMock()
        result = cmd_agent(argparse.Namespace(action='enable', agent_id=None, goal=None, webhook=None, min_severity=None))
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_disable_not_found(self, mock_instance, mock_print):
        registry = MagicMock()
        registry.disable_agent.return_value = False
        mock_instance.return_value = registry
        result = cmd_agent(argparse.Namespace(action='disable', agent_id='missing', goal=None, webhook=None, min_severity=None))
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('utils.agent_runner.AgentScheduler')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_run_success(self, mock_instance, mock_scheduler_cls, mock_print):
        mock_instance.return_value = MagicMock()
        scheduler = MagicMock()
        scheduler.run_agent_now.return_value = [SimpleNamespace(success=True, action_id='a1', message='ok')]
        mock_scheduler_cls.return_value = scheduler
        result = cmd_agent(argparse.Namespace(action='run', agent_id='auto-clean', goal=None, webhook=None, min_severity=None))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_logs_without_id(self, mock_instance, mock_print):
        registry = MagicMock()
        registry.get_recent_activity.return_value = []
        mock_instance.return_value = registry
        result = cmd_agent(argparse.Namespace(action='logs', agent_id=None, goal=None, webhook=None, min_severity=None))
        self.assertEqual(result, 0)

    @patch('cli.main._print')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_notify_missing_agent(self, mock_instance, mock_print):
        registry = MagicMock()
        registry.get_agent.return_value = None
        mock_instance.return_value = registry
        args = argparse.Namespace(action='notify', agent_id='ghost', goal=None, webhook='https://ex.com/hook', min_severity='high')
        result = cmd_agent(args)
        self.assertEqual(result, 1)

    @patch('cli.main._print')
    @patch('utils.agent_notifications.AgentNotifier.validate_webhook_url')
    @patch('utils.agents.AgentRegistry.instance')
    def test_agent_notify_invalid_webhook(self, mock_instance, mock_validate, mock_print):
        agent = SimpleNamespace(name='A1', notification_config={})
        registry = MagicMock()
        registry.get_agent.return_value = agent
        mock_instance.return_value = registry
        mock_validate.return_value = False
        args = argparse.Namespace(action='notify', agent_id='a1', goal=None, webhook='invalid://bad', min_severity=None)
        result = cmd_agent(args)
        self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()
