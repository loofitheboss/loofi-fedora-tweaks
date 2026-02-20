"""Tests for core/executor/action_result.py — ActionResult dataclass."""
import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from core.executor.action_result import ActionResult


class TestActionResultCreation(unittest.TestCase):
    """Tests for ActionResult construction and defaults."""

    def test_default_values(self):
        result = ActionResult(success=True, message="done")
        self.assertTrue(result.success)
        self.assertEqual(result.message, "done")
        self.assertIsNone(result.exit_code)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertIsNone(result.data)
        self.assertFalse(result.preview)
        self.assertFalse(result.needs_reboot)
        self.assertEqual(result.action_id, "")

    def test_all_fields(self):
        result = ActionResult(
            success=False,
            message="failed",
            exit_code=1,
            stdout="output",
            stderr="error",
            data={"key": "val"},
            preview=True,
            needs_reboot=True,
            timestamp=123.456,
            action_id="act-001",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "output")
        self.assertEqual(result.stderr, "error")
        self.assertEqual(result.data, {"key": "val"})
        self.assertTrue(result.preview)
        self.assertTrue(result.needs_reboot)
        self.assertAlmostEqual(result.timestamp, 123.456)
        self.assertEqual(result.action_id, "act-001")

    def test_timestamp_auto_generated(self):
        before = time.time()
        result = ActionResult(success=True, message="t")
        after = time.time()
        self.assertGreaterEqual(result.timestamp, before)
        self.assertLessEqual(result.timestamp, after)


class TestActionResultToDict(unittest.TestCase):
    """Tests for to_dict serialization."""

    def test_basic_roundtrip(self):
        result = ActionResult(success=True, message="ok", exit_code=0, stdout="hi", stderr="")
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertTrue(d["success"])
        self.assertEqual(d["message"], "ok")
        self.assertEqual(d["exit_code"], 0)

    def test_truncation(self):
        long_output = "x" * 10000
        result = ActionResult(success=True, message="big", stdout=long_output, stderr=long_output)
        d = result.to_dict()
        self.assertLessEqual(len(d["stdout"]), ActionResult._MAX_OUTPUT + 100)
        self.assertLessEqual(len(d["stderr"]), ActionResult._MAX_OUTPUT + 100)


class TestActionResultFromDict(unittest.TestCase):
    """Tests for from_dict deserialization."""

    def test_roundtrip(self):
        original = ActionResult(
            success=True,
            message="roundtrip",
            exit_code=0,
            stdout="out",
            stderr="err",
            data={"x": 1},
            preview=False,
            needs_reboot=True,
            action_id="a1",
        )
        d = original.to_dict()
        restored = ActionResult.from_dict(d)
        self.assertEqual(restored.success, original.success)
        self.assertEqual(restored.message, original.message)
        self.assertEqual(restored.exit_code, original.exit_code)
        self.assertEqual(restored.stdout, original.stdout)
        self.assertEqual(restored.data, original.data)
        self.assertEqual(restored.needs_reboot, original.needs_reboot)

    def test_from_empty_dict(self):
        result = ActionResult.from_dict({})
        self.assertFalse(result.success)
        self.assertEqual(result.message, "")
        self.assertIsNone(result.exit_code)

    def test_from_partial_dict(self):
        result = ActionResult.from_dict({"success": True, "message": "partial"})
        self.assertTrue(result.success)
        self.assertEqual(result.message, "partial")
        self.assertEqual(result.stdout, "")


class TestConvenienceConstructors(unittest.TestCase):
    """Tests for ok(), fail(), and previewed() factory methods."""

    def test_ok(self):
        result = ActionResult.ok("success msg")
        self.assertTrue(result.success)
        self.assertEqual(result.message, "success msg")

    def test_ok_with_kwargs(self):
        result = ActionResult.ok("done", exit_code=0, data={"installed": True})
        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.data, {"installed": True})

    def test_fail(self):
        result = ActionResult.fail("bad")
        self.assertFalse(result.success)
        self.assertEqual(result.message, "bad")

    def test_fail_with_kwargs(self):
        result = ActionResult.fail("err", exit_code=1, stderr="crash")
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stderr, "crash")

    def test_previewed(self):
        result = ActionResult.previewed("dnf", ["install", "vim"])
        self.assertTrue(result.success)
        self.assertTrue(result.preview)
        self.assertIn("PREVIEW", result.message)
        self.assertIn("dnf install vim", result.message)
        self.assertEqual(result.data["command"], "dnf")
        self.assertEqual(result.data["args"], ["install", "vim"])


if __name__ == "__main__":
    unittest.main()
