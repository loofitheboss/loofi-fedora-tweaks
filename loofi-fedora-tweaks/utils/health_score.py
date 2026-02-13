"""
Health Score Manager — v31.0 Smart UX
Aggregates system metrics into a single 0–100 health score.
"""

from dataclasses import dataclass, field
from typing import List

from utils.monitor import SystemMonitor
from utils.disk import DiskManager


@dataclass
class HealthScore:
    """Aggregated system health score."""
    score: int
    grade: str
    components: dict
    recommendations: List[str] = field(default_factory=list)

    @property
    def color(self) -> str:
        """Return color code based on grade."""
        return {
            "A": "#a6e3a1",
            "B": "#94e2d5",
            "C": "#f9e2af",
            "D": "#fab387",
            "F": "#f38ba8",
        }.get(self.grade, "#cdd6f4")


class HealthScoreManager:
    """Calculates a weighted system health score from multiple metrics."""

    # Weights for each component (must sum to 1.0)
    WEIGHTS = {
        "cpu": 0.25,
        "ram": 0.20,
        "disk": 0.20,
        "uptime": 0.15,
        "updates": 0.20,
    }

    @staticmethod
    def _score_cpu() -> tuple:
        """Score CPU usage (0–100, higher is better)."""
        cpu = SystemMonitor.get_cpu_info()
        if cpu is None:
            return 50, "CPU info unavailable"
        pct = min(cpu.load_percent, 100.0)
        score = max(0, 100 - pct)
        recommendation = None
        if pct >= 80:
            recommendation = "High CPU usage — consider closing background processes"
        return score, recommendation

    @staticmethod
    def _score_ram() -> tuple:
        """Score RAM usage (0–100, higher is better)."""
        mem = SystemMonitor.get_memory_info()
        if mem is None:
            return 50, "Memory info unavailable"
        pct = min(mem.percent_used, 100.0)
        score = max(0, 100 - pct)
        recommendation = None
        if pct >= 85:
            recommendation = "RAM usage is high — close unused applications"
        return score, recommendation

    @staticmethod
    def _score_disk() -> tuple:
        """Score root disk usage (0–100, higher is better)."""
        try:
            usage = DiskManager.get_disk_usage("/")
            if usage is None:
                return 50, "Disk info unavailable"
            pct = usage.percent_used if hasattr(usage, 'percent_used') else 0
            score = max(0, 100 - pct)
            recommendation = None
            if pct >= 90:
                recommendation = "Disk nearly full — run maintenance cleanup"
            elif pct >= 75:
                recommendation = "Disk usage above 75% — consider freeing space"
            return score, recommendation
        except Exception:
            return 50, None

    @staticmethod
    def _score_uptime() -> tuple:
        """Score based on uptime — moderate uptime is healthy."""
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.readline().split()[0])

            days = uptime_seconds / 86400
            # Optimal: 1-14 days. Too short = recent crash/restart. Too long = needs updates.
            if days < 0.042:  # < 1 hour
                score = 60
                recommendation = "System just started — wait for services to stabilize"
            elif days <= 14:
                score = 100
                recommendation = None
            elif days <= 30:
                score = 80
                recommendation = "Consider rebooting to apply pending updates"
            else:
                score = 60
                recommendation = "System hasn't been rebooted in over 30 days"
            return score, recommendation
        except Exception:
            return 50, None

    @staticmethod
    def _score_updates() -> tuple:
        """Score based on pending updates count."""
        try:
            import subprocess
            result = subprocess.run(
                ["dnf", "check-update", "--quiet"],
                capture_output=True, text=True, timeout=30
            )
            # dnf check-update returns exit code 100 if updates are available
            if result.returncode == 0:
                return 100, None  # No updates pending
            elif result.returncode == 100:
                lines = [line for line in result.stdout.strip().splitlines() if line.strip() and not line.startswith("Last")]
                count = len(lines)
                if count > 50:
                    score = 40
                    recommendation = f"{count} updates pending — run system update"
                elif count > 10:
                    score = 70
                    recommendation = f"{count} updates available"
                else:
                    score = 85
                    recommendation = f"{count} minor updates available"
                return score, recommendation
            else:
                return 50, None
        except Exception:
            return 75, None  # Can't check — assume moderate

    @classmethod
    def calculate(cls) -> HealthScore:
        """
        Calculate the overall system health score.

        Returns:
            HealthScore with score 0-100, grade A-F, components breakdown,
            and list of actionable recommendations.
        """
        components = {}
        recommendations = []

        scorers = {
            "cpu": cls._score_cpu,
            "ram": cls._score_ram,
            "disk": cls._score_disk,
            "uptime": cls._score_uptime,
            "updates": cls._score_updates,
        }

        weighted_total = 0.0
        for key, scorer in scorers.items():
            score, rec = scorer()
            components[key] = score
            weighted_total += score * cls.WEIGHTS[key]
            if rec:
                recommendations.append(rec)

        final_score = max(0, min(100, int(round(weighted_total))))
        grade = cls._score_to_grade(final_score)

        return HealthScore(
            score=final_score,
            grade=grade,
            components=components,
            recommendations=recommendations,
        )

    @staticmethod
    def _score_to_grade(score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 40:
            return "D"
        return "F"
