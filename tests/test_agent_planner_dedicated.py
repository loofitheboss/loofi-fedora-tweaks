"""Tests for utils/agent_planner.py — AgentPlanner, PlanStep, AgentPlan, GOAL_TEMPLATES.

Comprehensive tests covering dataclass creation, serialization, template matching,
Ollama LLM integration, and fallback behavior.
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.agent_planner import (
    GOAL_TEMPLATES,
    AgentPlan,
    AgentPlanner,
    PlanStep,
)
from utils.agents import (
    ActionSeverity,
    AgentAction,
    AgentConfig,
    AgentTrigger,
    AgentType,
    TriggerType,
)


class TestPlanStep(unittest.TestCase):
    """Tests for the PlanStep dataclass."""

    def test_creation_with_defaults(self):
        """PlanStep should default severity to INFO."""
        step = PlanStep(
            step_number=1, description="Check CPU", operation="monitor.check_cpu"
        )
        self.assertEqual(step.step_number, 1)
        self.assertEqual(step.description, "Check CPU")
        self.assertEqual(step.operation, "monitor.check_cpu")
        self.assertEqual(step.severity, ActionSeverity.INFO)

    def test_creation_with_explicit_severity(self):
        """PlanStep should accept an explicit severity."""
        step = PlanStep(
            step_number=2,
            description="Apply tuning",
            operation="tuner.apply_recommendation",
            severity=ActionSeverity.MEDIUM,
        )
        self.assertEqual(step.severity, ActionSeverity.MEDIUM)

    def test_to_dict_keys(self):
        """to_dict should contain step_number, description, operation, severity."""
        step = PlanStep(1, "desc", "op.name")
        d = step.to_dict()
        self.assertIn("step_number", d)
        self.assertIn("description", d)
        self.assertIn("operation", d)
        self.assertIn("severity", d)

    def test_to_dict_values(self):
        """to_dict should serialize severity as its enum value string."""
        step = PlanStep(3, "Scan ports", "security.scan_ports", ActionSeverity.LOW)
        d = step.to_dict()
        self.assertEqual(d["step_number"], 3)
        self.assertEqual(d["description"], "Scan ports")
        self.assertEqual(d["operation"], "security.scan_ports")
        self.assertEqual(d["severity"], "low")

    def test_to_dict_default_severity_value(self):
        """Default severity should serialize as 'info'."""
        step = PlanStep(1, "desc", "op")
        self.assertEqual(step.to_dict()["severity"], "info")

    def test_all_severity_levels(self):
        """PlanStep should accept every ActionSeverity level."""
        for severity in ActionSeverity:
            step = PlanStep(1, "test", "op", severity)
            self.assertEqual(step.severity, severity)
            self.assertEqual(step.to_dict()["severity"], severity.value)


class TestAgentPlan(unittest.TestCase):
    """Tests for the AgentPlan dataclass."""

    def _make_plan(self, **overrides):
        """Helper to create a minimal AgentPlan."""
        defaults = {
            "goal": "Keep system healthy",
            "agent_name": "Test Agent",
            "description": "A test agent",
            "agent_type": AgentType.SYSTEM_MONITOR,
            "steps": [PlanStep(1, "Check CPU", "monitor.check_cpu")],
            "trigger": AgentTrigger(TriggerType.INTERVAL, {"seconds": 60}),
            "settings": {"threshold": 90},
        }
        defaults.update(overrides)
        return AgentPlan(**defaults)

    def test_creation_defaults(self):
        """AgentPlan should default confidence to 1.0."""
        plan = self._make_plan()
        self.assertEqual(plan.confidence, 1.0)

    def test_creation_custom_confidence(self):
        """AgentPlan should accept a custom confidence."""
        plan = self._make_plan(confidence=0.7)
        self.assertEqual(plan.confidence, 0.7)

    def test_to_dict_structure(self):
        """to_dict should contain all expected keys."""
        plan = self._make_plan()
        d = plan.to_dict()
        expected_keys = {
            "goal",
            "agent_name",
            "description",
            "agent_type",
            "steps",
            "trigger",
            "settings",
            "confidence",
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values(self):
        """to_dict should serialize enums and nested objects correctly."""
        plan = self._make_plan()
        d = plan.to_dict()
        self.assertEqual(d["goal"], "Keep system healthy")
        self.assertEqual(d["agent_type"], "system_monitor")
        self.assertIsInstance(d["steps"], list)
        self.assertEqual(len(d["steps"]), 1)
        self.assertEqual(d["steps"][0]["operation"], "monitor.check_cpu")
        self.assertIsInstance(d["trigger"], dict)
        self.assertEqual(d["trigger"]["trigger_type"], "interval")

    def test_to_dict_multiple_steps(self):
        """to_dict should serialize all steps."""
        steps = [
            PlanStep(1, "Step 1", "op.one"),
            PlanStep(2, "Step 2", "op.two"),
            PlanStep(3, "Step 3", "op.three"),
        ]
        plan = self._make_plan(steps=steps)
        d = plan.to_dict()
        self.assertEqual(len(d["steps"]), 3)
        self.assertEqual(d["steps"][2]["step_number"], 3)

    def test_to_agent_config_returns_agent_config(self):
        """to_agent_config should return an AgentConfig instance."""
        plan = self._make_plan()
        config = plan.to_agent_config()
        self.assertIsInstance(config, AgentConfig)

    def test_to_agent_config_name_and_type(self):
        """to_agent_config should set name and type from plan."""
        plan = self._make_plan(
            agent_name="My Agent",
            agent_type=AgentType.SECURITY_GUARD,
        )
        config = plan.to_agent_config()
        self.assertEqual(config.name, "My Agent")
        self.assertEqual(config.agent_type, AgentType.SECURITY_GUARD)

    def test_to_agent_config_safety_defaults(self):
        """to_agent_config should start disabled and in dry-run mode."""
        plan = self._make_plan()
        config = plan.to_agent_config()
        self.assertFalse(config.enabled)
        self.assertTrue(config.dry_run)

    def test_to_agent_config_actions_mapping(self):
        """to_agent_config should convert steps to AgentAction objects."""
        steps = [
            PlanStep(1, "Check CPU load against threshold", "monitor.check_cpu"),
            PlanStep(
                2, "Apply tuning", "tuner.apply_recommendation", ActionSeverity.MEDIUM
            ),
        ]
        plan = self._make_plan(steps=steps)
        config = plan.to_agent_config()
        self.assertEqual(len(config.actions), 2)
        self.assertIsInstance(config.actions[0], AgentAction)
        self.assertEqual(config.actions[0].action_id, "step_1")
        self.assertEqual(config.actions[0].operation, "monitor.check_cpu")
        self.assertEqual(config.actions[0].severity, ActionSeverity.INFO)
        self.assertEqual(config.actions[1].action_id, "step_2")
        self.assertEqual(config.actions[1].severity, ActionSeverity.MEDIUM)

    def test_to_agent_config_action_name_truncation(self):
        """to_agent_config should truncate action name to 60 chars."""
        long_desc = "A" * 100
        steps = [PlanStep(1, long_desc, "op")]
        plan = self._make_plan(steps=steps)
        config = plan.to_agent_config()
        self.assertEqual(len(config.actions[0].name), 60)
        self.assertEqual(config.actions[0].description, long_desc)

    def test_to_agent_config_triggers(self):
        """to_agent_config should include the plan trigger."""
        trigger = AgentTrigger(TriggerType.INTERVAL, {"seconds": 300})
        plan = self._make_plan(trigger=trigger)
        config = plan.to_agent_config()
        self.assertEqual(len(config.triggers), 1)
        self.assertEqual(config.triggers[0].trigger_type, TriggerType.INTERVAL)
        self.assertEqual(config.triggers[0].config["seconds"], 300)

    def test_to_agent_config_settings(self):
        """to_agent_config should pass through settings."""
        plan = self._make_plan(settings={"cpu_threshold": 85, "auto_apply": False})
        config = plan.to_agent_config()
        self.assertEqual(config.settings["cpu_threshold"], 85)
        self.assertFalse(config.settings["auto_apply"])

    def test_to_agent_config_empty_agent_id(self):
        """to_agent_config should set agent_id to empty string (auto-generated later)."""
        plan = self._make_plan()
        config = plan.to_agent_config()
        # AgentConfig.__post_init__ auto-generates an ID when empty string is passed
        self.assertTrue(len(config.agent_id) > 0)


class TestGoalTemplates(unittest.TestCase):
    """Tests for GOAL_TEMPLATES module-level dict."""

    EXPECTED_KEYS = [
        "keep_system_healthy",
        "watch_security",
        "notify_updates",
        "auto_cleanup",
        "optimize_performance",
    ]

    def test_all_five_templates_exist(self):
        """GOAL_TEMPLATES should contain exactly 5 predefined templates."""
        self.assertEqual(len(GOAL_TEMPLATES), 5)
        for key in self.EXPECTED_KEYS:
            self.assertIn(key, GOAL_TEMPLATES)

    def test_templates_are_agent_plans(self):
        """Each template value should be an AgentPlan instance."""
        for key, plan in GOAL_TEMPLATES.items():
            self.assertIsInstance(
                plan, AgentPlan, f"Template '{key}' is not an AgentPlan"
            )

    def test_keep_system_healthy_template(self):
        """Health template should use SYSTEM_MONITOR type with 4 steps."""
        plan = GOAL_TEMPLATES["keep_system_healthy"]
        self.assertEqual(plan.agent_type, AgentType.SYSTEM_MONITOR)
        self.assertEqual(plan.agent_name, "Health Guardian")
        self.assertEqual(len(plan.steps), 4)
        self.assertEqual(plan.trigger.trigger_type, TriggerType.INTERVAL)
        self.assertEqual(plan.trigger.config["seconds"], 60)

    def test_watch_security_template(self):
        """Security template should use SECURITY_GUARD type with 3 steps."""
        plan = GOAL_TEMPLATES["watch_security"]
        self.assertEqual(plan.agent_type, AgentType.SECURITY_GUARD)
        self.assertEqual(plan.agent_name, "Security Sentinel")
        self.assertEqual(len(plan.steps), 3)
        ops = [s.operation for s in plan.steps]
        self.assertIn("security.scan_ports", ops)
        self.assertIn("security.check_firewall", ops)

    def test_notify_updates_template(self):
        """Updates template should use UPDATE_WATCHER type with 2 steps."""
        plan = GOAL_TEMPLATES["notify_updates"]
        self.assertEqual(plan.agent_type, AgentType.UPDATE_WATCHER)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.trigger.config["seconds"], 3600)

    def test_auto_cleanup_template(self):
        """Cleanup template should use CLEANUP_BOT type with 3 steps."""
        plan = GOAL_TEMPLATES["auto_cleanup"]
        self.assertEqual(plan.agent_type, AgentType.CLEANUP_BOT)
        self.assertEqual(len(plan.steps), 3)
        self.assertEqual(plan.trigger.config["seconds"], 86400)

    def test_optimize_performance_template(self):
        """Performance template should use PERFORMANCE_OPTIMIZER type with 2 steps."""
        plan = GOAL_TEMPLATES["optimize_performance"]
        self.assertEqual(plan.agent_type, AgentType.PERFORMANCE_OPTIMIZER)
        self.assertEqual(len(plan.steps), 2)
        # Second step should have MEDIUM severity
        self.assertEqual(plan.steps[1].severity, ActionSeverity.MEDIUM)

    def test_all_templates_have_nonempty_steps(self):
        """Every template should have at least one step."""
        for key, plan in GOAL_TEMPLATES.items():
            self.assertGreater(len(plan.steps), 0, f"Template '{key}' has no steps")

    def test_all_templates_have_interval_trigger(self):
        """Every template should use an INTERVAL trigger."""
        for key, plan in GOAL_TEMPLATES.items():
            self.assertEqual(
                plan.trigger.trigger_type,
                TriggerType.INTERVAL,
                f"Template '{key}' does not use INTERVAL trigger",
            )

    def test_all_templates_default_confidence(self):
        """Every template should have default confidence of 1.0."""
        for key, plan in GOAL_TEMPLATES.items():
            self.assertEqual(
                plan.confidence, 1.0, f"Template '{key}' confidence != 1.0"
            )


class TestAgentPlannerMatchTemplate(unittest.TestCase):
    """Tests for AgentPlanner._match_template keyword matching."""

    def test_match_health_keywords(self):
        """Goals with health keywords should match keep_system_healthy."""
        plan = AgentPlanner._match_template("Keep my system healthy")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.SYSTEM_MONITOR)

    def test_match_monitor_keyword(self):
        """Goal with 'monitor' should match keep_system_healthy."""
        plan = AgentPlanner._match_template("monitor my cpu and ram")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.SYSTEM_MONITOR)

    def test_match_security_keywords(self):
        """Goals with security keywords should match watch_security."""
        plan = AgentPlanner._match_template("watch for security threats")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.SECURITY_GUARD)

    def test_match_firewall_keyword(self):
        """Goal with 'firewall' should match watch_security."""
        plan = AgentPlanner._match_template("check my firewall status")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.SECURITY_GUARD)

    def test_match_update_keywords(self):
        """Goals with update keywords should match notify_updates."""
        plan = AgentPlanner._match_template("notify me about updates")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.UPDATE_WATCHER)

    def test_match_cleanup_keywords(self):
        """Goals with cleanup keywords should match auto_cleanup."""
        plan = AgentPlanner._match_template("clean up caches and temp files")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.CLEANUP_BOT)

    def test_match_performance_keywords(self):
        """Goals with performance keywords should match optimize_performance."""
        plan = AgentPlanner._match_template("optimize my system performance")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.PERFORMANCE_OPTIMIZER)

    def test_no_match_returns_none(self):
        """Goals with no matching keywords should return None."""
        plan = AgentPlanner._match_template("make me a sandwich")
        self.assertIsNone(plan)

    def test_case_insensitive_matching(self):
        """Keyword matching should be case-insensitive."""
        plan = AgentPlanner._match_template("KEEP MY SYSTEM HEALTHY")
        self.assertIsNotNone(plan)

    def test_matched_plan_uses_original_goal(self):
        """Matched plan should use the user's original goal text."""
        original = "Please monitor CPU temperature"
        plan = AgentPlanner._match_template(original)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.goal, original)

    def test_matched_plan_confidence_scoring(self):
        """Confidence should increase with more keyword matches (score * 0.3)."""
        # "cpu" and "memory" and "temperature" each match — 3 hits * 0.3 = 0.9
        plan = AgentPlanner._match_template("check cpu memory and temperature")
        self.assertIsNotNone(plan)
        self.assertGreater(plan.confidence, 0.3)

    def test_best_match_wins_among_templates(self):
        """When keywords span multiple templates, the highest-scoring one wins."""
        # "speed" matches optimize_performance; nothing else relevant here
        plan = AgentPlanner._match_template("make everything faster speed up")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.PERFORMANCE_OPTIMIZER)

    def test_confidence_capped_at_one(self):
        """Confidence should not exceed 1.0 even with many keyword matches."""
        # Many health keywords: health, healthy, monitor, cpu, memory, ram, temperature, temp
        plan = AgentPlanner._match_template(
            "health healthy monitor cpu memory ram temperature temp"
        )
        self.assertIsNotNone(plan)
        self.assertLessEqual(plan.confidence, 1.0)


