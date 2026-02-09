"""
Agent Planner — AI-powered natural language agent creation.
Part of v18.0 "Sentinel".

Provides:
- Natural language goal → agent config conversion
- Predefined goal templates for common tasks
- Ollama integration for intelligent plan generation
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.agents import (
    ActionSeverity,
    AgentAction,
    AgentConfig,
    AgentTrigger,
    AgentType,
    TriggerType,
)

logger = logging.getLogger(__name__)

@dataclass
class PlanStep:
    """A single step in an agent plan."""
    step_number: int
    description: str
    operation: str
    severity: ActionSeverity = ActionSeverity.INFO

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "description": self.description,
            "operation": self.operation,
            "severity": self.severity.value,
        }

@dataclass
class AgentPlan:
    """A generated plan for an agent from a natural language goal."""
    goal: str
    agent_name: str
    description: str
    agent_type: AgentType
    steps: List[PlanStep]
    trigger: AgentTrigger
    settings: Dict[str, Any]
    confidence: float = 1.0  # 0.0 - 1.0

    def to_agent_config(self) -> AgentConfig:
        """Convert this plan into an AgentConfig."""
        actions = []
        for step in self.steps:
            actions.append(AgentAction(
                action_id=f"step_{step.step_number}",
                name=step.description[:60],
                description=step.description,
                severity=step.severity,
                operation=step.operation,
            ))

        return AgentConfig(
            agent_id="",  # Will be auto-generated
            name=self.agent_name,
            agent_type=self.agent_type,
            description=self.description,
            enabled=False,
            triggers=[self.trigger],
            actions=actions,
            settings=self.settings,
            dry_run=True,  # Start in dry-run for safety
        )

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "agent_name": self.agent_name,
            "description": self.description,
            "agent_type": self.agent_type.value,
            "steps": [s.to_dict() for s in self.steps],
            "trigger": self.trigger.to_dict(),
            "settings": self.settings,
            "confidence": self.confidence,
        }

# ==================== Goal Templates ====================

GOAL_TEMPLATES: Dict[str, AgentPlan] = {
    "keep_system_healthy": AgentPlan(
        goal="Keep my system healthy",
        agent_name="Health Guardian",
        description="Monitors CPU, RAM, disk, and temperature with alerts on anomalies",
        agent_type=AgentType.SYSTEM_MONITOR,
        steps=[
            PlanStep(1, "Check CPU load against threshold", "monitor.check_cpu"),
            PlanStep(2, "Check memory usage against threshold", "monitor.check_memory"),
            PlanStep(3, "Check disk space against threshold", "monitor.check_disk"),
            PlanStep(4, "Check CPU temperature", "monitor.check_temperature"),
        ],
        trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": 60}),
        settings={
            "cpu_threshold": 90,
            "memory_threshold": 85,
            "disk_threshold": 90,
            "temp_threshold": 80,
        },
    ),
    "watch_security": AgentPlan(
        goal="Watch for security threats",
        agent_name="Security Sentinel",
        description="Monitors open ports, failed logins, and firewall status",
        agent_type=AgentType.SECURITY_GUARD,
        steps=[
            PlanStep(1, "Scan for open network ports", "security.scan_ports"),
            PlanStep(2, "Check for failed login attempts", "security.check_failed_logins"),
            PlanStep(3, "Verify firewall is active", "security.check_firewall"),
        ],
        trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": 300}),
        settings={
            "max_failed_logins": 5,
            "alert_on_new_port": True,
        },
    ),
    "notify_updates": AgentPlan(
        goal="Notify me about updates",
        agent_name="Update Notifier",
        description="Checks for DNF and Flatpak updates hourly",
        agent_type=AgentType.UPDATE_WATCHER,
        steps=[
            PlanStep(1, "Check for DNF package updates", "updates.check_dnf"),
            PlanStep(2, "Check for Flatpak application updates", "updates.check_flatpak"),
        ],
        trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": 3600}),
        settings={
            "notify_on_security_updates": True,
            "auto_download": False,
        },
    ),
    "auto_cleanup": AgentPlan(
        goal="Automatically clean up my system",
        agent_name="Cleanup Automator",
        description="Daily cleanup of caches, journals, and temp files",
        agent_type=AgentType.CLEANUP_BOT,
        steps=[
            PlanStep(1, "Check DNF cache size", "cleanup.dnf_cache"),
            PlanStep(2, "Check journal disk usage", "cleanup.vacuum_journal"),
            PlanStep(3, "Check temp directory sizes", "cleanup.temp_files"),
        ],
        trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": 86400}),
        settings={
            "journal_retain_days": 14,
            "cache_max_age_days": 30,
        },
    ),
    "optimize_performance": AgentPlan(
        goal="Optimize system performance automatically",
        agent_name="Performance Tuner",
        description="Detects workload type and suggests CPU/memory tuning",
        agent_type=AgentType.PERFORMANCE_OPTIMIZER,
        steps=[
            PlanStep(1, "Detect current workload type", "tuner.detect_workload"),
            PlanStep(
                2,
                "Apply tuning recommendations",
                "tuner.apply_recommendation",
                ActionSeverity.MEDIUM,
            ),
        ],
        trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": 120}),
        settings={
            "auto_apply": False,
            "min_change_interval": 300,
        },
    ),
}

class AgentPlanner:
    """
    Plans agent configurations from natural language goals.

    Uses template matching first, then falls back to Ollama LLM
    for custom goal interpretation if available.
    """

    # Known operation catalog for LLM reference
    OPERATION_CATALOG: List[Dict[str, str]] = [
        {"op": "monitor.check_cpu", "desc": "Check CPU usage against threshold", "severity": "info"},
        {"op": "monitor.check_memory", "desc": "Check memory usage against threshold", "severity": "info"},
        {"op": "monitor.check_disk", "desc": "Check disk space against threshold", "severity": "info"},
        {"op": "monitor.check_temperature", "desc": "Check CPU temperature", "severity": "info"},
        {"op": "security.scan_ports", "desc": "Scan for open network ports", "severity": "info"},
        {"op": "security.check_failed_logins", "desc": "Check for failed login attempts", "severity": "info"},
        {"op": "security.check_firewall", "desc": "Verify firewall is active", "severity": "low"},
        {"op": "updates.check_dnf", "desc": "Check for DNF package updates", "severity": "info"},
        {"op": "updates.check_flatpak", "desc": "Check for Flatpak updates", "severity": "info"},
        {"op": "cleanup.dnf_cache", "desc": "Check DNF cache size", "severity": "low"},
        {"op": "cleanup.vacuum_journal", "desc": "Check journal disk usage", "severity": "low"},
        {"op": "cleanup.temp_files", "desc": "Check temp directory sizes", "severity": "low"},
        {"op": "tuner.detect_workload", "desc": "Detect current workload type", "severity": "info"},
        {"op": "tuner.apply_recommendation", "desc": "Apply performance tuning", "severity": "medium"},
    ]

    @classmethod
    def plan_from_goal(cls, goal: str) -> AgentPlan:
        """
        Generate an agent plan from a natural language goal.

        1. First tries template matching against known goals
        2. Falls back to Ollama LLM interpretation if available
        3. Returns a conservative default if neither works
        """
        # Step 1: Template matching
        template = cls._match_template(goal)
        if template:
            return template

        # Step 2: Try Ollama-based planning
        llm_plan = cls._plan_with_ollama(goal)
        if llm_plan:
            return llm_plan

        # Step 3: Fall back to a generic monitoring agent
        return AgentPlan(
            goal=goal,
            agent_name=f"Custom Agent: {goal[:40]}",
            description=f"Agent created for goal: {goal}",
            agent_type=AgentType.CUSTOM,
            steps=[
                PlanStep(1, "Check CPU load", "monitor.check_cpu"),
                PlanStep(2, "Check memory usage", "monitor.check_memory"),
                PlanStep(3, "Check disk space", "monitor.check_disk"),
            ],
            trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": 300}),
            settings={"cpu_threshold": 90, "memory_threshold": 85, "disk_threshold": 90},
            confidence=0.3,
        )

    @classmethod
    def _match_template(cls, goal: str) -> Optional[AgentPlan]:
        """Match a goal against predefined templates using keyword matching."""
        goal_lower = goal.lower()

        keyword_map = {
            "keep_system_healthy": [
                "health", "healthy", "monitor", "watch system", "system status",
                "cpu", "memory", "ram", "temperature", "temp",
            ],
            "watch_security": [
                "security", "secure", "firewall", "ports", "login",
                "intrusion", "protect", "guard", "threat",
            ],
            "notify_updates": [
                "update", "upgrade", "patch", "new version",
                "dnf update", "flatpak update",
            ],
            "auto_cleanup": [
                "clean", "cleanup", "cache", "journal", "temp",
                "free space", "disk space", "garbage",
            ],
            "optimize_performance": [
                "performance", "optimize", "fast", "speed",
                "governor", "tuning", "slow", "workload",
            ],
        }

        best_match = None
        best_score = 0

        for template_key, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > best_score:
                best_score = score
                best_match = template_key

        if best_match and best_score >= 1:
            plan = GOAL_TEMPLATES[best_match]
            # Customize the plan with the user's original goal
            return AgentPlan(
                goal=goal,
                agent_name=plan.agent_name,
                description=plan.description,
                agent_type=plan.agent_type,
                steps=plan.steps,
                trigger=plan.trigger,
                settings=plan.settings,
                confidence=min(1.0, best_score * 0.3),
            )

        return None

    @classmethod
    def _plan_with_ollama(cls, goal: str) -> Optional[AgentPlan]:
        """Use Ollama to interpret a custom goal into an agent plan."""
        import shutil

        if not shutil.which("ollama"):
            return None

        # Build the prompt
        ops_desc = "\n".join(
            f"  - {op['op']}: {op['desc']} (severity: {op['severity']})"
            for op in cls.OPERATION_CATALOG
        )

        prompt = (
            "You are a system administration agent planner. "
            "Given a user's goal, select the most relevant operations and create a plan.\n\n"
            f"Available operations:\n{ops_desc}\n\n"
            f"User's goal: \"{goal}\"\n\n"
            "Respond with ONLY a JSON object (no markdown) with these fields:\n"
            "{\n"
            '  "agent_name": "short name",\n'
            '  "description": "one-line description",\n'
            '  "operations": ["op1", "op2"],\n'
            '  "interval_seconds": 300,\n'
            '  "settings": {}\n'
            "}\n"
        )

        try:
            result = subprocess.run(
                ["ollama", "run", "llama3.2", prompt],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return None

            response = result.stdout.strip()

            # Try to extract JSON from response
            # Handle cases where LLM wraps in ```json
            if "```" in response:
                parts = response.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        response = part
                        break

            data = json.loads(response)

            # Validate operations exist
            valid_ops = {op["op"] for op in cls.OPERATION_CATALOG}
            operations = [op for op in data.get("operations", []) if op in valid_ops]

            if not operations:
                return None

            steps = []
            for i, op in enumerate(operations, 1):
                op_info = next((o for o in cls.OPERATION_CATALOG if o["op"] == op), None)
                if op_info:
                    steps.append(PlanStep(
                        step_number=i,
                        description=op_info["desc"],
                        operation=op,
                        severity=ActionSeverity(op_info["severity"]),
                    ))

            interval = max(30, min(86400, data.get("interval_seconds", 300)))

            return AgentPlan(
                goal=goal,
                agent_name=data.get("agent_name", f"AI Agent: {goal[:30]}")[:60],
                description=data.get("description", goal)[:200],
                agent_type=AgentType.CUSTOM,
                steps=steps,
                trigger=AgentTrigger(TriggerType.INTERVAL, {"seconds": interval}),
                settings=data.get("settings", {}),
                confidence=0.7,
            )

        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("Ollama planning failed: %s", exc)
            return None

    @classmethod
    def list_goal_templates(cls) -> List[Dict[str, str]]:
        """List available goal templates for the UI."""
        return [
            {
                "key": key,
                "goal": plan.goal,
                "name": plan.agent_name,
                "description": plan.description,
                "type": plan.agent_type.value,
            }
            for key, plan in GOAL_TEMPLATES.items()
        ]

    @classmethod
    def get_operation_catalog(cls) -> List[Dict[str, str]]:
        """Return the catalog of available operations."""
        return cls.OPERATION_CATALOG.copy()