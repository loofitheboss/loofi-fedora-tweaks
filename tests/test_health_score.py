"""
Tests for HealthScoreManager — v31.0 Smart UX
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.health_score import HealthScoreManager, HealthScore


class TestHealthScore(unittest.TestCase):
    """Tests for HealthScore dataclass."""

    def test_health_score_creation(self):
        """HealthScore can be created with all fields."""
        hs = HealthScore(score=85, grade="B", components={"cpu": 90}, recommendations=["test"])
        self.assertEqual(hs.score, 85)
        self.assertEqual(hs.grade, "B")
        self.assertEqual(hs.components, {"cpu": 90})
        self.assertEqual(hs.recommendations, ["test"])

    def test_health_score_color_grade_a(self):
        """Grade A returns green color."""
        hs = HealthScore(score=95, grade="A", components={}, recommendations=[])
        self.assertEqual(hs.color, "#a6e3a1")

    def test_health_score_color_grade_b(self):
        """Grade B returns teal color."""
        hs = HealthScore(score=80, grade="B", components={}, recommendations=[])
        self.assertEqual(hs.color, "#94e2d5")

    def test_health_score_color_grade_c(self):
        """Grade C returns yellow color."""
        hs = HealthScore(score=65, grade="C", components={}, recommendations=[])
        self.assertEqual(hs.color, "#f9e2af")

    def test_health_score_color_grade_d(self):
        """Grade D returns orange color."""
        hs = HealthScore(score=45, grade="D", components={}, recommendations=[])
        self.assertEqual(hs.color, "#fab387")

    def test_health_score_color_grade_f(self):
        """Grade F returns red color."""
        hs = HealthScore(score=20, grade="F", components={}, recommendations=[])
        self.assertEqual(hs.color, "#f38ba8")

    def test_health_score_default_recommendations(self):
        """HealthScore has empty recommendations by default."""
        hs = HealthScore(score=50, grade="C", components={})
        self.assertEqual(hs.recommendations, [])


class TestHealthScoreManager(unittest.TestCase):
    """Tests for HealthScoreManager."""

    def test_score_to_grade_a(self):
        """Score >= 90 is grade A."""
        self.assertEqual(HealthScoreManager._score_to_grade(90), "A")
        self.assertEqual(HealthScoreManager._score_to_grade(100), "A")

    def test_score_to_grade_b(self):
        """Score 75-89 is grade B."""
        self.assertEqual(HealthScoreManager._score_to_grade(75), "B")
        self.assertEqual(HealthScoreManager._score_to_grade(89), "B")

    def test_score_to_grade_c(self):
        """Score 60-74 is grade C."""
        self.assertEqual(HealthScoreManager._score_to_grade(60), "C")
        self.assertEqual(HealthScoreManager._score_to_grade(74), "C")

    def test_score_to_grade_d(self):
        """Score 40-59 is grade D."""
        self.assertEqual(HealthScoreManager._score_to_grade(40), "D")
        self.assertEqual(HealthScoreManager._score_to_grade(59), "D")

    def test_score_to_grade_f(self):
        """Score < 40 is grade F."""
        self.assertEqual(HealthScoreManager._score_to_grade(39), "F")
        self.assertEqual(HealthScoreManager._score_to_grade(0), "F")

    @patch('utils.health_score.SystemMonitor.get_cpu_info')
    def test_score_cpu_healthy(self, mock_cpu):
        """Low CPU usage scores high."""
        mock_cpu.return_value = MagicMock(load_percent=10.0)
        score, rec = HealthScoreManager._score_cpu()
        self.assertEqual(score, 90)
        self.assertIsNone(rec)

    @patch('utils.health_score.SystemMonitor.get_cpu_info')
    def test_score_cpu_high(self, mock_cpu):
        """High CPU usage gives recommendation."""
        mock_cpu.return_value = MagicMock(load_percent=90.0)
        score, rec = HealthScoreManager._score_cpu()
        self.assertEqual(score, 10)
        self.assertIn("CPU", rec)

    @patch('utils.health_score.SystemMonitor.get_cpu_info')
    def test_score_cpu_unavailable(self, mock_cpu):
        """Missing CPU info returns neutral score."""
        mock_cpu.return_value = None
        score, rec = HealthScoreManager._score_cpu()
        self.assertEqual(score, 50)

    @patch('utils.health_score.SystemMonitor.get_memory_info')
    def test_score_ram_healthy(self, mock_mem):
        """Low RAM usage scores high."""
        mock_mem.return_value = MagicMock(percent_used=30.0)
        score, rec = HealthScoreManager._score_ram()
        self.assertEqual(score, 70)
        self.assertIsNone(rec)

    @patch('utils.health_score.SystemMonitor.get_memory_info')
    def test_score_ram_high(self, mock_mem):
        """High RAM usage gives recommendation."""
        mock_mem.return_value = MagicMock(percent_used=90.0)
        score, rec = HealthScoreManager._score_ram()
        self.assertEqual(score, 10)
        self.assertIn("RAM", rec)

    @patch('utils.health_score.SystemMonitor.get_memory_info')
    def test_score_ram_unavailable(self, mock_mem):
        """Missing RAM info returns neutral score."""
        mock_mem.return_value = None
        score, rec = HealthScoreManager._score_ram()
        self.assertEqual(score, 50)

    @patch('utils.health_score.DiskManager.get_disk_usage')
    def test_score_disk_healthy(self, mock_disk):
        """Low disk usage scores high."""
        mock_disk.return_value = MagicMock(percent_used=40)
        score, rec = HealthScoreManager._score_disk()
        self.assertEqual(score, 60)
        self.assertIsNone(rec)

    @patch('utils.health_score.DiskManager.get_disk_usage')
    def test_score_disk_full(self, mock_disk):
        """Nearly full disk gives recommendation."""
        mock_disk.return_value = MagicMock(percent_used=95)
        score, rec = HealthScoreManager._score_disk()
        self.assertEqual(score, 5)
        self.assertIn("full", rec)

    @patch('utils.health_score.DiskManager.get_disk_usage')
    def test_score_disk_unavailable(self, mock_disk):
        """Missing disk info returns neutral score."""
        mock_disk.return_value = None
        score, rec = HealthScoreManager._score_disk()
        self.assertEqual(score, 50)

    @patch('builtins.open')
    def test_score_uptime_healthy(self, mock_open):
        """Moderate uptime scores high."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readline.return_value = "259200.0 500000.0"  # 3 days
        score, rec = HealthScoreManager._score_uptime()
        self.assertEqual(score, 100)
        self.assertIsNone(rec)

    @patch('builtins.open')
    def test_score_uptime_very_long(self, mock_open):
        """Very long uptime gives recommendation."""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readline.return_value = "3000000.0 500000.0"  # 34 days
        score, rec = HealthScoreManager._score_uptime()
        self.assertEqual(score, 60)
        self.assertIn("30 days", rec)

    @patch('builtins.open', side_effect=OSError)
    def test_score_uptime_error(self, mock_open):
        """Uptime read error returns neutral score."""
        score, rec = HealthScoreManager._score_uptime()
        self.assertEqual(score, 50)

    @patch('subprocess.run')
    def test_score_updates_none_pending(self, mock_run):
        """No updates pending scores 100."""
        mock_run.return_value = MagicMock(returncode=0)
        score, rec = HealthScoreManager._score_updates()
        self.assertEqual(score, 100)
        self.assertIsNone(rec)

    @patch('subprocess.run')
    def test_score_updates_many_pending(self, mock_run):
        """Many updates pending lowers score."""
        lines = "\n".join([f"package-{i}  1.0  updates" for i in range(60)])
        mock_run.return_value = MagicMock(returncode=100, stdout=lines)
        score, rec = HealthScoreManager._score_updates()
        self.assertEqual(score, 40)
        self.assertIn("60", rec)

    @patch('subprocess.run')
    def test_score_updates_few_pending(self, mock_run):
        """Few updates pending scores high."""
        lines = "\n".join([f"package-{i}  1.0  updates" for i in range(3)])
        mock_run.return_value = MagicMock(returncode=100, stdout=lines)
        score, rec = HealthScoreManager._score_updates()
        self.assertEqual(score, 85)

    @patch('subprocess.run', side_effect=Exception("timeout"))
    def test_score_updates_error(self, mock_run):
        """Update check error returns moderate score."""
        score, rec = HealthScoreManager._score_updates()
        self.assertEqual(score, 75)

    @patch.object(HealthScoreManager, '_score_cpu', return_value=(90, None))
    @patch.object(HealthScoreManager, '_score_ram', return_value=(80, None))
    @patch.object(HealthScoreManager, '_score_disk', return_value=(70, None))
    @patch.object(HealthScoreManager, '_score_uptime', return_value=(100, None))
    @patch.object(HealthScoreManager, '_score_updates', return_value=(100, None))
    def test_calculate_healthy_system(self, m1, m2, m3, m4, m5):
        """Calculate returns weighted score for healthy system."""
        hs = HealthScoreManager.calculate()
        self.assertIsInstance(hs, HealthScore)
        self.assertGreater(hs.score, 0)
        self.assertLessEqual(hs.score, 100)
        self.assertIn(hs.grade, ["A", "B", "C", "D", "F"])
        self.assertEqual(len(hs.recommendations), 0)

    @patch.object(HealthScoreManager, '_score_cpu', return_value=(10, "CPU high"))
    @patch.object(HealthScoreManager, '_score_ram', return_value=(10, "RAM high"))
    @patch.object(HealthScoreManager, '_score_disk', return_value=(10, "Disk full"))
    @patch.object(HealthScoreManager, '_score_uptime', return_value=(50, "Reboot"))
    @patch.object(HealthScoreManager, '_score_updates', return_value=(40, "Updates"))
    def test_calculate_unhealthy_system(self, m1, m2, m3, m4, m5):
        """Calculate returns low score with recommendations for unhealthy system."""
        hs = HealthScoreManager.calculate()
        self.assertLess(hs.score, 50)
        self.assertGreater(len(hs.recommendations), 0)

    def test_weights_sum_to_one(self):
        """All weights must sum to 1.0."""
        total = sum(HealthScoreManager.WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0)


if __name__ == '__main__':
    unittest.main()
