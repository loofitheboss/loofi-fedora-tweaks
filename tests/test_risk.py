"""Tests for utils/risk.py — RiskRegistry and RiskLevel."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.risk import RiskLevel, RiskEntry, RiskRegistry


class TestRiskLevel(unittest.TestCase):
    """Tests for RiskLevel enum."""

    def test_values(self):
        self.assertEqual(RiskLevel.LOW.value, "low")
        self.assertEqual(RiskLevel.MEDIUM.value, "medium")
        self.assertEqual(RiskLevel.HIGH.value, "high")

    def test_all_levels(self):
        levels = list(RiskLevel)
        self.assertEqual(len(levels), 3)


class TestRiskEntry(unittest.TestCase):
    """Tests for RiskEntry dataclass."""

    def test_basic_entry(self):
        entry = RiskEntry(level=RiskLevel.LOW, description="Test action")
        self.assertEqual(entry.level, RiskLevel.LOW)
        self.assertEqual(entry.description, "Test action")
        self.assertIsNone(entry.revert_command)
        self.assertIsNone(entry.revert_description)

    def test_full_entry(self):
        entry = RiskEntry(
            level=RiskLevel.HIGH,
            description="Dangerous action",
            revert_command="undo-cmd",
            revert_description="Undo the dangerous action",
        )
        self.assertEqual(entry.level, RiskLevel.HIGH)
        self.assertEqual(entry.revert_command, "undo-cmd")
        self.assertEqual(entry.revert_description, "Undo the dangerous action")

    def test_frozen(self):
        entry = RiskEntry(level=RiskLevel.LOW, description="Test")
        with self.assertRaises(AttributeError):
            entry.level = RiskLevel.HIGH


class TestRiskRegistry(unittest.TestCase):
    """Tests for RiskRegistry singleton."""

    def test_singleton(self):
        r1 = RiskRegistry()
        r2 = RiskRegistry()
        self.assertIs(r1, r2)

    def test_get_risk_known_action(self):
        entry = RiskRegistry.get_risk("dnf_install")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.LOW)

    def test_get_risk_unknown_action(self):
        entry = RiskRegistry.get_risk("nonexistent_action_xyz")
        self.assertIsNone(entry)

    def test_get_revert_instructions(self):
        revert = RiskRegistry.get_revert_instructions("dnf_remove")
        self.assertIsNotNone(revert)
        self.assertIn("Reinstall", revert)

    def test_get_revert_instructions_none(self):
        revert = RiskRegistry.get_revert_instructions("nonexistent_xyz")
        self.assertIsNone(revert)

    def test_get_all_actions(self):
        actions = RiskRegistry.get_all_actions()
        self.assertIsInstance(actions, dict)
        self.assertGreater(len(actions), 10)

    def test_get_actions_by_level_low(self):
        low_actions = RiskRegistry.get_actions_by_level(RiskLevel.LOW)
        self.assertIsInstance(low_actions, dict)
        self.assertGreater(len(low_actions), 0)
        for entry in low_actions.values():
            self.assertEqual(entry.level, RiskLevel.LOW)

    def test_get_actions_by_level_high(self):
        high_actions = RiskRegistry.get_actions_by_level(RiskLevel.HIGH)
        self.assertIsInstance(high_actions, dict)
        self.assertGreater(len(high_actions), 0)
        for entry in high_actions.values():
            self.assertEqual(entry.level, RiskLevel.HIGH)

    # v37.0 Pinnacle — New action registrations

    def test_update_rollback_is_high(self):
        entry = RiskRegistry.get_risk("update_rollback")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.HIGH)

    def test_extension_install_is_medium(self):
        entry = RiskRegistry.get_risk("extension_install")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.MEDIUM)

    def test_flatpak_cleanup_is_low(self):
        entry = RiskRegistry.get_risk("flatpak_cleanup")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.LOW)

    def test_grub_apply_is_high(self):
        entry = RiskRegistry.get_risk("grub_apply")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.HIGH)

    def test_snapshot_create_is_low(self):
        entry = RiskRegistry.get_risk("snapshot_create")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.LOW)

    def test_snapshot_restore_is_high(self):
        entry = RiskRegistry.get_risk("snapshot_restore")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.HIGH)

    def test_snapshot_delete_is_medium(self):
        entry = RiskRegistry.get_risk("snapshot_delete")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.MEDIUM)

    def test_display_scaling_is_low(self):
        entry = RiskRegistry.get_risk("display_scaling")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, RiskLevel.LOW)

    def test_grub_set_timeout_has_revert(self):
        entry = RiskRegistry.get_risk("grub_set_timeout")
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry.revert_command)
        self.assertIsNotNone(entry.revert_description)

    def test_all_high_risk_actions_documented(self):
        """All HIGH risk actions must have a revert description."""
        high_actions = RiskRegistry.get_actions_by_level(RiskLevel.HIGH)
        for action_id, entry in high_actions.items():
            self.assertIsNotNone(
                entry.revert_description,
                f"HIGH risk action '{action_id}' missing revert_description"
            )


if __name__ == "__main__":
    unittest.main()
