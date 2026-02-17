"""Extended tests for utils/agent_runner.py coverage."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

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
        """Create a test AgentConfig with sensible defaults."""
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
        """Create a test AgentAction with sensible defaults."""
        base = {
            "action_id": "x1",
            "name": "Action",
            "description": "desc",
            "severity": ActionSeverity.LOW,
        }
        base.update(kwargs)
        return AgentAction(**base)

    # ==================== execute_action routing ====================

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    @patch("utils.agent_runner.CentralExecutor.run")
    def test_execute_action_command_path(self, mock_run, mock_can_proceed):
        """Command-based action routes through CentralExecutor."""
        mock_run.return_value = SimpleNamespace(
            success=True,
            message="ok",
            exit_code=0,
            stdout="hello",
        )
        agent = self._agent()
        action = self._action(command="echo", args=["hi"])
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertTrue(result.success)
        self.assertEqual(result.action_id, "x1")
        self.assertEqual(result.data.get("exit_code"), 0)

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    @patch("utils.agent_runner.CentralExecutor.run")
    def test_execute_action_git_push_master_blocked(self, mock_run, mock_can_proceed):
        """Agent command policy blocks git push to protected master branch."""
        agent = self._agent()
        action = self._action(command="git", args=["push", "origin", "master"])
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("not allowed to push to protected branch 'master'", result.message)
        self.assertTrue(result.data.get("policy_block"))
        mock_run.assert_not_called()

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    @patch("utils.agent_runner.CentralExecutor.run")
    def test_execute_action_git_push_feature_allowed(self, mock_run, mock_can_proceed):
        """Agent command policy allows git push to non-protected branches."""
        mock_run.return_value = SimpleNamespace(
            success=True,
            message="ok",
            exit_code=0,
            stdout="pushed",
        )
        agent = self._agent()
        action = self._action(
            command="git",
            args=["push", "origin", "codex/allow-agent-push"],
        )
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("exit_code"), 0)
        mock_run.assert_called_once()

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    @patch("utils.agent_runner.CentralExecutor.run")
    @patch("utils.agent_runner.AgentExecutor._is_on_protected_branch", return_value=True)
    def test_execute_action_git_push_implicit_blocked_on_master(
        self, mock_is_protected, mock_run, mock_can_proceed
    ):
        """Implicit git push is blocked when current branch is protected master."""
        agent = self._agent()
        action = self._action(command="git", args=["push"])
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("not allowed to push to protected branch 'master'", result.message)
        self.assertTrue(result.data.get("policy_block"))
        mock_run.assert_not_called()

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    @patch("utils.agent_runner.CentralExecutor.run")
    @patch("utils.agent_runner.AgentExecutor._is_on_protected_branch", return_value=False)
    def test_execute_action_git_push_implicit_allowed_on_feature(
        self, mock_is_protected, mock_run, mock_can_proceed
    ):
        """Implicit git push is allowed when current branch is not protected."""
        mock_run.return_value = SimpleNamespace(
            success=True,
            message="ok",
            exit_code=0,
            stdout="pushed",
        )
        agent = self._agent()
        action = self._action(command="git", args=["push"])
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("exit_code"), 0)
        mock_run.assert_called_once()

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    @patch(
        "utils.agent_runner.AgentExecutor._execute_operation",
        side_effect=RuntimeError("boom"),
    )
    def test_execute_action_operation_exception(self, mock_exec_op, mock_can_proceed):
        """Operation execution exceptions are wrapped as AgentResult failures."""
        agent = self._agent()
        action = self._action(operation="monitor.check_cpu")
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("Error executing", result.message)

    def test_execute_action_rate_limit_exceeded(self):
        """Rate limit exceeded returns failure without executing action."""
        agent = self._agent(max_actions_per_hour=0)
        action = self._action(operation="monitor.check_cpu")
        state = AgentState(
            agent_id="a1", actions_this_hour=10, hour_window_start=9999999999.0
        )

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("Rate limit", result.message)

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    def test_execute_action_dry_run(self, mock_can_proceed):
        """Dry run mode returns success without executing action."""
        agent = self._agent(dry_run=True)
        action = self._action(operation="monitor.check_cpu")
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertTrue(result.success)
        self.assertIn("[DRY RUN]", result.message)
        self.assertIn("Action", result.message)

    def test_execute_action_critical_severity_gate(self):
        """CRITICAL severity actions are blocked from automatic execution."""
        agent = self._agent()
        action = self._action(
            severity=ActionSeverity.CRITICAL, operation="monitor.check_cpu"
        )
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("manual confirmation", result.message)
        self.assertIn("critical", result.message.lower())

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=False)
    def test_execute_action_arbitrator_blocks(self, mock_can_proceed):
        """Arbitrator denial defers action with appropriate message."""
        agent = self._agent()
        action = self._action(operation="monitor.check_cpu")
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("deferred by arbitrator", result.message)
        self.assertTrue(result.data.get("arbitrator_block"))

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    def test_execute_action_no_op_path(self, mock_can_proceed):
        """Action with neither operation nor command returns no-op failure."""
        agent = self._agent()
        action = self._action()  # no operation, no command
        state = AgentState(agent_id="a1")

        result = AgentExecutor.execute_action(agent, action, state)
        self.assertFalse(result.success)
        self.assertIn("no operation or command", result.message)

    # ==================== _execute_operation ====================

    @patch(
        "utils.agent_runner.AgentExecutor._op_check_cpu",
        return_value=AgentResult(success=True, message="ok"),
    )
    def test_execute_operation_known_handler(self, mock_check_cpu):
        """Known operation name uses handler mapping."""
        result = AgentExecutor._execute_operation("monitor.check_cpu", {})
        self.assertTrue(result.success)

    def test_execute_operation_unknown(self):
        """Unknown operation name returns failure result."""
        result = AgentExecutor._execute_operation("nonexistent.operation", {})
        self.assertFalse(result.success)
        self.assertIn("Unknown operation", result.message)

    # ==================== _infer_priority ====================

    def test_infer_priority_variants(self):
        """Priority mapping covers critical, high/medium and low severities."""
        critical = self._action(severity=ActionSeverity.CRITICAL)
        high = self._action(severity=ActionSeverity.HIGH)
        medium = self._action(severity=ActionSeverity.MEDIUM)
        low = self._action(severity=ActionSeverity.LOW)

        self.assertEqual(str(AgentExecutor._infer_priority(critical).name), "CRITICAL")
        self.assertEqual(
            str(AgentExecutor._infer_priority(high).name), "USER_INTERACTION"
        )
        self.assertEqual(
            str(AgentExecutor._infer_priority(medium).name), "USER_INTERACTION"
        )
        self.assertEqual(str(AgentExecutor._infer_priority(low).name), "BACKGROUND")

    # ==================== _infer_resource ====================

    def test_infer_resource_variants(self):
        """Resource inference maps known operation prefixes."""
        self.assertEqual(
            AgentExecutor._infer_resource(self._action(operation="monitor.check_cpu")),
            "cpu",
        )
        self.assertEqual(
            AgentExecutor._infer_resource(
                self._action(operation="security.scan_ports")
            ),
            "network",
        )
        self.assertEqual(
            AgentExecutor._infer_resource(self._action(operation="cleanup.temp_files")),
            "disk",
        )
        self.assertEqual(
            AgentExecutor._infer_resource(self._action(operation="other.unknown")),
            "background_process",
        )

    def test_infer_resource_tuner_prefix(self):
        """Tuner prefix maps to cpu resource."""
        self.assertEqual(
            AgentExecutor._infer_resource(
                self._action(operation="tuner.detect_workload")
            ),
            "cpu",
        )

    def test_infer_resource_updates_prefix(self):
        """Updates prefix maps to network resource."""
        self.assertEqual(
            AgentExecutor._infer_resource(self._action(operation="updates.check_dnf")),
            "network",
        )

    def test_infer_resource_no_operation(self):
        """Action without operation returns background_process."""
        self.assertEqual(
            AgentExecutor._infer_resource(self._action()), "background_process"
        )

    # ==================== _get_operation_handlers ====================

    def test_get_operation_handlers_returns_all_14(self):
        """Handler mapping contains exactly 14 operation entries."""
        handlers = AgentExecutor._get_operation_handlers()
        self.assertEqual(len(handlers), 14)
        expected_keys = [
            "monitor.check_cpu",
            "monitor.check_memory",
            "monitor.check_disk",
            "monitor.check_temperature",
            "security.scan_ports",
            "security.check_failed_logins",
            "security.check_firewall",
            "updates.check_dnf",
            "updates.check_flatpak",
            "cleanup.dnf_cache",
            "cleanup.vacuum_journal",
            "cleanup.temp_files",
            "tuner.detect_workload",
            "tuner.apply_recommendation",
        ]
        for key in expected_keys:
            self.assertIn(key, handlers)
            self.assertTrue(callable(handlers[key]))

    # ==================== _op_check_cpu ====================

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_check_cpu_above_threshold(self, mock_open, mock_cpu_count):
        """CPU load above threshold triggers alert."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "8.0 4.0 2.0 1/200 1234"
        result = AgentExecutor._op_check_cpu({"cpu_threshold": 50})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("alert"))
        self.assertGreater(result.data.get("cpu_percent"), 50)

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_check_cpu_below_threshold(self, mock_open, mock_cpu_count):
        """CPU load below threshold returns normal status."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "0.2 0.1 0.1 1/200 1234"
        result = AgentExecutor._op_check_cpu({"cpu_threshold": 90})
        self.assertTrue(result.success)
        self.assertFalse(result.data.get("alert"))

    @patch("builtins.open", side_effect=OSError("no such file"))
    def test_op_check_cpu_oserror(self, mock_open):
        """CPU check OSError returns failure result."""
        result = AgentExecutor._op_check_cpu({})
        self.assertFalse(result.success)
        self.assertIn("Cannot read CPU", result.message)

    # ==================== _op_check_memory ====================

    @patch("builtins.open", create=True)
    def test_op_check_memory_above_threshold(self, mock_open):
        """Memory usage above threshold triggers alert."""
        meminfo = (
            "MemTotal:       16000000 kB\n"
            "MemFree:          500000 kB\n"
            "MemAvailable:    1000000 kB\n"
        )
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readlines.return_value = meminfo.strip().split("\n")
        result = AgentExecutor._op_check_memory({"memory_threshold": 50})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("alert"))

    @patch("builtins.open", create=True)
    def test_op_check_memory_below_threshold(self, mock_open):
        """Memory usage below threshold returns normal status."""
        meminfo = (
            "MemTotal:       16000000 kB\n"
            "MemFree:        10000000 kB\n"
            "MemAvailable:   14000000 kB\n"
        )
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readlines.return_value = meminfo.strip().split("\n")
        result = AgentExecutor._op_check_memory({"memory_threshold": 85})
        self.assertTrue(result.success)
        self.assertFalse(result.data.get("alert"))

    @patch("builtins.open", side_effect=OSError("no meminfo"))
    def test_op_check_memory_oserror(self, mock_open):
        """Memory check OSError returns failure result."""
        result = AgentExecutor._op_check_memory({})
        self.assertFalse(result.success)
        self.assertIn("Cannot read memory", result.message)

    # ==================== _op_check_disk ====================

    @patch("utils.agent_runner.os.statvfs")
    def test_op_check_disk_above_threshold(self, mock_statvfs):
        """Disk usage above threshold triggers alert."""
        mock_statvfs.return_value = SimpleNamespace(
            f_blocks=1000000,
            f_frsize=4096,
            f_bavail=10000,
        )
        result = AgentExecutor._op_check_disk({"disk_threshold": 50})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("alert"))

    @patch("utils.agent_runner.os.statvfs")
    def test_op_check_disk_below_threshold(self, mock_statvfs):
        """Disk usage below threshold returns normal status."""
        mock_statvfs.return_value = SimpleNamespace(
            f_blocks=1000000,
            f_frsize=4096,
            f_bavail=900000,
        )
        result = AgentExecutor._op_check_disk({"disk_threshold": 90})
        self.assertTrue(result.success)
        self.assertFalse(result.data.get("alert"))

    @patch("utils.agent_runner.os.statvfs", side_effect=OSError("disk error"))
    def test_op_check_disk_oserror(self, mock_statvfs):
        """Disk check OSError returns failure result."""
        result = AgentExecutor._op_check_disk({})
        self.assertFalse(result.success)
        self.assertIn("Cannot read disk", result.message)

    # ==================== _op_check_temperature ====================

    @patch("builtins.open", create=True)
    def test_op_check_temperature_above_threshold(self, mock_open):
        """Temperature above threshold triggers alert."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "95000"
        result = AgentExecutor._op_check_temperature({"temp_threshold": 80})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("alert"))
        self.assertAlmostEqual(result.data.get("temperature_c"), 95.0, places=1)

    @patch("builtins.open", create=True)
    def test_op_check_temperature_below_threshold(self, mock_open):
        """Temperature below threshold returns normal status."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "45000"
        result = AgentExecutor._op_check_temperature({"temp_threshold": 80})
        self.assertTrue(result.success)
        self.assertFalse(result.data.get("alert"))
        self.assertAlmostEqual(result.data.get("temperature_c"), 45.0, places=1)

    @patch("builtins.open", side_effect=OSError("no sensor"))
    def test_op_check_temperature_no_sensors(self, mock_open):
        """No readable thermal zones returns no-sensor message."""
        result = AgentExecutor._op_check_temperature({})
        self.assertTrue(result.success)
        self.assertIn("No temperature sensors", result.message)
        self.assertFalse(result.data.get("alert"))

    @patch("builtins.open", create=True)
    def test_op_check_temperature_valueerror_fallthrough(self, mock_open):
        """ValueError in zone read falls through to next zone or no-sensor."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "not_a_number"
        result = AgentExecutor._op_check_temperature({})
        self.assertTrue(result.success)
        self.assertIn("No temperature sensors", result.message)

    # ==================== _op_scan_ports ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_scan_ports_nonzero(self, mock_run):
        """Port scan nonzero return code is reported as failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = AgentExecutor._op_scan_ports({})
        self.assertFalse(result.success)

    @patch("utils.agent_runner.subprocess.run")
    def test_op_scan_ports_success(self, mock_run):
        """Port scan parses listening addresses from ss output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Netid State Recv-Q Send-Q Local Address:Port\ntcp LISTEN 0 128 0.0.0.0:22\n",
        )
        result = AgentExecutor._op_scan_ports({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("port_count"), 1)

    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("x"))
    def test_op_scan_ports_exception(self, mock_run):
        """Port scan OSError branch returns failure result."""
        result = AgentExecutor._op_scan_ports({})
        self.assertFalse(result.success)

    # ==================== _op_check_failed_logins ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_failed_logins_alert(self, mock_run):
        """Failed login check triggers alert above configured threshold."""
        mock_run.return_value = MagicMock(returncode=0, stdout="a\nb\nc\n")
        result = AgentExecutor._op_check_failed_logins({"max_failed_logins": 1})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("alert"))

    @patch("utils.agent_runner.subprocess.run")
    def test_op_failed_logins_below_threshold(self, mock_run):
        """Failed login count below threshold returns no alert."""
        mock_run.return_value = MagicMock(returncode=0, stdout="a\n")
        result = AgentExecutor._op_check_failed_logins({"max_failed_logins": 5})
        self.assertTrue(result.success)
        self.assertFalse(result.data.get("alert"))
        self.assertEqual(result.data.get("failed_logins"), 1)

    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("journalctl fail"))
    def test_op_failed_logins_exception(self, mock_run):
        """Failed login check exception returns failure result."""
        result = AgentExecutor._op_check_failed_logins({})
        self.assertFalse(result.success)
        self.assertIn("Login check failed", result.message)

    # ==================== _op_check_firewall ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_firewall_active(self, mock_run):
        """Active firewall returns success with no alert."""
        mock_run.return_value = MagicMock(returncode=0, stdout="active\n")
        result = AgentExecutor._op_check_firewall({})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("firewall_active"))
        self.assertFalse(result.data.get("alert"))

    @patch("utils.agent_runner.subprocess.run")
    def test_op_firewall_inactive(self, mock_run):
        """Firewall inactive path is reported as alerting success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="inactive\n")
        result = AgentExecutor._op_check_firewall({})
        self.assertTrue(result.success)
        self.assertTrue(result.data.get("alert"))

    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("x"))
    def test_op_firewall_exception(self, mock_run):
        """Firewall check exception path returns failure."""
        result = AgentExecutor._op_check_firewall({})
        self.assertFalse(result.success)

    # ==================== _op_check_dnf_updates ====================

    @patch("utils.agent_runner.SystemManager.is_atomic", return_value=False)
    @patch("utils.agent_runner.subprocess.run")
    def test_op_dnf_updates_available(self, mock_run, mock_atomic):
        """DNF check return code 100 reports available updates."""
        mock_run.return_value = MagicMock(returncode=100, stdout="pkg1\npkg2\n")
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("dnf_updates"), 2)

    @patch("utils.agent_runner.SystemManager.is_atomic", return_value=False)
    @patch("utils.agent_runner.subprocess.run")
    def test_op_dnf_updates_no_updates(self, mock_run, mock_atomic):
        """DNF check return code 0 reports system up to date."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("dnf_updates"), 0)
        self.assertFalse(result.data.get("alert"))
        self.assertIn("up to date", result.message.lower())

    @patch("utils.agent_runner.SystemManager.is_atomic", return_value=True)
    @patch("utils.agent_runner.subprocess.run")
    def test_op_dnf_updates_atomic_available(self, mock_run, mock_atomic):
        """Atomic system with available update reports rpm-ostree updates."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="AvailableUpdate:\n  Version: 40.20240101\n  Commit: abc123\n",
        )
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertTrue(result.success)
        self.assertIn("rpm-ostree", result.message)
        self.assertGreater(result.data.get("dnf_updates"), 0)

    @patch("utils.agent_runner.SystemManager.is_atomic", return_value=True)
    @patch("utils.agent_runner.subprocess.run")
    def test_op_dnf_updates_atomic_no_update(self, mock_run, mock_atomic):
        """Atomic system with no updates reports up to date."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No updates available.\n",
        )
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("dnf_updates"), 0)
        self.assertIn("up to date", result.message.lower())

    @patch("utils.agent_runner.SystemManager.is_atomic", return_value=False)
    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("x"))
    def test_op_dnf_updates_exception(self, mock_run, mock_atomic):
        """DNF check exception path returns failure."""
        result = AgentExecutor._op_check_dnf_updates({})
        self.assertFalse(result.success)

    # ==================== _op_check_flatpak_updates ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_flatpak_updates_success_with_updates(self, mock_run):
        """Flatpak check with available updates reports count."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="org.gnome.Calculator\norg.gnome.Gedit\norg.mozilla.Firefox\n",
        )
        result = AgentExecutor._op_check_flatpak_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("flatpak_updates"), 3)
        self.assertTrue(result.data.get("alert"))

    @patch("utils.agent_runner.subprocess.run")
    def test_op_flatpak_updates_nonzero(self, mock_run):
        """Flatpak non-zero return path reports check complete with zero updates."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = AgentExecutor._op_check_flatpak_updates({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("flatpak_updates"), 0)

    @patch("utils.agent_runner.subprocess.run", side_effect=FileNotFoundError())
    def test_op_flatpak_not_installed(self, mock_run):
        """Flatpak-not-installed path returns success with informative message."""
        result = AgentExecutor._op_check_flatpak_updates({})
        self.assertTrue(result.success)
        self.assertIn("not installed", result.message.lower())

    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("flatpak broken"))
    def test_op_flatpak_updates_oserror(self, mock_run):
        """Flatpak OSError (not FileNotFoundError) returns failure result."""
        result = AgentExecutor._op_check_flatpak_updates({})
        self.assertFalse(result.success)
        self.assertIn("Flatpak check failed", result.message)

    # ==================== _op_clean_dnf_cache ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_clean_dnf_cache_success_known_size(self, mock_run):
        """DNF cache with successful du reports size string."""
        mock_run.return_value = MagicMock(returncode=0, stdout="1.2G\t/var/cache/dnf")
        result = AgentExecutor._op_clean_dnf_cache({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("cache_size"), "1.2G")
        self.assertIn("1.2G", result.message)

    @patch("utils.agent_runner.subprocess.run")
    def test_op_clean_dnf_cache_unknown_size(self, mock_run):
        """DNF cache path with nonzero du result returns unknown size."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = AgentExecutor._op_clean_dnf_cache({})
        self.assertTrue(result.success)
        self.assertIn("unknown", result.message.lower())

    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("du fail"))
    def test_op_clean_dnf_cache_exception(self, mock_run):
        """DNF cache check exception returns failure result."""
        result = AgentExecutor._op_clean_dnf_cache({})
        self.assertFalse(result.success)
        self.assertIn("Cache check failed", result.message)

    # ==================== _op_vacuum_journal ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_vacuum_journal_success(self, mock_run):
        """Journal usage with successful journalctl reports disk usage."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Archived and active journals take up 256.0M in the file system.",
        )
        result = AgentExecutor._op_vacuum_journal({})
        self.assertTrue(result.success)
        self.assertIn("256.0M", result.message)

    @patch("utils.agent_runner.subprocess.run")
    def test_op_vacuum_journal_unknown(self, mock_run):
        """Journal usage non-zero path returns unknown usage summary."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = AgentExecutor._op_vacuum_journal({})
        self.assertTrue(result.success)
        self.assertIn("unknown", result.message.lower())

    @patch("utils.agent_runner.subprocess.run", side_effect=OSError("journal fail"))
    def test_op_vacuum_journal_exception(self, mock_run):
        """Journal check exception returns failure result."""
        result = AgentExecutor._op_vacuum_journal({})
        self.assertFalse(result.success)
        self.assertIn("Journal check failed", result.message)

    # ==================== _op_clean_temp_files ====================

    @patch("utils.agent_runner.subprocess.run")
    def test_op_clean_temp_files_all_success(self, mock_run):
        """Temp cleanup with all successful du calls reports sizes."""
        mock_run.return_value = MagicMock(returncode=0, stdout="500M\t/tmp")
        result = AgentExecutor._op_clean_temp_files({})
        self.assertTrue(result.success)
        self.assertFalse(result.data.get("alert"))
        # Both paths should have sizes
        self.assertIn("/tmp", result.data.get("sizes", {}))

    @patch("utils.agent_runner.subprocess.run")
    def test_op_clean_temp_files_handles_one_error(self, mock_run):
        """Temp cleanup size summary handles per-path subprocess exceptions."""
        mock_run.side_effect = [
            OSError("bad"),
            MagicMock(returncode=0, stdout="12M\t/home/user/.cache"),
        ]
        result = AgentExecutor._op_clean_temp_files({})
        self.assertTrue(result.success)
        self.assertEqual(result.data["sizes"]["/tmp"], "unknown")

    # ==================== _op_detect_workload ====================

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_detect_workload_idle(self, mock_open, mock_cpu_count):
        """Low CPU and low memory classified as idle workload."""
        # cpu_pct = (0.1/4)*100 = 2.5%, mem_pct = ((16000000-15000000)/16000000)*100 = 6.25%
        call_count = [0]
        loadavg_data = "0.1 0.05 0.02 1/200 1234"
        meminfo_data = [
            "MemTotal:       16000000 kB\n",
            "MemFree:        14000000 kB\n",
            "MemAvailable:   15000000 kB\n",
        ]

        def open_side_effect(path, *args, **kwargs):
            """Return different mock for loadavg vs meminfo."""
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            if "loadavg" in str(path):
                m.read.return_value = loadavg_data
            else:
                m.readlines.return_value = meminfo_data
            return m

        mock_open.side_effect = open_side_effect
        result = AgentExecutor._op_detect_workload({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("workload"), "idle")

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_detect_workload_light(self, mock_open, mock_cpu_count):
        """Moderate CPU (10-30%) with low memory classified as light."""
        # cpu_pct = (0.8/4)*100 = 20%
        loadavg_data = "0.8 0.4 0.3 1/200 1234"
        meminfo_data = [
            "MemTotal:       16000000 kB\n",
            "MemFree:        14000000 kB\n",
            "MemAvailable:   15000000 kB\n",
        ]

        def open_side_effect(path, *args, **kwargs):
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            if "loadavg" in str(path):
                m.read.return_value = loadavg_data
            else:
                m.readlines.return_value = meminfo_data
            return m

        mock_open.side_effect = open_side_effect
        result = AgentExecutor._op_detect_workload({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("workload"), "light")

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_detect_workload_moderate(self, mock_open, mock_cpu_count):
        """CPU 30-70% classified as moderate workload."""
        # cpu_pct = (2.0/4)*100 = 50%
        loadavg_data = "2.0 1.5 1.0 1/200 1234"
        meminfo_data = [
            "MemTotal:       16000000 kB\n",
            "MemFree:         8000000 kB\n",
            "MemAvailable:   10000000 kB\n",
        ]

        def open_side_effect(path, *args, **kwargs):
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            if "loadavg" in str(path):
                m.read.return_value = loadavg_data
            else:
                m.readlines.return_value = meminfo_data
            return m

        mock_open.side_effect = open_side_effect
        result = AgentExecutor._op_detect_workload({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("workload"), "moderate")

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_detect_workload_heavy(self, mock_open, mock_cpu_count):
        """CPU 70-90% classified as heavy workload."""
        # cpu_pct = (3.2/4)*100 = 80%
        loadavg_data = "3.2 2.5 2.0 1/200 1234"
        meminfo_data = [
            "MemTotal:       16000000 kB\n",
            "MemFree:         2000000 kB\n",
            "MemAvailable:    4000000 kB\n",
        ]

        def open_side_effect(path, *args, **kwargs):
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            if "loadavg" in str(path):
                m.read.return_value = loadavg_data
            else:
                m.readlines.return_value = meminfo_data
            return m

        mock_open.side_effect = open_side_effect
        result = AgentExecutor._op_detect_workload({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("workload"), "heavy")

    @patch("utils.agent_runner.os.cpu_count", return_value=4)
    @patch("builtins.open", create=True)
    def test_op_detect_workload_extreme(self, mock_open, mock_cpu_count):
        """CPU 90%+ classified as extreme workload."""
        # cpu_pct = (4.0/4)*100 = 100%
        loadavg_data = "4.0 3.5 3.0 1/200 1234"
        meminfo_data = [
            "MemTotal:       16000000 kB\n",
            "MemFree:          500000 kB\n",
            "MemAvailable:    1000000 kB\n",
        ]

        def open_side_effect(path, *args, **kwargs):
            m = MagicMock()
            m.__enter__ = lambda s: s
            m.__exit__ = MagicMock(return_value=False)
            if "loadavg" in str(path):
                m.read.return_value = loadavg_data
            else:
                m.readlines.return_value = meminfo_data
            return m

        mock_open.side_effect = open_side_effect
        result = AgentExecutor._op_detect_workload({})
        self.assertTrue(result.success)
        self.assertEqual(result.data.get("workload"), "extreme")

    @patch("builtins.open", side_effect=OSError("no loadavg"))
    def test_op_detect_workload_oserror(self, mock_open):
        """Workload detection OSError returns failure result."""
        result = AgentExecutor._op_detect_workload({})
        self.assertFalse(result.success)
        self.assertIn("Workload detection failed", result.message)

    # ==================== _op_apply_tuning ====================

    def test_op_apply_tuning_auto_apply_disabled(self):
        """Auto-apply disabled (default) returns informational message."""
        result = AgentExecutor._op_apply_tuning({})
        self.assertTrue(result.success)
        self.assertIn("auto-apply disabled", result.message.lower())
        self.assertFalse(result.data.get("alert"))

    def test_op_apply_tuning_auto_apply_enabled(self):
        """Auto-apply enabled path returns privilege escalation message."""
        result = AgentExecutor._op_apply_tuning({"auto_apply": True})
        self.assertTrue(result.success)
        self.assertIn("privilege escalation", result.message.lower())


class TestAgentSchedulerExtended(unittest.TestCase):
    """Branch coverage for AgentScheduler internals."""

    def _agent(self, **kwargs):
        """Create a test AgentConfig with interval trigger and one action."""
        base = {
            "agent_id": "a1",
            "name": "A1",
            "agent_type": AgentType.CUSTOM,
            "description": "x",
            "triggers": [
                AgentTrigger(trigger_type=TriggerType.INTERVAL, config={"seconds": 1})
            ],
            "actions": [
                AgentAction(
                    action_id="act1",
                    name="n1",
                    description="d1",
                    severity=ActionSeverity.LOW,
                    operation="monitor.check_cpu",
                )
            ],
        }
        base.update(kwargs)
        return AgentConfig(**base)

    # ==================== start / stop / is_running ====================

    def test_scheduler_start_when_already_running(self):
        """Starting scheduler when already running is a no-op."""
        scheduler = AgentScheduler()
        # Simulate running state: stop_event not set, thread alive
        scheduler._stop_event.clear()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        scheduler._thread = mock_thread
        scheduler.start()
        # Thread should not have been replaced
        self.assertIs(scheduler._thread, mock_thread)

    def test_scheduler_stop(self):
        """Stopping scheduler sets stop_event and joins thread."""
        scheduler = AgentScheduler()
        scheduler._stop_event = MagicMock()
        scheduler._thread = MagicMock()
        scheduler._thread.is_alive.return_value = True

        scheduler.stop()
        scheduler._stop_event.set.assert_called_once()
        scheduler._thread.join.assert_called_once_with(timeout=5)

    def test_scheduler_stop_no_alive_thread(self):
        """Stopping scheduler with no alive thread skips join."""
        scheduler = AgentScheduler()
        scheduler._stop_event = MagicMock()
        scheduler._thread = MagicMock()
        scheduler._thread.is_alive.return_value = False

        scheduler.stop()
        scheduler._stop_event.set.assert_called_once()
        scheduler._thread.join.assert_not_called()

    def test_scheduler_set_result_callback(self):
        """set_result_callback stores the callback."""
        scheduler = AgentScheduler()
        cb = MagicMock()
        scheduler.set_result_callback(cb)
        self.assertIs(scheduler._on_result, cb)

    def test_scheduler_is_running_property(self):
        """is_running property reflects _stop_event and thread state."""
        scheduler = AgentScheduler()
        self.assertFalse(scheduler.is_running)
        # Simulate running: stop_event not set, thread alive
        scheduler._stop_event.clear()
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        scheduler._thread = mock_thread
        self.assertTrue(scheduler.is_running)

    # ==================== _run_loop ====================

    @patch("utils.agent_runner.time.time", return_value=1000)
    @patch("utils.agent_runner.AgentRegistry.instance")
    def test_run_loop_executes_interval_agent(self, mock_instance, mock_time):
        """Scheduler loop executes eligible interval trigger and saves state."""
        scheduler = AgentScheduler()
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.is_set.side_effect = [False, True]
        scheduler._stop_event.wait.return_value = None

        reg = MagicMock()
        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE, last_run=0)
        reg.get_enabled_agents.return_value = [agent]
        reg.get_state.return_value = state
        mock_instance.return_value = reg

        with patch.object(scheduler, "_execute_agent") as mock_exec:
            scheduler._run_loop()
            mock_exec.assert_called_once()
            reg.save.assert_called_once()

    @patch("utils.agent_runner.time.time", return_value=1000)
    @patch("utils.agent_runner.AgentRegistry.instance")
    def test_run_loop_skips_non_idle_state(self, mock_instance, mock_time):
        """Scheduler loop skips agents not in idle/running state."""
        scheduler = AgentScheduler()
        scheduler._stop_event = MagicMock()
        scheduler._stop_event.is_set.side_effect = [False, True]
        scheduler._stop_event.wait.return_value = None

        reg = MagicMock()
        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.PAUSED, last_run=0)
        reg.get_enabled_agents.return_value = [agent]
        reg.get_state.return_value = state
        mock_instance.return_value = reg

        with patch.object(scheduler, "_execute_agent") as mock_exec:
            scheduler._run_loop()
            mock_exec.assert_not_called()

    # ==================== _execute_agent ====================

    @patch("utils.agent_runner.AgentExecutor.execute_action")
    def test_execute_agent_callback_exception(self, mock_exec):
        """Agent execution continues when result callback raises error."""
        scheduler = AgentScheduler()
        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE)
        reg = MagicMock()
        scheduler._on_result = MagicMock(side_effect=RuntimeError("cb"))
        mock_exec.return_value = AgentResult(
            success=True, message="ok", data={"alert": True}
        )

        with patch.object(scheduler, "_notify_result") as mock_notify:
            scheduler._execute_agent(agent, state, reg)
            self.assertEqual(state.status, AgentStatus.IDLE)
            mock_notify.assert_called_once()

    @patch("utils.agent_runner.AgentExecutor.execute_action")
    def test_execute_agent_stop_event_breaks_loop(self, mock_exec):
        """Stop event during action loop breaks execution early."""
        scheduler = AgentScheduler()
        agent = self._agent(
            actions=[
                AgentAction(
                    action_id="a1",
                    name="n1",
                    description="d1",
                    severity=ActionSeverity.LOW,
                    operation="monitor.check_cpu",
                ),
                AgentAction(
                    action_id="a2",
                    name="n2",
                    description="d2",
                    severity=ActionSeverity.LOW,
                    operation="monitor.check_memory",
                ),
            ]
        )
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE)
        reg = MagicMock()
        scheduler._stop_event.set()  # Set stop immediately
        mock_exec.return_value = AgentResult(success=True, message="ok")

        with patch.object(scheduler, "_notify_result"):
            scheduler._execute_agent(agent, state, reg)
            # Should not have executed any actions because stop_event was set
            mock_exec.assert_not_called()

    @patch("utils.agent_runner.AgentExecutor.execute_action")
    def test_execute_agent_no_callback(self, mock_exec):
        """Agent execution without callback set does not raise."""
        scheduler = AgentScheduler()
        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE)
        reg = MagicMock()
        scheduler._on_result = None
        mock_exec.return_value = AgentResult(
            success=True, message="ok", data={"alert": False}
        )

        with patch.object(scheduler, "_notify_result"):
            scheduler._execute_agent(agent, state, reg)
            self.assertEqual(state.status, AgentStatus.IDLE)

    @patch("utils.agent_runner.AgentExecutor.execute_action")
    def test_execute_agent_alert_logging(self, mock_exec):
        """Agent result with alert data triggers warning log."""
        scheduler = AgentScheduler()
        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE)
        reg = MagicMock()
        scheduler._on_result = None
        mock_exec.return_value = AgentResult(
            success=True, message="CPU high", data={"alert": True}
        )

        with patch.object(scheduler, "_notify_result"):
            with patch("utils.agent_runner.logger") as mock_logger:
                scheduler._execute_agent(agent, state, reg)
                mock_logger.warning.assert_called()

    # ==================== run_agent_now ====================

    @patch("utils.agent_runner.AgentRegistry.instance")
    def test_run_agent_now_agent_not_found(self, mock_instance):
        """Manual trigger for nonexistent agent returns failure result."""
        scheduler = AgentScheduler()
        reg = MagicMock()
        reg.get_agent.return_value = None
        mock_instance.return_value = reg

        results = scheduler.run_agent_now("nonexistent")
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("not found", results[0].message)

    @patch("utils.agent_runner.AgentExecutor.execute_action")
    @patch("utils.agent_runner.AgentRegistry.instance")
    def test_run_agent_now_callback_exception(self, mock_instance, mock_exec):
        """Manual run continues and saves even when callback raises."""
        scheduler = AgentScheduler()
        scheduler._on_result = MagicMock(side_effect=RuntimeError("cb"))

        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE)
        reg = MagicMock()
        reg.get_agent.return_value = agent
        reg.get_state.return_value = state
        mock_instance.return_value = reg
        mock_exec.return_value = AgentResult(success=True, message="ok")

        with patch.object(scheduler, "_notify_result"):
            results = scheduler.run_agent_now("a1")
            self.assertEqual(len(results), 1)
            reg.save.assert_called_once()

    @patch("utils.agent_runner.AgentExecutor.execute_action")
    @patch("utils.agent_runner.AgentRegistry.instance")
    def test_run_agent_now_success(self, mock_instance, mock_exec):
        """Successful manual run returns results and saves state."""
        scheduler = AgentScheduler()
        agent = self._agent()
        state = AgentState(agent_id="a1", status=AgentStatus.IDLE)
        reg = MagicMock()
        reg.get_agent.return_value = agent
        reg.get_state.return_value = state
        mock_instance.return_value = reg
        mock_exec.return_value = AgentResult(success=True, message="done")

        with patch.object(scheduler, "_notify_result"):
            results = scheduler.run_agent_now("a1")
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0].success)
            self.assertEqual(state.status, AgentStatus.IDLE)
            reg.save.assert_called_once()

    # ==================== _notify_result ====================

    @patch(
        "utils.agent_notifications.AgentNotificationConfig.from_dict",
        side_effect=RuntimeError("x"),
    )
    @patch("utils.agent_notifications.AgentNotifier")
    def test_notify_result_exception_is_swallowed(
        self, mock_notifier_cls, mock_from_dict
    ):
        """Notification failures are swallowed and do not raise."""
        scheduler = AgentScheduler()
        agent = self._agent()
        result = AgentResult(success=True, message="ok")
        scheduler._notify_result(agent, result)
        self.assertTrue(hasattr(scheduler, "_notifier"))
        scheduler._notifier.notify.assert_not_called()

    @patch("utils.agent_notifications.AgentNotificationConfig.from_dict")
    @patch("utils.agent_notifications.AgentNotifier")
    def test_notify_result_success(self, mock_notifier_cls, mock_from_dict):
        """Successful notification path creates notifier and calls notify."""
        scheduler = AgentScheduler()
        agent = self._agent()
        result = AgentResult(success=True, message="ok")
        mock_config = MagicMock()
        mock_from_dict.return_value = mock_config

        scheduler._notify_result(agent, result)
        self.assertTrue(hasattr(scheduler, "_notifier"))


if __name__ == "__main__":
    unittest.main()
