"""Tests for utils/guided_tour.py"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.guided_tour import GuidedTourManager, TourStep


class TestTourStep(unittest.TestCase):
    """Tests for TourStep dataclass."""

    def test_creation(self):
        """Test TourStep can be created with all fields."""
        step = TourStep(
            widget_name="sidebar",
            title="Sidebar Nav",
            description="Browse tools here.",
            position="right",
        )
        self.assertEqual(step.widget_name, "sidebar")
        self.assertEqual(step.title, "Sidebar Nav")
        self.assertEqual(step.position, "right")


class TestGuidedTourManagerNeedsTour(unittest.TestCase):
    """Tests for GuidedTourManager.needs_tour()."""

    @patch('utils.guided_tour._TOUR_SENTINEL')
    def test_needs_tour_when_no_sentinel(self, mock_sentinel):
        """Test tour is needed when sentinel file doesn't exist."""
        mock_sentinel.exists.return_value = False

        self.assertTrue(GuidedTourManager.needs_tour())

    @patch('utils.guided_tour._TOUR_SENTINEL')
    def test_no_tour_when_sentinel_exists(self, mock_sentinel):
        """Test tour is not needed when sentinel exists."""
        mock_sentinel.exists.return_value = True

        self.assertFalse(GuidedTourManager.needs_tour())


class TestGuidedTourManagerMarkComplete(unittest.TestCase):
    """Tests for GuidedTourManager.mark_tour_complete()."""

    @patch('utils.guided_tour._TOUR_SENTINEL')
    @patch('utils.guided_tour._CONFIG_DIR')
    def test_mark_complete_creates_sentinel(self, mock_config, mock_sentinel):
        """Test marking tour complete creates the sentinel file."""
        mock_config.mkdir = MagicMock()
        mock_sentinel.touch = MagicMock()

        GuidedTourManager.mark_tour_complete()

        mock_config.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_sentinel.touch.assert_called_once()

    @patch('utils.guided_tour._TOUR_SENTINEL')
    @patch('utils.guided_tour._CONFIG_DIR')
    def test_mark_complete_handles_os_error(self, mock_config, mock_sentinel):
        """Test that OSError is handled gracefully."""
        mock_config.mkdir.side_effect = OSError("Permission denied")

        # Should not raise
        GuidedTourManager.mark_tour_complete()


class TestGuidedTourManagerResetTour(unittest.TestCase):
    """Tests for GuidedTourManager.reset_tour()."""

    @patch('utils.guided_tour._TOUR_SENTINEL')
    def test_reset_removes_sentinel(self, mock_sentinel):
        """Test resetting tour removes the sentinel file."""
        mock_sentinel.exists.return_value = True
        mock_sentinel.unlink = MagicMock()

        GuidedTourManager.reset_tour()

        mock_sentinel.unlink.assert_called_once()

    @patch('utils.guided_tour._TOUR_SENTINEL')
    def test_reset_no_op_when_no_sentinel(self, mock_sentinel):
        """Test resetting when no sentinel is a no-op."""
        mock_sentinel.exists.return_value = False

        # Should not raise
        GuidedTourManager.reset_tour()

    @patch('utils.guided_tour._TOUR_SENTINEL')
    def test_reset_handles_os_error(self, mock_sentinel):
        """Test that OSError during reset is handled gracefully."""
        mock_sentinel.exists.return_value = True
        mock_sentinel.unlink.side_effect = OSError("Permission denied")

        # Should not raise
        GuidedTourManager.reset_tour()


class TestGuidedTourManagerGetSteps(unittest.TestCase):
    """Tests for GuidedTourManager.get_tour_steps()."""

    def test_returns_list(self):
        """Test that get_tour_steps returns a list."""
        steps = GuidedTourManager.get_tour_steps()

        self.assertIsInstance(steps, list)
        self.assertGreater(len(steps), 0)

    def test_all_steps_are_tour_step(self):
        """Test all returned items are TourStep instances."""
        steps = GuidedTourManager.get_tour_steps()

        for step in steps:
            self.assertIsInstance(step, TourStep)

    def test_steps_have_required_fields(self):
        """Test all steps have non-empty required fields."""
        steps = GuidedTourManager.get_tour_steps()

        for step in steps:
            self.assertTrue(step.widget_name, f"Step missing widget_name: {step}")
            self.assertTrue(step.title, f"Step missing title: {step}")
            self.assertTrue(step.description, f"Step missing description: {step}")
            self.assertIn(step.position, ["left", "right", "above", "below"])

    def test_returns_copy(self):
        """Test that returned list is a copy."""
        steps1 = GuidedTourManager.get_tour_steps()
        steps2 = GuidedTourManager.get_tour_steps()

        self.assertIsNot(steps1, steps2)

    def test_default_steps_include_key_features(self):
        """Test default tour includes sidebar and command palette."""
        steps = GuidedTourManager.get_tour_steps()
        widget_names = [s.widget_name for s in steps]

        self.assertIn("sidebar", widget_names)
        self.assertIn("commandPalette", widget_names)


class TestGuidedTourManagerStepCount(unittest.TestCase):
    """Tests for GuidedTourManager.get_step_count()."""

    def test_step_count_matches_steps(self):
        """Test step count matches actual steps list length."""
        count = GuidedTourManager.get_step_count()
        steps = GuidedTourManager.get_tour_steps()

        self.assertEqual(count, len(steps))

    def test_step_count_positive(self):
        """Test step count is positive."""
        self.assertGreater(GuidedTourManager.get_step_count(), 0)


if __name__ == '__main__':
    unittest.main()
