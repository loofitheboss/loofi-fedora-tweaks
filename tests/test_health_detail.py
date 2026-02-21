"""Tests for utils/health_detail.py"""
import unittest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.health_detail import HealthDetailManager, ComponentScore, HealthFix
from utils.health_score import HealthScore


class TestComponentScore(unittest.TestCase):
    """Tests for ComponentScore dataclass."""

    def test_creation(self):
        """Test ComponentScore can be created with all fields."""
        cs = ComponentScore(
            name="CPU Usage", key="cpu", score=85, weight=0.25,
            weighted_score=21.25, status="healthy", recommendation=None,
        )
        self.assertEqual(cs.name, "CPU Usage")
        self.assertEqual(cs.score, 85)
        self.assertEqual(cs.status, "healthy")
        self.assertIsNone(cs.recommendation)

    def test_with_recommendation(self):
        """Test ComponentScore with a recommendation."""
        cs = ComponentScore(
            name="Disk Space", key="disk", score=30, weight=0.20,
            weighted_score=6.0, status="critical", recommendation="Disk nearly full",
        )
        self.assertEqual(cs.recommendation, "Disk nearly full")
        self.assertEqual(cs.status, "critical")


class TestHealthFix(unittest.TestCase):
    """Tests for HealthFix dataclass."""

    def test_creation(self):
        """Test HealthFix can be created."""
        fix = HealthFix(
            title="Improve Disk Space", description="Disk nearly full",
            tab_id="storage", severity="high",
        )
        self.assertEqual(fix.tab_id, "storage")
        self.assertEqual(fix.severity, "high")


class TestHealthDetailManagerComponentScores(unittest.TestCase):
    """Tests for HealthDetailManager.get_component_scores()."""

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_all_healthy(self, mock_calc):
        """Test component scores when all components are healthy."""
        mock_calc.return_value = HealthScore(
            score=90, grade="A",
            components={"cpu": 95, "ram": 90, "disk": 85, "uptime": 100, "updates": 100},
            recommendations=[],
        )

        scores = HealthDetailManager.get_component_scores()

        self.assertEqual(len(scores), 5)
        self.assertIn("cpu", scores)
        self.assertEqual(scores["cpu"].status, "healthy")
        self.assertEqual(scores["cpu"].score, 95)
        self.assertIsNone(scores["cpu"].recommendation)

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_degraded_system(self, mock_calc):
        """Test component scores with degraded components."""
        mock_calc.return_value = HealthScore(
            score=55, grade="C",
            components={"cpu": 30, "ram": 60, "disk": 40, "uptime": 80, "updates": 70},
            recommendations=["High CPU usage — consider closing background processes", "Disk nearly full — run maintenance cleanup"],
        )

        scores = HealthDetailManager.get_component_scores()

        self.assertEqual(scores["cpu"].status, "critical")
        self.assertEqual(scores["ram"].status, "warning")
        self.assertEqual(scores["disk"].status, "critical")
        self.assertEqual(scores["uptime"].status, "healthy")

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_recommendations_matched(self, mock_calc):
        """Test that recommendations are matched to components."""
        mock_calc.return_value = HealthScore(
            score=55, grade="C",
            components={"cpu": 30, "ram": 90, "disk": 40, "uptime": 80, "updates": 70},
            recommendations=["High CPU usage — consider closing background processes", "Disk nearly full — run maintenance cleanup"],
        )

        scores = HealthDetailManager.get_component_scores()

        self.assertIsNotNone(scores["cpu"].recommendation)
        self.assertIn("CPU", scores["cpu"].recommendation)
        self.assertIsNotNone(scores["disk"].recommendation)
        self.assertIn("Disk", scores["disk"].recommendation)

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_weighted_scores(self, mock_calc):
        """Test that weighted scores are calculated correctly."""
        mock_calc.return_value = HealthScore(
            score=80, grade="B",
            components={"cpu": 80, "ram": 80, "disk": 80, "uptime": 80, "updates": 80},
            recommendations=[],
        )

        scores = HealthDetailManager.get_component_scores()

        self.assertAlmostEqual(scores["cpu"].weighted_score, 80 * 0.25)
        self.assertAlmostEqual(scores["ram"].weighted_score, 80 * 0.20)


