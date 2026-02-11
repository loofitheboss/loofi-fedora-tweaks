"""
Tests for v18.0 Sentinel — Agent Framework.
"""

import json
import os
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))


class TestAgentDataclasses:
    """Test agent data structures."""

    def test_agent_result_auto_timestamp(self):
        from utils.agents import AgentResult
        r = AgentResult(success=True, message="OK")
        assert r.timestamp > 0
        assert r.success is True

    def test_agent_result_to_dict(self):
        from utils.agents import AgentResult
        r = AgentResult(success=False, message="fail", action_id="a1", timestamp=1000.0)
        d = r.to_dict()
        assert d["success"] is False
        assert d["message"] == "fail"
        assert d["action_id"] == "a1"
        assert d["timestamp"] == 1000.0

    def test_agent_trigger_roundtrip(self):
        from utils.agents import AgentTrigger, TriggerType
        t = AgentTrigger(TriggerType.INTERVAL, {"seconds": 60})
        d = t.to_dict()
        t2 = AgentTrigger.from_dict(d)
        assert t2.trigger_type == TriggerType.INTERVAL
        assert t2.config["seconds"] == 60

    def test_agent_action_roundtrip(self):
        from utils.agents import AgentAction, ActionSeverity
        a = AgentAction(
            action_id="test",
            name="Test Action",
            description="A test",
            severity=ActionSeverity.LOW,
            operation="monitor.check_cpu",
        )
        d = a.to_dict()
        a2 = AgentAction.from_dict(d)
        assert a2.action_id == "test"
        assert a2.severity == ActionSeverity.LOW
        assert a2.operation == "monitor.check_cpu"

    def test_agent_config_auto_id(self):
        from utils.agents import AgentConfig, AgentType
        c = AgentConfig(agent_id="", name="Test", agent_type=AgentType.CUSTOM, description="test")
        assert c.agent_id != ""
        assert c.created_at > 0

    def test_agent_config_roundtrip(self):
        from utils.agents import AgentConfig, AgentType, AgentTrigger, TriggerType
        c = AgentConfig(
            agent_id="test-id",
            name="My Agent",
            agent_type=AgentType.SYSTEM_MONITOR,
            description="monitors stuff",
            triggers=[AgentTrigger(TriggerType.INTERVAL, {"seconds": 30})],
        )
        d = c.to_dict()
        c2 = AgentConfig.from_dict(d)
        assert c2.agent_id == "test-id"
        assert c2.name == "My Agent"
        assert c2.agent_type == AgentType.SYSTEM_MONITOR
        assert len(c2.triggers) == 1

    def test_agent_state_can_act(self):
        from utils.agents import AgentState
        s = AgentState(agent_id="test")
        assert s.can_act(10) is True
        s.actions_this_hour = 10
        s.hour_window_start = time.time()
        assert s.can_act(10) is False

    def test_agent_state_rate_limit_resets(self):
        from utils.agents import AgentState
        s = AgentState(agent_id="test")
        s.actions_this_hour = 10
        s.hour_window_start = time.time() - 7200  # 2 hours ago
        assert s.can_act(10) is True
        assert s.actions_this_hour == 0

    def test_agent_state_record_action(self):
        from utils.agents import AgentState, AgentResult
        s = AgentState(agent_id="test")
        r = AgentResult(success=True, message="OK", action_id="a1")
        s.record_action(r)
        assert s.run_count == 1
        assert s.error_count == 0
        assert len(s.history) == 1

    def test_agent_state_record_error(self):
        from utils.agents import AgentState, AgentResult
        s = AgentState(agent_id="test")
        r = AgentResult(success=False, message="fail", action_id="a1")
        s.record_action(r)
        assert s.error_count == 1

    def test_agent_state_history_bounded(self):
        from utils.agents import AgentState, AgentResult
        s = AgentState(agent_id="test")
        for i in range(120):
            s.record_action(AgentResult(success=True, message=f"msg {i}"))
        assert len(s.history) <= 100

    def test_agent_state_roundtrip(self):
        from utils.agents import AgentState, AgentResult, AgentStatus
        s = AgentState(agent_id="test", status=AgentStatus.RUNNING, run_count=5)
        s.record_action(AgentResult(success=True, message="OK", action_id="a1"))
        d = s.to_dict()
        s2 = AgentState.from_dict(d)
        assert s2.agent_id == "test"
        assert s2.status == AgentStatus.RUNNING
        assert s2.run_count == 6
        assert len(s2.history) == 1


