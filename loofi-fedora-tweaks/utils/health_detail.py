"""
Health Detail Manager — v47.0 UX Improvement.

Provides per-component health score breakdowns and actionable fix suggestions
with navigation targets. Extends HealthScoreManager with drill-down capability.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from utils.health_score import HealthScoreManager
from utils.log import get_logger

logger = get_logger(__name__)


@dataclass
class ComponentScore:
    """Individual health component score with context."""
    name: str
    key: str
    score: int
    weight: float
    weighted_score: float
    status: str  # "healthy", "warning", "critical"
    recommendation: Optional[str] = None


@dataclass
class HealthFix:
    """Actionable fix suggestion with navigation target."""
    title: str
    description: str
    tab_id: str
    severity: str  # "low", "medium", "high"


# Map health component keys to the tab that can address the issue
_COMPONENT_TAB_MAP: Dict[str, str] = {
    "cpu": "monitor",
    "ram": "monitor",
    "disk": "storage",
    "uptime": "maintenance",
    "updates": "software",
}

_COMPONENT_NAMES: Dict[str, str] = {
    "cpu": "CPU Usage",
    "ram": "Memory",
    "disk": "Disk Space",
    "uptime": "System Uptime",
    "updates": "Pending Updates",
}


class HealthDetailManager:
    """Provides detailed health score breakdowns and actionable fixes."""

    @staticmethod
    def get_component_scores() -> Dict[str, ComponentScore]:
        """Calculate and return per-component health scores.

        Returns:
            Dict mapping component key to ComponentScore with detailed info.
        """
        health = HealthScoreManager.calculate()
        components: Dict[str, ComponentScore] = {}

        for key, score_value in health.components.items():
            weight = HealthScoreManager.WEIGHTS.get(key, 0.0)
            weighted = score_value * weight

            if score_value >= 75:
                status = "healthy"
            elif score_value >= 50:
                status = "warning"
            else:
                status = "critical"

            recommendation = None
            for rec in health.recommendations:
                rec_lower = rec.lower()
                if key == "cpu" and "cpu" in rec_lower:
                    recommendation = rec
                    break
                elif key == "ram" and ("ram" in rec_lower or "memory" in rec_lower):
                    recommendation = rec
                    break
                elif key == "disk" and "disk" in rec_lower:
                    recommendation = rec
                    break
                elif key == "uptime" and ("uptime" in rec_lower or "reboot" in rec_lower or "started" in rec_lower):
                    recommendation = rec
                    break
                elif key == "updates" and "update" in rec_lower:
                    recommendation = rec
                    break

            components[key] = ComponentScore(
                name=_COMPONENT_NAMES.get(key, key.title()),
                key=key,
                score=score_value,
                weight=weight,
                weighted_score=weighted,
                status=status,
                recommendation=recommendation,
            )

        return components

    @staticmethod
    def get_actionable_fixes() -> List[HealthFix]:
        """Generate actionable fix suggestions based on current health.

        Returns:
            List of HealthFix objects with navigation targets, sorted by severity.
        """
        health = HealthScoreManager.calculate()
        fixes: List[HealthFix] = []

        for key, score_value in health.components.items():
            if score_value >= 75:
                continue

            tab_id = _COMPONENT_TAB_MAP.get(key, "dashboard")
            name = _COMPONENT_NAMES.get(key, key.title())

            if score_value < 50:
                severity = "high"
            else:
                severity = "medium"

            # Find matching recommendation
            description = f"{name} score is {score_value}/100"
            for rec in health.recommendations:
                rec_lower = rec.lower()
                if key in rec_lower or (key == "ram" and "memory" in rec_lower):
                    description = rec
                    break

            fixes.append(HealthFix(
                title=f"Improve {name}",
                description=description,
                tab_id=tab_id,
                severity=severity,
            ))

        severity_order = {"high": 0, "medium": 1, "low": 2}
        fixes.sort(key=lambda f: severity_order.get(f.severity, 2))
        return fixes
