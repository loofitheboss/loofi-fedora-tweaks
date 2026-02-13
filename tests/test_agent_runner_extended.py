"""Extended tests for utils/agent_runner.py coverage."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.agents import (
    ActionSeverity,
    AgentAction,
    AgentConfig,
    AgentResult,
    AgentState,
    AgentStatus,
    AgentTrigger,
    AgentType,
    TriggerType,
)
from utils.agent_runner import AgentExecutor, AgentScheduler


class TestAgentExecutorExtended(unittest.TestCase):
    """Branch coverage for AgentExecutor operations and routing."""

    def _agent(self, **kwargs):
        base = {
            "agent_id": "a1",
            "name": "Agent",
            "agent_type": AgentType.CUSTOM,
            "description": "test",
            "settings": {},
        }
        base.update(kwargs)
        return AgentConfig(**base)

    def _action(self, **kwargs):
        base = {
            "action_id": "x1",
            "name": "Action",
            "description": "desc",
            "severity": ActionSeverity.LOW,
        }
        base.update(kwargs)
        return AgentAction(**base)

    @patch('utils.agent_runner.Arbitrator.can_proceed', return_value=True)
    @patch('utils.agent_runner.CentralExecutor.run')
    def test_execute_action_command_path(self, mock_run, mock_can_proceed):
        """Command-based action routes through CentralExecutor."""
        mock_run.return_value = SimpleNamespace(
            success=True,
            message='ok',
            exit_code=0,
            stdout='hello',
        )
        agent = self._agent()
        action = self._action(command='echo', args=['hi'])
        state = AgentState(agent_id='a1')

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertTrue(result.success)
        self.assertEqual(result.action_id, 'x1')
        self.assertEqual(result.data.get('exit_code'), 0)

    @patch('utils.agent_runner.Arbitrator.can_proceed', return_value=True)
    @patch('utils.agent_runner.AgentExecutor._execute_operation', side_effect=RuntimeError('boom'))
    def test_execute_action_operation_exception(self, mock_exec_op, mock_can_proceed):
        """Operation execution exceptions are wrapped as AgentResult failures."""
        agent = self._agent()
        action = self._action(operation='monitor.check_cpu')
        state = AgentState(agent_id='a1')

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn('Error executing', result.message)

    @patch('utils.agent_runner.AgentExecutor._op_check_cpu', return_value=AgentResult(success=True, message='ok'))
    def test_execute_operation_known_handler(self, mock_check_cpu):
        """Known operation name uses handler mapping."""
        result = AgentExecutor._execute_operation('monitor.check_cpu', {})
        self.assertTrue(result.success)

    def test_infer_priority_variants(self):
        """Priority mapping covers critical, high/medium and low severities."""
        critical = self._action(severity=ActionSeverity.CRITICAL)
        high = self._action(severity=ActionSeverity.HIGH)
        medium = self._action(severity=ActionSeverity.MEDIUM)
        low = self._action(severity=ActionSeverity.LOW)

        self.assertEqual(str(AgentExecutor._infer_priority(critical).name), 'CRITICAL')
        self.assertEqual(str(AgentExecutor._infer_priority(high).name), 'USER_INTERACTION')
        self.assertEqual(str(AgentExecutor._infer_priority(medium).name), 'USER_INTERACTION')
        self.assertEqual(str(AgentExecutor._infer_priority(low).name), 'BACKGROUND')

    def test_infer_resource_variants(self):
        """Resource inference maps known operation prefixes."""
        self.assertEqual(AgentExecutor._infer_resource(self._action(operation='monitor.check_cpu')), 'cpu')
        self.assertEqual(AgentExecutor._infer_resource(self._action(operation='security.scan_ports')), 'network')
        self.assertEqual(AgentExecutor._infer_resource(self._action(operation='cleanup.temp_files')), 'disk')
        self.assertEqual(AgentExecutor._infer_resource(self._action(operation='other.unknown')), 'background_process')

    @patch('utils.agent_runner.subprocess.run')
    def test_op_scan_ports_nonzero(self, mock_run):
        """Port scan nonzero return code is reported as failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        result = AgentExecutor._op_scan_ports({})
        self.assertFalse(result.success)

    @patch('utils.agent_runner.subprocess.run')
    def test_op_scan_ports_success(self, mock_run):
        """Port scan parses listening addresses from ss output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Netid State Recv-Q Send-Q Local Address:Port\ntcp LISTEN 0 128 0.0.0.0:22\n',
        )
        result = AgentExecutor._op_scan_ports({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get('port_count'), 1)

    @patch('utils.agent_runner.subprocess.run', side_effect=OSError('x'))
    def test_op_scan_ports_exception(self, mock_run):
        """Port scan OSError branch returns failure result."""
        result = AgentExecutor._op_scan_ports({})
        self.assertFalse(result.success)

    @patch('utils.agent_runner.subprocess.run')
    def test_op_failed_logins_alert(self, mock_run):
        """Failed login check triggers alert above configured threshold."""
        mock_run.return_value = MagicMock(returncode=0, stdout='a\nb\nc\n')
        result = AgentExecutor._op_check_failed_logins({'max_failed_logins': 1})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get('alert'))

    @patch('utils.agent_runner.subprocess.run')
    def test_op_firewall_inactive(self, mock_run):
        """Firewall inactive path is reported as alerting success."""
        mock_run.return_value = MagicMock(returncode=0, stdout='inactive\n')
        result = AgentExecutor._op_check_firewall({})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get('alert'))

    @patch('utils.agent_runner.subprocess.run', side_effect=OSError('x'))
    def test_op_firewall_exception(self, mock_run):
        """Firewall check exception path returns failure."""
        result = AgentExecutor._op_check_firewall({})
        self.assertFalse(result.success)

    @patch('utils.agent_runner.subprocess.run')
    def test_op_dnf_updates_available(self, mock_run):
        """DNF check return code 100 reports available updates."""
        mock_run.return_value = MagicMock(returncode=100, stdout='pkg1\npkg2\n')
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get('dnf_updates'), 2)

    @patch('utils.agent_runner.subprocess.run', side_effect=OSError('x'))
    def test_op_dnf_updates_exception(self, mock_run):
        """DNF check exception path returns failure."""
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertFalse(result.success)

    @patch('utils.agent_runner.subprocess.run')
    def test_op_flatpak_updates_nonzero(self, mock_run):
        """Flatpak non-zero return path reports check complete with zero updates."""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        result = AgentExecutor._op_check_flatpak_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get('flatpak_updates'), 0)

    @patch('utils.agent_runner.subprocess.run', side_effect=FileNotFoundError())
    def test_op_flatpak_not_installed(self, mock_run):
        """Flatpak-not-installed path returns success with informative message."""
        result = AgentExecutor._op_check_flatpak_updates({})
        self.assertTrue(result.success)
        self.assertIn('not installed', result.message.lower())

    @patch('utils.agent_runner.subprocess.run')
    def test_op_clean_dnf_cache_unknown_size(self, mock_run):
        """DNF cache path with nonzero du result returns unknown size."""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        result = AgentExecutor._op_clean_dnf_cache({})
        self.assertTrue(result.success)
        self.assertIn('unknown', result.message.lower())

    @patch('utils.agent_runner.subprocess.run')
    def test_op_vacuum_journal_unknown(self, mock_run):
        """Journal usage non-zero path returns unknown usage summary."""
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        result = AgentExecutor._op_vacuum_journal({})
        self.assertTrue(result.success)
        self.assertIn('unknown', result.message.lower())

    @patch('utils.agent_runner.subprocess.run')
    def test_op_clean_temp_files_handles_one_error(self, mock_run):
        """Temp cleanup size summary handles per-path subprocess exceptions."""
        mock_run.side_effect = [
            OSError('bad'),
            MagicMock(returncode=0, stdout='12M\t/home/user/.cache'),
        ]
        result = AgentExecutor._op_clean_temp_files({})
        self.assertTrue(result.success)
        self.assertEqual(result.data['sizes']['/tmp'], 'unknown')

    def test_op_apply_tuning_auto_apply_enabled(self):
        """Auto-apply enabled path returns privilege escalation message."""
        result = AgentExecutor._op_apply_tuning({'auto_apply': True})
        self.assertTrue(result.success)
        self.assertIn('privilege escalation', result.message.lower())


class TestAgentSchedulerExtended(unittest.TestCase):
    """Branch coverage for AgentScheduler internals."""

    def _agent(self):
        return AgentConfig(
            agent_id='a1',
            name='A1',
            agent_type=AgentType.CUSTOM,
            description='x',
            triggers=[AgentTrigger(trigger_type=TriggerType.INTERVAL, config={'seconds': 1})],
            actions=[
                AgentAction(
                    action_id='act1',
                    name='n1',
                    description='d1',
                    severity=ActionSeverity.LOW,
                    operation='monitor.check_cpu',
                )
            ],
        )

    @patch('utils.agent_runner.time.time', return_value=1000)
    @patch('utils.agent_runner.AgentRegistry.instance')
    def test_run_loop_executes_interval_agent(self, mock_instance, mock_time):
        """Scheduler loop executes eligible interval trigger and saves state."""
        scheduler = AgentScheduler()
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.is_set.side_effect = [False, True]
        scheduler._stop_event.wait.return_value = None

        reg = MagicMock()
        agent = self._agent()
        state = AgentState(agent_id='a1', status=AgentStatus.IDLE, last_run=0)
        reg.get_enabled_agents.return_value = [agent]
        reg.get_state.return_value = state
        mock_instance.return_value = reg

        with patch.object(scheduler, '_execute_agent') as mock_exec:
            scheduler._run_loop()
            mock_exec.assert_called_once()
            reg.save.assert_called_once()

    @patch('utils.agent_runner.time.time', return_value=1000)
    @patch('utils.agent_runner.AgentRegistry.instance')
    def test_run_loop_skips_non_idle_state(self, mock_instance, mock_time):
        """Scheduler loop skips agents not in idle/running state."""
        scheduler = AgentScheduler()
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.is_set.side_effect = [False, True]
        scheduler._stop_event.wait.return_value = None

        reg = MagicMock()
        agent = self._agent()
        state = AgentState(agent_id='a1', status=AgentStatus.PAUSED, last_run=0)
        reg.get_enabled_agents.return_value = [agent]
        reg.get_state.return_value = state
        mock_instance.return_value = reg

        with patch.object(scheduler, '_execute_agent') as mock_exec:
            scheduler._run_loop()
            mock_exec.assert_not_called()

    @patch('utils.agent_runner.AgentExecutor.execute_action')
    def test_execute_agent_callback_exception(self, mock_exec):
        """Agent execution continues when result callback raises error."""
        scheduler = AgentScheduler()
        agent = self._agent()
        state = AgentState(agent_id='a1', status=AgentStatus.IDLE)
        reg = MagicMock()
        scheduler._on_result = MagicMock(side_effect=RuntimeError('cb'))
        mock_exec.return_value = AgentResult(success=True, message='ok', data={'alert': True})

        with patch.object(scheduler, '_notify_result') as mock_notify:
            scheduler._execute_agent(agent, state, reg)
            self.assertEqual(state.status, AgentStatus.IDLE)
            mock_notify.assert_called_once()

    @patch('utils.agent_runner.AgentExecutor.execute_action')
    @patch('utils.agent_runner.AgentRegistry.instance')
    def test_run_agent_now_callback_exception(self, mock_instance, mock_exec):
        """Manual run continues and saves even when callback raises."""
        scheduler = AgentScheduler()
        scheduler._on_result = MagicMock(side_effect=RuntimeError('cb'))

        agent = self._agent()
        state = AgentState(agent_id='a1', status=AgentStatus.IDLE)
        reg = MagicMock()
        reg.get_agent.return_value = agent
        reg.get_state.return_value = state
        mock_instance.return_value = reg
        mock_exec.return_value = AgentResult(success=True, message='ok')

        with patch.object(scheduler, '_notify_result'):
            results = scheduler.run_agent_now('a1')
            self.assertEqual(len(results), 1)
            reg.save.assert_called_once()

    @patch('utils.agent_notifications.AgentNotificationConfig.from_dict', side_effect=RuntimeError('x'))
    @patch('utils.agent_notifications.AgentNotifier')
    def test_notify_result_exception_is_swallowed(self, mock_notifier_cls, mock_from_dict):
        """Notification failures are swallowed and do not raise."""
        scheduler = AgentScheduler()
        agent = self._agent()
        result = AgentResult(success=True, message='ok')
        scheduler._notify_result(agent, result)
        self.assertTrue(hasattr(scheduler, '_notifier'))
        scheduler._notifier.notify.assert_not_called()


if __name__ == '__main__':
    unittest.main()