class TestAgentPlannerPlanWithOllama(unittest.TestCase):
    """Tests for AgentPlanner._plan_with_ollama LLM integration."""

    def _ollama_json_response(self, data):
        """Helper to create a mock subprocess result with JSON stdout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(data)
        return mock_result

    @patch("shutil.which")
    def test_no_ollama_binary_returns_none(self, mock_which):
        """Should return None when ollama is not installed."""
        mock_which.return_value = None
        result = AgentPlanner._plan_with_ollama("some goal")
        self.assertIsNone(result)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_success(self, mock_which, mock_run):
        """Should return an AgentPlan when ollama returns valid JSON."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "CPU Watcher",
                "description": "Watches CPU usage",
                "operations": ["monitor.check_cpu", "monitor.check_memory"],
                "interval_seconds": 120,
                "settings": {"alert": True},
            }
        )
        plan = AgentPlanner._plan_with_ollama("watch my cpu")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_name, "CPU Watcher")
        self.assertEqual(plan.agent_type, AgentType.CUSTOM)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.confidence, 0.7)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_nonzero_returncode(self, mock_which, mock_run):
        """Should return None when ollama exits with non-zero returncode."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = MagicMock(returncode=1, stdout="error")
        result = AgentPlanner._plan_with_ollama("some goal")
        self.assertIsNone(result)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_timeout(self, mock_which, mock_run):
        """Should return None when ollama subprocess times out."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ollama", timeout=30)
        result = AgentPlanner._plan_with_ollama("some goal")
        self.assertIsNone(result)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_invalid_json(self, mock_which, mock_run):
        """Should return None when ollama returns non-JSON output."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = MagicMock(returncode=0, stdout="not json at all")
        result = AgentPlanner._plan_with_ollama("some goal")
        self.assertIsNone(result)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_os_error(self, mock_which, mock_run):
        """Should return None when subprocess raises OSError."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.side_effect = OSError("Permission denied")
        result = AgentPlanner._plan_with_ollama("some goal")
        self.assertIsNone(result)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_no_valid_operations(self, mock_which, mock_run):
        """Should return None when ollama returns operations not in catalog."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "Bad Agent",
                "description": "Bad",
                "operations": ["nonexistent.operation", "fake.op"],
                "interval_seconds": 60,
                "settings": {},
            }
        )
        result = AgentPlanner._plan_with_ollama("do something weird")
        self.assertIsNone(result)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_json_in_markdown_codeblock(self, mock_which, mock_run):
        """Should extract JSON from markdown code block wrapping."""
        mock_which.return_value = "/usr/bin/ollama"
        json_data = json.dumps(
            {
                "agent_name": "Extracted Agent",
                "description": "From codeblock",
                "operations": ["monitor.check_cpu"],
                "interval_seconds": 300,
                "settings": {},
            }
        )
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f"Here's the plan:\n```json\n{json_data}\n```\n",
        )
        plan = AgentPlanner._plan_with_ollama("watch cpu")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_name, "Extracted Agent")

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_interval_clamped_min(self, mock_which, mock_run):
        """Interval should be clamped to minimum 30 seconds."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "Fast Agent",
                "description": "Too fast",
                "operations": ["monitor.check_cpu"],
                "interval_seconds": 5,
                "settings": {},
            }
        )
        plan = AgentPlanner._plan_with_ollama("check cpu fast")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.trigger.config["seconds"], 30)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_interval_clamped_max(self, mock_which, mock_run):
        """Interval should be clamped to maximum 86400 seconds."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "Slow Agent",
                "description": "Too slow",
                "operations": ["monitor.check_cpu"],
                "interval_seconds": 999999,
                "settings": {},
            }
        )
        plan = AgentPlanner._plan_with_ollama("check cpu rarely")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.trigger.config["seconds"], 86400)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_name_truncated_to_60(self, mock_which, mock_run):
        """Agent name from ollama should be truncated to 60 chars."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "A" * 100,
                "description": "Long name",
                "operations": ["monitor.check_cpu"],
                "interval_seconds": 300,
                "settings": {},
            }
        )
        plan = AgentPlanner._plan_with_ollama("test")
        self.assertIsNotNone(plan)
        self.assertLessEqual(len(plan.agent_name), 60)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_description_truncated_to_200(self, mock_which, mock_run):
        """Description from ollama should be truncated to 200 chars."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "Agent",
                "description": "D" * 300,
                "operations": ["monitor.check_cpu"],
                "interval_seconds": 300,
                "settings": {},
            }
        )
        plan = AgentPlanner._plan_with_ollama("test")
        self.assertIsNotNone(plan)
        self.assertLessEqual(len(plan.description), 200)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_missing_agent_name_uses_fallback(self, mock_which, mock_run):
        """Missing agent_name should use a fallback with the goal text."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "description": "No name given",
                "operations": ["monitor.check_cpu"],
                "interval_seconds": 300,
                "settings": {},
            }
        )
        plan = AgentPlanner._plan_with_ollama("watch my stuff")
        self.assertIsNotNone(plan)
        self.assertIn("AI Agent", plan.agent_name)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_step_severity_from_catalog(self, mock_which, mock_run):
        """Steps should get severity from OPERATION_CATALOG, not hardcoded."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = self._ollama_json_response(
            {
                "agent_name": "Tuner",
                "description": "Apply tuning",
                "operations": ["tuner.apply_recommendation"],
                "interval_seconds": 300,
                "settings": {},
            }
        )
        plan = AgentPlanner._plan_with_ollama("tune performance")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.steps[0].severity, ActionSeverity.MEDIUM)

    @patch("utils.agent_planner.subprocess.run")
    @patch("shutil.which")
    def test_ollama_subprocess_called_with_timeout(self, mock_which, mock_run):
        """subprocess.run should be called with timeout=30."""
        mock_which.return_value = "/usr/bin/ollama"
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        AgentPlanner._plan_with_ollama("goal")
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs["timeout"], 30)


class TestAgentPlannerPlanFromGoal(unittest.TestCase):
    """Tests for AgentPlanner.plan_from_goal orchestration."""

    @patch.object(AgentPlanner, "_plan_with_ollama")
    @patch.object(AgentPlanner, "_match_template")
    def test_template_match_returned_first(self, mock_template, mock_ollama):
        """Should return template match without calling ollama."""
        mock_plan = MagicMock(spec=AgentPlan)
        mock_template.return_value = mock_plan
        result = AgentPlanner.plan_from_goal("keep system healthy")
        self.assertIs(result, mock_plan)
        mock_ollama.assert_not_called()

    @patch.object(AgentPlanner, "_plan_with_ollama")
    @patch.object(AgentPlanner, "_match_template")
    def test_ollama_fallback_when_no_template(self, mock_template, mock_ollama):
        """Should try ollama when template matching returns None."""
        mock_template.return_value = None
        mock_ollama_plan = MagicMock(spec=AgentPlan)
        mock_ollama.return_value = mock_ollama_plan
        result = AgentPlanner.plan_from_goal("custom goal here")
        self.assertIs(result, mock_ollama_plan)

    @patch.object(AgentPlanner, "_plan_with_ollama")
    @patch.object(AgentPlanner, "_match_template")
    def test_generic_fallback_when_both_fail(self, mock_template, mock_ollama):
        """Should return generic plan when both template and ollama fail."""
        mock_template.return_value = None
        mock_ollama.return_value = None
        result = AgentPlanner.plan_from_goal("something completely unknown")
        self.assertIsInstance(result, AgentPlan)
        self.assertEqual(result.agent_type, AgentType.CUSTOM)
        self.assertEqual(result.confidence, 0.3)

    @patch.object(AgentPlanner, "_plan_with_ollama")
    @patch.object(AgentPlanner, "_match_template")
    def test_generic_fallback_has_three_steps(self, mock_template, mock_ollama):
        """Generic fallback should have 3 monitoring steps."""
        mock_template.return_value = None
        mock_ollama.return_value = None
        result = AgentPlanner.plan_from_goal("unknown")
        self.assertEqual(len(result.steps), 3)
        ops = [s.operation for s in result.steps]
        self.assertIn("monitor.check_cpu", ops)
        self.assertIn("monitor.check_memory", ops)
        self.assertIn("monitor.check_disk", ops)

    @patch.object(AgentPlanner, "_plan_with_ollama")
    @patch.object(AgentPlanner, "_match_template")
    def test_generic_fallback_uses_original_goal(self, mock_template, mock_ollama):
        """Generic fallback should preserve the user's original goal."""
        mock_template.return_value = None
        mock_ollama.return_value = None
        goal = "do something exotic with my system"
        result = AgentPlanner.plan_from_goal(goal)
        self.assertEqual(result.goal, goal)
        self.assertIn(goal[:40], result.agent_name)

    @patch.object(AgentPlanner, "_plan_with_ollama")
    @patch.object(AgentPlanner, "_match_template")
    def test_generic_fallback_interval_300(self, mock_template, mock_ollama):
        """Generic fallback should use 300-second interval."""
        mock_template.return_value = None
        mock_ollama.return_value = None
        result = AgentPlanner.plan_from_goal("unknown")
        self.assertEqual(result.trigger.trigger_type, TriggerType.INTERVAL)
        self.assertEqual(result.trigger.config["seconds"], 300)


