"""
Tests for utils/formatting.py — shared formatting utilities.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.formatting import bytes_to_human, seconds_to_human, percent_bar, truncate


class TestBytesToHuman(unittest.TestCase):
    """Tests for bytes_to_human()."""

    def test_zero_bytes(self):
        result = bytes_to_human(0)
        self.assertEqual(result, "0.0 B")

    def test_bytes_range(self):
        result = bytes_to_human(500)
        self.assertEqual(result, "500.0 B")

    def test_kibibytes(self):
        result = bytes_to_human(1024)
        self.assertEqual(result, "1.0 KiB")

    def test_mebibytes(self):
        result = bytes_to_human(1024 * 1024)
        self.assertEqual(result, "1.0 MiB")

    def test_gibibytes(self):
        result = bytes_to_human(1024 ** 3)
        self.assertEqual(result, "1.0 GiB")

    def test_tebibytes(self):
        result = bytes_to_human(1024 ** 4)
        self.assertEqual(result, "1.0 TiB")

    def test_pebibytes(self):
        result = bytes_to_human(1024 ** 5)
        self.assertEqual(result, "1.0 PiB")

    def test_exbibytes(self):
        result = bytes_to_human(1024 ** 6)
        self.assertEqual(result, "1.0 EiB")

    def test_fractional_value(self):
        result = bytes_to_human(1536)
        self.assertEqual(result, "1.5 KiB")

    def test_negative_bytes(self):
        result = bytes_to_human(-1024)
        self.assertEqual(result, "-1.0 KiB")

    def test_custom_suffix(self):
        result = bytes_to_human(1024, suffix="b")
        self.assertEqual(result, "1.0 Kib")

    def test_large_value(self):
        result = bytes_to_human(2.5 * 1024 ** 3)
        self.assertEqual(result, "2.5 GiB")


class TestSecondsToHuman(unittest.TestCase):
    """Tests for seconds_to_human()."""

    def test_zero_seconds(self):
        result = seconds_to_human(0)
        self.assertEqual(result, "0s")

    def test_seconds_only(self):
        result = seconds_to_human(45)
        self.assertEqual(result, "45s")

    def test_minutes_and_seconds(self):
        result = seconds_to_human(125)
        self.assertEqual(result, "2m 5s")

    def test_exactly_one_minute(self):
        result = seconds_to_human(60)
        self.assertEqual(result, "1m 0s")

    def test_hours_minutes_seconds(self):
        result = seconds_to_human(3661)
        self.assertEqual(result, "1h 1m 1s")

    def test_exactly_one_hour(self):
        result = seconds_to_human(3600)
        self.assertEqual(result, "1h 0m 0s")

    def test_multiple_hours(self):
        result = seconds_to_human(7384)
        self.assertEqual(result, "2h 3m 4s")

    def test_fractional_seconds(self):
        result = seconds_to_human(30.7)
        self.assertEqual(result, "31s")

    def test_just_under_minute(self):
        result = seconds_to_human(59)
        self.assertEqual(result, "59s")


class TestPercentBar(unittest.TestCase):
    """Tests for percent_bar()."""

    def test_zero_percent(self):
        result = percent_bar(0)
        self.assertIn("0%", result)
        self.assertIn("[", result)
        self.assertIn("]", result)

    def test_100_percent(self):
        result = percent_bar(100)
        self.assertIn("100%", result)

    def test_50_percent(self):
        result = percent_bar(50)
        self.assertIn("50%", result)

    def test_custom_width(self):
        result = percent_bar(50, width=10)
        # 50% of 10 = 5 fills
        self.assertEqual(result, "[=====     ] 50%")

    def test_custom_fill_and_empty(self):
        result = percent_bar(25, width=4, fill="#", empty=".")
        self.assertEqual(result, "[#...] 25%")

    def test_default_width_full(self):
        result = percent_bar(100, width=10)
        self.assertEqual(result, "[==========] 100%")


class TestTruncate(unittest.TestCase):
    """Tests for truncate()."""

    def test_short_text_unchanged(self):
        result = truncate("hello", max_len=80)
        self.assertEqual(result, "hello")

    def test_exact_length_unchanged(self):
        text = "a" * 80
        result = truncate(text, max_len=80)
        self.assertEqual(result, text)

    def test_long_text_truncated(self):
        text = "a" * 100
        result = truncate(text, max_len=80)
        self.assertEqual(len(result), 80)
        self.assertTrue(result.endswith("..."))

    def test_custom_suffix(self):
        text = "a" * 100
        result = truncate(text, max_len=50, suffix=">>")
        self.assertTrue(result.endswith(">>"))
        self.assertEqual(len(result), 50)

    def test_empty_string(self):
        result = truncate("", max_len=80)
        self.assertEqual(result, "")

    def test_single_char_max_len(self):
        result = truncate("abcdef", max_len=4)
        self.assertEqual(len(result), 4)
        self.assertTrue(result.endswith("..."))


if __name__ == '__main__':
    unittest.main()
