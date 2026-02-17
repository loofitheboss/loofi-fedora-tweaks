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

        self.assertEqual(
            table.verticalHeader().minimumSectionSize(),
            table.verticalHeader().defaultSectionSize(),
        )

    def test_configure_table_sets_fixed_vertical_size_policy(self):
        """configure_table keeps table height constrained in stacked layouts."""
        from PyQt6.QtWidgets import QSizePolicy

        table = QTableWidget(0, 2)

        BaseTab.configure_table(table)

        policy = table.sizePolicy()
        self.assertEqual(policy.verticalPolicy(), QSizePolicy.Policy.Fixed)
        self.assertGreater(table.height(), 0)

    def test_ensure_table_row_heights_respects_max_visible_rows_property(self):
        """ensure_table_row_heights caps table height using maxVisibleRows."""
        table = QTableWidget(0, 2)
        table.setProperty("maxVisibleRows", 2)

        BaseTab.configure_table(table)
        table.setRowCount(5)
        BaseTab.ensure_table_row_heights(table)

        row_height = table.verticalHeader().defaultSectionSize()
        max_expected = table.horizontalHeader().height() + (row_height * 2) + 64
        self.assertLessEqual(table.height(), max_expected)

    def test_configure_table_sets_default_max_visible_rows_property(self):
        """configure_table applies default visible row cap when absent."""
        table = QTableWidget(0, 2)

        BaseTab.configure_table(table)

        self.assertEqual(
            table.property("maxVisibleRows"), BaseTab._DEFAULT_TABLE_VISIBLE_ROWS
        )