class TestAgentRegistry:
    """Test AgentRegistry operations."""

    def setup_method(self):
        from utils.agents import AgentRegistry
        AgentRegistry.reset()

    def test_builtin_agents_loaded(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            agents = registry.list_agents()
            assert len(agents) >= 5  # 5 built-in agents

    def test_register_custom_agent(self):
        from utils.agents import AgentRegistry, AgentConfig, AgentType
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            config = AgentConfig(
                agent_id="custom-1",
                name="Custom",
                agent_type=AgentType.CUSTOM,
                description="test",
            )
            registered = registry.register_agent(config)
            assert registered.agent_id == "custom-1"
            assert registry.get_agent("custom-1") is not None

    def test_remove_custom_agent(self):
        from utils.agents import AgentRegistry, AgentConfig, AgentType
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            config = AgentConfig(
                agent_id="custom-rm",
                name="ToRemove",
                agent_type=AgentType.CUSTOM,
                description="test",
            )
            registry.register_agent(config)
            assert registry.remove_agent("custom-rm") is True
            assert registry.get_agent("custom-rm") is None

    def test_cannot_remove_builtin(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            assert registry.remove_agent("builtin-sysmon") is False

    def test_enable_disable(self):
        from utils.agents import AgentRegistry, AgentStatus
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            registry.enable_agent("builtin-sysmon")
            agent = registry.get_agent("builtin-sysmon")
            assert agent.enabled is True
            state = registry.get_state("builtin-sysmon")
            assert state.status == AgentStatus.IDLE

            registry.disable_agent("builtin-sysmon")
            agent = registry.get_agent("builtin-sysmon")
            assert agent.enabled is False
            state = registry.get_state("builtin-sysmon")
            assert state.status == AgentStatus.DISABLED

    def test_get_agent_summary(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            summary = registry.get_agent_summary()
            assert "total_agents" in summary
            assert "enabled" in summary
            assert summary["total_agents"] >= 5

    def test_create_custom_agent(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            agent = registry.create_custom_agent(
                name="Test Custom",
                description="A test agent",
            )
            assert agent.name == "Test Custom"
            assert registry.get_agent(agent.agent_id) is not None

    def test_persistence(self):
        from utils.agents import AgentRegistry, AgentConfig, AgentType
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            reg1 = AgentRegistry()
            reg1.register_agent(AgentConfig(
                agent_id="persist-test",
                name="Persist",
                agent_type=AgentType.CUSTOM,
                description="test",
            ))
            reg1.save()

            # Load fresh
            reg2 = AgentRegistry.__new__(AgentRegistry)
            reg2._agents = {}
            reg2._states = {}
            AgentRegistry._CONFIG_DIR = tmpdir
            reg2._ensure_config_dir = lambda: None
            reg2._load()
            assert reg2.get_agent("persist-test") is not None

    def test_update_settings(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry._CONFIG_DIR = tmpdir
            registry = AgentRegistry()
            result = registry.update_agent_settings("builtin-sysmon", {"cpu_threshold": 95})
            assert result is True
            agent = registry.get_agent("builtin-sysmon")
            assert agent.settings["cpu_threshold"] == 95


class TestAgentExecutor:
    """Test agent action execution."""

    def test_dry_run(self):
        from utils.agents import AgentConfig, AgentAction, AgentState, AgentType, ActionSeverity
        from utils.agent_runner import AgentExecutor

        agent = AgentConfig(
            agent_id="test", name="Test", agent_type=AgentType.CUSTOM,
            description="test", dry_run=True,
        )
        action = AgentAction(
            action_id="a1", name="Test", description="test",
            severity=ActionSeverity.INFO, operation="monitor.check_cpu",
        )
        state = AgentState(agent_id="test")

        result = AgentExecutor.execute_action(agent, action, state)
        assert result.success is True
        assert "[DRY RUN]" in result.message

    def test_rate_limit(self):
        from utils.agents import AgentConfig, AgentAction, AgentState, AgentType, ActionSeverity
        from utils.agent_runner import AgentExecutor

        agent = AgentConfig(
            agent_id="test", name="Test", agent_type=AgentType.CUSTOM,
            description="test", max_actions_per_hour=0,
        )
        action = AgentAction(
            action_id="a1", name="Test", description="test",
            severity=ActionSeverity.INFO,
        )
        state = AgentState(agent_id="test")

        result = AgentExecutor.execute_action(agent, action, state)
        assert result.success is False
        assert "Rate limit" in result.message

    def test_critical_blocked(self):
        from utils.agents import AgentConfig, AgentAction, AgentState, AgentType, ActionSeverity
        from utils.agent_runner import AgentExecutor

        agent = AgentConfig(
            agent_id="test", name="Test", agent_type=AgentType.CUSTOM,
            description="test",
        )
        action = AgentAction(
            action_id="a1", name="Critical Op", description="test",
            severity=ActionSeverity.CRITICAL, operation="something",
        )
        state = AgentState(agent_id="test")

        result = AgentExecutor.execute_action(agent, action, state)
        assert result.success is False
        assert "manual confirmation" in result.message

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    def test_unknown_operation(self, _mock_can_proceed):
        from utils.agents import AgentConfig, AgentAction, AgentState, AgentType, ActionSeverity
        from utils.agent_runner import AgentExecutor

        agent = AgentConfig(
            agent_id="test", name="Test", agent_type=AgentType.CUSTOM,
            description="test",
        )
        action = AgentAction(
            action_id="a1", name="Test", description="test",
            severity=ActionSeverity.INFO, operation="nonexistent.op",
        )
        state = AgentState(agent_id="test")

        result = AgentExecutor.execute_action(agent, action, state)
        assert result.success is False
        assert "Unknown operation" in result.message

    @patch("utils.agent_runner.Arbitrator.can_proceed", return_value=True)
    def test_no_operation_or_command(self, _mock_can_proceed):
        from utils.agents import AgentConfig, AgentAction, AgentState, AgentType, ActionSeverity
        from utils.agent_runner import AgentExecutor

        agent = AgentConfig(
            agent_id="test", name="Test", agent_type=AgentType.CUSTOM,
            description="test",
        )
        action = AgentAction(
            action_id="a1", name="Test", description="test",
            severity=ActionSeverity.INFO,
        )
        state = AgentState(agent_id="test")

        result = AgentExecutor.execute_action(agent, action, state)
        assert result.success is False
        assert "no operation or command" in result.message

    def test_arbitrator_blocks_action(self):
        from utils.agents import AgentConfig, AgentAction, AgentState, AgentType, ActionSeverity
        from utils.agent_runner import AgentExecutor

        agent = AgentConfig(
            agent_id="test", name="Test", agent_type=AgentType.CUSTOM,
            description="test",
        )
        action = AgentAction(
            action_id="a1", name="Blocked", description="test",
            severity=ActionSeverity.LOW, operation="monitor.check_cpu",
        )
        state = AgentState(agent_id="test")

        with patch("utils.agent_runner.Arbitrator.can_proceed", return_value=False):
            result = AgentExecutor.execute_action(agent, action, state)
            assert result.success is False
            assert result.data and result.data.get("arbitrator_block") is True


class TestAgentArbitrator:
    """Test agent resource arbitration."""

    def test_cpu_request_blocked_on_thermal(self):
        from utils.arbitrator import Arbitrator, AgentRequest, Priority
        from utils.temperature import TemperatureSensor

        hot_cpu = [
            TemperatureSensor(
                name="coretemp",
                label="Core 0",
                current=95.0,
                high=90.0,
                critical=100.0,
                sensor_type="cpu",
            )
        ]

        with patch("utils.arbitrator.TemperatureManager.get_cpu_temps", return_value=hot_cpu):
            arbitrator = Arbitrator(cpu_thermal_limit_c=90.0)
            request = AgentRequest(
                agent_name="Builder",
                resource="cpu",
                priority=Priority.BACKGROUND,
            )
            assert arbitrator.can_proceed(request) is False

    def test_cpu_request_allows_critical_on_thermal(self):
        from utils.arbitrator import Arbitrator, AgentRequest, Priority
        from utils.temperature import TemperatureSensor

        hot_cpu = [
            TemperatureSensor(
                name="coretemp",
                label="Core 0",
                current=95.0,
                high=90.0,
                critical=100.0,
                sensor_type="cpu",
            )
        ]

        with patch("utils.arbitrator.TemperatureManager.get_cpu_temps", return_value=hot_cpu):
            arbitrator = Arbitrator(cpu_thermal_limit_c=90.0)
            request = AgentRequest(
                agent_name="Guardian",
                resource="cpu",
                priority=Priority.CRITICAL,
            )
            assert arbitrator.can_proceed(request) is True

    def test_background_blocked_on_battery(self):
        from utils.arbitrator import Arbitrator, AgentRequest, Priority

        with patch("utils.arbitrator.SystemPulse.get_power_state", return_value="battery"):
            arbitrator = Arbitrator()
            request = AgentRequest(
                agent_name="Cleanup",
                resource="background_process",
                priority=Priority.BACKGROUND,
            )
            assert arbitrator.can_proceed(request) is False

    def test_background_allowed_on_ac(self):
        from utils.arbitrator import Arbitrator, AgentRequest, Priority

        with patch("utils.arbitrator.SystemPulse.get_power_state", return_value="ac"):
            arbitrator = Arbitrator()
            request = AgentRequest(
                agent_name="Cleanup",
                resource="background_process",
                priority=Priority.BACKGROUND,
            )
            assert arbitrator.can_proceed(request) is True


class TestAgentOperations:
    """Test built-in agent operations."""

    def test_check_cpu(self):
        from utils.agent_runner import AgentExecutor
        result = AgentExecutor._op_check_cpu({"cpu_threshold": 90})
        assert result.success is True
        assert result.data is not None

    def test_check_memory(self):
        from utils.agent_runner import AgentExecutor
        result = AgentExecutor._op_check_memory({"memory_threshold": 85})
        assert result.success is True
        assert "memory_percent" in (result.data or {}) or "Memory" in result.message

    def test_check_disk(self):
        from utils.agent_runner import AgentExecutor
        result = AgentExecutor._op_check_disk({"disk_threshold": 90})
        assert result.success is True

    def test_check_temperature(self):
        from utils.agent_runner import AgentExecutor
        result = AgentExecutor._op_check_temperature({"temp_threshold": 80})
        assert result.success is True

    def test_detect_workload(self):
        from utils.agent_runner import AgentExecutor
        result = AgentExecutor._op_detect_workload({})
        assert result.success is True
        assert result.data is not None
        assert "workload" in result.data


class TestAgentPlanner:
    """Test AI-powered agent planning."""

    def test_template_matching_health(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("Keep my system healthy")
        assert plan.agent_name == "Health Guardian"
        assert len(plan.steps) >= 3

    def test_template_matching_security(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("Watch for security threats")
        assert "Security" in plan.agent_name
        assert len(plan.steps) >= 2

    def test_template_matching_updates(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("Notify me about updates")
        assert "Update" in plan.agent_name

    def test_template_matching_cleanup(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("Automatically clean up my system")
        assert "Cleanup" in plan.agent_name

    def test_template_matching_performance(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("Optimize system performance automatically")
        assert "Performance" in plan.agent_name

    def test_unknown_goal_fallback(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("do something totally random and unique 12345")
        assert plan is not None
        assert plan.confidence <= 0.5
        assert len(plan.steps) > 0

    def test_plan_to_agent_config(self):
        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal("Keep my system healthy")
        config = plan.to_agent_config()
        assert config.name == plan.agent_name
        assert len(config.actions) == len(plan.steps)
        assert config.dry_run is True  # Safety default

    def test_list_goal_templates(self):
        from utils.agent_planner import AgentPlanner
        templates = AgentPlanner.list_goal_templates()
        assert len(templates) == 5
        assert all("key" in t for t in templates)
        assert all("goal" in t for t in templates)

    def test_operation_catalog(self):
        from utils.agent_planner import AgentPlanner
        catalog = AgentPlanner.get_operation_catalog()
        assert len(catalog) >= 14
        assert all("op" in item for item in catalog)


class TestAgentScheduler:
    """Test agent scheduler."""

    def test_scheduler_start_stop(self):
        from utils.agent_runner import AgentScheduler
        scheduler = AgentScheduler()
        assert scheduler.is_running is False
        scheduler.start()
        assert scheduler.is_running is True
        scheduler.stop()
        assert scheduler.is_running is False

    def test_run_agent_now_not_found(self):
        from utils.agent_runner import AgentScheduler
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            scheduler = AgentScheduler()
            results = scheduler.run_agent_now("nonexistent")
            assert len(results) == 1
            assert results[0].success is False

    def test_run_agent_now_builtin(self):
        from utils.agent_runner import AgentScheduler
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            scheduler = AgentScheduler()
            results = scheduler.run_agent_now("builtin-sysmon")
            assert len(results) >= 1
            # All should have been executed
            for r in results:
                assert r.action_id != ""

    def test_result_callback(self):
        from utils.agent_runner import AgentScheduler
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            results_received = []
            scheduler = AgentScheduler()
            scheduler.set_result_callback(lambda aid, r: results_received.append((aid, r)))
            scheduler.run_agent_now("builtin-sysmon")
            assert len(results_received) >= 1


class TestAgentCLI:
    """Test CLI agent commands."""

    def test_cli_agent_list(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            from cli.main import main
            exit_code = main(["agent", "list"])
            assert exit_code == 0

    def test_cli_agent_status(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            from cli.main import main
            exit_code = main(["agent", "status"])
            assert exit_code == 0

    def test_cli_agent_templates(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            from cli.main import main
            exit_code = main(["agent", "templates"])
            assert exit_code == 0

    def test_cli_agent_create(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            from cli.main import main
            exit_code = main(["agent", "create", "--goal", "Keep my system healthy"])
            assert exit_code == 0

    def test_cli_agent_enable_disable(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            from cli.main import main
            assert main(["agent", "enable", "builtin-sysmon"]) == 0
            assert main(["agent", "disable", "builtin-sysmon"]) == 0

    def test_cli_agent_logs(self):
        from utils.agents import AgentRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            AgentRegistry.reset()
            AgentRegistry._CONFIG_DIR = tmpdir
            from cli.main import main
            exit_code = main(["agent", "logs"])
            assert exit_code == 0
