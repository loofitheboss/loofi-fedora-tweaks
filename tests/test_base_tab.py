"""Tests for ui/base_tab.py."""

import os
import sys
import unittest

from PyQt6.QtWidgets import QTableWidget

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from ui.base_tab import BaseTab


class TestBaseTabConfigureTable(unittest.TestCase):
    """Tests for BaseTab.configure_table."""

    def test_configure_table_sets_readable_row_height(self):
        """configure_table uses font-aware row height with safe minimum."""
        table = QTableWidget(0, 3)

        BaseTab.configure_table(table)

        metrics = table.fontMetrics()
        expected_min = max(
            44,
            metrics.height() + 20,
            metrics.boundingRect("Ag 🟢 ✅ ⚠️").height() + 20,
        )
        header = table.verticalHeader()
        self.assertEqual(header.defaultSectionSize(), expected_min)
        self.assertEqual(header.minimumSectionSize(), expected_min)

    def test_configure_table_applies_base_table_object_name(self):
        """configure_table applies base object name for QSS hooks."""
        table = QTableWidget(0, 2)

        BaseTab.configure_table(table)

        self.assertEqual(table.objectName(), "baseTable")

    def test_configure_table_keeps_static_row_resize_mode(self):
        """configure_table avoids auto-resize that can hide empty-state rows."""
        table = QTableWidget(1, 2)

        BaseTab.configure_table(table)

        self.assertEqual(table.verticalHeader().minimumSectionSize(), table.verticalHeader().defaultSectionSize())
