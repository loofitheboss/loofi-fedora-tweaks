# Prompt: P4 TEST Phase (State-File)

> Agent: test-writer | Model: GPT-4o | Cost: LABOR

ROLE: Test Writer
INPUT: `.workflow/specs/tasks-vXX.md` + changed modules/tests + AGENTS.md (test conventions)
GOAL: Validate behavior and emit test artifact.

INSTRUCTIONS:
1. Read task artifact to identify changed files.
2. Read AGENTS.md for testing rules and conventions.
3. Add/update tests for success, failure, and edge paths.
4. Follow testing patterns from AGENTS.md:
   - Framework: unittest + unittest.mock
   - Use @patch decorators ONLY (never context managers)
   - Mock: subprocess.run, subprocess.check_output, shutil.which, os.path.exists, builtins.open
   - Test both success AND failure paths
   - Test both dnf and rpm-ostree paths (where applicable)
   - Patch at module-under-test namespace: 'utils.module.subprocess.run'
5. Run test suite and summarize outcomes.
6. Write report to `.workflow/reports/test-results-vXX.json`.

TEST STRUCTURE:
```python
"""Tests for utils/module.py"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))

from utils.module import Manager

class TestManager(unittest.TestCase):
    """Tests for Manager operations."""

    @patch('utils.module.subprocess.run')
    def test_operation_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='OK')
        result = Manager.operation()
        self.assertIsNotNone(result)
        mock_run.assert_called_once()

    @patch('utils.module.subprocess.run')
    def test_operation_failure(self, mock_run):
        mock_run.side_effect = subprocess.SubprocessError("fail")
        result = Manager.operation()
        self.assertEqual(result, [])  # safe default
```

RULES:
- No root/system changes in tests (all mocked).
- Prefer existing fixtures and patterns.
- Ensure changed areas meet >=80% coverage.
- Never hardcode versions in tests (use dynamic assertions).

EXIT CRITERIA:
- [ ] Tests pass
- [ ] Coverage target met (80%+)
- [ ] Report artifact written to `.workflow/reports/test-results-vXX.json`