class TestAgentPlannerListAndCatalog(unittest.TestCase):
    """Tests for list_goal_templates and get_operation_catalog."""

    def test_list_goal_templates_returns_list(self):
        """list_goal_templates should return a list of dicts."""
        templates = AgentPlanner.list_goal_templates()
        self.assertIsInstance(templates, list)
        self.assertEqual(len(templates), 5)

    def test_list_goal_templates_dict_keys(self):
        """Each template dict should have key, goal, name, description, type."""
        templates = AgentPlanner.list_goal_templates()
        expected_keys = {"key", "goal", "name", "description", "type"}
        for t in templates:
            self.assertEqual(set(t.keys()), expected_keys)

    def test_list_goal_templates_contains_all_keys(self):
        """list_goal_templates should include all 5 template keys."""
        templates = AgentPlanner.list_goal_templates()
        keys = {t["key"] for t in templates}
        self.assertIn("keep_system_healthy", keys)
        self.assertIn("watch_security", keys)
        self.assertIn("notify_updates", keys)
        self.assertIn("auto_cleanup", keys)
        self.assertIn("optimize_performance", keys)

    def test_get_operation_catalog_returns_list(self):
        """get_operation_catalog should return a list of dicts."""
        catalog = AgentPlanner.get_operation_catalog()
        self.assertIsInstance(catalog, list)
        self.assertGreater(len(catalog), 0)

    def test_get_operation_catalog_dict_keys(self):
        """Each catalog entry should have op, desc, severity."""
        catalog = AgentPlanner.get_operation_catalog()
        for entry in catalog:
            self.assertIn("op", entry)
            self.assertIn("desc", entry)
            self.assertIn("severity", entry)

    def test_get_operation_catalog_returns_copy(self):
        """get_operation_catalog should return a copy, not the original."""
        catalog1 = AgentPlanner.get_operation_catalog()
        catalog2 = AgentPlanner.get_operation_catalog()
        self.assertIsNot(catalog1, catalog2)
        self.assertEqual(catalog1, catalog2)

    def test_get_operation_catalog_not_mutated(self):
        """Modifying the returned catalog should not affect the class variable."""
        catalog = AgentPlanner.get_operation_catalog()
        original_len = len(AgentPlanner.OPERATION_CATALOG)
        catalog.append({"op": "fake.op", "desc": "Fake", "severity": "info"})
        self.assertEqual(len(AgentPlanner.OPERATION_CATALOG), original_len)

    def test_operation_catalog_has_14_entries(self):
        """OPERATION_CATALOG should have 14 known operations."""
        self.assertEqual(len(AgentPlanner.OPERATION_CATALOG), 14)