class TestHealthDetailManagerActionableFixes(unittest.TestCase):
    """Tests for HealthDetailManager.get_actionable_fixes()."""

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_no_fixes_when_healthy(self, mock_calc):
        """Test no fixes generated when all components are healthy."""
        mock_calc.return_value = HealthScore(
            score=95, grade="A",
            components={"cpu": 95, "ram": 90, "disk": 85, "uptime": 100, "updates": 100},
            recommendations=[],
        )

        fixes = HealthDetailManager.get_actionable_fixes()

        self.assertEqual(len(fixes), 0)

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_fixes_for_degraded_components(self, mock_calc):
        """Test fixes generated for degraded components."""
        mock_calc.return_value = HealthScore(
            score=40, grade="D",
            components={"cpu": 30, "ram": 90, "disk": 40, "uptime": 80, "updates": 70},
            recommendations=["High CPU usage — consider closing background processes", "Disk nearly full — run maintenance cleanup"],
        )

        fixes = HealthDetailManager.get_actionable_fixes()

        self.assertGreater(len(fixes), 0)
        tab_ids = [f.tab_id for f in fixes]
        self.assertIn("monitor", tab_ids)  # CPU fix
        self.assertIn("storage", tab_ids)  # Disk fix

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_fixes_sorted_by_severity(self, mock_calc):
        """Test fixes are sorted with high severity first."""
        mock_calc.return_value = HealthScore(
            score=35, grade="D",
            components={"cpu": 30, "ram": 60, "disk": 40, "uptime": 80, "updates": 50},
            recommendations=[],
        )

        fixes = HealthDetailManager.get_actionable_fixes()

        if len(fixes) >= 2:
            severity_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(fixes) - 1):
                self.assertLessEqual(
                    severity_order.get(fixes[i].severity, 2),
                    severity_order.get(fixes[i + 1].severity, 2),
                )

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_fix_severity_thresholds(self, mock_calc):
        """Test that severity is correctly assigned based on score."""
        mock_calc.return_value = HealthScore(
            score=50, grade="C",
            components={"cpu": 30, "ram": 60, "disk": 90, "uptime": 80, "updates": 90},
            recommendations=[],
        )

        fixes = HealthDetailManager.get_actionable_fixes()

        cpu_fix = next((f for f in fixes if f.tab_id == "monitor"), None)
        if cpu_fix:
            self.assertEqual(cpu_fix.severity, "high")  # score < 50

        ram_fix = next((f for f in fixes if "Memory" in f.title), None)
        if ram_fix:
            self.assertEqual(ram_fix.severity, "medium")  # 50 <= score < 75

    @patch('utils.health_detail.HealthScoreManager.calculate')
    def test_fix_tab_mapping(self, mock_calc):
        """Test that fixes map to correct navigation tabs."""
        mock_calc.return_value = HealthScore(
            score=30, grade="D",
            components={"cpu": 20, "ram": 20, "disk": 20, "uptime": 20, "updates": 20},
            recommendations=[],
        )

        fixes = HealthDetailManager.get_actionable_fixes()

        tab_map = {f.title: f.tab_id for f in fixes}
        if "Improve CPU Usage" in tab_map:
            self.assertEqual(tab_map["Improve CPU Usage"], "monitor")
        if "Improve Disk Space" in tab_map:
            self.assertEqual(tab_map["Improve Disk Space"], "storage")
        if "Improve Pending Updates" in tab_map:
            self.assertEqual(tab_map["Improve Pending Updates"], "software")


if __name__ == '__main__':
    unittest.main()