class TestAgentPlannerIntegration(unittest.TestCase):
    """Integration-style tests for full plan_from_goal flow."""

    def test_health_goal_end_to_end(self):
        """Full flow: health goal -> template match -> valid AgentConfig."""
        plan = AgentPlanner.plan_from_goal("Keep my system healthy and monitor CPU")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.agent_type, AgentType.SYSTEM_MONITOR)
        config = plan.to_agent_config()
        self.assertIsInstance(config, AgentConfig)
        self.assertFalse(config.enabled)
        self.assertTrue(config.dry_run)
        self.assertGreater(len(config.actions), 0)

    def test_security_goal_end_to_end(self):
        """Full flow: security goal -> template match -> valid AgentConfig."""
        plan = AgentPlanner.plan_from_goal("protect my system from security threats")
        self.assertIsNotNone(plan)
        config = plan.to_agent_config()
        self.assertEqual(config.agent_type, AgentType.SECURITY_GUARD)

    @patch("shutil.which")
    def test_unknown_goal_no_ollama(self, mock_which):
        """Unknown goal without ollama -> generic fallback with 0.3 confidence."""
        mock_which.return_value = None
        plan = AgentPlanner.plan_from_goal("bake a pie with system resources")
        self.assertEqual(plan.agent_type, AgentType.CUSTOM)
        self.assertEqual(plan.confidence, 0.3)
        config = plan.to_agent_config()
        self.assertEqual(len(config.actions), 3)

    def test_plan_to_dict_is_json_serializable(self):
        """AgentPlan.to_dict() output should be JSON serializable."""
        plan = AgentPlanner.plan_from_goal("monitor system health")
        d = plan.to_dict()
        # Should not raise
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)
        roundtripped = json.loads(serialized)
        self.assertEqual(roundtripped["goal"], plan.goal)


if __name__ == "__main__":
    unittest.main()
